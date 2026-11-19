from __future__ import annotations

import os
import uuid
from pathlib import Path

from slugify import slugify

from app.core.exceptions import ValidationException

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
    "text/markdown",
    "application/octet-stream",
}


def validate_document_file(filename: str, content_type: str, size_bytes: int, max_mb: int) -> None:
    if not filename or len(filename) > 500:
        raise ValidationException(message="Invalid or missing filename.")

    dangerous_chars = ["..", "\\", "/", "\x00"]
    for char in dangerous_chars:
        if char in filename and char != "/":
            raise ValidationException(message=f"Filename contains invalid characters: {char}")

    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValidationException(
            message=f"Unsupported file format '{ext or 'unknown'}'. CiteVerify supports PDF (.pdf), Word (.docx), and plain text (.txt) files.",
            detail=f"Received filename: {filename}",
        )

    if size_bytes == 0:
        raise ValidationException(
            message="Uploaded file is empty (0 bytes). Please upload a valid document containing scientific content.",
            detail="The file has zero content.",
        )

    max_bytes = max_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise ValidationException(
            message=f"File too large. Maximum allowed size is {max_mb} MB.",
            detail=f"File size: {size_bytes / (1024 * 1024):.1f} MB, limit: {max_mb} MB",
        )


def validate_pdf_file(filename: str, content_type: str, size_bytes: int, max_mb: int) -> None:
    """Backward-compatible validator delegating to validate_document_file."""
    validate_document_file(filename, content_type, size_bytes, max_mb)


def safe_filename(original_filename: str) -> str:
    path_obj = Path(original_filename)
    stem = path_obj.stem
    ext = path_obj.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        ext = ".pdf"
    safe_stem = slugify(stem, max_length=100) or "document"
    unique_id = uuid.uuid4().hex[:8]
    return f"{unique_id}_{safe_stem}{ext}"


def validate_file_path(path: str, base_dir: str) -> bool:
    try:
        resolved_path = Path(path).resolve()
        resolved_base = Path(base_dir).resolve()
        return resolved_path.is_relative_to(resolved_base)
    except (ValueError, OSError):
        return False
