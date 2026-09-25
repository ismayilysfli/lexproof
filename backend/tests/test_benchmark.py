import pytest


@pytest.mark.parametrize(
    "query,expected_article",
    [
        pytest.param(
            "I have the right to get a copy of the personal data a company holds about me.",
            "Article 15",
            id="article-15",
            marks=pytest.mark.benchmark("Retrieval", "Article 15"),
        ),
        pytest.param(
            "A company must report certain personal data breaches within 72 hours.",
            "Article 33",
            id="article-33",
            marks=pytest.mark.benchmark("Retrieval", "Article 33"),
        ),
        pytest.param(
            "I can object to my personal data being used for direct marketing.",
            "Article 21",
            id="article-21",
            marks=pytest.mark.benchmark("Retrieval", "Article 21"),
        ),
        pytest.param(
            "Companies must use appropriate security measures to protect personal data.",
            "Article 32",
            id="article-32",
            marks=pytest.mark.benchmark("Retrieval", "Article 32"),
        ),
    ],
)
def test_retrieval_finds_expected_article_in_top_three(indexed_client, query, expected_article):
    response = indexed_client.post("/retrieval/search", json={"query": query, "top_k": 3})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["document"] == "gdpr.pdf"
    assert body["result_count"] == len(body["results"]) == 3
    headings = [result["heading"] for result in body["results"]]
    assert expected_article in headings, f"Expected {expected_article}; top 3: {headings}"


@pytest.mark.parametrize(
    "claim,expected_verdict,expected_article",
    [
        pytest.param(
            "A controller must notify the supervisory authority of certain personal data breaches within 72 hours where feasible.",
            "SUPPORTED", "Article 33",
            id="supported",
            marks=pytest.mark.benchmark("Verification", "SUPPORTED"),
        ),
        pytest.param(
            "A controller must report a personal data breach within 24 hours.",
            "CONTRADICTED", "Article 33",
            id="contradicted",
            marks=pytest.mark.benchmark("Verification", "CONTRADICTED"),
        ),
        pytest.param(
            "Every company must give customers a free laptop after a personal data breach.",
            "INSUFFICIENT_EVIDENCE", None,
            id="insufficient-evidence",
            marks=pytest.mark.benchmark("Verification", "INSUFFICIENT_EVIDENCE"),
        ),
    ],
)
def test_verification_verdict_and_primary_evidence(indexed_client, claim, expected_verdict, expected_article):
    response = indexed_client.post("/verify", json={"claim": claim})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["verdict"] == expected_verdict, body
    assert body["document"] == "gdpr.pdf"
    assert 0 <= body["confidence"] <= 1
    assert body["evidence"]
    primary = body["primary_evidence"]
    assert primary["text"].strip()
    assert 1 <= primary["page_start"] <= primary["page_end"] <= 88
    if expected_article is not None:
        assert primary["heading"] == expected_article, primary
