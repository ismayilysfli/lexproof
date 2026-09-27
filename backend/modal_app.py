import os
import modal

APP_NAME = "lexproof-api"

EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
VERIFICATION_MODEL = "MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli"

INDEX_PATH = "/data/indexes/retrieval.npz"
GDPR_PATH = "/data/test-laws/gdpr.pdf"


def download_models():
    from sentence_transformers import SentenceTransformer
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    SentenceTransformer(EMBEDDING_MODEL)

    AutoTokenizer.from_pretrained(VERIFICATION_MODEL)
    AutoModelForSequenceClassification.from_pretrained(
        VERIFICATION_MODEL
    )

    print("LexProof models cached successfully.")


image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_requirements("backend/requirements.txt")
    .run_function(
        download_models,
        timeout=1800,
        memory=4096,
    )
    .add_local_dir(
        "backend/app",
        "/root/app",
        copy=True,
    )
    .add_local_dir(
        "data",
        "/data",
        copy=True,
    )
    .env({
        "LEXPROOF_INDEX_PATH": INDEX_PATH,
    })
)

app = modal.App(APP_NAME)


@app.function(
    image=image,
    cpu=2,
    memory=4096,
    timeout=300,
    startup_timeout=600,
    max_containers=2,
    scaledown_window=600,
)
@modal.asgi_app()
def lexproof_api():
    # Set explicitly before importing LexProof services.
    os.environ["LEXPROOF_INDEX_PATH"] = INDEX_PATH

    from app.services.legal_retriever import (
        index_chunks,
        load_cached_index,
    )

    print("LexProof index path:", INDEX_PATH)
    print("Index file exists:", os.path.exists(INDEX_PATH))
    print("GDPR PDF exists:", os.path.exists(GDPR_PATH))

    restored = load_cached_index()

    if restored:
        print("LexProof retrieval index restored successfully.")

    else:
        print(
            "Cached index could not be restored. "
            "Rebuilding GDPR index automatically..."
        )

        if not os.path.exists(GDPR_PATH):
            raise RuntimeError(
                f"GDPR source PDF missing at {GDPR_PATH}"
            )

        from app.services.pdf_parser import extract_pdf_text
        from app.services.legal_chunker import chunk_legal_document

        with open(GDPR_PATH, "rb") as file:
            pdf_bytes = file.read()

        parsed = extract_pdf_text(pdf_bytes)

        chunked = chunk_legal_document(
            parsed["pages"]
        )

        result = index_chunks(
            chunks=chunked["chunks"],
            document_name="gdpr.pdf",
        )

        print(
            "GDPR index rebuilt successfully:",
            result,
        )

    from app.main import app as fastapi_app

    return fastapi_app
