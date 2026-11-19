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
        raw_claims = []
        try:
            raw_claims = await self.gemini_service.extract_claims(
                text=body_text,
                document_title=document.document_title or "",
            )
        except Exception as e:
            logger.warning(f"AI claim extraction unavailable or timed out ({e}). Using deterministic extraction fallback.")

        if not raw_claims:
            raw_claims = self._extract_deterministic_claims(body_text)

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

    def _extract_deterministic_claims(self, text: str) -> list[dict]:
        """
        Deterministic rule-based scientific claim extractor.
        Identifies sentences with citation markers and empirical scientific findings.
        """
        import re
        claims = []
        if not text:
            return claims

        citation_re = re.compile(
            r'(\[\d+(?:[,\s–-]+\d+)*\]|\([A-Z][a-zA-Z\s]+(?:et al\.?)?,?\s*(?:19|20)\d{2}\))'
        )
        finding_re = re.compile(
            r'\b(?:demonstrated|achieved|reduced|increased|found|showed|outperformed|reported|observed|concluded|indicated|improved|correlated|associated|synthesized|exhibited|accuracy|auc|p\s*[<=]|%)\b',
            re.IGNORECASE,
        )

        paragraphs = text.split("\n\n")
        para_idx = 0

        for para in paragraphs:
            para = para.strip()
            if not para or len(para) < 30:
                continue
            para_idx += 1

            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < 25:
                    continue

                markers = citation_re.findall(sentence)
                has_finding = bool(finding_re.search(sentence))

                if markers or has_finding:
                    clean_text = sentence.replace("\n", " ").strip()
                    claims.append({
                        "claim_text": clean_text,
                        "citation_markers": markers,
                        "page_number": max(1, para_idx // 4),
                        "paragraph": para_idx,
                        "category": "finding" if has_finding else "methodology",
                        "extraction_explanation": f"Extracted via deterministic scientific claim analysis with citation markers {markers}." if markers else "Extracted empirical quantitative finding.",
                    })

                if len(claims) >= 15:
                    break
            if len(claims) >= 15:
                break

        return claims

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
