from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.exceptions import DocumentNotFoundException
from app.database import get_db
from app.models.citation import Citation
from app.schemas.citation import CitationResponse, CitationsExtractionResponse
from app.services.citation_extraction_service import CitationExtractionService
from app.services.gemini_service import GeminiService
from app.services.reference_matching_service import ReferenceMatchingService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{document_id}/extract-citations", response_model=CitationsExtractionResponse)
async def extract_citations(document_id: str, db: Session = Depends(get_db)):
    try:
        gemini = GeminiService()
        service = CitationExtractionService()
        await service.extract_all_citations(db, document_id, gemini_service=gemini)
        
        citations_db = db.query(Citation).filter(Citation.document_id == document_id).all()
        matched = sum(1 for c in citations_db if c.matching_status == "matched")
        unmatched = sum(1 for c in citations_db if c.matching_status == "unmatched")
        ambiguous = sum(1 for c in citations_db if c.matching_status == "ambiguous")

        return CitationsExtractionResponse(
            document_id=document_id,
            citations=[CitationResponse.model_validate(c) for c in citations_db],
            total_found=len(citations_db),
            matched_count=matched,
            unmatched_count=unmatched,
            ambiguous_count=ambiguous,
            message=f"Extracted {len(citations_db)} citations and bibliography entries.",
        )
    except DocumentNotFoundException as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        logger.error(f"Citation extraction failure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Citation extraction failed: {str(e)}")


@router.get("/{document_id}/citations", response_model=List[CitationResponse])
async def get_citations(document_id: str, db: Session = Depends(get_db)):
    citations = db.query(Citation).filter(Citation.document_id == document_id).all()
    return [CitationResponse.model_validate(c) for c in citations]


@router.post("/{document_id}/match-citations")
async def match_citations(document_id: str, db: Session = Depends(get_db)):
    try:
        ref_service = ReferenceMatchingService()
        match_result = ref_service.match_all_citations(db, document_id)
        association_count = ref_service.associate_citations_with_claims(db, document_id)
        return {
            "document_id": document_id,
            "matching_results": match_result,
            "claim_associations_created": association_count,
            "message": (
                f"Reference matching complete: {match_result['matched']} matched, "
                f"{match_result['ambiguous']} ambiguous, {match_result['unmatched']} unmatched."
            ),
        }
    except Exception as e:
        logger.error(f"Citation matching failure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Citation matching failed: {str(e)}")
