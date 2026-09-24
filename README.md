# LexProof

LexProof verifies AI-generated legal claims against authoritative legal sources.

## Architecture

- Frontend: Next.js + TypeScript + Tailwind
- Backend: FastAPI + Python
- Legal document parsing: PyMuPDF
- Retrieval / embeddings: coming next
- Claim verification: coming next

## Development

Frontend:

    cd frontend
    npm run dev

Backend:

    cd backend
    .\.venv\Scripts\Activate.ps1
    uvicorn app.main:app --reload
