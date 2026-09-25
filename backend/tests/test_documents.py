import pytest

from app.services.legal_chunker import chunk_legal_document
from app.services.pdf_parser import extract_pdf_text


def test_gdpr_parser_preserves_pages_and_text(gdpr_pdf):
    parsed = extract_pdf_text(gdpr_pdf)
    assert parsed["page_count"] == 88
    assert len(parsed["pages"]) == 88
    assert parsed["character_count"] > 100_000
    assert [page["page_number"] for page in parsed["pages"]] == list(range(1, 89))
    assert "72 hours" in " ".join(parsed["text"].split())


def test_upload_chunks_gdpr_into_complete_articles(client, gdpr_pdf):
    response = client.post(
        "/documents/upload",
        files={"file": ("gdpr.pdf", gdpr_pdf, "application/pdf")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["filename"] == "gdpr.pdf"
    assert body["chunking_strategy"] == "article"
    assert body["chunk_count"] == 99
    chunks = body["chunks"]
    assert [chunk["heading"] for chunk in chunks] == [
        f"Article {number}" for number in range(1, 100)
    ]
    assert len({chunk["chunk_id"] for chunk in chunks}) == 99
    for chunk in chunks:
        assert chunk["text"].startswith(chunk["heading"])
        assert len(chunk["text"]) > len(chunk["heading"])
        assert 1 <= chunk["page_start"] <= chunk["page_end"] <= body["page_count"]
    article_33 = chunks[32]
    assert "72 hours" in " ".join(article_33["text"].split())
    assert article_33["chapter"] == "CHAPTER IV"


def test_chunker_keeps_cross_page_articles_and_ignores_citation_headings():
    chunked = chunk_legal_document([
        {"page_number": 1, "text": "CHAPTER I\nArticle 1\nFirst provision.\nArticle 63.\nA citation."},
        {"page_number": 2, "text": "Continued provision.\nArticle 2\nSecond provision."},
    ])
    assert chunked["strategy"] == "article"
    assert chunked["chunk_count"] == 2
    first, second = chunked["chunks"]
    assert first["heading"] == "Article 1"
    assert "Article 63.\nA citation.\nContinued provision." in first["text"]
    assert (first["page_start"], first["page_end"]) == (1, 2)
    assert second["heading"] == "Article 2"


def test_chunker_falls_back_to_pages_without_article_headings():
    chunked = chunk_legal_document([
        {"page_number": 1, "text": ""},
        {"page_number": 2, "text": "Plain legal text."},
    ])
    assert chunked["strategy"] == "page_fallback"
    assert chunked["chunk_count"] == 1
    chunk = chunked["chunks"][0]
    assert chunk["heading"] is None
    assert chunk["text"] == "Plain legal text."
    assert (chunk["page_start"], chunk["page_end"]) == (2, 2)


@pytest.mark.parametrize("endpoint", ["/documents/upload", "/retrieval/index"])
@pytest.mark.parametrize("filename,contents", [("law.txt", b"text"), ("empty.pdf", b"")])
def test_upload_rejects_invalid_input(client, endpoint, filename, contents):
    response = client.post(endpoint, files={"file": (filename, contents)})
    assert response.status_code == 400, response.text
