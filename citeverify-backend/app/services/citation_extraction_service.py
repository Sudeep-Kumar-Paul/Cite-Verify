from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import DocumentNotFoundException
from app.models.citation import Citation
from app.models.document import Document
from app.utils.doi_utils import extract_doi_from_text

logger = logging.getLogger(__name__)

# Patterns for in-text citations
NUMBERED_CITATION_RE = re.compile(r'\[(\d+(?:[,\s\-–]\s*\d+)*)\]')
AUTHOR_YEAR_RE = re.compile(
    r'\(([A-Z][a-zA-Z\-\']+(?:\s+(?:and|&)\s+[A-Z][a-zA-Z\-\']+)?(?:\s+et\s+al\.?)?)(?:,\s*(\d{4}))?\)'
)
NARRATIVE_CITATION_RE = re.compile(
    r'([A-Z][a-zA-Z\-\']+(?:\s+et\s+al\.?)?)\s+\((\d{4})\)'
)

# Patterns for reference list parsing
NUMBERED_REF_RE = re.compile(r'^\s*\[?(\d+)\]?[\.\s]+(.+)', re.MULTILINE)
APA_REF_YEAR_RE = re.compile(r'\((\d{4})\)')
TITLE_QUOTED_RE = re.compile(r'["“]([^"”]{10,250})["”]')


class CitationExtractionService:

    def extract_in_text_citations(self, text: str) -> list[dict]:
        citations = []
        seen_markers = set()

        # Numbered citations: [1], [2, 3], [1-3]
        for match in NUMBERED_CITATION_RE.finditer(text):
            marker = match.group(0)
            inner = match.group(1)
            normalized = []
            parts = re.split(r'[,\s]+', inner)
            for part in parts:
                range_match = re.match(r'(\d+)\s*[-–]\s*(\d+)', part)
                if range_match:
                    start, end = int(range_match.group(1)), int(range_match.group(2))
                    normalized.extend(str(n) for n in range(start, end + 1))
                elif part.strip().isdigit():
                    normalized.append(part.strip())
            if marker not in seen_markers:
                seen_markers.add(marker)
                citations.append({"marker": marker, "type": "numbered", "normalized": normalized})

        # Author-year: (Smith, 2023)
        for match in AUTHOR_YEAR_RE.finditer(text):
            marker = match.group(0)
            author = match.group(1).strip()
            year = match.group(2)
            if marker not in seen_markers and year:
                seen_markers.add(marker)
                key = f"{author}_{year}"
                citations.append({"marker": marker, "type": "author_year", "normalized": [key]})

        # Narrative: Smith et al. (2023)
        for match in NARRATIVE_CITATION_RE.finditer(text):
            author = match.group(1).strip()
            year = match.group(2)
            marker = f"{author} ({year})"
            if marker not in seen_markers:
                seen_markers.add(marker)
                key = f"{author}_{year}"
                citations.append({"marker": marker, "type": "narrative", "normalized": [key]})

        return citations

    def _parse_numbered_references(self, text: str) -> list[dict]:
        refs = []
        matches = list(NUMBERED_REF_RE.finditer(text))
        for i, match in enumerate(matches):
            ref_num = int(match.group(1))
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            raw_text = text[start:end].strip()
            refs.append({
                "reference_number": ref_num,
                "raw_text": raw_text,
                "authors": self._extract_authors_heuristic(raw_text),
                "title": self._extract_title_heuristic(raw_text),
                "year": self._extract_year(raw_text),
                "doi": extract_doi_from_text(raw_text),
                "journal": None,
            })
        return refs

    def _parse_unstructured_references(self, text: str) -> list[dict]:
        refs = []
        entries = re.split(r'\n\s*\n+', text)
        for entry in entries:
            entry = entry.strip()
            if len(entry) < 20:
                continue
            refs.append({
                "reference_number": None,
                "raw_text": entry,
                "authors": self._extract_authors_heuristic(entry),
                "title": self._extract_title_heuristic(entry),
                "year": self._extract_year(entry),
                "doi": extract_doi_from_text(entry),
                "journal": None,
            })
        return refs

    def _extract_authors_heuristic(self, text: str) -> Optional[str]:
        first_line = text.split("\n")[0]
        # Common end markers for author strings in references: year or period
        author_part = re.split(r'\(\d{4}\)|\.\s', first_line)[0].strip()
        if author_part and len(author_part) < 300:
            return author_part
        return None

    def _extract_title_heuristic(self, text: str) -> Optional[str]:
        m = TITLE_QUOTED_RE.search(text)
        if m:
            return m.group(1).strip()
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) >= 2:
            candidate = sentences[1].strip()
            if 10 < len(candidate) < 300 and not candidate.startswith("http"):
                return candidate
        return None

    def _extract_year(self, text: str) -> Optional[int]:
        matches = APA_REF_YEAR_RE.findall(text)
        plain_years = re.findall(r'\b(19\d{2}|20[0-2]\d)\b', text)
        candidates = [int(y) for y in (matches + plain_years)]
        return candidates[0] if candidates else None

    def parse_references_section(self, references_text: str) -> list[dict]:
        if not references_text:
            return []
        numbered = self._parse_numbered_references(references_text)
        if numbered:
            return numbered
        return self._parse_unstructured_references(references_text)

    async def extract_all_citations(
        self, db: Session, document_id: str, gemini_service=None
    ) -> dict:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise DocumentNotFoundException(document_id)

        in_text = self.extract_in_text_citations(document.body_text or document.extracted_text or "")
        references = self.parse_references_section(document.references_text or "")

        if gemini_service and len(references) < 2 and document.references_text:
            try:
                gemini_refs = await gemini_service.extract_citations_from_text(document.references_text)
                if gemini_refs:
                    references = gemini_refs
            except Exception as e:
                logger.warning(f"Gemini fallback citation extraction failed: {e}")

        # Remove existing citations for clean re-extraction
        db.query(Citation).filter(Citation.document_id == document_id).delete()

        saved = []
        for ref in references:
            ref_num = ref.get("reference_number")
            marker = f"[{ref_num}]" if ref_num else (ref.get("raw_text", "")[:40] or "Ref")
            citation = Citation(
                id=str(uuid.uuid4()),
                document_id=document_id,
                citation_marker=marker,
                reference_number=ref_num,
                authors=ref.get("authors"),
                title=ref.get("title"),
                year=ref.get("year"),
                doi=ref.get("doi"),
                raw_reference_text=ref.get("raw_text"),
                matching_status="unmatched",
                is_ambiguous=False,
            )
            db.add(citation)
            saved.append(citation)

        db.commit()
        logger.info(f"Extracted {len(in_text)} in-text citations, {len(saved)} reference records for document {document_id}.")
        return {
            "in_text_citations": in_text,
            "references": references,
            "total_citations": len(saved),
        }
