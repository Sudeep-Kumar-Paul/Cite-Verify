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
    message: str
