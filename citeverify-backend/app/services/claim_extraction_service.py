from __future__ import annotations

import json
import logging
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import DocumentNotFoundException, ProcessingException
from app.models.claim import Claim
from app.models.document import Document
from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class ClaimExtractionService:

    def __init__(self, gemini_service: Optional[GeminiService] = None):
        self.gemini_service = gemini_service or GeminiService()

    async def extract_claims(self, db: Session, document_id: str) -> list[Claim]:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise DocumentNotFoundException(document_id)

        if not document.extracted_text:
            raise ProcessingException(
                message="Document has not been extracted yet.",
                detail="Please run /extract on the document before extracting claims.",
            )

        body_text = document.body_text or document.extracted_text
        raw_claims = await self.gemini_service.extract_claims(
            text=body_text,
            document_title=document.document_title or "",
        )

        if not raw_claims:
            logger.info(f"No claims extracted for document {document_id}.")
            return []

        saved_claims = []
        for raw in raw_claims:
            claim_text = raw.get("claim_text", "").strip()
            if not claim_text:
                continue

            markers = raw.get("citation_markers", [])
            markers_json = json.dumps(markers) if isinstance(markers, list) else json.dumps([])

            claim = Claim(
                id=str(uuid.uuid4()),
                document_id=document_id,
                claim_text=claim_text,
                page_number=raw.get("page_number"),
                paragraph=raw.get("paragraph"),
                category=raw.get("category", "other"),
                citation_markers=markers_json,
                extraction_explanation=raw.get("extraction_explanation"),
                status="pending",
            )
            db.add(claim)
            saved_claims.append(claim)

        db.commit()
        for c in saved_claims:
            db.refresh(c)
        logger.info(f"Saved {len(saved_claims)} claims for document {document_id}.")
        return saved_claims

    def get_claims(self, db: Session, document_id: str) -> list[Claim]:
        return db.query(Claim).filter(Claim.document_id == document_id).all()

    def delete_claim(self, db: Session, claim_id: str) -> bool:
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            return False
        db.delete(claim)
        db.commit()
        return True

    def update_claim_status(self, db: Session, claim_id: str, status: str) -> Claim:
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim {claim_id} not found")
        claim.status = status
        db.commit()
        db.refresh(claim)
        return claim
