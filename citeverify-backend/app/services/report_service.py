from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.claim import Claim
from app.models.citation import Citation
from app.models.document import Document
from app.models.source import Source
from app.models.verification import Verification

logger = logging.getLogger(__name__)
settings = get_settings()

VERDICT_COLORS = {
    "SUPPORTED": (0.0, 0.5, 0.0),
    "PARTIALLY_SUPPORTED": (0.8, 0.45, 0.0),
    "UNSUPPORTED": (0.8, 0.0, 0.0),
    "CONTRADICTORY": (0.6, 0.0, 0.6),
    "NEEDS_HUMAN_REVIEW": (0.35, 0.35, 0.35),
    "POSSIBLY_OUTDATED": (0.5, 0.3, 0.0),
}


class ReportService:

    def __init__(self):
        Path(settings.reports_dir).mkdir(parents=True, exist_ok=True)

    def generate_summary(self, db: Session, document_id: str) -> dict:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return {}

        claims = db.query(Claim).filter(Claim.document_id == document_id).all()
        citations = db.query(Citation).filter(Citation.document_id == document_id).all()
        matched_citations = [c for c in citations if c.matching_status == "matched"]

        counts = {
            "SUPPORTED": 0,
            "PARTIALLY_SUPPORTED": 0,
            "UNSUPPORTED": 0,
            "CONTRADICTORY": 0,
            "NEEDS_HUMAN_REVIEW": 0,
            "POSSIBLY_OUTDATED": 0,
        }
        claim_summaries = []

        for claim in claims:
            if claim.verifications:
                v = claim.verifications[-1]
                verdict = v.verdict
                counts[verdict] = counts.get(verdict, 0) + 1
                claim_summaries.append({
                    "claim_id": claim.id,
                    "claim_text": claim.claim_text[:200],
                    "verdict": verdict,
                    "confidence_level": v.confidence_level,
                    "human_review_required": v.human_review_required,
                })

        return {
            "document_id": document_id,
            "document_title": document.document_title,
            "filename": document.filename,
            "total_claims": len(claims),
            "total_citations": len(citations),
            "matched_references": len(matched_citations),
            "supported_count": counts["SUPPORTED"],
            "partially_supported_count": counts["PARTIALLY_SUPPORTED"],
            "unsupported_count": counts["UNSUPPORTED"],
            "contradictory_count": counts["CONTRADICTORY"],
            "needs_review_count": counts["NEEDS_HUMAN_REVIEW"],
            "possibly_outdated_count": counts["POSSIBLY_OUTDATED"],
            "claim_summaries": claim_summaries,
            "generated_at": datetime.now(timezone.utc),
        }

    def generate_pdf_report(
        self, db: Session, document_id: str, include_evidence: bool = True
    ) -> str:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            HRFlowable,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        summary = self.generate_summary(db, document_id)
        claims = db.query(Claim).filter(Claim.document_id == document_id).all()

        output_path = str(Path(settings.reports_dir) / f"{document_id}_report.pdf")

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("CoverTitle", parent=styles["Title"], fontSize=22, spaceAfter=10)
        h1_style = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=15, spaceAfter=8)
        h2_style = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, spaceAfter=4)
        body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9, spaceAfter=4)
        small_style = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, textColor=colors.gray)

        story = []

        # Title & Meta
        story.append(Paragraph("CiteVerify — Scientific Verification Report", title_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.navy))
        story.append(Spacer(1, 0.4 * cm))

        doc_title = summary.get("document_title") or summary.get("filename", "Academic Document")
        gen_time = summary.get("generated_at")
        gen_str = gen_time.strftime("%Y-%m-%d %H:%M:%S UTC") if isinstance(gen_time, datetime) else str(gen_time)
        story.append(Paragraph(f"<b>Document Title:</b> {doc_title}", body_style))
        story.append(Paragraph(f"<b>Filename:</b> {summary.get('filename')}", body_style))
        story.append(Paragraph(f"<b>Verification Date:</b> {gen_str}", body_style))
        story.append(Spacer(1, 0.6 * cm))

        # Metrics Table
        data = [
            ["Verification Metric", "Count"],
            ["Total Extracted Claims", str(summary.get("total_claims", 0))],
            ["Total Citations Detected", str(summary.get("total_citations", 0))],
            ["Matched References", str(summary.get("matched_references", 0))],
            ["Supported Claims", str(summary.get("supported_count", 0))],
            ["Partially Supported Claims", str(summary.get("partially_supported_count", 0))],
            ["Unsupported Claims", str(summary.get("unsupported_count", 0))],
            ["Contradictory Claims", str(summary.get("contradictory_count", 0))],
            ["Requires Human Review", str(summary.get("needs_review_count", 0))],
            ["Possibly Outdated", str(summary.get("possibly_outdated_count", 0))],
        ]
        t = Table(data, colWidths=[11 * cm, 4 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.navy),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.96, 0.96, 0.99)]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.8 * cm))

        # Claim-by-claim analysis
        story.append(Paragraph("Detailed Claim-by-Claim Verification", h1_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.navy))
        story.append(Spacer(1, 0.3 * cm))

        for i, claim in enumerate(claims, 1):
            if not claim.verifications:
                continue
            v = claim.verifications[-1]
            source = v.source

            story.append(Paragraph(f"<b>Claim #{i}:</b> <i>\"{claim.claim_text}\"</i>", body_style))

            # Verdict badge
            rgb = VERDICT_COLORS.get(v.verdict, (0.2, 0.2, 0.2))
            v_style = ParagraphStyle(
                f"V_{i}", parent=styles["Normal"],
                textColor=colors.Color(*rgb), fontName="Helvetica-Bold", fontSize=10,
            )
            story.append(Paragraph(f"Verdict: {v.verdict.replace('_', ' ')}", v_style))

            conf_score = f"{v.confidence_score:.0%}" if v.confidence_score is not None else "N/A"
            story.append(Paragraph(
                f"Confidence: <b>{v.confidence_level}</b> ({conf_score}) — {v.confidence_reason or ''}",
                small_style,
            ))

            if source:
                story.append(Paragraph(f"<b>Matched Source:</b> {source.title}", body_style))
                if source.doi:
                    story.append(Paragraph(f"<b>DOI:</b> https://doi.org/{source.doi}", small_style))
                story.append(Paragraph(f"<b>Evidence Type:</b> {source.evidence_type}", small_style))
            else:
                story.append(Paragraph("<b>Matched Source:</b> No verifiable publication found", small_style))

            story.append(Paragraph(f"<b>Analysis:</b> {v.explanation or 'None'}", body_style))

            if include_evidence and v.evidence_passages:
                try:
                    passages = json.loads(v.evidence_passages)
                    if passages:
                        story.append(Paragraph("<b>Retrieved Evidence Passages:</b>", body_style))
                        for p in passages[:2]:
                            excerpt = p.get("text", "")[:350]
                            quote_style = ParagraphStyle(
                                "Quote", parent=styles["Normal"], fontSize=8,
                                leftIndent=15, textColor=colors.navy,
                            )
                            story.append(Paragraph(f'• "{excerpt}"', quote_style))
                except Exception:
                    pass

            if v.issues:
                try:
                    issues = json.loads(v.issues)
                    if issues:
                        for issue in issues:
                            story.append(Paragraph(f"⚠ {issue}", small_style))
                except Exception:
                    pass

            story.append(Spacer(1, 0.4 * cm))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.whitesmoke))

        # Methodology Notes
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("Verification Methodology & Transparency Notice", h1_style))
        notice = (
            "CiteVerify employs multi-stage verification: PDF extraction via PyMuPDF, "
            "DOI and title resolution via Crossref and Semantic Scholar, and claim-to-evidence "
            "comparative analysis with Google Gemini. Automated results are intended to support "
            "scholarly rigor and peer review, not replace human editorial judgment."
        )
        story.append(Paragraph(notice, body_style))

        doc.build(story)
        logger.info(f"Report generated: {output_path}")
        return output_path

    def get_report_path(self, document_id: str) -> Optional[str]:
        path = Path(settings.reports_dir) / f"{document_id}_report.pdf"
        return str(path) if path.exists() else None
