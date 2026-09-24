from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.pdf_parser import extract_pdf_text
from app.services.legal_chunker import chunk_legal_document


router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)


MAX_FILE_SIZE = 20 * 1024 * 1024


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...)
):
    filename = file.filename or ""

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are currently supported."
        )

    contents = await file.read()

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="Uploaded PDF is empty."
        )

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="PDF is too large. Maximum size is 20 MB."
        )

    try:
        parsed = extract_pdf_text(contents)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to parse PDF: {str(exc)}"
        )

    if not parsed["text"].strip():
        raise HTTPException(
            status_code=422,
            detail=(
                "No readable text was found in this PDF. "
                "The document may be scanned or image-based."
            )
        )

    chunking = chunk_legal_document(parsed["pages"])

    return {
        "filename": filename,
        "content_type": file.content_type,
        "page_count": parsed["page_count"],
        "character_count": parsed["character_count"],
        "chunking_strategy": chunking["strategy"],
        "chunk_count": chunking["chunk_count"],
        "chunks": chunking["chunks"],
    }
