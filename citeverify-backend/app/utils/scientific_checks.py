from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple


# Regex patterns for scientific metrics, numbers, and units
PERCENT_RE = re.compile(r'(\d+(?:\.\d+)?)\s*(?:%|percent(?:age)?)', re.IGNORECASE)
NUMBER_RE = re.compile(r'\b\d+(?:\.\d+)?\b')
AUC_RE = re.compile(
    r'\b(?:auc|auroc|roc|area under (?:the )?(?:receiver operating )?(?:characteristic )?curve)\b',
    re.IGNORECASE
)
ACCURACY_RE = re.compile(r'\b(?:accuracy|diagnostic accuracy)\b', re.IGNORECASE)
P_VALUE_RE = re.compile(r'\bp\s*(?:<|>|=)\s*(0\.\d+)', re.IGNORECASE)

ANIMAL_TERMS = {
    "mice", "mouse", "murine", "rat", "rats", "rodent", "rodents",
    "in vitro", "in vivo (mice)", "zebrafish", "drosophila", "primate model"
}

HUMAN_TERMS = {
    "human", "humans", "patients", "participants", "adults", "children",
    "clinical cohort", "men", "women", "population"
}

CAUSAL_CLAIM_VERBS = {
    "causes", "caused", "causing", "eliminates", "eliminated", "cures",
    "leads to", "prevents", "eradicates", "proves"
}

CORRELATION_TERMS = {
    "associated with", "correlated with", "linked to", "observed in",
    "risk factor", "co-occurs", "statistical relationship"
}

INCREASE_TERMS = {"increase", "increases", "increased", "increasing", "higher", "elevation", "elevated", "gain"}
DECREASE_TERMS = {"decrease", "decreases", "decreased", "decreasing", "lower", "reduction", "reduced", "lowered", "drop"}


