from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AlignmentTier(str, Enum):
    STRONG = "STRONG"           # 80-100%: Green
    MODERATE = "MODERATE"       # 50-79%: Amber
    WEAK = "WEAK"               # 0-49%: Red
    NOT_SCOREABLE = "NOT_SCOREABLE"


def calculate_evidence_alignment_score(
    verdict: str,
    evidence_type: str,
    source_found: bool,
    doi_verified: bool = False,
    has_doi: bool = False,
    matching_status: str = "VERIFIED_MATCH",
    numerical_match: Optional[bool] = None,
    metric_mismatch: bool = False,
    unit_mismatch: bool = False,
    causation_fallacy: bool = False,
    animal_to_human_fallacy: bool = False,
    human_review_required: bool = False,
) -> Dict[str, Any]:
    """
    Transparent Evidence Alignment Score (EAS) Engine (0–100%).

    RATIONALE & FORMULA:
    --------------------
    1. Base Publication Identity (max 20 pts)
       - Verified match (Crossref/DOI/authors): 20 pts
       - Possible match: 12 pts
       - Mismatched DOI or metadata: 0 pts + penalty (-15)
       - Source not found: 0 pts

    2. Evidence Provenance & Depth (max 25 pts)
       - Full-text original paper: 25 pts
       - Abstract-only evidence: 12 pts
       - Metadata-only: 0 pts

    3. Verdict & Claim Support Degree (max 35 pts)
       - SUPPORTED: 35 pts
       - PARTIALLY_SUPPORTED: 18 pts
       - POTENTIALLY_OUTDATED / POSSIBLY_OUTDATED: 10 pts
       - UNSUPPORTED: 0 pts (capped at max 45% overall)
       - CONTRADICTORY: -15 pts (capped at max 25% overall)
       - NEEDS_HUMAN_REVIEW: Unscoreable if no evidence

    4. Deterministic Scientific & Numerical Checks (max 20 pts)
       - Numerical agreement: +10 pts
       - Numerical/metric mismatch (e.g. AUC vs accuracy): -15 pts
       - Unit mismatch (e.g. g vs mg): -20 pts
       - Causation/generalization flaw: -15 pts
       - Standard population alignment: +10 pts
    """
    v = (verdict or "").upper()
    if v == "POSSIBLY_OUTDATED":
        v = "POTENTIALLY_OUTDATED"

    # Non-scoreable conditions
    if not source_found or evidence_type == "none" or (v == "NEEDS_HUMAN_REVIEW" and evidence_type == "metadata_only"):
        return {
            "score": None,
            "percentage": None,
            "tier": AlignmentTier.NOT_SCOREABLE,
            "color": "neutral",
            "display_text": "Not scoreable — insufficient verified evidence.",
            "is_scoreable": False,
            "breakdown": {
                "publication_identity": 0,
                "evidence_provenance": 0,
                "verdict_support": 0,
                "deterministic_checks": 0,
            },
            "explanation": "Insufficient verifiable evidence retrieved from the cited publication to calculate an alignment score.",
        }

    # 1. Publication Identity
    pub_score = 0
    if matching_status in ("VERIFIED_MATCH", "matched"):
        pub_score = 20 if doi_verified else 16
    elif matching_status == "POSSIBLE_MATCH":
        pub_score = 12
    elif matching_status in ("DOI_MISMATCH", "METADATA_MISMATCH"):
        pub_score = -15
    elif has_doi:
        pub_score = 10

    # 2. Evidence Provenance
    prov_score = 0
    if evidence_type == "full_text":
        prov_score = 25
    elif evidence_type == "abstract_only":
        prov_score = 12
    elif evidence_type == "metadata_only":
        prov_score = 2

    # 3. Verdict Support
    verdict_score = 0
    if v == "SUPPORTED":
        verdict_score = 35
    elif v == "PARTIALLY_SUPPORTED":
        verdict_score = 18
    elif v == "POTENTIALLY_OUTDATED":
        verdict_score = 10
    elif v == "UNSUPPORTED":
        verdict_score = 0
    elif v == "CONTRADICTORY":
        verdict_score = -15
    elif v == "NEEDS_HUMAN_REVIEW":
        verdict_score = 5

    # 4. Deterministic Scientific Checks
    det_score = 10  # default baseline
    if numerical_match is True:
        det_score += 10
    if metric_mismatch:
        det_score -= 15
    if unit_mismatch:
        det_score -= 20
    if causation_fallacy:
        det_score -= 15
    if animal_to_human_fallacy:
        det_score -= 15

    total = pub_score + prov_score + verdict_score + det_score
    total = max(0, min(100, total))

    # Strict Cap Safeguards:
    # Contradictory evidence must NEVER receive high alignment
    if v == "CONTRADICTORY":
        total = min(25, total)
    elif v == "UNSUPPORTED":
        total = min(45, total)
    elif v in ("PARTIALLY_SUPPORTED", "POTENTIALLY_OUTDATED"):
        total = min(78, total)
    elif metric_mismatch or unit_mismatch:
        total = min(60, total)
    elif evidence_type == "abstract_only":
        total = min(78, total)

    # Determine Tier and Presentation Color
    if total >= 80:
        tier = AlignmentTier.STRONG
        color = "green"
        display_text = f"{total}% — Strong Evidence Alignment"
    elif total >= 50:
        tier = AlignmentTier.MODERATE
        color = "amber"
        display_text = f"{total}% — Moderate Evidence Alignment"
    else:
        tier = AlignmentTier.WEAK
        color = "red"
        display_text = f"{total}% — Weak Evidence Alignment"

    return {
        "score": round(total / 100.0, 3),
        "percentage": int(total),
        "tier": tier,
        "color": color,
        "display_text": display_text,
        "is_scoreable": True,
        "breakdown": {
            "publication_identity": pub_score,
            "evidence_provenance": prov_score,
            "verdict_support": verdict_score,
            "deterministic_checks": det_score,
        },
        "explanation": f"Evidence Alignment Score of {total}% calculated across publication identity ({pub_score}/20), provenance depth ({prov_score}/25), claim support ({verdict_score}/35), and deterministic scientific checks ({det_score}/20).",
    }


