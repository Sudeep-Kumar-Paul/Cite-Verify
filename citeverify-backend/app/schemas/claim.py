from __future__ import annotations

import json
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class ClaimBase(BaseModel):
    claim_text: str
    page_number: Optional[int] = None
    paragraph: Optional[str] = None
    category: Optional[str] = None
    citation_markers: List[str] = []
    extraction_explanation: Optional[str] = None


class ClaimCreate(ClaimBase):
    document_id: str


class ClaimResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    claim_text: str
    page_number: Optional[int] = None
    paragraph: Optional[str] = None
    category: Optional[str] = None
    citation_markers: List[str] = []
    extraction_explanation: Optional[str] = None
    status: str = "pending"

    @field_validator("citation_markers", mode="before")
    @classmethod
    def parse_citation_markers(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, ValueError):
                return []
        if isinstance(v, list):
            return v
        return []


class ClaimsExtractionResponse(BaseModel):
    document_id: str
    claims: List[ClaimResponse]
    total_found: int
    message: str
