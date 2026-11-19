from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.claim import Claim
    from app.models.citation import Citation


class Document(Base):
    __tablename__ = "documents"
    __allow_unmapped__ = True

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(500), nullable=False)
    upload_path = Column(String(1000), nullable=False)
    upload_date = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    processing_status = Column(String(50), default="uploaded", nullable=False)
    page_count = Column(Integer, nullable=True)
    extracted_text = Column(Text, nullable=True)
    body_text = Column(Text, nullable=True)
    references_text = Column(Text, nullable=True)
    document_title = Column(String(1000), nullable=True)
    is_scanned = Column(Boolean, default=False, nullable=False)
    extraction_error = Column(String(2000), nullable=True)

    claims = relationship("Claim", back_populates="document", cascade="all, delete-orphan")
    citations = relationship("Citation", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Document id={self.id} filename={self.filename} status={self.processing_status}>"
