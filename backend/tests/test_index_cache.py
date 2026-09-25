import json

import numpy as np
import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import legal_retriever


QUERY = {"query": "A company must report certain personal data breaches within 72 hours.", "top_k": 3}


@pytest.fixture
def empty_index(indexed_client, monkeypatch):
    # Reset only index state, simulating restart without reloading expensive models.
    # monkeypatch restores the session's GDPR index after each cache test.
    monkeypatch.setattr(legal_retriever, "_embeddings", None)
    monkeypatch.setattr(legal_retriever, "_title_embeddings", None)
    monkeypatch.setattr(legal_retriever, "_entries", [])
    monkeypatch.setattr(legal_retriever, "_article_titles", {})
    monkeypatch.setattr(legal_retriever, "_document_name", None)


def test_saved_index_is_restored_on_application_startup(indexed_client, index_cache_path, monkeypatch):
    before = indexed_client.post("/retrieval/search", json=QUERY)
    assert before.status_code == 200, before.text
    assert index_cache_path.is_file()
    # Simulate the empty index state of a new process, retaining loaded models.
    with monkeypatch.context() as patch:
        patch.setattr(legal_retriever, "_embeddings", None)
        patch.setattr(legal_retriever, "_title_embeddings", None)
        patch.setattr(legal_retriever, "_entries", [])
        patch.setattr(legal_retriever, "_article_titles", {})
        patch.setattr(legal_retriever, "_document_name", None)
        with TestClient(app) as restarted:
            after = restarted.post("/retrieval/search", json=QUERY)
            assert after.status_code == 200, after.text
            assert after.json() == before.json()
            # The verifier's passage retrieval uses the same restored index.
            passages = legal_retriever.search_passages(QUERY["query"], top_k=3)
            assert passages["document"] == "gdpr.pdf"
            assert "Article 33" in [item["heading"] for item in passages["results"]]


@pytest.mark.parametrize("damage", ["missing", "corrupt", "model", "version", "shape", "nonfinite"])
def test_unusable_cache_keeps_api_available_but_unindexed(
    empty_index, index_cache_path, tmp_path, monkeypatch, damage,
):
    path = tmp_path / "invalid.npz"
    if damage == "corrupt":
        path.write_bytes(b"not an index")
    elif damage != "missing":
        with np.load(index_cache_path, allow_pickle=False) as cached:
            arrays = {name: cached[name] for name in cached.files}
        metadata = json.loads(arrays["metadata"].item())
        if damage == "model":
            metadata["model"] = "incompatible-model"
        elif damage == "version":
            metadata["version"] = -1
        elif damage == "shape":
            arrays["embeddings"] = arrays["embeddings"][:-1]
        elif damage == "nonfinite":
            arrays["embeddings"][0, 0] = np.nan
        arrays["metadata"] = np.array(json.dumps(metadata))
        np.savez_compressed(path, **arrays)
    monkeypatch.setenv("LEXPROOF_INDEX_PATH", str(path))
    with TestClient(app) as restarted:
        assert restarted.get("/health").json() == {"status": "ok"}
        for endpoint, body in [
            ("/retrieval/search", QUERY),
            ("/verify", {"claim": QUERY["query"]}),
        ]:
            response = restarted.post(endpoint, json=body)
            assert response.status_code == 400, response.text
            assert response.json()["detail"] == "No document has been indexed yet."


@pytest.mark.parametrize("article_heading", [True, False], ids=["article", "page-fallback"])
def test_reindex_replaces_persisted_document(empty_index, tmp_path, monkeypatch, article_heading):
    path = tmp_path / "rebuilt.npz"
    monkeypatch.setenv("LEXPROOF_INDEX_PATH", str(path))
    with pymupdf.open() as document:
        page = document.new_page()
        heading = "Article 1\n" if article_heading else ""
        page.insert_text((72, 72), heading + "Security measures\nCompanies must protect personal data.")
        pdf = document.tobytes()
    with TestClient(app) as client:
        for filename in ("first.pdf", "replacement.pdf"):
            response = client.post(
                "/retrieval/index", files={"file": (filename, pdf, "application/pdf")},
            )
            assert response.status_code == 200, response.text
            assert response.json()["document"] == filename
            assert legal_retriever.load_cached_index()
            result = legal_retriever.search_passages("protect personal data", top_k=1)
            assert result["document"] == filename
            assert result["results"][0]["document"] == filename
    assert list(tmp_path.iterdir()) == [path], "Atomic writes must not leave temporary files"


def test_cache_write_failure_preserves_in_memory_index(empty_index, tmp_path, monkeypatch, caplog):
    blocked_parent = tmp_path / "not-a-directory"
    blocked_parent.write_text("A file cannot be used as the cache directory.")
    monkeypatch.setenv("LEXPROOF_INDEX_PATH", str(blocked_parent / "index.npz"))
    with pymupdf.open() as document:
        document.new_page().insert_text((72, 72), "Article 1\nCompanies must protect personal data.")
        pdf = document.tobytes()
    with TestClient(app) as client:
        response = client.post(
            "/retrieval/index", files={"file": ("memory.pdf", pdf, "application/pdf")},
        )
        assert response.status_code == 200, response.text
        response = client.post("/retrieval/search", json=QUERY)
        assert response.status_code == 200, response.text
        assert response.json()["document"] == "memory.pdf"
        assert response.json()["results"][0]["heading"] == "Article 1"
    assert "Unable to save retrieval index" in caplog.text
