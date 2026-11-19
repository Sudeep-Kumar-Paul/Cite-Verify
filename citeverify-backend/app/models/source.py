from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Source(Base):
    __tablename__ = "sources"
    __allow_unmapped__ = True

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(Text, nullable=False)
    authors = Column(Text, nullable=True)
    publication_year = Column(Integer, nullable=True)
    doi = Column(String(500), nullable=True)
    source_url = Column(String(2000), nullable=True)
    pdf_url = Column(String(2000), nullable=True)
    abstract = Column(Text, nullable=True)
    full_text = Column(Text, nullable=True)
    evidence_type = Column(String(50), default="metadata_only", nullable=False)
    semantic_scholar_id = Column(String(200), nullable=True)
    crossref_verified = Column(Boolean, default=False, nullable=False)
    retrieval_date = Column(DateTime(timezone=True), nullable=True)
    retrieval_error = Column(String(2000), nullable=True)

    verifications = relationship("Verification", back_populates="source")

    def __repr__(self) -> str:
        return f"<Source id={self.id} title={self.title[:50] if self.title else ''}>"
