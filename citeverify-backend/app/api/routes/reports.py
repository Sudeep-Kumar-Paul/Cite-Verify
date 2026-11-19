from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.report import ReportExportRequest, ReportSummary
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{document_id}", response_model=ReportSummary)
async def get_report_summary(document_id: str, db: Session = Depends(get_db)):
    service = ReportService()
    summary = service.generate_summary(db, document_id)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")
    return ReportSummary(**summary)


@router.post("/{document_id}/export")
async def export_report(document_id: str, request: ReportExportRequest, db: Session = Depends(get_db)):
    try:
        service = ReportService()
        report_path = service.generate_pdf_report(
            db=db,
            document_id=document_id,
            include_evidence=request.include_evidence_passages,
        )
        return {
            "document_id": document_id,
            "report_path": report_path,
            "download_url": f"/api/reports/{document_id}/download",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Report export error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Report export failed: {str(e)}")


@router.get("/{document_id}/download")
async def download_report(document_id: str, db: Session = Depends(get_db)):
    service = ReportService()
    report_path = service.get_report_path(document_id)
    if not report_path:
        raise HTTPException(
            status_code=404,
            detail=f"Report for document '{document_id}' has not been generated. Call POST /api/reports/{document_id}/export first.",
        )
    return FileResponse(
        path=report_path,
        media_type="application/pdf",
        filename=f"citeverify_report_{document_id}.pdf",
        headers={"Content-Disposition": f'attachment; filename="citeverify_report_{document_id}.pdf"'},
    )