def calculate_confidence(
    evidence_type: str,
    verdict: str,
    has_doi: bool,
    doi_verified: bool,
    numerical_match: bool,
    source_found: bool,
    matching_status: str = "VERIFIED_MATCH",
    metric_mismatch: bool = False,
    unit_mismatch: bool = False,
) -> dict:
    """
    Backwards-compatible confidence calculation enriched with the Evidence Alignment Score.
    """
    if not source_found:
        alignment = calculate_evidence_alignment_score(
            verdict=verdict,
            evidence_type=evidence_type,
            source_found=False,
        )
        return {
            "level": ConfidenceLevel.LOW,
            "score": 0.1,
            "reason": "No source paper could be located for this claim. Human review is required.",
            "alignment": alignment,
        }

    v = (verdict or "").upper()
    if v == "NEEDS_HUMAN_REVIEW":
        alignment = calculate_evidence_alignment_score(
            verdict=v,
            evidence_type=evidence_type,
            source_found=source_found,
            doi_verified=doi_verified,
            has_doi=has_doi,
        )
        return {
            "level": ConfidenceLevel.LOW,
            "score": 0.2,
            "reason": "Verdict is NEEDS_HUMAN_REVIEW — insufficient evidence was available for automated verification.",
            "alignment": alignment,
        }

    # Base score from evidence type
    base_score = {
        "full_text": 0.75,
        "abstract_only": 0.45,
        "metadata_only": 0.15,
    }.get(evidence_type, 0.15)

    if doi_verified:
        base_score += 0.08
    elif has_doi:
        base_score += 0.04

    if numerical_match:
        base_score += 0.07

    if v == "PARTIALLY_SUPPORTED":
        base_score -= 0.05
    elif v in ("UNSUPPORTED", "CONTRADICTORY", "POSSIBLY_OUTDATED", "POTENTIALLY_OUTDATED"):
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

    alignment = calculate_evidence_alignment_score(
        verdict=v,
        evidence_type=evidence_type,
        source_found=source_found,
        doi_verified=doi_verified,
        has_doi=has_doi,
        matching_status=matching_status,
        numerical_match=numerical_match,
        metric_mismatch=metric_mismatch,
        unit_mismatch=unit_mismatch,
    )

    return {
        "level": level,
        "score": score,
        "reason": reason,
        "alignment": alignment,
    }


def aggregate_confidence_scores(scores: List[float]) -> float:
    if not scores:
        return 0.0
    return round(max(0.0, min(1.0, sum(scores) / len(scores))), 3)
