from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.claim import Claim


class Citation(Base):
    __tablename__ = "citations"
    __allow_unmapped__ = True

    # Standardized matching states
    VERIFIED_MATCH = "VERIFIED_MATCH"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    DOI_MISMATCH = "DOI_MISMATCH"
    METADATA_MISMATCH = "METADATA_MISMATCH"
    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="SET NULL"), nullable=True)
    citation_marker = Column(String(200), nullable=False)
    reference_number = Column(Integer, nullable=True)
    authors = Column(String(1000), nullable=True)
    title = Column(Text, nullable=True)
    year = Column(Integer, nullable=True)
    journal = Column(String(500), nullable=True)
    doi = Column(String(500), nullable=True)
    raw_reference_text = Column(Text, nullable=True)
    matching_status = Column(String(50), default="unmatched", nullable=False)
    is_ambiguous = Column(Boolean, default=False, nullable=False)
    matched_reference_id = Column(String(36), nullable=True)

    document = relationship("Document", back_populates="citations")
    claim = relationship("Claim", back_populates="citations")

    def __repr__(self) -> str:
        return f"<Citation id={self.id} marker={self.citation_marker}>"
