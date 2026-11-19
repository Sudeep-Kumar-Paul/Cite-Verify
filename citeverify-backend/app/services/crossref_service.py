from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import quote

import requests
from fuzzywuzzy import fuzz
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.core.exceptions import ExternalAPIException
from app.utils.doi_utils import normalize_doi

logger = logging.getLogger(__name__)
settings = get_settings()

BASE_URL = "https://api.crossref.org/works"


class CrossrefService:

    def __init__(self):
        email = settings.crossref_email or "citeverify@example.com"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": f"CiteVerify/1.0 (mailto:{email})",
        })
        self.timeout = settings.external_api_timeout_seconds

    def _normalize(self, item: dict) -> dict:
        authors_raw = item.get("author", [])
        authors = []
        for a in authors_raw:
            parts = []
            if a.get("given"):
                parts.append(a["given"])
            if a.get("family"):
                parts.append(a["family"])
            if parts:
                authors.append(" ".join(parts))

        title_list = item.get("title", [])
        title = title_list[0] if title_list else ""
        container_list = item.get("container-title", [])
        journal = container_list[0] if container_list else ""

        published = item.get("published", {}) or {}
        date_parts = published.get("date-parts", [[]])
        year = date_parts[0][0] if date_parts and date_parts[0] else None

        doi = item.get("DOI", "")
        return {
            "doi": normalize_doi(doi) if doi else None,
            "title": title,
            "authors": authors,
            "year": year,
            "journal": journal,
            "publisher": item.get("publisher", ""),
            "doi_url": f"https://doi.org/{doi}" if doi else None,
            "is_valid": True,
        }

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=8), reraise=True)
    def verify_doi(self, doi: str) -> Optional[dict]:
        clean_doi = normalize_doi(doi)
        try:
            resp = self.session.get(
                f"{BASE_URL}/{quote(clean_doi, safe='')}",
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                return self._normalize(data.get("message", {}))
            if resp.status_code == 404:
                logger.info(f"DOI not found in Crossref: {clean_doi}")
                return None
            raise ExternalAPIException("Crossref", f"HTTP {resp.status_code}")
        except requests.Timeout:
            logger.warning(f"Crossref lookup timed out for DOI: {clean_doi}")
            return None
        except ExternalAPIException:
            raise
        except Exception as e:
            logger.error(f"Crossref lookup error: {e}")
            return None

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=8), reraise=True)
    def search_by_title(self, title: str, limit: int = 3) -> list[dict]:
        try:
            resp = self.session.get(
                BASE_URL,
                params={
                    "query.title": title,
                    "rows": limit,
                    "select": "DOI,title,author,published,container-title,publisher",
                },
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                items = resp.json().get("message", {}).get("items", [])
                return [self._normalize(item) for item in items]
            return []
        except requests.Timeout:
            logger.warning("Crossref title search timed out.")
            return []
        except Exception as e:
            logger.error(f"Crossref title search error: {e}")
            return []

    def calculate_metadata_match(self, citation: dict, crossref_result: dict) -> dict:
        title_score = 0.0
        if citation.get("title") and crossref_result.get("title"):
            title_score = fuzz.token_sort_ratio(
                citation["title"].lower(), crossref_result["title"].lower()
            ) / 100.0

        author_score = 0.0
        if citation.get("authors") and crossref_result.get("authors"):
            cit_authors = citation["authors"] if isinstance(citation["authors"], str) else " ".join(citation["authors"])
            res_authors = crossref_result["authors"] if isinstance(crossref_result["authors"], str) else " ".join(crossref_result["authors"])
            author_score = fuzz.token_set_ratio(cit_authors.lower(), res_authors.lower()) / 100.0

        year_match = False
        if citation.get("year") and crossref_result.get("year"):
            try:
                year_match = abs(int(citation["year"]) - int(crossref_result["year"])) <= 1
            except (ValueError, TypeError):
                year_match = False

        overall = title_score * 0.60 + author_score * 0.30 + (0.10 if year_match else 0.0)
        return {
            "title_score": round(title_score, 3),
            "author_score": round(author_score, 3),
            "year_match": year_match,
            "overall_score": round(overall, 3),
            "is_good_match": overall >= 0.70,
        }
