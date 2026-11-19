from __future__ import annotations

import re
import unicodedata
from typing import List


def clean_extracted_text(text: str) -> str:
    if not text:
        return ""
    # Remove null bytes and non-printable control characters (keep newlines, tabs)
    text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C" or ch in "\n\t\r")
    # Normalize unicode
    text = unicodedata.normalize("NFKC", text)
    # Collapse multiple blank lines to max 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove trailing whitespace from each line
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def detect_references_section(text: str) -> tuple[str, str]:
    patterns = [
        r"(?im)^(references|bibliography|works\s+cited|reference\s+list|literature\s+cited)\s*$",
        r"(?im)^(references|bibliography|works\s+cited|reference\s+list)\s*\n",
    ]
    split_pos = -1
    for pattern in patterns:
        matches = list(re.finditer(pattern, text))
        if matches:
            # Use LAST match to avoid splitting on "References" in body text
            split_pos = matches[-1].start()
            break
    if split_pos == -1:
        return text, ""
    body = text[:split_pos].strip()
    references = text[split_pos:].strip()
    return body, references


def extract_page_texts(doc) -> List[dict]:
    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        pages.append({
            "page_num": page_num + 1,
            "text": clean_extracted_text(text),
            "char_count": len(text),
        })
    return pages


def estimate_scanned(text: str, page_count: int) -> bool:
    if page_count <= 0:
        return False
    avg_chars = len(text.strip()) / page_count
    return avg_chars < 100


def normalize_whitespace(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"[^\S\n]+", " ", text)
    return text.strip()
