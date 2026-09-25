import re
from typing import Dict, List

import torch
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
)

from app.services.legal_retriever import search_passages


MODEL_NAME = (
    "MoritzLaurer/"
    "multilingual-MiniLMv2-L6-mnli-xnli"
)

_tokenizer = None
_nli_model = None


TIME_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*"
    r"(hours?|days?|weeks?|months?|years?)\b",
    re.IGNORECASE,
)


ABSOLUTE_TERMS = [
    "always",
    "never",
    "every",
    "without exception",
    "in all cases",
    "regardless of",
    "həmişə",
    "heç vaxt",
    "istisnasız",
    "bütün hallarda",
]


CONDITIONAL_MARKERS = [
    "unless",
    "except",
    "only if",
    "where one of the following",
    "shall not apply",
    "does not apply",
    "where feasible",
    "subject to",
    "provided that",
]


def _get_nli_model():
    global _tokenizer
    global _nli_model

    if _tokenizer is None:
        _tokenizer = AutoTokenizer.from_pretrained(
            MODEL_NAME
        )

    if _nli_model is None:
        _nli_model = (
            AutoModelForSequenceClassification
            .from_pretrained(MODEL_NAME)
        )

        _nli_model.eval()

    return _tokenizer, _nli_model


def _predict_nli(
    premise: str,
    hypothesis: str,
) -> Dict:
    tokenizer, model = _get_nli_model()

    encoded = tokenizer(
        premise,
        hypothesis,
        return_tensors="pt",
        truncation=True,
        max_length=512,
    )

    with torch.no_grad():
        logits = model(
            **encoded
        ).logits[0]

    probabilities = torch.softmax(
        logits,
        dim=-1,
    )

    scores = {
        "entailment": 0.0,
        "neutral": 0.0,
        "contradiction": 0.0,
    }

    for index, probability in enumerate(
        probabilities
    ):
        label = model.config.id2label[
            index
        ].lower()

        if label in scores:
            scores[label] = float(
                probability
            )

    return scores


def _extract_times(text: str) -> List:
    results = []

    for match in TIME_PATTERN.finditer(text):
        value = float(match.group(1))

        unit = match.group(2).lower()

        if unit.endswith("s"):
            unit = unit[:-1]

        results.append(
            (value, unit)
        )

    return results


def _has_time_conflict(
    claim: str,
    evidence: str,
) -> bool:
    claim_times = _extract_times(claim)
    evidence_times = _extract_times(evidence)

    if not claim_times or not evidence_times:
        return False

    for claim_value, claim_unit in claim_times:
        same_unit_values = [
            evidence_value
            for evidence_value, evidence_unit
            in evidence_times
            if evidence_unit == claim_unit
        ]

        if (
            same_unit_values
            and claim_value not in same_unit_values
        ):
            return True

    return False


def _looks_overbroad(
    claim: str,
    evidence: str,
) -> bool:
    claim_lower = claim.lower()
    evidence_lower = evidence.lower()

    has_absolute_term = any(
        term in claim_lower
        for term in ABSOLUTE_TERMS
    )

    has_condition = any(
        marker in evidence_lower
        for marker in CONDITIONAL_MARKERS
    )

    return (
        has_absolute_term
        and has_condition
    )


def _prepare_evidence(
    result: Dict,
) -> str:
    title = result.get("title") or ""
    text = result.get("text") or ""

    if title:
        return f"{title}. {text}"

    return text


def _evidence_candidates(result: Dict) -> List[Dict]:
    """Keep passage context and also evaluate intact numbered paragraphs."""
    text = result.get("text") or ""
    candidates = [result]
    starts = list(re.finditer(r"(?<!\S)\d+\.(?=\s+[A-Z]|\s*$)", text))

    for start, following in zip(starts, starts[1:]):
        end = following.start()
        paragraph = text[start.start():end].strip()
        body = text[start.end():end].strip()
        # Require the next paragraph marker: a window can end at a sentence
        # boundary before a paragraph's qualifications. Keep all its sentences.
        if body and body.endswith((".", "!", "?")) and paragraph != text:
            candidates.append({**result, "text": paragraph})

    return candidates


