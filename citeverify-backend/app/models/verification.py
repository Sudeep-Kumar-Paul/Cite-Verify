from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.claim import Claim
    from app.models.source import Source


class Verification(Base):
    __tablename__ = "verifications"
    __allow_unmapped__ = True

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    source_id = Column(String(36), ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    verdict = Column(String(50), nullable=False)
    explanation = Column(Text, nullable=True)
    evidence_passages = Column(Text, nullable=True)
    confidence_level = Column(String(20), default="LOW", nullable=False)
    confidence_score = Column(Float, nullable=True)
    confidence_reason = Column(Text, nullable=True)
    issues = Column(Text, nullable=True)
    limitations = Column(Text, nullable=True)
    human_review_required = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    claim = relationship("Claim", back_populates="verifications")
    source = relationship("Source", back_populates="verifications")

    def __repr__(self) -> str:
        return f"<Verification id={self.id} verdict={self.verdict}>"
