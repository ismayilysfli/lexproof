import { useState } from "react";
import {
  evidenceKey,
  evidenceTitle,
  GDPR_SOURCE,
  getTimeComparison,
  isGdpr,
  pageLabel,
  type Evidence,
  type VerificationResult,
} from "@/lib/verification";
import { ArrowIcon, DocumentIcon, StatusIcon } from "./icons";

const VERDICTS = {
  SUPPORTED: {
    label: "Supported",
    kind: "supported",
    message: "Primary legal evidence supports this claim.",
    explanation:
      "The retrieved primary-law evidence directly supports the claim.",
  },
  CONTRADICTED: {
    label: "Contradicted",
    kind: "contradicted",
    message: "Primary legal evidence conflicts with this claim.",
    explanation:
      "The retrieved primary-law evidence conflicts with a material part of the claim.",
  },
  INSUFFICIENT_EVIDENCE: {
    label: "Insufficient evidence",
    kind: "insufficient",
    message:
      "Relevant law was found, but it does not establish or directly disprove this claim.",
    explanation:
      "Relevant provisions were found, but they do not establish or directly disprove the claim.",
  },
} as const;

function ConfidenceIndicator({ confidence }: { confidence: number }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="confidence">
      <div className="confidence-label">
        Verification confidence
        <span className="help-wrapper">
          <button
            type="button"
            className="help-button"
            aria-label="About verification confidence"
            aria-expanded={open}
            aria-controls="confidence-help"
            onClick={() => setOpen(!open)}
            onKeyDown={(event) => {
              if (event.key === "Escape") setOpen(false);
            }}
            onBlur={() => setOpen(false)}
          >
            i
          </button>
          {open && (
            <span className="help-tooltip" id="confidence-help" role="note">
              Reflects the strength of the retrieved evidence and verification
              model output. It is not a probability of legal certainty.
            </span>
          )}
        </span>
      </div>
      <span className="confidence-value">
        {Math.round(confidence * 100)}
        <span>%</span>
      </span>
    </div>
  );
}

function VerdictCard({ result }: { result: VerificationResult }) {
  const config = VERDICTS[result.verdict];
  return (
    <section
      className={`verdict-card ${config.kind}`}
      aria-labelledby="verdict-title"
    >
      <div className="verdict-main">
        <span className="eyebrow">THE VERDICT</span>
        <h2 id="verdict-title">
          <StatusIcon kind={config.kind} />
          {config.label}
        </h2>
        <p>{config.message}</p>
      </div>
      <ConfidenceIndicator confidence={result.confidence} />
    </section>
  );
}

function ClaimLawComparison({
  comparison,
}: {
  comparison: NonNullable<ReturnType<typeof getTimeComparison>>;
}) {
  return (
    <section className="claim-comparison" aria-label="Claim versus primary law">
      <div>
        <span className="eyebrow">YOUR CLAIM</span>
        <strong className="claim-time">{comparison.claim}</strong>
        <span>Stated notification deadline</span>
      </div>
      <span className="comparison-sign" role="img" aria-label="differs from">
        ≠
      </span>
      <div>
        <span className="eyebrow">
          PRIMARY LAW <span className="inline-citation">/ ARTICLE 33</span>
        </span>
        <strong>{comparison.law}</strong>
        <span>{comparison.qualification}</span>
      </div>
    </section>
  );
}

function LegalText({ text, highlight }: { text: string; highlight: boolean }) {
  if (!highlight) return <>{text}</>;
  // Highlight only text present verbatim in this passage.
  return (
    <>
      {text
        .split(/(where feasible,?\s+not later than\s+72\s+hours)/gi)
        .map((part, index) =>
          index % 2 ? <mark key={index}>{part}</mark> : part,
        )}
    </>
  );
}