class ScientificChecker:
    """
    Deterministic scientific check engine to cross-verify claims against source evidence text.
    Catches metric mismatches (e.g. AUC vs accuracy), numerical exaggeration, unit errors,
    causation vs correlation fallacies, and animal-to-human overgeneralizations.
    """

    @staticmethod
    def extract_numbers(text: str) -> List[float]:
        if not text:
            return []
        numbers = []
        for match in NUMBER_RE.finditer(text):
            try:
                numbers.append(float(match.group(0)))
            except ValueError:
                continue
        return numbers

    @staticmethod
    def extract_percentages(text: str) -> List[float]:
        if not text:
            return []
        percentages = []
        for match in PERCENT_RE.finditer(text):
            try:
                percentages.append(float(match.group(1)))
            except ValueError:
                continue
        return percentages

    @classmethod
    def check_metric_mismatch(cls, claim_text: str, evidence_text: str) -> Dict[str, Any]:
        """
        Detects if claim cites accuracy/percentage when source only provides AUC/ROC/F1.
        E.g., Gulshan et al: claim cites 94.5% accuracy while evidence provides AUC 0.991.
        """
        claim_lower = claim_text.lower()
        ev_lower = evidence_text.lower()

        claim_has_accuracy = bool(re.search(r'\b(?:accuracy|diagnostic accuracy)\b', claim_lower))
        claim_has_auc = bool(AUC_RE.search(claim_lower))

        evidence_has_auc = bool(AUC_RE.search(ev_lower))
        evidence_has_accuracy = bool(re.search(r'\b(?:accuracy|diagnostic accuracy)\b', ev_lower))

        mismatch_detected = False
        detail = ""

        if claim_has_accuracy and evidence_has_auc and not evidence_has_accuracy:
            mismatch_detected = True
            detail = "Metric Mismatch: Claim asserts specific diagnostic accuracy (%), but source evidence measures Area Under the ROC Curve (AUC). AUC and diagnostic accuracy are fundamentally different performance metrics."
        elif not claim_has_auc and evidence_has_auc and "accuracy" in claim_lower:
            mismatch_detected = True
            detail = "Metric Mismatch: Accuracy is claimed, but cited evidence establishes Area Under Curve (AUC), not threshold-specific percentage accuracy."

        return {
            "mismatch_detected": mismatch_detected,
            "detail": detail,
        }

    @classmethod
    def check_direction_inversion(cls, claim_text: str, evidence_text: str) -> Dict[str, Any]:
        """
        Detects if claim asserts an increase while evidence reports a reduction/decrease (or vice versa).
        E.g., Claim says 'increased mortality by 15%', source says '15% reduction in mortality'.
        """
        claim_words = set(claim_text.lower().split())
        ev_words = set(evidence_text.lower().split())

        claim_increase = bool(claim_words & INCREASE_TERMS)
        claim_decrease = bool(claim_words & DECREASE_TERMS)

        ev_increase = bool(ev_words & INCREASE_TERMS)
        ev_decrease = bool(ev_words & DECREASE_TERMS)

        inverted = False
        detail = ""

        if claim_increase and ev_decrease and not ev_increase:
            inverted = True
            detail = "Direction Inversion: Claim asserts an increase/elevation, but source evidence reports a reduction/decrease."
        elif claim_decrease and ev_increase and not ev_decrease:
            inverted = True
            detail = "Direction Inversion: Claim asserts a decrease/reduction, but source evidence reports an increase/elevation."

        return {
            "inverted": inverted,
            "detail": detail,
        }

    @classmethod
    def check_animal_to_human_generalization(cls, claim_text: str, evidence_text: str) -> Dict[str, Any]:
        """
        Detects if study was conducted on animal models (mice, rats, zebrafish) while claim generalizes to humans.
        """
        claim_lower = claim_text.lower()
        ev_lower = evidence_text.lower()

        claim_mentions_human = any(term in claim_lower for term in HUMAN_TERMS)
        evidence_is_animal = any(term in ev_lower for term in ANIMAL_TERMS)
        
        # Check if actual clinical human trial was conducted, filtering out "unstudied in humans"
        untested_in_humans = any(
            phrase in ev_lower for phrase in [
                "unstudied", "untested", "not assessed", "not evaluated",
                "remains to be tested in humans", "in humans is unstudied"
            ]
        )
        evidence_is_clinical = (
            any(term in ev_lower for term in ["clinical trial", "clinical cohort", "randomized controlled trial", "in human patients"])
            and not untested_in_humans
        )

        flaw_detected = False
        detail = ""

        if evidence_is_animal and not evidence_is_clinical:
            if claim_mentions_human or "patients" in claim_lower:
                flaw_detected = True
                detail = "Generalization Flaw: Research was conducted in preclinical animal/in-vitro models, but the claim generalizes conclusions to humans."

        return {
            "flaw_detected": flaw_detected,
            "detail": detail,
        }

    @classmethod
    def check_correlation_vs_causation(cls, claim_text: str, evidence_text: str) -> Dict[str, Any]:
        """
        Detects if claim asserts causation ('causes', 'eliminates', 'cures', 'prevents')
        when evidence only establishes correlation/association or explicitly disclaims causation.
        """
        claim_lower = claim_text.lower()
        ev_lower = evidence_text.lower()

        has_causal_claim = any(verb in claim_lower for verb in CAUSAL_CLAIM_VERBS)
        
        explicit_disclaimer = any(
            phrase in ev_lower for phrase in [
                "prevents causal conclusions", "cannot prove causation", "does not prove causation",
                "cannot establish causation", "observational study", "unmeasured confounding", "cannot be ruled out"
            ]
        )
        causal_verbs_in_evidence = [
            v for v in CAUSAL_CLAIM_VERBS
            if v in ev_lower and f"{v} causal" not in ev_lower
        ]
        
        has_correlation_only = (
            any(term in ev_lower for term in CORRELATION_TERMS)
            and (explicit_disclaimer or not causal_verbs_in_evidence)
        )

        flaw_detected = False
        detail = ""

        if has_causal_claim and has_correlation_only:
            flaw_detected = True
            detail = "Causation Fallacy: Claim makes a definitive causal assertion ('causes'/'eliminates'/'prevents'), but source evidence only demonstrates statistical correlation/association."

        return {
            "flaw_detected": flaw_detected,
            "detail": detail,
        }

    @classmethod
    def check_numerical_consistency(cls, claim_text: str, evidence_text: str) -> Dict[str, Any]:
        """
        Checks if percentages or numbers stated in the claim match numbers found in the evidence.
        """
        claim_pcts = cls.extract_percentages(claim_text)
        ev_pcts = cls.extract_percentages(evidence_text)

        if not claim_pcts:
            return {"has_numerical_claim": False, "matched": True, "detail": ""}

        # If claim asserts a percentage, check if it appears in evidence
        matches = [p for p in claim_pcts if any(abs(p - ep) < 0.1 for ep in ev_pcts)]

        if len(matches) == len(claim_pcts):
            return {
                "has_numerical_claim": True,
                "matched": True,
                "detail": f"Exact numerical percentage match found in source ({', '.join(f'{p}%' for p in matches)}).",
            }

        # Check if numbers are exaggerated or missing
        detail = f"Numerical check: Claim specifies percentage {claim_pcts}, but evidence contains {ev_pcts if ev_pcts else 'no matching percentages'}."
        return {
            "has_numerical_claim": True,
            "matched": False,
            "detail": detail,
        }

    @classmethod
    def run_all_checks(cls, claim_text: str, evidence_text: str) -> Dict[str, Any]:
        metric_res = cls.check_metric_mismatch(claim_text, evidence_text)
        direction_res = cls.check_direction_inversion(claim_text, evidence_text)
        animal_res = cls.check_animal_to_human_generalization(claim_text, evidence_text)
        causal_res = cls.check_correlation_vs_causation(claim_text, evidence_text)
        num_res = cls.check_numerical_consistency(claim_text, evidence_text)

        issues = []
        if metric_res["mismatch_detected"]:
            issues.append(metric_res["detail"])
        if direction_res["inverted"]:
            issues.append(direction_res["detail"])
        if animal_res["flaw_detected"]:
            issues.append(animal_res["detail"])
        if causal_res["flaw_detected"]:
            issues.append(causal_res["detail"])
        if num_res["has_numerical_claim"] and not num_res["matched"]:
            issues.append(num_res["detail"])

        return {
            "metric_mismatch": metric_res["mismatch_detected"],
            "direction_inverted": direction_res["inverted"],
            "animal_to_human_flaw": animal_res["flaw_detected"],
            "causation_fallacy": causal_res["flaw_detected"],
            "numerical_match": num_res["matched"] if num_res["has_numerical_claim"] else None,
            "issues": issues,
        }
