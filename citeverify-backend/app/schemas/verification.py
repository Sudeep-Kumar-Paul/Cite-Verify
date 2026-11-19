from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class EvidencePassage(BaseModel):
    text: str
    page_number: Optional[int] = None
    source_url: Optional[str] = None


class ConfidenceInfo(BaseModel):
    level: str  # HIGH, MEDIUM, LOW
    score: float
    reason: str
    alignment_score: Optional[int] = None
    alignment_tier: Optional[str] = None
    alignment_display: Optional[str] = None
    is_scoreable: bool = True


class SourceInfo(BaseModel):
    title: str
    doi: Optional[str] = None
    url: Optional[str] = None
    evidence_type: str = "metadata_only"  # full_text, abstract_only, metadata_only
    authors: Optional[List[str]] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    publisher: Optional[str] = None
    doi_url: Optional[str] = None
    matching_status: Optional[str] = "VERIFIED_MATCH"


class DirectClaimVerificationRequest(BaseModel):
    claim_text: str
    citation: Optional[str] = None
    doi: Optional[str] = None
    context: Optional[str] = None


class VerificationResult(BaseModel):
    claim_id: str
    claim_text: str
    citation_reference: Optional[str] = None
    source: Optional[SourceInfo] = None
    verdict: str
    explanation: str
    evidence_passages: List[EvidencePassage] = []
    confidence: ConfidenceInfo
    issues: List[str] = []
    human_review_required: bool = False
    alignment_score: Optional[int] = None
    alignment_tier: Optional[str] = None
    alignment_display: Optional[str] = None
    is_scoreable: bool = True
    traceability_node_id: Optional[str] = None


class VerificationRequest(BaseModel):
    document_id: str
    claim_ids: Optional[List[str]] = None
    confirmed_references: Optional[Dict[str, str]] = None


class VerificationResponse(BaseModel):
    document_id: str
    results: List[VerificationResult]
    total_claims: int
    supported: int = 0
    partially_supported: int = 0
    unsupported: int = 0
    contradictory: int = 0
    needs_human_review: int = 0
    possibly_outdated: int = 0
    traceability_graph: Optional[Dict[str, Any]] = None
    message: str
