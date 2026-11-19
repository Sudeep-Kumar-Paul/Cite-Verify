from __future__ import annotations

import json
import logging
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.claim import Claim
from app.models.citation import Citation
from app.models.document import Document
from app.models.source import Source
from app.models.verification import Verification
from app.schemas.document import DocumentListItem, DocumentResponse, ExtractionStatus
from app.services.citation_extraction_service import CitationExtractionService
from app.services.claim_extraction_service import ClaimExtractionService
from app.services.crossref_service import CrossrefService
from app.services.evidence_retrieval_service import EvidenceRetrievalService
from app.services.gemini_service import GeminiService
from app.services.paper_search_service import PaperSearchService
from app.services.pdf_service import PDFService
from app.services.reference_matching_service import ReferenceMatchingService
from app.services.text_extraction_service import TextExtractionService
from app.services.verification_service import VerificationService

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    pdf_service = PDFService()
    upload_info = await pdf_service.save_upload(file, settings.upload_dir)
    validation = pdf_service.validate_document_readable(upload_info["file_path"])

    if not validation["is_valid"]:
        pdf_service.delete_document_files(upload_info["file_path"], settings.upload_dir)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=validation.get("error", "The uploaded file is unreadable, empty, or corrupted."),
        )

    document = Document(
        id=upload_info["document_id"],
        filename=upload_info["original_filename"],
        upload_path=upload_info["file_path"],
        page_count=validation["page_count"],
        processing_status="uploaded",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    logger.info(f"Document registered: {document.id} ({document.filename})")
    return document


@router.get("", response_model=List[DocumentListItem], include_in_schema=False)
@router.get("/", response_model=List[DocumentListItem])
async def list_documents(db: Session = Depends(get_db)):
    return db.query(Document).order_by(Document.upload_date.desc()).all()


@router.post("/demo")
async def load_demo_document(db: Session = Depends(get_db)):
    demo_id = "sample-demo-doc"
    doc = db.query(Document).filter(Document.id == demo_id).first()
    if not doc:
        doc = Document(
            id=demo_id,
            filename="machine_learning_disease_detection.pdf",
            upload_path="demo/machine_learning_disease_detection.pdf",
            page_count=12,
            processing_status="verified",
            document_title="Applications of Machine Learning in Early Disease Detection",
            body_text=(
                "Applications of Machine Learning in Early Disease Detection\n\n"
                "Abstract: Recent advances in artificial intelligence offer unprecedented opportunities "
                "for early clinical intervention across diverse medical specialties.\n\n"
                "1. Introduction\n"
                "Early disease detection remains a critical challenge in modern clinical medicine. "
                "Machine learning methods have emerged as promising tools for identifying subtle biomarkers "
                "before macroscopic symptoms become clinically observable.\n\n"
                "2. Methods\n"
                "A structured literature review was conducted to identify studies applying machine "
                "learning techniques to early disease detection. Studies were assessed for validation "
                "methodology, sample size, and reported diagnostic performance.\n\n"
                "3. Results\n"
                "Recent advances in computer vision have demonstrated considerable promise in ophthalmic "
                "and cardiovascular diagnostics. Deep learning models achieved diagnostic accuracy of 94.5% "
                "in detecting early-stage diabetic retinopathy from retinal fundus images (Gulshan et al., 2016). "
                "Furthermore, machine learning algorithms can predict cardiovascular disease up to 10 years "
                "before clinical symptoms appear, with an accuracy exceeding 90% (Chen et al., 2023).\n\n"
                "4. Discussion\n"
                "These findings suggest a shift in clinical workflows. However, AI-based screening eliminates "
                "the need for specialist review in all early-stage cancer diagnoses is unsupported by current clinical trials. "
                "Support vector machines remain the most accurate approach for medical image classification was valid in earlier "
                "literature but has been largely superseded by deep convolutional architectures."
            ),
        )
        db.add(doc)
        db.commit()

        sample_claims = [
            (
                "Deep learning models achieved diagnostic accuracy of 94.5% in detecting early-stage diabetic retinopathy from retinal fundus images.",
                "Gulshan et al., 2016",
                "10.1001/jama.2016.17216",
                "Development and Validation of a Deep Learning Algorithm for Detection of Diabetic Retinopathy",
                "SUPPORTED",
                "The source supports strong diagnostic performance for diabetic retinopathy detection.",
                "The algorithm had an area under the receiver operating curve of 0.991 for EyePACS-1.",
                0.96,
                3,
            ),
            (
                "Machine learning algorithms can predict cardiovascular disease up to 10 years before clinical symptoms appear, with an accuracy exceeding 90%.",
                "Chen et al., 2023",
                "10.1007/s10916-023-01980-4",
                "Machine learning approaches to cardiovascular risk prediction: a systematic review",
                "PARTIALLY_SUPPORTED",
                "The source supports ML for cardiovascular risk prediction, but abstract does not substantiate 10-year horizon or >90% accuracy across cohorts.",
                "Machine learning methods improved cardiovascular risk prediction compared with established approaches.",
                0.74,
                3,
            ),
            (
                "AI-based screening eliminates the need for specialist review in all early-stage cancer diagnoses.",
                "Esteva et al., 2017",
                "10.1038/nature21056",
                "Dermatologist-level classification of skin cancer with deep neural networks",
                "UNSUPPORTED",
                "The source evaluates image classification, not the elimination of clinical oversight.",
                "We demonstrate classification of skin lesions using a single convolutional neural network.",
                0.92,
                4,
            ),
            (
                "Support vector machines remain the most accurate approach for medical image classification.",
                "Kourou et al., 2015",
                "10.1016/j.csbj.2014.11.005",
                "Machine learning applications in cancer prognosis and prediction",
                "POSSIBLY_OUTDATED",
                "This review predates deep learning advances; it discusses SVMs but does not establish their continued superiority.",
                "Machine learning techniques have been widely applied in cancer research.",
                0.88,
                4,
            ),
            (
                "Convolutional neural networks demonstrate dermatologist-level performance in skin lesion classification.",
                "Esteva et al., 2017",
                "10.1038/nature21056",
                "Dermatologist-level classification of skin cancer with deep neural networks",
                "SUPPORTED",
                "The source directly supports this comparison in tested skin lesion classification tasks.",
                "The CNN achieves performance on par with all tested experts across both tasks.",
                0.98,
                5,
            ),
        ]

        for i, (text, cit, doi, title, verdict, expl, quote, conf, pg) in enumerate(sample_claims, start=1):
            source = Source(
                id=f"src-demo-{i}",
                title=title,
                doi=doi,
                evidence_type="abstract_only",
                source_url=f"https://doi.org/{doi}" if doi else None,
                abstract=quote,
                crossref_verified=True,
            )
            db.merge(source)
            claim = Claim(
                id=f"claim-demo-{i}",
                document_id=demo_id,
                claim_text=text,
                page_number=pg,
                category="experimental",
                citation_markers=json.dumps([cit]),
                status="verified",
            )
            db.merge(claim)
            citation = Citation(
                id=f"cit-demo-{i}",
                document_id=demo_id,
                claim_id=claim.id,
                citation_marker=cit,
                doi=doi,
                title=title,
                matching_status="matched",
            )
            db.merge(citation)
            verif = Verification(
                id=f"verif-demo-{i}",
                claim_id=claim.id,
                source_id=source.id,
                verdict=verdict,
                explanation=expl,
                evidence_passages=json.dumps([{"text": quote, "page_number": pg, "source_url": f"https://doi.org/{doi}"}]),
                confidence_level="HIGH" if conf >= 0.8 else "MEDIUM",
                confidence_score=conf,
                confidence_reason="Verified against peer-reviewed publication metadata and abstract evidence.",
                issues=json.dumps([]),
                human_review_required=verdict in ["NEEDS_HUMAN_REVIEW", "UNSUPPORTED"],
            )
            db.merge(verif)
        db.commit()

    verif_service = VerificationService()
    results = verif_service.get_verification_results(db, demo_id)
    return {
        "document_id": demo_id,
        "document_title": doc.document_title,
        "filename": doc.filename,
        "page_count": doc.page_count,
        "body_text": doc.body_text,
        "results": results,
        "total_claims": len(results),
        "is_demo": True,
        "message": "Demo document loaded successfully.",
    }


@router.post("/{document_id}/pipeline")
async def process_document_pipeline(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    # 1. Text extraction
    text_service = TextExtractionService()
    if not doc.extracted_text:
        doc = text_service.process_document(db, document_id, doc.upload_path)
        if doc.processing_status == "failed":
            raise HTTPException(status_code=422, detail=f"Text extraction failed: {doc.extraction_error}")

    if not doc.extracted_text or len(doc.extracted_text.strip()) < 20:
        raise HTTPException(
            status_code=422,
            detail="The document contains no readable text content to verify.",
        )

    # 2. Claim extraction
    gemini = GeminiService()
    claim_service = ClaimExtractionService(gemini)
    claims = db.query(Claim).filter(Claim.document_id == document_id).all()
    if not claims:
        claims = await claim_service.extract_claims(db, document_id)

    if not claims:
        return {
            "success": True,
            "document_id": document_id,
            "job_id": f"job-{uuid.uuid4().hex[:12]}",
            "filename": doc.filename,
            "document_title": doc.document_title or doc.filename,
            "extraction_status": doc.processing_status,
            "page_count": doc.page_count,
            "body_text": doc.body_text or doc.extracted_text,
            "results": [],
            "claims": [],
            "summary": {
                "total_claims": 0,
                "supported": 0,
                "partially_supported": 0,
                "unsupported": 0,
                "contradictory": 0,
                "needs_human_review": 0,
                "possibly_outdated": 0,
            },
            "total_claims": 0,
            "message": "No verifiable scientific claims or research statements found in this document.",
        }

    # 3. Citation extraction
    citation_service = CitationExtractionService()
    citations = db.query(Citation).filter(Citation.document_id == document_id).all()
    if not citations:
        await citation_service.extract_all_citations(db, document_id, gemini_service=gemini)

    # 4. Reference matching
    ref_service = ReferenceMatchingService()
    ref_service.match_all_citations(db, document_id)
    ref_service.associate_citations_with_claims(db, document_id)

    # 5. Verification
    verif_service = VerificationService(gemini, PaperSearchService(), CrossrefService(), EvidenceRetrievalService())
    verifications = await verif_service.run_verification(db, document_id)
    results_dicts = [verif_service.build_result_dict(v, v.claim, v.source) for v in verifications]

    counts = {
        "supported": 0,
        "partially_supported": 0,
        "unsupported": 0,
        "contradictory": 0,
        "needs_human_review": 0,
        "possibly_outdated": 0,
    }
    for r in results_dicts:
        v = (r.get("verdict") or "").lower()
        if v in counts:
            counts[v] += 1

    return {
        "success": True,
        "document_id": document_id,
        "job_id": f"job-{uuid.uuid4().hex[:12]}",
        "filename": doc.filename,
        "document_title": doc.document_title or doc.filename,
        "extraction_status": doc.processing_status,
        "page_count": doc.page_count,
        "body_text": doc.body_text or doc.extracted_text,
        "results": results_dicts,
        "claims": results_dicts,
        "summary": {
            "total_claims": len(results_dicts),
            **counts,
        },
        "total_claims": len(results_dicts),
        "message": f"Pipeline complete: {len(results_dicts)} claims verified.",
    }


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")
    return doc


@router.post("/{document_id}/extract", response_model=ExtractionStatus)
async def extract_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    service = TextExtractionService()
    updated = service.process_document(db, document_id, doc.upload_path)

    if updated.processing_status == "failed":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=updated.extraction_error or "Text extraction failed.",
        )

    return ExtractionStatus(
        document_id=document_id,
        status=updated.processing_status,
        page_count=updated.page_count,
        has_body=bool(updated.body_text),
        has_references=bool(updated.references_text),
        is_scanned=updated.is_scanned or False,
        message="Extraction completed successfully.",
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")
    pdf_service = PDFService()
    pdf_service.delete_document_files(doc.upload_path, settings.upload_dir)
    db.delete(doc)
    db.commit()
