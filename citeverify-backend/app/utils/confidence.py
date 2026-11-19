from __future__ import annotations

from enum import Enum
from typing import List


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


def calculate_confidence(
    evidence_type: str,
    verdict: str,
    has_doi: bool,
    doi_verified: bool,
    numerical_match: bool,
    source_found: bool,
) -> dict:
    if not source_found:
        return {
            "level": ConfidenceLevel.LOW,
            "score": 0.1,
            "reason": "No source paper could be located for this claim. Human review is required.",
        }

    if verdict == "NEEDS_HUMAN_REVIEW":
        return {
            "level": ConfidenceLevel.LOW,
            "score": 0.2,
            "reason": "Verdict is NEEDS_HUMAN_REVIEW — insufficient evidence was available for automated verification.",
        }

    # Base score from evidence type
    base_score = {
        "full_text": 0.75,
        "abstract_only": 0.45,
        "metadata_only": 0.15,
    }.get(evidence_type, 0.15)

    # Adjustments
    if doi_verified:
        base_score += 0.08
    elif has_doi:
        base_score += 0.04

    if numerical_match:
        base_score += 0.07

    # Penalty for weaker verdicts
    if verdict == "PARTIALLY_SUPPORTED":
        base_score -= 0.05
    elif verdict in ("UNSUPPORTED", "CONTRADICTORY", "POSSIBLY_OUTDATED"):
        base_score -= 0.10

    score = round(max(0.0, min(1.0, base_score)), 3)

    if score >= 0.75:
        level = ConfidenceLevel.HIGH
        reason = (
            "High confidence: full text retrieved, DOI verified"
            + (", numerical values matched." if numerical_match else ".")
        )
    elif score >= 0.45:
        level = ConfidenceLevel.MEDIUM
        reason = (
            f"Medium confidence: based on {'abstract' if evidence_type == 'abstract_only' else 'partial evidence'}. "
            "Full paper text may contain additional context not captured here."
        )
    else:
        level = ConfidenceLevel.LOW
        reason = (
            "Low confidence: only publication metadata was available, or the evidence type "
            "was insufficient to make a reliable determination."
        )

    return {"level": level, "score": score, "reason": reason}


def aggregate_confidence_scores(scores: List[float]) -> float:
    if not scores:
        return 0.0
    return round(max(0.0, min(1.0, sum(scores) / len(scores))), 3)
