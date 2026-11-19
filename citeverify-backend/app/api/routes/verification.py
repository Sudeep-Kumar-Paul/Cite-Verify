from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.exceptions import ExternalAPIException
from app.database import get_db
from app.schemas.verification import (
    ConfidenceInfo,
    DirectClaimVerificationRequest,
    EvidencePassage,
    SourceInfo,
    VerificationRequest,
    VerificationResponse,
    VerificationResult,
)
from app.services.crossref_service import CrossrefService
from app.services.evidence_retrieval_service import EvidenceRetrievalService
from app.services.gemini_service import GeminiService
from app.services.paper_search_service import PaperSearchService
from app.services.verification_service import VerificationService

logger = logging.getLogger(__name__)
router = APIRouter()


def _build_response(document_id: str, results_dicts: list[dict]) -> VerificationResponse:
    counts = {
        "supported": 0,
        "partially_supported": 0,
        "unsupported": 0,
        "contradictory": 0,
        "needs_human_review": 0,
        "possibly_outdated": 0,
    }
    result_objects = []
    for rd in results_dicts:
        verdict = rd.get("verdict", "NEEDS_HUMAN_REVIEW")
        key = verdict.lower()
        if key in counts:
            counts[key] += 1

        source_info = None
        if rd.get("source"):
            source_info = SourceInfo(**rd["source"])

        evidence_passages = [EvidencePassage(**p) for p in rd.get("evidence_passages", [])]
        confidence = ConfidenceInfo(**rd["confidence"])

        result_objects.append(
            VerificationResult(
                claim_id=rd["claim_id"],
                claim_text=rd["claim_text"],
                citation_reference=rd.get("citation_reference"),
                source=source_info,
                verdict=verdict,
                explanation=rd.get("explanation", ""),
                evidence_passages=evidence_passages,
                confidence=confidence,
                issues=rd.get("issues", []),
                human_review_required=rd.get("human_review_required", False),
            )
        )

    return VerificationResponse(
        document_id=document_id,
        results=result_objects,
        total_claims=len(result_objects),
        **counts,
        message=f"Verification complete: {len(result_objects)} claims verified.",
    )


@router.post("/verify-claim", response_model=VerificationResult)
@router.post("/verify-statement", response_model=VerificationResult)
async def verify_claim_endpoint(
    request: DirectClaimVerificationRequest,
    db: Session = Depends(get_db),
):
    if not request.claim_text or not request.claim_text.strip():
        raise HTTPException(status_code=422, detail="claim_text cannot be empty.")
    try:
        service = VerificationService()
        result_dict = await service.verify_direct_claim(
            db=db,
            claim_text=request.claim_text,
            citation_str=request.citation,
            doi_str=request.doi,
            context=request.context,
        )
        source_info = None
        if result_dict.get("source"):
            source_info = SourceInfo(**result_dict["source"])
        evidence_passages = [EvidencePassage(**p) for p in result_dict.get("evidence_passages", [])]
        confidence = ConfidenceInfo(**result_dict["confidence"])

        return VerificationResult(
            claim_id=result_dict["claim_id"],
            claim_text=result_dict["claim_text"],
            citation_reference=result_dict.get("citation_reference"),
            source=source_info,
            verdict=result_dict.get("verdict", "NEEDS_HUMAN_REVIEW"),
            explanation=result_dict.get("explanation", ""),
            evidence_passages=evidence_passages,
            confidence=confidence,
            issues=result_dict.get("issues", []),
            human_review_required=result_dict.get("human_review_required", False),
        )
    except Exception as e:
        logger.error(f"Direct verification error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Claim verification failed: {str(e)}")


@router.post("/run", response_model=VerificationResponse)
async def run_verification(request: VerificationRequest, db: Session = Depends(get_db)):
    try:
        gemini_service = GeminiService()
        paper_search = PaperSearchService()
        crossref = CrossrefService()
        evidence = EvidenceRetrievalService()
        service = VerificationService(gemini_service, paper_search, crossref, evidence)

        verifications = await service.run_verification(
            db=db,
            document_id=request.document_id,
            claim_ids=request.claim_ids,
            confirmed_references=request.confirmed_references,
        )

        results_dicts = []
        for v in verifications:
            results_dicts.append(service.build_result_dict(v, v.claim, v.source))

        return _build_response(request.document_id, results_dicts)

    except ExternalAPIException as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Verification run failure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")


@router.get("/documents/{document_id}/results", response_model=VerificationResponse)
async def get_verification_results(document_id: str, db: Session = Depends(get_db)):
    try:
        gemini_service = GeminiService()
        paper_search = PaperSearchService()
        crossref = CrossrefService()
        evidence = EvidenceRetrievalService()
        service = VerificationService(gemini_service, paper_search, crossref, evidence)

        results_dicts = service.get_verification_results(db, document_id)
        return _build_response(document_id, results_dicts)
    except Exception as e:
        logger.error(f"Get verification results failure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
