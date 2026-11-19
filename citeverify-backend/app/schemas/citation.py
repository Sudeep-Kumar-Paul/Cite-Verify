from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class CitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    claim_id: Optional[str] = None
    citation_marker: str
    reference_number: Optional[int] = None
    authors: Optional[str] = None
    title: Optional[str] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    raw_reference_text: Optional[str] = None
    matching_status: str = "unmatched"
    is_ambiguous: bool = False


class CitationsExtractionResponse(BaseModel):
    document_id: str
    citations: List[CitationResponse]
    total_found: int
    matched_count: int
    unmatched_count: int
    ambiguous_count: int
    message: str
