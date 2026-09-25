from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.legal_verifier import (
    verify_claim,
)


router = APIRouter(
    tags=["Verification"],
)


class VerifyRequest(BaseModel):
    claim: str = Field(
        min_length=3,
        max_length=1000,
    )

    retrieval_k: int = Field(
        default=8,
        ge=3,
        le=15,
    )


@router.post("/verify")
def verify(
    request: VerifyRequest,
):
    try:
        return verify_claim(
            claim=request.claim,
            retrieval_k=request.retrieval_k,
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Verification failed: "
                f"{str(exc)}"
            ),
        )
