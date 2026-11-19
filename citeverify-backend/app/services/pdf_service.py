from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Optional

import aiofiles
import fitz  # PyMuPDF
from fastapi import UploadFile

from app.config import get_settings
from app.core.exceptions import ValidationException
from app.core.security import (
    safe_filename,
    validate_document_file,
    validate_file_path,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class PDFService:

    async def save_upload(self, file: UploadFile, upload_dir: str) -> dict:
        filename = file.filename or "document.pdf"
        content_type = file.content_type or "application/octet-stream"
        content = await file.read()
        size_bytes = len(content)

        # Validate format, length, characters, and non-empty file
        validate_document_file(filename, content_type, size_bytes, settings.max_upload_size_mb)

        document_id = uuid.uuid4().hex
        safe_name = safe_filename(filename)
        doc_dir = Path(upload_dir) / document_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        file_path = doc_dir / safe_name

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        logger.info(f"Saved upload: document_id={document_id}, path={file_path}, size={size_bytes}B")
        return {
            "document_id": document_id,
            "original_filename": filename,
            "safe_filename": safe_name,
            "file_path": str(file_path),
            "file_size_bytes": size_bytes,
        }

    def validate_document_readable(self, file_path: str) -> dict:
        ext = Path(file_path).suffix.lower()

        if ext == ".docx":
            try:
                import docx
                doc = docx.Document(file_path)
                p_count = len(doc.paragraphs)
                est_pages = max(1, p_count // 25)
                return {
                    "is_valid": True,
                    "page_count": est_pages,
                    "error": None,
                    "is_encrypted": False,
                }
            except Exception as e:
                logger.error(f"DOCX readability validation error for {file_path}: {e}")
                return {
                    "is_valid": False,
                    "page_count": 0,
                    "error": f"Invalid or corrupted Word document: {str(e)}",
                    "is_encrypted": False,
                }

        elif ext == ".txt":
            try:
                content = ""
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except UnicodeDecodeError:
                    with open(file_path, "r", encoding="latin-1") as f:
                        content = f.read()

                if not content.strip():
                    return {
                        "is_valid": False,
                        "page_count": 0,
                        "error": "Text file is empty and contains no readable characters.",
                        "is_encrypted": False,
                    }

                est_pages = max(1, len(content) // 3000)
                return {
                    "is_valid": True,
                    "page_count": est_pages,
                    "error": None,
                    "is_encrypted": False,
                }
            except Exception as e:
                logger.error(f"TXT readability validation error for {file_path}: {e}")
                return {
                    "is_valid": False,
                    "page_count": 0,
                    "error": f"Invalid or unreadable text document: {str(e)}",
                    "is_encrypted": False,
                }

        # PDF handling
        try:
            doc = fitz.open(file_path)
            is_encrypted = doc.is_encrypted
            if is_encrypted:
                doc.close()
                return {
                    "is_valid": False,
                    "page_count": 0,
                    "error": "PDF is encrypted or password-protected.",
                    "is_encrypted": True,
                }
            page_count = len(doc)
            if page_count == 0:
                doc.close()
                return {
                    "is_valid": False,
                    "page_count": 0,
                    "error": "PDF document contains 0 pages.",
                    "is_encrypted": False,
                }
            doc.close()
            return {
                "is_valid": True,
                "page_count": page_count,
                "error": None,
                "is_encrypted": False,
            }
        except Exception as e:
            logger.error(f"PDF validation error for {file_path}: {e}")
            return {
                "is_valid": False,
                "page_count": 0,
                "error": f"Unreadable or corrupted PDF document: {str(e)}",
                "is_encrypted": False,
            }

    def validate_pdf_readable(self, file_path: str) -> dict:
        """Backward-compatible validation function."""
        return self.validate_document_readable(file_path)

    def delete_document_files(self, file_path: str, upload_dir: Optional[str] = None) -> bool:
        try:
            fp = Path(file_path)
            if not fp.exists():
                return False
            base = Path(upload_dir or settings.upload_dir).resolve()
            if upload_dir and not validate_file_path(str(fp.parent), str(base)):
                logger.warning(f"Attempted path traversal deletion: {file_path}")
                return False
            if fp.is_file():
                fp.unlink()
            parent = fp.parent
            if parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
            return True
        except Exception as e:
            logger.error(f"Error deleting files at {file_path}: {e}")
            return False

    def get_file_size_mb(self, file_path: str) -> float:
        try:
            return os.path.getsize(file_path) / (1024 * 1024)
        except OSError:
            return 0.0
