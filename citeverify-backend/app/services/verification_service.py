from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.claim import Claim
from app.models.citation import Citation
from app.models.document import Document
from app.models.source import Source
from app.models.verification import Verification
from app.services.crossref_service import CrossrefService
from app.services.evidence_retrieval_service import EvidenceRetrievalService
from app.services.gemini_service import GeminiService
from app.services.paper_search_service import PaperSearchService
from app.utils.confidence import calculate_confidence
from app.utils.doi_utils import extract_doi_from_text, normalize_doi

logger = logging.getLogger(__name__)
settings = get_settings()


class VerificationService:

    def __init__(
        self,
        gemini_service: Optional[GeminiService] = None,
        paper_search_service: Optional[PaperSearchService] = None,
        crossref_service: Optional[CrossrefService] = None,
        evidence_retrieval_service: Optional[EvidenceRetrievalService] = None,
    ):
        self.gemini = gemini_service or GeminiService()
        self.paper_search = paper_search_service or PaperSearchService()
        self.crossref = crossref_service or CrossrefService()
        self.evidence_retrieval = evidence_retrieval_service or EvidenceRetrievalService()

    async def _find_source_paper(self, citation: Citation) -> Optional[dict]:
        # 1. Check DOI in Crossref
        if citation.doi:
            crossref_result = self.crossref.verify_doi(citation.doi)
            if crossref_result:
                ss_data = self.paper_search.search_by_doi(citation.doi)
                paper_data = ss_data or {}
                for k, v in crossref_result.items():
                    if v and not paper_data.get(k):
                        paper_data[k] = v
                paper_data["crossref_verified"] = True
                logger.info(f"Resolved source paper via DOI {citation.doi}")
                return paper_data

        # 2. Search by title in Semantic Scholar
        if citation.title:
            ss_result = self.paper_search.find_best_match(
                title=citation.title,
                authors=citation.authors or "",
                year=citation.year,
            )
            if ss_result:
                return ss_result

        # 3. Search Crossref by title
        if citation.title:
            cr_results = self.crossref.search_by_title(citation.title, limit=3)
            for result in cr_results:
                match = self.crossref.calculate_metadata_match(
                    {"title": citation.title, "authors": citation.authors, "year": citation.year},
                    result,
                )
                if match["is_good_match"]:
                    return result

        logger.warning(f"No source paper found for citation: {citation.title or citation.citation_marker}")
        return None

    async def verify_claim(self, db: Session, claim: Claim, downloads_dir: str) -> Verification:
        logger.info(f"Starting verification for claim {claim.id}: '{claim.claim_text[:60]}'")

        citations = db.query(Citation).filter(Citation.claim_id == claim.id).all()
        if not citations and claim.citation_markers:
            try:
                markers = json.loads(claim.citation_markers)
                if markers:
                    citations = db.query(Citation).filter(
                        Citation.document_id == claim.document_id,
                        Citation.citation_marker.in_(markers),
                    ).all()
            except Exception:
                pass

        source = None
        for citation in citations:
            paper_data = await self._find_source_paper(citation)
            if paper_data:
                source = await self.evidence_retrieval.retrieve_source_evidence(
                    db, citation, paper_data, downloads_dir
                )
                break

        # Fallback literature search via Semantic Scholar and Crossref if no source paper was resolved from explicit citations
        if not source:
            claim_doi = extract_doi_from_text(claim.claim_text)
            fallback_paper = None
            if claim_doi:
                ss_data = self.paper_search.search_by_doi(claim_doi)
                cr_data = self.crossref.verify_doi(claim_doi)
                if ss_data or cr_data:
                    fallback_paper = ss_data or cr_data
                    if cr_data and fallback_paper:
                        for k, v in cr_data.items():
                            if v and not fallback_paper.get(k):
                                fallback_paper[k] = v
                        fallback_paper["crossref_verified"] = True

            if not fallback_paper:
                # Search by claim text
                search_query = claim.claim_text[:140]
                ss_results = self.paper_search.search_by_title(search_query, limit=3)
                if ss_results:
                    fallback_paper = ss_results[0]

            if not fallback_paper:
                cr_results = self.crossref.search_by_title(claim.claim_text[:100], limit=2)
                if cr_results:
                    fallback_paper = cr_results[0]

            if isinstance(fallback_paper, dict):
                src_title = str(fallback_paper.get("title") or "")
                src_abstract = str(fallback_paper.get("abstract") or "")
                authors_val = fallback_paper.get("authors")
                if isinstance(authors_val, list):
                    authors_str = ", ".join(str(a) for a in authors_val)
                elif isinstance(authors_val, str):
                    authors_str = authors_val
                else:
                    authors_str = ""

                year_val = fallback_paper.get("year")
                pub_year = int(year_val) if isinstance(year_val, int) else None

                source = Source(
                    id=str(uuid.uuid4()),
                    title=src_title or "Retrieved Scientific Literature",
                    authors=authors_str,
                    publication_year=pub_year,
                    doi=str(fallback_paper.get("doi") or claim_doi or "") or None,
                    source_url=str(fallback_paper.get("url") or "") or (f"https://doi.org/{fallback_paper.get('doi')}" if fallback_paper.get("doi") else None),
                    pdf_url=str(fallback_paper.get("pdf_url") or "") or None,
                    abstract=src_abstract,
                    evidence_type="abstract_only" if src_abstract else "metadata_only",
                    crossref_verified=bool(fallback_paper.get("crossref_verified") is True),
                )
                db.add(source)
                db.commit()
                db.refresh(source)
                logger.info(f"Fallback literature search resolved source for claim {claim.id}: '{source.title[:50]}'")

        evidence_summary = None
        if source:
            evidence_summary = self.evidence_retrieval.get_evidence_summary(source, claim.claim_text)

        passage_texts = []
        if evidence_summary:
            passage_texts = [p["text"] for p in evidence_summary.get("relevant_passages", [])]

        source_title = source.title if source else ""
        source_abstract = source.abstract if source else ""
        evidence_type = source.evidence_type if source else "metadata_only"

        gemini_result = await self.gemini.verify_claim(
            claim_text=claim.claim_text,
            evidence_passages=passage_texts,
            source_title=source_title,
            source_abstract=source_abstract,
            evidence_type=evidence_type,
        )

        verdict = gemini_result.get("verdict", "NEEDS_HUMAN_REVIEW")
        explanation = gemini_result.get("explanation", "")
        issues = gemini_result.get("issues", [])
        human_review = gemini_result.get("human_review_required", True)
        relevant_passages = gemini_result.get("relevant_passages", [])

        evidence_passages = []
        for passage in relevant_passages:
            evidence_passages.append({
                "text": passage,
                "page_number": None,
                "source_url": source.source_url if source else None,
            })

        conf = calculate_confidence(
            evidence_type=evidence_type,
            verdict=verdict,
            has_doi=bool(source.doi if source else None),
            doi_verified=bool(source.crossref_verified if source else False),
            numerical_match=False,
            source_found=source is not None,
        )

        if not source:
            issues.append("No source publication could be located for this claim.")
            human_review = True
        elif evidence_type == "abstract_only":
            issues.append("Only abstract was available; claim could not be validated against full paper.")
        elif evidence_type == "metadata_only":
            issues.append("Only metadata was retrieved; text verification was not possible.")

        verification = Verification(
            id=str(uuid.uuid4()),
            claim_id=claim.id,
            source_id=source.id if source else None,
            verdict=verdict,
            explanation=explanation,
            evidence_passages=json.dumps(evidence_passages),
            confidence_level=conf["level"],
            confidence_score=conf["score"],
            confidence_reason=conf["reason"],
            issues=json.dumps(issues),
            limitations=(
                "Evidence based on abstract only." if evidence_type == "abstract_only"
                else "Evaluated against full paper text." if evidence_type == "full_text"
                else "No text content retrieved."
            ),
            human_review_required=human_review,
        )
        db.add(verification)
        claim.status = "verified"
        db.commit()
        db.refresh(verification)
        return verification

    async def run_verification(
        self,
        db: Session,
        document_id: str,
        claim_ids: Optional[list[str]] = None,
        confirmed_references: Optional[dict] = None,
    ) -> list[Verification]:
        query = db.query(Claim).filter(Claim.document_id == document_id)
        if claim_ids:
            query = query.filter(Claim.id.in_(claim_ids))
        claims = query.all()

        if not claims:
            logger.warning(f"No claims found for document {document_id}")
            return []

        downloads_dir = f"{settings.upload_dir}/{document_id}/sources"
        results = []
        for claim in claims:
            try:
                verification = await self.verify_claim(db, claim, downloads_dir)
                results.append(verification)
            except Exception as e:
                logger.error(f"Error verifying claim {claim.id}: {e}", exc_info=True)
                fallback = Verification(
                    id=str(uuid.uuid4()),
                    claim_id=claim.id,
                    source_id=None,
                    verdict="NEEDS_HUMAN_REVIEW",
                    explanation=f"Verification encountered an unexpected error: {str(e)[:400]}",
                    evidence_passages=json.dumps([]),
                    confidence_level="LOW",
                    confidence_score=0.1,
                    confidence_reason="Verification pipeline failure.",
                    issues=json.dumps([f"Processing error: {str(e)[:200]}"]),
                    human_review_required=True,
                )
                db.add(fallback)
                claim.status = "verified"
                db.commit()
                results.append(fallback)

        return results

    def get_verification_results(self, db: Session, document_id: str) -> list[dict]:
        claims = db.query(Claim).filter(Claim.document_id == document_id).all()
        results = []
        for claim in claims:
            if not claim.verifications:
                continue
            v = claim.verifications[-1]
            results.append(self.build_result_dict(v, claim, v.source))
        return results

    def build_result_dict(
        self, verification: Verification, claim: Claim, source: Optional[Source]
    ) -> dict:
        evidence_passages = []
        if verification.evidence_passages:
            try:
                evidence_passages = json.loads(verification.evidence_passages)
            except Exception:
                pass

        issues = []
        if verification.issues:
            try:
                issues = json.loads(verification.issues)
            except Exception:
                pass

        citation_ref = None
        if claim.citations:
            c = claim.citations[0]
            if c.authors and c.year:
                citation_ref = f"{c.authors} ({c.year})"
            elif c.citation_marker:
                citation_ref = c.citation_marker
            elif c.title:
                citation_ref = c.title
        elif claim.citation_markers:
            try:
                markers = json.loads(claim.citation_markers)
                if markers:
                    citation_ref = ", ".join(markers)
            except Exception:
                citation_ref = claim.citation_markers

        source_info = None
        if source:
            authors_list = [a.strip() for a in source.authors.split(",")] if source.authors else []
            source_info = {
                "title": source.title,
                "doi": source.doi,
                "url": source.source_url or (f"https://doi.org/{source.doi}" if source.doi else None),
                "evidence_type": source.evidence_type or "metadata_only",
                "authors": authors_list,
                "year": source.publication_year,
                "doi_url": f"https://doi.org/{source.doi}" if source.doi else None,
            }

        return {
            "claim_id": claim.id,
            "claim_text": claim.claim_text,
            "citation_reference": citation_ref,
            "source": source_info,
            "verdict": verification.verdict,
            "explanation": verification.explanation or "",
            "evidence_passages": evidence_passages,
            "confidence": {
                "level": verification.confidence_level,
                "score": verification.confidence_score or 0.0,
                "reason": verification.confidence_reason or "",
            },
            "issues": issues,
            "human_review_required": verification.human_review_required,
        }

    async def verify_direct_claim(
        self,
        db: Session,
        claim_text: str,
        citation_str: Optional[str] = None,
        doi_str: Optional[str] = None,
        context: Optional[str] = None,
    ) -> dict:
        claim_text = (claim_text or "").strip()
        if not claim_text:
            raise ValueError("Claim text cannot be empty.")

        # 1. Resolve DOI
        extracted_doi = None
        if doi_str and doi_str.strip():
            extracted_doi = normalize_doi(doi_str.strip())
        elif citation_str:
            extracted_doi = extract_doi_from_text(citation_str)
        if not extracted_doi:
            extracted_doi = extract_doi_from_text(claim_text)

        paper_data = None

        # Try DOI first in Crossref & Semantic Scholar
        if extracted_doi:
            crossref_res = self.crossref.verify_doi(extracted_doi)
            ss_data = self.paper_search.search_by_doi(extracted_doi)
            if crossref_res or ss_data:
                paper_data = ss_data or {}
                if crossref_res:
                    for k, v in crossref_res.items():
                        if v and not paper_data.get(k):
                            paper_data[k] = v
                    paper_data["crossref_verified"] = True
                if not paper_data.get("doi"):
                    paper_data["doi"] = extracted_doi

        # Try Citation search
        if not paper_data and citation_str and citation_str.strip():
            ss_res = self.paper_search.find_best_match(citation_str.strip())
            if ss_res:
                paper_data = ss_res
            else:
                cr_results = self.crossref.search_by_title(citation_str.strip(), limit=3)
                for res in cr_results:
                    match = self.crossref.calculate_metadata_match(
                        {"title": citation_str.strip()}, res
                    )
                    if match.get("is_good_match"):
                        paper_data = res
                        break
                if not paper_data and cr_results:
                    paper_data = cr_results[0]

        # Try Claim keywords search in Semantic Scholar if no source yet
        if not paper_data:
            search_query = claim_text[:140]
            ss_results = self.paper_search.search_by_title(search_query, limit=3)
            if ss_results:
                paper_data = ss_results[0]

        # 2. Evidence Retrieval & Source Creation
        source = None
        passage_texts = []
        source_title = ""
        source_abstract = ""
        evidence_type = "metadata_only"

        if paper_data:
            source_title = paper_data.get("title", "")
            source_abstract = paper_data.get("abstract", "") or ""
            authors_str = ", ".join(paper_data.get("authors", [])) if isinstance(paper_data.get("authors"), list) else str(paper_data.get("authors", ""))

            source = Source(
                id=str(uuid.uuid4()),
                title=source_title or (citation_str or "Cited Literature"),
                authors=authors_str,
                publication_year=paper_data.get("year"),
                doi=paper_data.get("doi") or extracted_doi,
                source_url=paper_data.get("url") or (f"https://doi.org/{paper_data.get('doi')}" if paper_data.get("doi") else None),
                pdf_url=paper_data.get("pdf_url"),
                abstract=source_abstract,
                evidence_type="abstract_only" if source_abstract else "metadata_only",
                semantic_scholar_id=paper_data.get("semantic_scholar_id"),
                crossref_verified=paper_data.get("crossref_verified", False),
                retrieval_date=datetime.now(timezone.utc),
            )
            db.add(source)
            db.commit()
            db.refresh(source)

            evidence_type = source.evidence_type
            if source_abstract:
                summary = self.evidence_retrieval.get_evidence_summary(source, claim_text)
                passage_texts = [p["text"] for p in summary.get("relevant_passages", [])]
                if not passage_texts and source_abstract:
                    passage_texts = [source_abstract[:800]]

        # 3. AI Verification
        gemini_result = await self.gemini.verify_claim(
            claim_text=claim_text,
            evidence_passages=passage_texts,
            source_title=source_title,
            source_abstract=source_abstract,
            evidence_type=evidence_type,
        )

        verdict = gemini_result.get("verdict", "NEEDS_HUMAN_REVIEW")
        explanation = gemini_result.get("explanation", "")
        issues = gemini_result.get("issues", [])
        human_review = gemini_result.get("human_review_required", False)
        relevant_passages = gemini_result.get("relevant_passages", [])

        evidence_passages_list = []
        for p in relevant_passages:
            evidence_passages_list.append({
                "text": p,
                "page_number": None,
                "source_url": source.source_url if source else None,
            })
        if not evidence_passages_list and passage_texts:
            for p in passage_texts:
                evidence_passages_list.append({
                    "text": p,
                    "page_number": None,
                    "source_url": source.source_url if source else None,
                })

        conf = calculate_confidence(
            evidence_type=evidence_type,
            verdict=verdict,
            has_doi=bool(source.doi if source else None),
            doi_verified=bool(source.crossref_verified if source else False),
            numerical_match=False,
            source_found=source is not None,
        )

        if not source:
            issues.append("No peer-reviewed publication or source record matching this statement or citation could be identified.")
            human_review = True

        # 4. Store in database
        direct_doc = db.query(Document).filter(Document.id == "direct-verification-history").first()
        if not direct_doc:
            direct_doc = Document(
                id="direct-verification-history",
                filename="direct_claim_verifications.txt",
                upload_path="direct-verifications",
                processing_status="verified",
                document_title="Direct Claim Verifications",
            )
            db.add(direct_doc)
            db.commit()

        claim_record = Claim(
            id=str(uuid.uuid4()),
            document_id=direct_doc.id,
            claim_text=claim_text,
            paragraph=context or claim_text,
            category="scientific_statement",
            citation_markers=json.dumps([citation_str]) if citation_str else None,
            extraction_explanation="Directly submitted scientific statement for verification.",
            status="verified",
        )
        db.add(claim_record)
        db.commit()
        db.refresh(claim_record)

        if citation_str or extracted_doi:
            cit_record = Citation(
                id=str(uuid.uuid4()),
                document_id=direct_doc.id,
                claim_id=claim_record.id,
                citation_marker=citation_str or extracted_doi or "Direct Citation",
                doi=extracted_doi or (source.doi if source else None),
                title=source.title if source else (citation_str or "Submitted Citation"),
                authors=source.authors if source else None,
                year=source.publication_year if source else None,
                matching_status="matched" if source else "unmatched",
            )
            db.add(cit_record)
            db.commit()

        verification_record = Verification(
            id=str(uuid.uuid4()),
            claim_id=claim_record.id,
            source_id=source.id if source else None,
            verdict=verdict,
            explanation=explanation,
            evidence_passages=json.dumps(evidence_passages_list),
            confidence_level=conf["level"],
            confidence_score=conf["score"],
            confidence_reason=conf["reason"],
            issues=json.dumps(issues),
            limitations=(
                "Evidence based on abstract only." if evidence_type == "abstract_only"
                else "Evaluated against full paper text." if evidence_type == "full_text"
                else "No published literature content retrieved."
            ),
            human_review_required=human_review,
        )
        db.add(verification_record)
        db.commit()
        db.refresh(verification_record)

        return self.build_result_dict(verification_record, claim_record, source)
