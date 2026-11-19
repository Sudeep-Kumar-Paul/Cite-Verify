from __future__ import annotations

import re
from typing import List, Optional

DOI_PATTERN = re.compile(
    r"10\.\d{4,9}/[^\s\"'<>\[\]{}|\\^`]+"
)
DOI_URL_PREFIXES = [
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "doi:",
]


def extract_doi_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    match = DOI_PATTERN.search(text)
    if match:
        doi = match.group(0).rstrip(".,;)")
        return normalize_doi(doi)
    return None


def normalize_doi(doi: str) -> str:
    if not doi:
        return doi
    doi = doi.strip()
    for prefix in DOI_URL_PREFIXES:
        if doi.lower().startswith(prefix.lower()):
            doi = doi[len(prefix):]
            break
    return doi.lower().strip()


def build_doi_url(doi: str) -> str:
    return f"https://doi.org/{normalize_doi(doi)}"


def is_valid_doi_format(doi: str) -> bool:
    if not doi:
        return False
    doi = normalize_doi(doi)
    return bool(DOI_PATTERN.match(doi))


def extract_dois_from_references(references_text: str) -> List[str]:
    matches = DOI_PATTERN.findall(references_text)
    dois = []
    seen = set()
    for m in matches:
        doi = normalize_doi(m.rstrip(".,;)"))
        if doi not in seen:
            seen.add(doi)
            dois.append(doi)
    return dois
