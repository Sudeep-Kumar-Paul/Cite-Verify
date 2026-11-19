from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import requests
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.citation import Citation
from app.models.source import Source

logger = logging.getLogger(__name__)
settings = get_settings()

MAX_SOURCE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB


class EvidenceRetrievalService:

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "CiteVerify/1.0 (academic evidence retriever)"})
        self.timeout = settings.external_api_timeout_seconds

    def download_open_access_pdf(
        self, pdf_url: str, save_dir: str, source_id: str
    ) -> dict:
        try:
            Path(save_dir).mkdir(parents=True, exist_ok=True)
            resp = self.session.get(pdf_url, timeout=self.timeout, stream=True)
            if resp.status_code != 200:
                return {
                    "success": False,
                    "file_path": None,
                    "error": f"HTTP {resp.status_code}",
                    "file_size_bytes": 0,
                }

            content_type = resp.headers.get("content-type", "")
            if "pdf" not in content_type.lower() and not pdf_url.lower().endswith(".pdf"):
                return {
                    "success": False,
                    "file_path": None,
                    "error": "URL did not return application/pdf",
                    "file_size_bytes": 0,
                }

            file_path = Path(save_dir) / f"{source_id}.pdf"
            total_size = 0
            with open(file_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    total_size += len(chunk)
                    if total_size > MAX_SOURCE_SIZE_BYTES:
                        file_path.unlink(missing_ok=True)
                        return {
                            "success": False,
                            "file_path": None,
                            "error": "Source PDF exceeded size limit (>100MB)",
                            "file_size_bytes": total_size,
                        }
                    f.write(chunk)

            # Validate readable with PyMuPDF
            try:
                doc = fitz.open(str(file_path))
                if len(doc) == 0:
                    doc.close()
                    file_path.unlink(missing_ok=True)
                    return {
                        "success": False,
                        "file_path": None,
                        "error": "Downloaded PDF contains zero pages",
                        "file_size_bytes": total_size,
                    }
                doc.close()
            except Exception as e:
                file_path.unlink(missing_ok=True)
                return {
                    "success": False,
                    "file_path": None,
                    "error": f"Corrupt PDF file: {e}",
                    "file_size_bytes": total_size,
                }

            return {
                "success": True,
                "file_path": str(file_path),
                "error": None,
                "file_size_bytes": total_size,
            }
        except requests.Timeout:
            return {
                "success": False,
                "file_path": None,
                "error": "Download connection timed out",
                "file_size_bytes": 0,
            }
        except Exception as e:
            logger.error(f"Open-access PDF download error: {e}")
            return {
                "success": False,
                "file_path": None,
                "error": str(e),
                "file_size_bytes": 0,
            }

    def extract_text_from_source_pdf(self, file_path: str) -> dict:
        try:
            doc = fitz.open(file_path)
            pages = []
            full_text_parts = []
            for i in range(len(doc)):
                page = doc[i]
                text = page.get_text("text").strip()
                pages.append({"page_num": i + 1, "text": text})
                if text:
                    full_text_parts.append(text)
            doc.close()
            return {
                "full_text": "\n\n".join(full_text_parts),
                "pages": pages,
                "page_count": len(pages),
            }
        except Exception as e:
            logger.error(f"Text extraction failed on source PDF {file_path}: {e}")
            return {"full_text": "", "pages": [], "page_count": 0}

    def find_relevant_passages(
        self, source_text: str, claim_text: str, window_size: int = 500
    ) -> list[dict]:
        if not source_text or not claim_text:
            return []

        claim_words = set(claim_text.lower().split())
        stopwords = {
            "the", "a", "an", "and", "or", "in", "of", "to", "is", "are", "was",
            "were", "that", "this", "it", "for", "with", "as", "at", "by", "from",
            "on", "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might", "which", "who",
        }
        claim_keywords = claim_words - stopwords

        words = source_text.split()
        window_words = max(20, window_size // 5)
        step = max(1, window_words // 2)

        scored_passages = []
        for i in range(0, max(1, len(words) - window_words), step):
            window = words[i:i + window_words]
            window_text = " ".join(window)
            window_lower = window_text.lower()
            keyword_hits = sum(1 for kw in claim_keywords if kw in window_lower)
            if keyword_hits == 0:
                continue
            score = keyword_hits / max(len(claim_keywords), 1)
            scored_passages.append({
                "text": window_text,
                "page_number": None,
                "relevance_score": score,
            })

        scored_passages.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored_passages[:5]

    async def retrieve_source_evidence(
        self, db: Session, citation: Citation, paper_data: dict, downloads_dir: str
    ) -> Source:
        doi = paper_data.get("doi")
        if doi:
            existing = db.query(Source).filter(Source.doi == doi).first()
            if existing:
                return existing

        source_id = str(uuid.uuid4())
        pdf_url = paper_data.get("pdf_url")
        full_text = None
        evidence_type = "metadata_only"
        retrieval_error = None

        if pdf_url:
            download_result = self.download_open_access_pdf(pdf_url, downloads_dir, source_id)
            if download_result["success"]:
                extracted = self.extract_text_from_source_pdf(download_result["file_path"])
                full_text = extracted.get("full_text", "")
                evidence_type = "full_text" if full_text else "abstract_only"
            else:
                retrieval_error = download_result.get("error")
                evidence_type = "abstract_only" if paper_data.get("abstract") else "metadata_only"
        elif paper_data.get("abstract"):
            evidence_type = "abstract_only"

        source = Source(
            id=source_id,
            title=paper_data.get("title", "Unknown"),
            authors=json.dumps(paper_data.get("authors", [])),
            publication_year=paper_data.get("year"),
            doi=doi,
            source_url=paper_data.get("url"),
            pdf_url=pdf_url,
            abstract=paper_data.get("abstract"),
            full_text=full_text,
            evidence_type=evidence_type,
            semantic_scholar_id=paper_data.get("semantic_scholar_id"),
            crossref_verified=paper_data.get("crossref_verified", False),
            retrieval_date=datetime.now(timezone.utc),
            retrieval_error=retrieval_error,
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        return source

    def get_evidence_summary(self, source: Source, claim_text: str) -> dict:
        available_text = source.full_text or source.abstract or ""
        passages = self.find_relevant_passages(available_text, claim_text) if available_text else []
        if source.evidence_type == "full_text":
            quality = "good"
        elif source.evidence_type == "abstract_only":
            quality = "limited"
        else:
            quality = "insufficient"
        return {
            "evidence_type": source.evidence_type,
            "available_text": available_text,
            "relevant_passages": passages,
            "evidence_quality": quality,
        }
