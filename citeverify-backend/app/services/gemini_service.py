from __future__ import annotations

import json
import logging
from typing import Any, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.utils.scientific_checks import ScientificChecker

logger = logging.getLogger(__name__)
settings = get_settings()


CLAIM_SYSTEM_PROMPT = """You are a scientific claim extraction assistant for CiteVerify.

Your task is to extract verifiable scientific claims from academic document text.

CRITICAL RULES:
- Only extract claims that are EXPLICITLY stated in the provided text.
- Do NOT invent, infer, or paraphrase claims not present in the text.
- Focus on: statistical claims, experimental findings, causal claims, quantitative results, and research conclusions that require citation support.
- For each claim, record its citation markers exactly as they appear in the surrounding text (e.g. [1], [2, 3], (Smith, 2023)).
- Preserve the original wording of the statement.

Return valid JSON with this exact schema:
{
  "claims": [
    {
      "claim_text": "Exact claim text from document",
      "page_number": null,
      "paragraph": "Surrounding context (max 500 characters)",
      "category": "statistical|causal|experimental|conclusion|quantitative|other",
      "citation_markers": ["[1]", "(Smith, 2023)"],
      "extraction_explanation": "Brief rationale why this claim requires scientific verification"
    }
  ]
}

If no verifiable claims are found, return {"claims": []}.
Output ONLY valid JSON without Markdown fences or commentary.
"""

VERIFICATION_SYSTEM_PROMPT = """You are a rigorous scientific claim verification assistant for CiteVerify.

Your task is to compare a scientific claim against retrieved source evidence.

CRITICAL AI SAFEGUARDS — STRICT ADHERENCE REQUIRED:
1. NEVER invent supporting passages or quotations.
2. NEVER fabricate research findings.
3. NEVER treat publication metadata (title, authors, year) alone as evidence.
4. NEVER treat a similar title as proof that the source supports the claim.
5. ALWAYS return NEEDS_HUMAN_REVIEW when the provided evidence is genuinely insufficient.
6. Clearly distinguish between what the retrieved text directly states versus secondary interpretations.
7. Scrutinize numerical values, percentages, sample sizes, and study populations.
8. Distinguish correlation from causation.
9. If evidence is abstract-only, explicitly state this limitation.

Allowed verdicts:
- SUPPORTED: Evidence directly and fully supports all material aspects of the claim.
- PARTIALLY_SUPPORTED: Evidence supports part of the claim or introduces major caveats, limitations, or metric nuances.
- UNSUPPORTED: Evidence discusses the topic or methods but does NOT substantiate or demonstrate the claim.
- CONTRADICTORY: Evidence directly conflicts with, inverts, or disproves the claim (e.g. increase vs decrease).
- POTENTIALLY_OUTDATED: Claim was supported by older findings, but newer scientific consensus or subsequent research indicates it is outdated.
- NEEDS_HUMAN_REVIEW: Retrieved evidence is insufficient, ambiguous, or unavailable to make an automated determination.

Return valid JSON with this exact schema:
{
  "verdict": "SUPPORTED|PARTIALLY_SUPPORTED|UNSUPPORTED|CONTRADICTORY|POTENTIALLY_OUTDATED|NEEDS_HUMAN_REVIEW",
  "explanation": "Detailed evidence-based explanation referencing specific source points and numerical checks",
  "issues": ["List of specific issues, limitations, or caveats identified"],
  "human_review_required": false,
  "used_passage_ids": ["P1", "P2"],
  "relevant_passages": ["Direct authentic excerpt from provided evidence"]
}

Output ONLY valid JSON without Markdown fences or commentary.
"""


