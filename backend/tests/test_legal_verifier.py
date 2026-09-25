from app.services.legal_verifier import _evidence_candidates


def test_paragraph_candidates_keep_qualifications_and_source_metadata():
    paragraph = (
        "1. A person may object to processing. "
        "This right does not apply where processing is required by law."
    )
    passage = {
        "text": f"Right to object {paragraph} 2. The controller must respond.",
        "heading": "Article 99",
        "page_start": 3,
        "page_end": 4,
        "retrieval_score": 0.85,
    }

    candidates = _evidence_candidates(passage)

    assert candidates == [passage, {**passage, "text": paragraph}]


def test_paragraph_candidates_exclude_overlap_and_truncated_paragraphs():
    passage = {
        "text": "remaining overlap from an earlier paragraph. 2. An unfinished clause"
    }
    assert _evidence_candidates(passage) == [passage]


def test_paragraph_candidates_do_not_split_dates_or_article_references():
    passage = {
        "text": "Published 4.5.2016 under Article 6(1). Processing is permitted."
    }
    assert _evidence_candidates(passage) == [passage]