function PrimaryEvidenceCard({
  evidence,
  document,
  highlight,
}: {
  evidence: Evidence;
  document: string;
  highlight: boolean;
}) {
  const knownSource = isGdpr(evidence.document ?? document);
  const title = evidenceTitle(evidence);
  const headingPrefix = [evidence.heading, title].filter(Boolean).join(" ");
  const passage =
    headingPrefix && evidence.text.startsWith(`${headingPrefix} `)
      ? evidence.text.slice(headingPrefix.length).trimStart()
      : evidence.text;
  const longText = passage.length > 850;
  // Keep a complete sentence at the preview boundary. The full returned passage stays accessible.
  const sentenceEnd = passage.indexOf(". ", 450);
  const cutoff = sentenceEnd >= 0 && sentenceEnd < 1000 ? sentenceEnd + 1 : 850;
  const preview = longText ? passage.slice(0, cutoff) : passage;
  return (
    <article className="primary-evidence" aria-labelledby="evidence-title">
      <div className="source-header">
        <div>
          <DocumentIcon />
          <span>{knownSource ? GDPR_SOURCE.name : document}</span>
          <span className="source-tag">
            {knownSource ? "Primary source" : "Indexed source"}
          </span>
        </div>
        <span className="evidence-label">PRIMARY EVIDENCE</span>
      </div>
      <div className="evidence-body">
        <div className="article-heading">
          <span className="article-number">
            {evidence.heading || "Legal provision"}
          </span>
          <span className="page-reference">{pageLabel(evidence)}</span>
        </div>
        <h3 id="evidence-title">{title || "Retrieved legal evidence"}</h3>
        <div className="evidence-metadata">
          {[evidence.chapter?.replace(/^CHAPTER/, "Chapter"), evidence.section]
            .filter(Boolean)
            .map((item) => (
              <span key={item}>{item}</span>
            ))}
        </div>
        <blockquote>
          <LegalText text={preview} highlight={highlight} />
          {longText && <span> …</span>}
        </blockquote>
        {longText && (
          <details className="full-passage">
            <summary>
              Read full evidence passage{" "}
              <span className="expand-mark" aria-hidden="true">
                +
              </span>
            </summary>
            <blockquote>
              <LegalText text={passage} highlight={highlight} />
            </blockquote>
          </details>
        )}
      </div>
      <div className="source-footer">
        <span>
          {knownSource
            ? GDPR_SOURCE.publisher
            : "Source as indexed by the verification service"}
        </span>
        {knownSource && (
          <a
            href={GDPR_SOURCE.url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="View official EUR-Lex source (opens in a new tab)"
          >
            View official source <ArrowIcon diagonal />
          </a>
        )}
      </div>
    </article>
  );
}

function EvidenceList({ result }: { result: VerificationResult }) {
  const primaryKey = evidenceKey(result.primary_evidence);
  const all = [
    ...new Map(
      [result.primary_evidence, ...result.evidence].map((item) => [
        evidenceKey(item),
        item,
      ]),
    ).values(),
  ];
  const remaining = all.filter((item) => evidenceKey(item) !== primaryKey);
  if (!remaining.length) return null;
  return (
    <details className="evidence-list">
      <summary>
        <span>
          View all evidence{" "}
          <span className="evidence-count">({all.length})</span>
        </span>
        <span className="expand-mark" aria-hidden="true">
          +
        </span>
      </summary>
      <div className="additional-evidence">
        <p>
          The primary evidence appears above. These are the other retrieved
          passages; relevance alone does not establish the claim.
        </p>
        {remaining.map((item) => (
          <article className="additional-evidence-card" key={evidenceKey(item)}>
            <div>
              <strong>{item.heading || "Legal provision"}</strong>
              <span>{pageLabel(item)}</span>
            </div>
            <h4>{evidenceTitle(item) || "Retrieved evidence"}</h4>
            <p>
              {item.text.length > 360
                ? `${item.text.slice(0, 360)}…`
                : item.text}
            </p>
            {item.text.length > 360 && (
              <details>
                <summary>Read passage</summary>
                <p>{item.text}</p>
              </details>
            )}
          </article>
        ))}
      </div>
    </details>
  );
}

function explanation(
  result: VerificationResult,
  comparison: ReturnType<typeof getTimeComparison>,
) {
  if (comparison)
    return "The claim states that notification must occur within 24 hours. Article 33 instead provides a 72-hour notification period, where feasible. The provision also includes conditions and exceptions; read the evidence below for context.";
  if (
    result.verdict === "CONTRADICTED" &&
    result.primary_evidence.heuristics?.overbroad_conflict
  )
    return "The claim presents an unconditional obligation, but the retrieved provision includes conditions or exceptions that materially limit it.";
  return VERDICTS[result.verdict].explanation;
}

export function VerificationReport({ result }: { result: VerificationResult }) {
  const comparison = getTimeComparison(result);
  return (
    <div className="verification-report result-reveal">
      <div className="report-heading">
        <span className="eyebrow">VERIFICATION REPORT</span>
        <span>
          <span className="complete-dot" />
          Analysis complete
        </span>
      </div>
      <VerdictCard result={result} />
      <div className="verified-claim">
        <span className="eyebrow">CLAIM REVIEWED</span>
        <p>{result.claim}</p>
      </div>
      {comparison && <ClaimLawComparison comparison={comparison} />}
      <section className="explanation">
        <h3>Why LexProof reached this result</h3>
        <p>{explanation(result, comparison)}</p>
      </section>
      <PrimaryEvidenceCard
        evidence={result.primary_evidence}
        document={result.document}
        highlight={!!comparison}
      />
      <EvidenceList result={result} />
      <p className="result-notice">{result.notice}</p>
    </div>
  );
}
