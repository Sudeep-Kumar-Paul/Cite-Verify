from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import DocumentNotFoundException, ProcessingException
from app.database import get_db
from app.models.claim import Claim
from app.schemas.claim import ClaimResponse, ClaimsExtractionResponse
from app.services.claim_extraction_service import ClaimExtractionService
from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{document_id}/extract-claims", response_model=ClaimsExtractionResponse)
async def extract_claims(document_id: str, db: Session = Depends(get_db)):
    try:
        gemini_service = GeminiService()
        service = ClaimExtractionService(gemini_service)
        claims = await service.extract_claims(db, document_id)
        return ClaimsExtractionResponse(
            document_id=document_id,
            claims=[ClaimResponse.model_validate(c) for c in claims],
            total_found=len(claims),
            message=f"Successfully extracted {len(claims)} claims." if claims else "No scientific claims found in text.",
        )
    except DocumentNotFoundException as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ProcessingException as e:
        raise HTTPException(status_code=422, detail=e.message)
    except Exception as e:
        logger.error(f"Claim extraction failure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Claim extraction failed: {str(e)}")


@router.get("/{document_id}/claims", response_model=List[ClaimResponse])
async def get_claims(document_id: str, db: Session = Depends(get_db)):
    claims = db.query(Claim).filter(Claim.document_id == document_id).all()
    return [ClaimResponse.model_validate(c) for c in claims]


@router.delete("/{document_id}/claims/{claim_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_claim(document_id: str, claim_id: str, db: Session = Depends(get_db)):
    service = ClaimExtractionService()
    deleted = service.delete_claim(db, claim_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found.")