def verify_claim(
    claim: str,
    retrieval_k: int = 8,
) -> Dict:
    retrieval = search_passages(
        query=claim,
        top_k=retrieval_k,
    )

    evaluated = []

    candidates = [
        candidate
        for result in retrieval["results"]
        for candidate in _evidence_candidates(result)
    ]

    for result in candidates:
        premise = _prepare_evidence(
            result
        )

        nli = _predict_nli(
            premise=premise,
            hypothesis=claim,
        )

        time_conflict = _has_time_conflict(
            claim,
            premise,
        )

        overbroad = _looks_overbroad(
            claim,
            premise,
        )

        raw_entailment = nli["entailment"]
        raw_neutral = nli["neutral"]
        raw_contradiction = nli[
            "contradiction"
        ]

        entailment = raw_entailment
        neutral = raw_neutral
        contradiction = raw_contradiction

        retrieval_score = float(
            result["retrieval_score"]
        )

        # Explicit numerical/time disagreement is
        # strong contradiction evidence.
        if time_conflict:
            contradiction = max(
                contradiction,
                0.92,
            )

            entailment = min(
                entailment,
                0.08,
            )

        # Words such as "always", "never", and "every"
        # are NOT enough by themselves to prove a
        # contradiction. Only apply this heuristic when
        # the evidence already substantially supports
        # the core proposition and is highly relevant.
        overbroad_conflict = (
            overbroad
            and raw_entailment >= 0.45
            and retrieval_score >= 0.84
        )

        if overbroad_conflict:
            contradiction = max(
                contradiction,
                0.72,
            )

            entailment = min(
                entailment,
                0.35,
            )

        relevance_weight = (
            0.65
            + 0.35 * retrieval_score
        )

        support_score = (
            entailment
            * relevance_weight
        )

        contradiction_score = (
            contradiction
            * relevance_weight
        )

        evaluated.append({
            **result,
            "nli": {
                "entailment": round(
                    entailment,
                    4,
                ),
                "neutral": round(
                    neutral,
                    4,
                ),
                "contradiction": round(
                    contradiction,
                    4,
                ),
            },
            "heuristics": {
                "time_conflict": time_conflict,
                "overbroad_claim": overbroad,
                "overbroad_conflict": overbroad_conflict,
            },
            "support_score": round(
                support_score,
                4,
            ),
            "contradiction_score": round(
                contradiction_score,
                4,
            ),
        })

    best_support = max(
        evaluated,
        key=lambda item: item[
            "support_score"
        ],
    )

    best_contradiction = max(
        evaluated,
        key=lambda item: item[
            "contradiction_score"
        ],
    )

    support_score = best_support[
        "support_score"
    ]

    contradiction_score = (
        best_contradiction[
            "contradiction_score"
        ]
    )

    if (
        support_score >= 0.62
        and support_score
        >= contradiction_score + 0.08
    ):
        verdict = "SUPPORTED"
        confidence = support_score
        primary = best_support

    elif (
        contradiction_score >= 0.62
        and contradiction_score
        >= support_score + 0.08
    ):
        verdict = "CONTRADICTED"
        confidence = contradiction_score
        primary = best_contradiction

    else:
        verdict = "INSUFFICIENT_EVIDENCE"

        primary = max(
            evaluated,
            key=lambda item: item[
                "retrieval_score"
            ],
        )

        neutral_candidates = []

        for item in evaluated:
            retrieval_score = float(
                item["retrieval_score"]
            )

            relevance_weight = (
                0.65
                + 0.35 * retrieval_score
            )

            neutral_score = (
                item["nli"]["neutral"]
                * relevance_weight
            )

            neutral_candidates.append(
                neutral_score
            )

        confidence = max(
            neutral_candidates
        )

    ranked_evidence = sorted(
        evaluated,
        key=lambda item: max(
            item["support_score"],
            item["contradiction_score"],
        ),
        reverse=True,
    )

    primary_evidence = {
        "document": primary.get(
            "document"
        ),
        "heading": primary.get(
            "heading"
        ),
        "title": primary.get(
            "title"
        ),
        "chapter": primary.get(
            "chapter"
        ),
        "section": primary.get(
            "section"
        ),
        "page_start": primary.get(
            "page_start"
        ),
        "page_end": primary.get(
            "page_end"
        ),
        "text": primary.get(
            "text"
        ),
        "retrieval_score": primary.get(
            "retrieval_score"
        ),
        "nli": primary.get(
            "nli"
        ),
        "heuristics": primary.get(
            "heuristics"
        ),
    }

    return {
        "claim": claim,
        "verdict": verdict,
        "confidence": round(
            confidence,
            4,
        ),
        "document": retrieval[
            "document"
        ],
        "verification_model": MODEL_NAME,
        "primary_evidence": primary_evidence,
        "evidence": ranked_evidence[:5],
        "notice": (
            "Automated evidence analysis. "
            "Not legal advice."
        ),
    }