class GeminiService:

    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model or "gemini-3.8-flash"
        self._client = None
        if self.api_key:
            try:
                import google.genai as genai
                self._client = genai.Client(api_key=self.api_key, http_options={"api_version": "v1beta"})
                logger.info(f"GeminiService initialized with model: {self.model}")
            except Exception as e:
                logger.warning(f"Failed to initialize google-genai Client: {e}")
        else:
            logger.info("GeminiService initialized without API key (mock or development mode).")

    @property
    def client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY environment variable is not configured.")
            import google.genai as genai
            self._client = genai.Client(api_key=self.api_key, http_options={"api_version": "v1beta"})
        return self._client

    def _call_gemini_api(self, contents: str, config: dict):
        models_to_try = [self.model]
        for fallback in ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"]:
            if fallback not in models_to_try:
                models_to_try.append(fallback)
        
        last_error = None
        for m in models_to_try:
            try:
                return self.client.models.generate_content(
                    model=m,
                    contents=contents,
                    config=config,
                )
            except Exception as err:
                last_error = err
                logger.warning(f"Gemini call to model '{m}' failed: {err}. Attempting fallback if available.")
        if last_error:
            raise last_error

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    async def extract_claims(self, text: str, document_title: str = "") -> list[dict]:
        if not text or len(text.strip()) < 50:
            logger.warning("Text too short for claim extraction.")
            return []

        truncated = text[:100000]
        user_message = (
            f"Extract scientific claims from this academic document.\n"
            f"Document Title: {document_title or 'Unknown'}\n\n"
            f"Document Text:\n{truncated}"
        )

        try:
            response = self._call_gemini_api(
                contents=user_message,
                config={
                    "system_instruction": CLAIM_SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                },
            )
            raw = response.text or "{}"
            # Clean possible markdown block wrappers if present
            raw_clean = raw.strip()
            if raw_clean.startswith("```json"):
                raw_clean = raw_clean[7:]
            if raw_clean.startswith("```"):
                raw_clean = raw_clean[3:]
            if raw_clean.endswith("```"):
                raw_clean = raw_clean[:-3]
            parsed = json.loads(raw_clean.strip())
            claims = parsed.get("claims", [])
            logger.info(f"Gemini extracted {len(claims)} claims.")
            return claims
        except json.JSONDecodeError as e:
            logger.warning(f"Gemini returned non-JSON response: {e}")
            return []
        except Exception as e:
            logger.error(f"Gemini claim extraction call failed: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    async def verify_claim(
        self,
        claim_text: str,
        evidence_passages: Any,
        source_title: str,
        source_abstract: str,
        evidence_type: str,
    ) -> dict:
        evidence_context = ""
        indexed_passages = {}
        full_evidence_corpus = source_abstract or ""

        if evidence_passages:
            evidence_context += "RETRIEVED SOURCE PASSAGES:\n"
            for i, p in enumerate(evidence_passages, 1):
                if isinstance(p, dict):
                    pid = p.get("id", f"P{i}")
                    ptext = p.get("text", "")
                    pnum = p.get("page_number")
                    page_str = f"Page: {pnum}" if pnum else "Page: Unavailable"
                    indexed_passages[pid] = p
                    evidence_context += f"[{pid}] ({page_str}): {ptext}\n\n"
                    full_evidence_corpus += " " + ptext
                else:
                    pid = f"P{i}"
                    ptext = str(p)
                    indexed_passages[pid] = {"id": pid, "text": ptext, "page_number": None}
                    evidence_context += f"[{pid}]: {ptext}\n\n"
                    full_evidence_corpus += " " + ptext

        if source_abstract:
            evidence_context += f"SOURCE ABSTRACT:\n{source_abstract}\n\n"

        if not evidence_context.strip():
            return {
                "verdict": "NEEDS_HUMAN_REVIEW",
                "explanation": "No source text or abstract could be retrieved for this claim. Verification requires human inspection.",
                "issues": ["No evidence available for automated verification"],
                "human_review_required": True,
                "relevant_passages": [],
            }

        # Deterministic scientific pre-checks
        sci_checks = ScientificChecker.run_all_checks(claim_text, full_evidence_corpus)

        user_message = (
            f"CLAIM TO VERIFY:\n{claim_text}\n\n"
            f"SOURCE PAPER TITLE: {source_title or 'Unknown'}\n"
            f"EVIDENCE TYPE: {evidence_type}\n\n"
            f"{evidence_context}\n"
            f"Assess whether the evidence above supports, partially supports, contradicts, or fails to support the claim.\n"
            f"Reference the specific passage IDs (e.g. ['P1']) you based your assessment on."
        )

        try:
            response = self._call_gemini_api(
                contents=user_message,
                config={
                    "system_instruction": VERIFICATION_SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                },
            )
            raw = response.text or "{}"
            raw_clean = raw.strip()
            if raw_clean.startswith("```json"):
                raw_clean = raw_clean[7:]
            if raw_clean.startswith("```"):
                raw_clean = raw_clean[3:]
            if raw_clean.endswith("```"):
                raw_clean = raw_clean[:-3]
            parsed = json.loads(raw_clean.strip())

            valid_verdicts = {
                "SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED",
                "CONTRADICTORY", "POTENTIALLY_OUTDATED", "POSSIBLY_OUTDATED", "NEEDS_HUMAN_REVIEW",
            }
            raw_v = (parsed.get("verdict") or "NEEDS_HUMAN_REVIEW").upper()
            if raw_v not in valid_verdicts:
                raw_v = "NEEDS_HUMAN_REVIEW"
                parsed.setdefault("issues", []).append("AI returned unrecognized verdict code; defaulted to NEEDS_HUMAN_REVIEW.")

            # Standardize POSSIBLY_OUTDATED to POTENTIALLY_OUTDATED while preserving legacy equivalence
            if raw_v == "POSSIBLY_OUTDATED":
                raw_v = "POTENTIALLY_OUTDATED"

            # Apply Deterministic Scientific Safeguards
            issues = parsed.get("issues", [])
            for sci_issue in sci_checks["issues"]:
                if sci_issue not in issues:
                    issues.append(sci_issue)

            if sci_checks["direction_inverted"]:
                raw_v = "CONTRADICTORY"
                parsed["human_review_required"] = False
            elif sci_checks["metric_mismatch"] and raw_v == "SUPPORTED":
                raw_v = "PARTIALLY_SUPPORTED"
            elif sci_checks["causation_fallacy"] and raw_v == "SUPPORTED":
                raw_v = "PARTIALLY_SUPPORTED"
            elif sci_checks["animal_to_human_flaw"] and raw_v == "SUPPORTED":
                raw_v = "PARTIALLY_SUPPORTED"

            parsed["verdict"] = raw_v
            parsed["issues"] = issues
            parsed["scientific_checks"] = sci_checks

            # Resolve authentic passages using passage IDs (anti-hallucination)
            used_ids = parsed.get("used_passage_ids", [])
            verified_passages = []
            for pid in used_ids:
                if pid in indexed_passages:
                    verified_passages.append(indexed_passages[pid]["text"])

            # If Gemini output quotations in relevant_passages, strictly verify they exist in source text
            for raw_quote in parsed.get("relevant_passages", []):
                if raw_quote and raw_quote in full_evidence_corpus and raw_quote not in verified_passages:
                    verified_passages.append(raw_quote)

            # Fallback to top indexed passage if none resolved
            if not verified_passages and indexed_passages:
                first_key = next(iter(indexed_passages))
                verified_passages.append(indexed_passages[first_key]["text"])

            parsed["relevant_passages"] = verified_passages
            return parsed

        except json.JSONDecodeError as e:
            logger.warning(f"Gemini returned non-JSON verification response: {e}")
            return {
                "verdict": "NEEDS_HUMAN_REVIEW",
                "explanation": "Verification engine returned an unparseable response.",
                "issues": ["Malformed AI verification output"],
                "human_review_required": True,
                "relevant_passages": [],
                "scientific_checks": sci_checks,
            }
        except Exception as e:
            logger.error(f"Gemini verification call failed: {e}")
            raise

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=8))
    async def extract_citations_from_text(self, references_text: str) -> list[dict]:
        if not references_text or len(references_text.strip()) < 20:
            return []
        prompt = (
            "Parse the following academic references text into structured reference records.\n\n"
            "Return JSON: {\"references\": [{\"reference_number\": int_or_null, \"authors\": \"str\", "
            "\"title\": \"str\", \"year\": int_or_null, \"doi\": \"str_or_null\", "
            "\"journal\": \"str_or_null\", \"raw_text\": \"str\"}]}\n\n"
            f"References:\n{references_text[:20000]}"
        )
        try:
            response = self._call_gemini_api(
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            raw = response.text or "{}"
            raw_clean = raw.strip()
            if raw_clean.startswith("```json"):
                raw_clean = raw_clean[7:]
            if raw_clean.startswith("```"):
                raw_clean = raw_clean[3:]
            if raw_clean.endswith("```"):
                raw_clean = raw_clean[:-3]
            parsed = json.loads(raw_clean.strip())
            return parsed.get("references", [])
        except Exception as e:
            logger.warning(f"Gemini citation extraction fallback failed: {e}")
            return []
