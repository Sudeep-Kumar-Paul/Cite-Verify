from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ClaimSummary(BaseModel):
    claim_id: str
    claim_text: str
    verdict: str
    confidence_level: str
    human_review_required: bool


class ReportSummary(BaseModel):
    document_id: str
    document_title: Optional[str] = None
    filename: str
    total_claims: int
    total_citations: int
    matched_references: int
    supported_count: int
    partially_supported_count: int
    unsupported_count: int
    contradictory_count: int
    needs_review_count: int
    possibly_outdated_count: int
    claim_summaries: List[ClaimSummary]
    generated_at: datetime


class ReportExportRequest(BaseModel):
    document_id: Optional[str] = None
    include_evidence_passages: bool = True
    include_source_metadata: bool = True
