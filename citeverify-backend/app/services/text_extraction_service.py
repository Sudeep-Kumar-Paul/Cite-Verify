from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
from sqlalchemy.orm import Session

from app.models.document import Document
from app.utils.text_cleaner import (
    clean_extracted_text,
    detect_references_section,
    estimate_scanned,
    extract_page_texts,
)

logger = logging.getLogger(__name__)


class TextExtractionService:

    def extract_text_from_pdf(self, file_path: str) -> dict:
        try:
            doc = fitz.open(file_path)
            pages = extract_page_texts(doc)
            full_text = "\n\n".join(p["text"] for p in pages if p["text"])
            full_text = clean_extracted_text(full_text)
            page_count = len(doc)
            total_chars = sum(p["char_count"] for p in pages)
            is_scanned = estimate_scanned(full_text, page_count)

            # Check if image-only / scanned PDF without embedded text
            has_images = any(len(page.get_images()) > 0 for page in doc)
            doc.close()

            if total_chars < 50 and has_images:
                return {
                    "success": False,
                    "full_text": "",
                    "pages": pages,
                    "page_count": page_count,
                    "total_chars": total_chars,
                    "is_scanned": True,
                    "error": "Document appears to be a scanned or image-only PDF with no selectable text. OCR (Optical Character Recognition) is required to process this file.",
                }

            if not full_text.strip():
                return {
                    "success": False,
                    "full_text": "",
                    "pages": pages,
                    "page_count": page_count,
                    "total_chars": 0,
                    "is_scanned": is_scanned,
                    "error": "PDF document contains no extractable text content.",
                }

            return {
                "success": True,
                "full_text": full_text,
                "pages": pages,
                "page_count": page_count,
                "total_chars": total_chars,
                "is_scanned": is_scanned,
                "error": None,
            }
        except Exception as e:
            logger.error(f"Text extraction failed for PDF {file_path}: {e}")
            return {
                "success": False,
                "full_text": "",
                "pages": [],
                "page_count": 0,
                "total_chars": 0,
                "is_scanned": False,
                "error": f"Failed to extract PDF: {str(e)}",
            }

    def extract_text_from_docx(self, file_path: str) -> dict:
        try:
            import docx

            doc = docx.Document(file_path)
            paragraphs_text = []
            for p in doc.paragraphs:
                text = p.text.strip()
                if text:
                    paragraphs_text.append(text)

            # Also extract table text
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                    if row_text:
                        paragraphs_text.append(row_text)

            full_text = "\n\n".join(paragraphs_text)
            full_text = clean_extracted_text(full_text)
            total_chars = len(full_text)

            if not full_text.strip():
                return {
                    "success": False,
                    "full_text": "",
                    "pages": [],
                    "page_count": 0,
                    "total_chars": 0,
                    "is_scanned": False,
                    "error": "Word document (.docx) is empty and contains no text content.",
                }

            est_pages = max(1, len(doc.paragraphs) // 25)
            pages = [{"page_num": 1, "text": full_text, "char_count": total_chars}]

            return {
                "success": True,
                "full_text": full_text,
                "pages": pages,
                "page_count": est_pages,
                "total_chars": total_chars,
                "is_scanned": False,
                "error": None,
            }
        except Exception as e:
            logger.error(f"Text extraction failed for DOCX {file_path}: {e}")
            return {
                "success": False,
                "full_text": "",
                "pages": [],
                "page_count": 0,
                "total_chars": 0,
                "is_scanned": False,
                "error": f"Failed to extract Word document: {str(e)}",
            }

    def extract_text_from_txt(self, file_path: str) -> dict:
        try:
            content = ""
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(file_path, "r", encoding="latin-1") as f:
                    content = f.read()

            full_text = clean_extracted_text(content)
            total_chars = len(full_text)

            if not full_text.strip():
                return {
                    "success": False,
                    "full_text": "",
                    "pages": [],
                    "page_count": 0,
                    "total_chars": 0,
                    "is_scanned": False,
                    "error": "Text file (.txt) is empty and contains no readable characters.",
                }

            est_pages = max(1, total_chars // 3000)
            pages = [{"page_num": 1, "text": full_text, "char_count": total_chars}]

            return {
                "success": True,
                "full_text": full_text,
                "pages": pages,
                "page_count": est_pages,
                "total_chars": total_chars,
                "is_scanned": False,
                "error": None,
            }
        except Exception as e:
            logger.error(f"Text extraction failed for TXT {file_path}: {e}")
            return {
                "success": False,
                "full_text": "",
                "pages": [],
                "page_count": 0,
                "total_chars": 0,
                "is_scanned": False,
                "error": f"Failed to extract text document: {str(e)}",
            }

    def extract_document_text(self, file_path: str) -> dict:
        ext = Path(file_path).suffix.lower()
        if ext == ".docx":
            return self.extract_text_from_docx(file_path)
        elif ext == ".txt":
            return self.extract_text_from_txt(file_path)
        else:
            return self.extract_text_from_pdf(file_path)

    def detect_document_title(self, text: str) -> Optional[str]:
        if not text:
            return None
        first_part = text[:600]
        lines = [line.strip() for line in first_part.split("\n") if line.strip()]
        for line in lines[:10]:
            if 15 <= len(line) <= 250:
                if not line.replace(" ", "").isdigit():
                    return line
        return None

    def split_body_references(self, full_text: str) -> tuple[str, str]:
        return detect_references_section(full_text)

    def process_document(self, db: Session, document_id: str, file_path: str) -> Document:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        document.processing_status = "extracting"
        db.commit()

        try:
            result = self.extract_document_text(file_path)
            if not result["success"]:
                document.processing_status = "failed"
                document.extraction_error = result["error"]
                db.commit()
                return document

            document.extracted_text = result["full_text"]
            document.page_count = result["page_count"]
            document.is_scanned = result["is_scanned"]

            body_text, references_text = self.split_body_references(result["full_text"])
            document.body_text = body_text
            document.references_text = references_text

            title = self.detect_document_title(result["full_text"])
            document.document_title = title or document.filename

            document.processing_status = "extracted"
            document.extraction_error = None
            db.commit()
            db.refresh(document)
            logger.info(f"Extracted text for document {document_id}: {result['page_count']} pages, {result['total_chars']} chars")
        except Exception as e:
            logger.error(f"Processing failed for document {document_id}: {e}")
            document.processing_status = "failed"
            document.extraction_error = str(e)
            db.rollback()
            db.commit()

        return document
