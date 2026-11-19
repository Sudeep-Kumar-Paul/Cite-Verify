from __future__ import annotations

import json
import logging
import re
from typing import Optional

from fuzzywuzzy import fuzz
from sqlalchemy.orm import Session

from app.models.citation import Citation
from app.models.claim import Claim

logger = logging.getLogger(__name__)

AUTHOR_YEAR_THRESHOLD = 70


class ReferenceMatchingService:

    def match_numbered_citations(
        self, in_text_citations: list[Citation], references: list[Citation]
    ) -> list[tuple[Citation, Citation, float]]:
        ref_by_number = {r.reference_number: r for r in references if r.reference_number is not None}
        matches = []
        for cit in in_text_citations:
            if cit.reference_number and cit.reference_number in ref_by_number:
                matches.append((cit, ref_by_number[cit.reference_number], 1.0))
        return matches

    def match_author_year_citations(
        self, in_text_citations: list[Citation], references: list[Citation]
    ) -> list[tuple[Citation, Citation, float]]:
        matches = []
        for cit in in_text_citations:
            if not cit.authors or not cit.year:
                continue
            candidates = []
            for ref in references:
                if not ref.authors:
                    continue
                if ref.year and abs(ref.year - cit.year) > 1:
                    continue
                score = fuzz.token_sort_ratio(cit.authors.lower(), ref.authors.lower()) / 100.0
                if score >= AUTHOR_YEAR_THRESHOLD / 100.0:
                    candidates.append((ref, score))
            if len(candidates) == 1:
                matches.append((cit, candidates[0][0], candidates[0][1]))
            elif len(candidates) > 1:
                candidates.sort(key=lambda x: x[1], reverse=True)
                matches.append((cit, candidates[0][0], candidates[0][1]))
        return matches

    def match_all_citations(self, db: Session, document_id: str) -> dict:
        all_citations = db.query(Citation).filter(Citation.document_id == document_id).all()

        in_text = [
            c for c in all_citations
            if not c.raw_reference_text or len(c.raw_reference_text) < 20
        ]
        references = [
            c for c in all_citations
            if c.reference_number is not None or (c.raw_reference_text and len(c.raw_reference_text) >= 20)
        ]

        matched = 0
        unmatched = 0
        ambiguous = 0

        # Match numbered
        numbered_matches = self.match_numbered_citations(in_text, references)
        for cit, ref, score in numbered_matches:
            cit.matching_status = "matched"
            cit.matched_reference_id = ref.id
            ref.matching_status = "matched"
            matched += 1

        # Match author-year
        remaining_in_text = [c for c in in_text if c.matching_status == "unmatched"]
        author_year_matches = self.match_author_year_citations(remaining_in_text, references)
        for cit, ref, score in author_year_matches:
            if score >= 0.85:
                cit.matching_status = "matched"
                cit.matched_reference_id = ref.id
                ref.matching_status = "matched"
                matched += 1
            else:
                cit.matching_status = "ambiguous"
                cit.is_ambiguous = True
                cit.matched_reference_id = ref.id
                ambiguous += 1

        for cit in all_citations:
            if cit.matching_status == "unmatched":
                unmatched += 1

        db.commit()
        return {
            "matched": matched,
            "unmatched": unmatched,
            "ambiguous": ambiguous,
            "total": len(all_citations),
        }

    def associate_citations_with_claims(self, db: Session, document_id: str) -> int:
        claims = db.query(Claim).filter(Claim.document_id == document_id).all()
        citations = db.query(Citation).filter(Citation.document_id == document_id).all()

        marker_to_citation = {c.citation_marker: c for c in citations}

        count = 0
        for claim in claims:
            if not claim.citation_markers:
                continue
            try:
                markers = json.loads(claim.citation_markers)
            except (json.JSONDecodeError, TypeError):
                continue
            for marker in markers:
                cit = marker_to_citation.get(marker)
                if cit and cit.claim_id is None:
                    cit.claim_id = claim.id
                    count += 1

        db.commit()
        return count
