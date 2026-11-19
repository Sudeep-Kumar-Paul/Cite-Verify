from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

# ── In-Memory SQLite Test Fixtures ───────────────────────────────────────────

TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_db():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(test_db):
    with TestClient(app) as c:
        yield c


# ── 1. API Health & Root Tests ───────────────────────────────────────────────

class TestHealthAndBasics:
    def test_health_endpoint(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app"] == "CiteVerify"
        assert "timestamp" in data

    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "docs" in data

    def test_swagger_docs(self, client):
        response = client.get("/docs")
        assert response.status_code == 200


# ── 2. DOI Utils Tests ───────────────────────────────────────────────────────

class TestDOIUtils:
    def test_extract_doi_standard(self):
        from app.utils.doi_utils import extract_doi_from_text
        text = "This paper was published with DOI: 10.1038/nature12345."
        assert extract_doi_from_text(text) == "10.1038/nature12345"

    def test_extract_doi_from_url(self):
        from app.utils.doi_utils import extract_doi_from_text
        text = "Available online at https://doi.org/10.1016/j.cell.2023.01.001"
        assert extract_doi_from_text(text) == "10.1016/j.cell.2023.01.001"

    def test_normalize_doi(self):
        from app.utils.doi_utils import normalize_doi
        assert normalize_doi("https://doi.org/10.1038/NATURE12345") == "10.1038/nature12345"
        assert normalize_doi("doi: 10.1038/nature12345") == "10.1038/nature12345"

    def test_valid_doi_format(self):
        from app.utils.doi_utils import is_valid_doi_format
        assert is_valid_doi_format("10.1038/s41586-021-03819-2") is True
        assert is_valid_doi_format("10.1145/3372278.3390670") is True

    def test_invalid_doi_format(self):
        from app.utils.doi_utils import is_valid_doi_format
        assert is_valid_doi_format("not-a-doi") is False
        assert is_valid_doi_format("11.1234/something") is False
        assert is_valid_doi_format("") is False

    def test_extract_dois_from_references(self):
        from app.utils.doi_utils import extract_dois_from_references
        refs = (
            "[1] Smith et al. Nature, 2021. https://doi.org/10.1038/abc1\n"
            "[2] Doe et al. Science, 2022. doi:10.1126/xyz2\n"
        )
        dois = extract_dois_from_references(refs)
        assert len(dois) == 2
        assert "10.1038/abc1" in dois
        assert "10.1126/xyz2" in dois


# ── 3. Text Cleaner & Scanned PDF Detection ──────────────────────────────────

class TestTextCleaner:
    def test_detect_references_section(self):
        from app.utils.text_cleaner import detect_references_section
        full_text = (
            "Section 1: Introduction\n\n"
            "This study investigates neural networks.\n\n"
            "References\n"
            "[1] LeCun, Y. Deep learning. Nature, 2015.\n"
            "[2] Vaswani, A. Attention is all you need. NeurIPS, 2017."
        )
        body, refs = detect_references_section(full_text)
        assert "Introduction" in body
        assert "References" in refs
        assert "Vaswani" in refs

    def test_estimate_scanned_detection(self):
        from app.utils.text_cleaner import estimate_scanned
        assert estimate_scanned("Page 1 text", 10) is True  # Sparse -> likely scanned
        dense_text = "word " * 600
        assert estimate_scanned(dense_text, 2) is False


# ── 4. Citation Extraction Tests ─────────────────────────────────────────────

class TestCitationExtraction:
    def test_numbered_citations(self):
        from app.services.citation_extraction_service import CitationExtractionService
        service = CitationExtractionService()
        text = "Previous studies [1] and recent works [2, 3] showed improvement [4-6]."
        citations = service.extract_in_text_citations(text)
        markers = [c["marker"] for c in citations]
        assert "[1]" in markers
        assert "[2, 3]" in markers
        assert "[4-6]" in markers

    def test_author_year_citations(self):
        from app.services.citation_extraction_service import CitationExtractionService
        service = CitationExtractionService()
        text = "According to (Smith, 2023) and (Vaswani et al., 2017), transformers excel."
        citations = service.extract_in_text_citations(text)
        assert any(c["type"] == "author_year" for c in citations)

    def test_narrative_citations(self):
        from app.services.citation_extraction_service import CitationExtractionService
        service = CitationExtractionService()
        text = "As stated by Brown (2022) and Jones et al. (2020), results are consistent."
        citations = service.extract_in_text_citations(text)
        assert any(c["type"] == "narrative" for c in citations)

    def test_parse_references_numbered(self):
        from app.services.citation_extraction_service import CitationExtractionService
        service = CitationExtractionService()
        bib = (
            "[1] J. Smith, 'Deep Learning Advances', IEEE, 2021. doi:10.1109/test.2021\n"
            "[2] A. Jones, 'Statistical Methods', Springer, 2020."
        )
        refs = service.parse_references_section(bib)
        assert len(refs) == 2
        assert refs[0]["reference_number"] == 1
        assert refs[0]["doi"] == "10.1109/test.2021"


# ── 5. Confidence Calculation Tests ──────────────────────────────────────────

class TestConfidenceScoring:
    def test_full_text_supported_high(self):
        from app.utils.confidence import calculate_confidence
        c = calculate_confidence("full_text", "SUPPORTED", True, True, True, True)
        assert c["level"] == "HIGH"
        assert c["score"] >= 0.75

    def test_abstract_only_reduced(self):
        from app.utils.confidence import calculate_confidence
        c = calculate_confidence("abstract_only", "PARTIALLY_SUPPORTED", True, False, False, True)
        assert c["level"] in ("MEDIUM", "LOW")
        assert c["score"] < 0.75

    def test_needs_human_review_low(self):
        from app.utils.confidence import calculate_confidence
        c = calculate_confidence("full_text", "NEEDS_HUMAN_REVIEW", True, True, True, True)
        assert c["level"] == "LOW"

    def test_missing_source_low(self):
        from app.utils.confidence import calculate_confidence
        c = calculate_confidence("metadata_only", "NEEDS_HUMAN_REVIEW", False, False, False, False)
        assert c["level"] == "LOW"
        assert c["score"] <= 0.2


# ── 6. Verification Engine Scenarios (Mocked) ────────────────────────────────

class TestVerificationEngineScenarios:

    def _setup_pipeline(self, gemini_mock, paper_search_mock, crossref_mock, evidence_mock):
        from app.services.verification_service import VerificationService
        return VerificationService(gemini_mock, paper_search_mock, crossref_mock, evidence_mock)

    @pytest.mark.asyncio
    async def test_scenario_1_supported_claim(self, test_db):
        """Scenario 1: A correctly supported claim with verified source."""
        from app.models.citation import Citation
        from app.models.claim import Claim
        from app.models.document import Document
        from app.models.source import Source

        doc = Document(id="doc-s1", filename="paper.pdf", upload_path="/tmp/p.pdf")
        test_db.add(doc)
        claim = Claim(
            id="claim-s1",
            document_id="doc-s1",
            claim_text="The model achieved 92.4% accuracy on ImageNet.",
            citation_markers=json.dumps(["[1]"]),
            status="pending",
        )
        test_db.add(claim)
        cit = Citation(
            id="cit-s1",
            document_id="doc-s1",
            claim_id="claim-s1",
            citation_marker="[1]",
            doi="10.1038/s123",
            title="Scaling Vision Models",
            year=2023,
        )
        test_db.add(cit)
        test_db.commit()

        mock_gemini = MagicMock()
        mock_gemini.verify_claim = AsyncMock(return_value={
            "verdict": "SUPPORTED",
            "explanation": "The source paper explicitly reports 92.4% top-1 accuracy on ImageNet.",
            "issues": [],
            "human_review_required": False,
            "relevant_passages": ["We obtain 92.4% top-1 accuracy on ImageNet validation set."],
        })

        mock_ps = MagicMock()
        mock_ps.search_by_doi = MagicMock(return_value=None)
        mock_ps.find_best_match = MagicMock(return_value={
            "title": "Scaling Vision Models",
            "authors": ["A. Researcher"],
            "year": 2023,
            "doi": "10.1038/s123",
            "abstract": "We achieve 92.4% accuracy on ImageNet.",
            "pdf_url": "https://example.com/paper.pdf",
            "url": "https://example.com/paper",
        })

        mock_cr = MagicMock()
        mock_cr.verify_doi = MagicMock(return_value={"is_valid": True, "doi": "10.1038/s123"})
        mock_cr.calculate_metadata_match = MagicMock(return_value={"is_good_match": True})

        mock_ev = MagicMock()
        mock_source = Source(
            id="src-s1",
            title="Scaling Vision Models",
            doi="10.1038/s123",
            evidence_type="full_text",
            source_url="https://example.com/paper",
            abstract="We achieve 92.4% accuracy on ImageNet.",
            full_text="We obtain 92.4% top-1 accuracy on ImageNet validation set.",
        )
        mock_ev.retrieve_source_evidence = AsyncMock(return_value=mock_source)
        mock_ev.get_evidence_summary = MagicMock(return_value={
            "evidence_type": "full_text",
            "available_text": mock_source.full_text,
            "relevant_passages": [{"text": "We obtain 92.4% top-1 accuracy", "relevance_score": 0.95}],
            "evidence_quality": "good",
        })

        service = self._setup_pipeline(mock_gemini, mock_ps, mock_cr, mock_ev)
        result = await service.verify_claim(test_db, claim, "/tmp/sources")

        assert result.verdict == "SUPPORTED"
        assert result.human_review_required is False
        assert result.confidence_level in ("HIGH", "MEDIUM")

    @pytest.mark.asyncio
    async def test_scenario_2_partially_supported_claim(self, test_db):
        """Scenario 2: A partially supported claim with caveats."""
        from app.models.claim import Claim
        from app.models.document import Document

        doc = Document(id="doc-s2", filename="study.pdf", upload_path="/tmp/p.pdf")
        test_db.add(doc)
        claim = Claim(id="claim-s2", document_id="doc-s2", claim_text="Drug X cures hypertension in all patients.", status="pending")
        test_db.add(claim)
        test_db.commit()

        mock_gemini = MagicMock()
        mock_gemini.verify_claim = AsyncMock(return_value={
            "verdict": "PARTIALLY_SUPPORTED",
            "explanation": "Drug X showed efficacy in mild hypertension only, not in all patients.",
            "issues": ["Claim generalizes beyond the studied cohort"],
            "human_review_required": True,
            "relevant_passages": ["Drug X reduced blood pressure in mild stage 1 hypertension."],
        })
        mock_ps = MagicMock()
        mock_ps.find_best_match = MagicMock(return_value={"title": "Drug X Trial", "authors": ["B. Doe"], "year": 2022})
        mock_cr = MagicMock()
        mock_ev = MagicMock()
        mock_ev.retrieve_source_evidence = AsyncMock(return_value=None)

        service = self._setup_pipeline(mock_gemini, mock_ps, mock_cr, mock_ev)
        result = await service.verify_claim(test_db, claim, "/tmp/sources")
        assert result.verdict == "PARTIALLY_SUPPORTED"

    @pytest.mark.asyncio
    async def test_scenario_3_unsupported_claim(self, test_db):
        """Scenario 3: An unsupported claim."""
        from app.models.claim import Claim
        from app.models.document import Document

        doc = Document(id="doc-s3", filename="test.pdf", upload_path="/tmp/p.pdf")
        test_db.add(doc)
        claim = Claim(id="claim-s3", document_id="doc-s3", claim_text="Solar activity caused 80% of global temperature change.", status="pending")
        test_db.add(claim)
        test_db.commit()

        mock_gemini = MagicMock()
        mock_gemini.verify_claim = AsyncMock(return_value={
            "verdict": "UNSUPPORTED",
            "explanation": "The cited study does not find that solar activity was the primary driver of temperature change.",
            "issues": ["No statistical evidence found in source to support the 80% figure"],
            "human_review_required": False,
            "relevant_passages": ["Solar forcing accounts for less than 10% of total variance."],
        })
        service = self._setup_pipeline(mock_gemini, MagicMock(), MagicMock(), MagicMock())
        result = await service.verify_claim(test_db, claim, "/tmp/sources")
        assert result.verdict == "UNSUPPORTED"

    @pytest.mark.asyncio
    async def test_scenario_4_contradictory_claim(self, test_db):
        """Scenario 4: A contradictory claim."""
        from app.models.claim import Claim
        from app.models.document import Document

        doc = Document(id="doc-s4", filename="test.pdf", upload_path="/tmp/p.pdf")
        test_db.add(doc)
        claim = Claim(id="claim-s4", document_id="doc-s4", claim_text="Vitamin C was found to increase mortality by 15%.", status="pending")
        test_db.add(claim)
        test_db.commit()

        mock_gemini = MagicMock()
        mock_gemini.verify_claim = AsyncMock(return_value={
            "verdict": "CONTRADICTORY",
            "explanation": "The source study found Vitamin C was associated with a decrease in mortality, not an increase.",
            "issues": ["Direction of effect is inverted from source findings"],
            "human_review_required": False,
            "relevant_passages": ["Vitamin C intake showed a 15% reduction in all-cause mortality."],
        })
        service = self._setup_pipeline(mock_gemini, MagicMock(), MagicMock(), MagicMock())
        result = await service.verify_claim(test_db, claim, "/tmp/sources")
        assert result.verdict == "CONTRADICTORY"

    @pytest.mark.asyncio
    async def test_scenario_5_missing_citation(self, test_db):
        """Scenario 5: Missing citation - should require human review."""
        from app.models.claim import Claim
        from app.models.document import Document

        doc = Document(id="doc-s5", filename="test.pdf", upload_path="/tmp/p.pdf")
        test_db.add(doc)
        claim = Claim(id="claim-s5", document_id="doc-s5", claim_text="Unreferenced assertion regarding physics constants.", status="pending")
        test_db.add(claim)
        test_db.commit()

        mock_gemini = MagicMock()
        mock_gemini.verify_claim = AsyncMock(return_value={
            "verdict": "NEEDS_HUMAN_REVIEW",
            "explanation": "No source paper could be located. Citation is missing.",
            "issues": ["Citation missing or unmatched"],
            "human_review_required": True,
            "relevant_passages": [],
        })
        service = self._setup_pipeline(mock_gemini, MagicMock(), MagicMock(), MagicMock())
        result = await service.verify_claim(test_db, claim, "/tmp/sources")
        assert result.verdict == "NEEDS_HUMAN_REVIEW"
        assert result.human_review_required is True

    @pytest.mark.asyncio
    async def test_scenario_6_incorrect_doi(self, test_db):
        """Scenario 6: Incorrect DOI falls back to title search gracefully."""
        from app.models.claim import Claim
        from app.models.citation import Citation
        from app.models.document import Document
        from app.models.source import Source

        doc = Document(id="doc-s6", filename="test.pdf", upload_path="/tmp/p.pdf")
        test_db.add(doc)
        claim = Claim(id="claim-s6", document_id="doc-s6", claim_text="Quantum teleportation fidelity reached 90%.", status="pending")
        test_db.add(claim)
        cit = Citation(
            id="cit-s6",
            document_id="doc-s6",
            claim_id="claim-s6",
            citation_marker="[1]",
            doi="10.9999/nonexistent.doi",
            title="Quantum Teleportation Progress",
            year=2021,
        )
        test_db.add(cit)
        test_db.commit()

        mock_cr = MagicMock()
        mock_cr.verify_doi = MagicMock(return_value=None)  # 404
        mock_cr.search_by_title = MagicMock(return_value=[])

        mock_ps = MagicMock()
        mock_ps.search_by_doi = MagicMock(return_value=None)
        mock_ps.find_best_match = MagicMock(return_value={
            "title": "Quantum Teleportation Progress",
            "authors": ["C. Quantum"],
            "year": 2021,
            "abstract": "We observe teleportation fidelity of 90%.",
        })

        mock_ev = MagicMock()
        mock_source = Source(
            id="src-s6",
            title="Quantum Teleportation Progress",
            doi="10.9999/nonexistent.doi",
            evidence_type="abstract_only",
            source_url="https://example.com/quantum",
            abstract="We observe teleportation fidelity of 90%.",
        )
        mock_ev.retrieve_source_evidence = AsyncMock(return_value=mock_source)
        mock_ev.get_evidence_summary = MagicMock(return_value={
            "evidence_type": "abstract_only",
            "available_text": mock_source.abstract,
            "relevant_passages": [{"text": "teleportation fidelity of 90%", "relevance_score": 0.9}],
            "evidence_quality": "medium",
        })
        mock_gemini = MagicMock()
        mock_gemini.verify_claim = AsyncMock(return_value={
            "verdict": "SUPPORTED",
            "explanation": "Found via title fallback search; source supports 90% fidelity.",
            "issues": ["Original DOI was invalid; matched via title search"],
            "human_review_required": False,
            "relevant_passages": ["teleportation fidelity of 90%"],
        })

        service = self._setup_pipeline(mock_gemini, mock_ps, mock_cr, mock_ev)
        result = await service.verify_claim(test_db, claim, "/tmp/sources")
        assert result.verdict == "SUPPORTED"

    @pytest.mark.asyncio
    async def test_scenario_7_unavailable_source_paper(self, test_db):
        """Scenario 7: Source paper unavailable - marks as NEEDS_HUMAN_REVIEW."""
        from app.models.claim import Claim
        from app.models.document import Document

        doc = Document(id="doc-s7", filename="test.pdf", upload_path="/tmp/p.pdf")
        test_db.add(doc)
        claim = Claim(id="claim-s7", document_id="doc-s7", claim_text="Proprietary algorithm benchmark claim.", status="pending")
        test_db.add(claim)
        test_db.commit()

        mock_ps = MagicMock()
        mock_ps.find_best_match = MagicMock(return_value=None)
        mock_cr = MagicMock()
        mock_cr.verify_doi = MagicMock(return_value=None)
        mock_cr.search_by_title = MagicMock(return_value=[])

        mock_gemini = MagicMock()
        mock_gemini.verify_claim = AsyncMock(return_value={
            "verdict": "NEEDS_HUMAN_REVIEW",
            "explanation": "Paper could not be retrieved from any repository.",
            "issues": ["Source paper unavailable"],
            "human_review_required": True,
            "relevant_passages": [],
        })

        service = self._setup_pipeline(mock_gemini, mock_ps, mock_cr, MagicMock())
        result = await service.verify_claim(test_db, claim, "/tmp/sources")
        assert result.verdict == "NEEDS_HUMAN_REVIEW"
        assert result.human_review_required is True

    @pytest.mark.asyncio
    async def test_scenario_8_abstract_insufficient_evidence(self, test_db):
        """Scenario 8: Abstract available but lacks statistical proof -> NEEDS_HUMAN_REVIEW."""
        from app.models.claim import Claim
        from app.models.citation import Citation
        from app.models.document import Document
        from app.models.source import Source
        from app.models.source import Source

        doc = Document(id="doc-s8", filename="test.pdf", upload_path="/tmp/p.pdf")
        test_db.add(doc)
        claim = Claim(
            id="claim-s8",
            document_id="doc-s8",
            claim_text="The therapy showed a p-value of 0.0031 in subgroup D.",
            status="pending",
        )
        test_db.add(claim)
        cit = Citation(id="cit-s8", document_id="doc-s8", claim_id="claim-s8", citation_marker="[1]", title="Clinical Trial")
        test_db.add(cit)
        test_db.commit()

        source = Source(
            id="src-s8",
            title="Clinical Trial",
            abstract="We evaluated the therapy in general cohorts.",
            full_text=None,
            evidence_type="abstract_only",
        )
        mock_ev = MagicMock()
        mock_ev.retrieve_source_evidence = AsyncMock(return_value=source)
        mock_ev.get_evidence_summary = MagicMock(return_value={
            "evidence_type": "abstract_only",
            "available_text": source.abstract,
            "relevant_passages": [],
            "evidence_quality": "limited",
        })

        mock_gemini = MagicMock()
        mock_gemini.verify_claim = AsyncMock(return_value={
            "verdict": "NEEDS_HUMAN_REVIEW",
            "explanation": "The abstract does not report subgroup D p-values. Full text inspection required.",
            "issues": ["Abstract lacks subgroup statistical details"],
            "human_review_required": True,
            "relevant_passages": [],
        })

        service = self._setup_pipeline(mock_gemini, MagicMock(), MagicMock(), mock_ev)
        result = await service.verify_claim(test_db, claim, "/tmp/sources")
        assert result.verdict == "NEEDS_HUMAN_REVIEW"
        assert result.confidence_level == "LOW"


# ── 7. Database Persistence Tests ────────────────────────────────────────────

class TestDatabasePersistence:
    def test_document_crud(self, test_db):
        from app.models.document import Document
        doc = Document(
            id="test-doc-1",
            filename="nature_paper.pdf",
            upload_path="/uploads/nature_paper.pdf",
            processing_status="uploaded",
            page_count=12,
        )
        test_db.add(doc)
        test_db.commit()

        fetched = test_db.query(Document).filter(Document.id == "test-doc-1").first()
        assert fetched is not None
        assert fetched.filename == "nature_paper.pdf"
        assert fetched.page_count == 12

    def test_claim_and_citation_relationships(self, test_db):
        from app.models.claim import Claim
        from app.models.citation import Citation
        from app.models.document import Document
        from app.models.source import Source

        doc = Document(id="doc-rel", filename="paper.pdf", upload_path="/tmp/p.pdf")
        test_db.add(doc)

        claim = Claim(
            id="c1",
            document_id="doc-rel",
            claim_text="CRISPR efficiency is 85%.",
            category="experimental",
        )
        test_db.add(claim)

        citation = Citation(
            id="cit1",
            document_id="doc-rel",
            claim_id="c1",
            citation_marker="[1]",
            reference_number=1,
            title="CRISPR Genome Editing",
        )
        test_db.add(citation)
        test_db.commit()

        assert len(doc.claims) == 1
        assert len(doc.citations) == 1
        assert doc.claims[0].citations[0].title == "CRISPR Genome Editing"


# ── 8. Report Service PDF Generation ─────────────────────────────────────────

class TestReportGeneration:
    def test_generate_pdf_report(self, test_db, tmp_path):
        from app.models.claim import Claim
        from app.models.document import Document
        from app.models.verification import Verification
        from app.services.report_service import ReportService

        doc = Document(id="doc-rep", filename="sample.pdf", upload_path="/tmp/sample.pdf", document_title="Sample Study")
        test_db.add(doc)

        claim = Claim(id="c-rep", document_id="doc-rep", claim_text="Finding X is significant (p<0.05).")
        test_db.add(claim)

        v = Verification(
            id="v-rep",
            claim_id="c-rep",
            verdict="SUPPORTED",
            explanation="The source confirms the finding.",
            confidence_level="HIGH",
            confidence_score=0.85,
            evidence_passages=json.dumps([{"text": "Finding X has p=0.03"}]),
        )
        test_db.add(v)
        test_db.commit()

        service = ReportService()
        report_path = service.generate_pdf_report(test_db, "doc-rep")
        import os
        assert os.path.exists(report_path)
        assert os.path.getsize(report_path) > 500  # Non-trivial PDF generated
