from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DocumentCreate(BaseModel):
    filename: str


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    upload_date: datetime
    processing_status: str
    page_count: Optional[int] = None
    is_scanned: bool = False
    extraction_error: Optional[str] = None
    document_title: Optional[str] = None
    upload_path: str
    extracted_text: Optional[str] = None
    body_text: Optional[str] = None
    references_text: Optional[str] = None


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    upload_date: datetime
    processing_status: str
    page_count: Optional[int] = None
    document_title: Optional[str] = None


class ExtractionStatus(BaseModel):
    document_id: str
    status: str
    page_count: Optional[int] = None
    has_body: bool = False
    has_references: bool = False
    is_scanned: bool = False
    message: str
