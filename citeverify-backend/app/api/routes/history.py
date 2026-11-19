from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.claim import Claim
from app.models.document import Document
from app.services.crossref_service import CrossrefService
from app.services.evidence_retrieval_service import EvidenceRetrievalService
from app.services.gemini_service import GeminiService
from app.services.paper_search_service import PaperSearchService
from app.services.report_service import ReportService
from app.services.verification_service import VerificationService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", include_in_schema=False)
@router.get("/")
async def get_history(db: Session = Depends(get_db)):
    documents = db.query(Document).order_by(Document.upload_date.desc()).all()
    history = []
    report_service = ReportService()

    for doc in documents:
        total_claims = db.query(Claim).filter(Claim.document_id == doc.id).count()
        verified_claims = db.query(Claim).filter(
            Claim.document_id == doc.id, Claim.status == "verified"
        ).count()
        has_report = report_service.get_report_path(doc.id) is not None

        history.append({
            "document_id": doc.id,
            "filename": doc.filename,
            "upload_date": doc.upload_date.isoformat() if doc.upload_date else None,
            "processing_status": doc.processing_status,
            "document_title": doc.document_title,
            "page_count": doc.page_count,
            "total_claims": total_claims,
            "verified_claims": verified_claims,
            "has_report": has_report,
        })
    return history


@router.get("/documents/{document_id}/results")
async def get_document_results(document_id: str, db: Session = Depends(get_db)):
    service = VerificationService(
        GeminiService(),
        PaperSearchService(),
        CrossrefService(),
        EvidenceRetrievalService(),
    )
    results = service.get_verification_results(db, document_id)
    return {"document_id": document_id, "results": results, "total": len(results)}
