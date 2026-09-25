from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.routes.documents import (
    router as documents_router,
)
from app.routes.retrieval import (
    router as retrieval_router,
)
from app.routes.verification import (
    router as verification_router,
)
from app.services.legal_retriever import load_cached_index


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_cached_index()
    yield


app = FastAPI(
    title="LexProof API",
    description=(
        "Verify AI-generated legal claims "
        "against authoritative legal sources."
    ),
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    documents_router
)

app.include_router(
    retrieval_router
)

app.include_router(
    verification_router
)


@app.get("/")
def root():
    return {
        "name": "LexProof API",
        "version": "0.3.0",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
    }
