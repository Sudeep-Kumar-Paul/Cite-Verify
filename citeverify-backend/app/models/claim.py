from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.verification import Verification


class Claim(Base):
    __tablename__ = "claims"
    __allow_unmapped__ = True

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    claim_text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    paragraph = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    citation_markers = Column(Text, nullable=True)
    extraction_explanation = Column(Text, nullable=True)
    status = Column(String(50), default="pending", nullable=False)

    document = relationship("Document", back_populates="claims")
    citations = relationship("Citation", back_populates="claim")
    verifications = relationship("Verification", back_populates="claim", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Claim id={self.id} status={self.status}>"
