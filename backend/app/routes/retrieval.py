from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.services.legal_chunker import chunk_legal_document
from app.services.legal_retriever import (
    index_chunks,
    search_index,
)
from app.services.pdf_parser import extract_pdf_text


router = APIRouter(
    prefix="/retrieval",
    tags=["Retrieval"],
)


MAX_FILE_SIZE = 20 * 1024 * 1024


class SearchRequest(BaseModel):
    query: str = Field(
        min_length=2,
        max_length=1000,
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
    )


@router.post("/index")
async def index_document(
    file: UploadFile = File(...)
):
    filename = file.filename or ""

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    contents = await file.read()

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="Uploaded PDF is empty.",
        )

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="PDF is too large.",
        )

    try:
        parsed = extract_pdf_text(contents)

        chunked = chunk_legal_document(
            parsed["pages"]
        )

        indexed = index_chunks(
            chunks=chunked["chunks"],
            document_name=filename,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Indexing failed: {str(exc)}",
        )

    return {
        "filename": filename,
        "page_count": parsed["page_count"],
        "chunking_strategy": chunked["strategy"],
        **indexed,
    }


@router.post("/search")
def search(request: SearchRequest):
    try:
        return search_index(
            query=request.query,
            top_k=request.top_k,
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )
