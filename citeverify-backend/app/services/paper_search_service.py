from __future__ import annotations

import logging
from typing import Optional

import requests
from fuzzywuzzy import fuzz
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.core.exceptions import ExternalAPIException

logger = logging.getLogger(__name__)
settings = get_settings()

BASE_URL = "https://api.semanticscholar.org/graph/v1"
FIELDS = "title,authors,year,externalIds,abstract,openAccessPdf,url"


class PaperSearchService:

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "CiteVerify/1.0 (academic verification tool)"})
        if settings.semantic_scholar_api_key:
            self.session.headers["x-api-key"] = settings.semantic_scholar_api_key
        self.timeout = settings.external_api_timeout_seconds

    def _normalize_paper(self, item: dict) -> dict:
        authors = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]
        external_ids = item.get("externalIds", {}) or {}
        open_access = item.get("openAccessPdf") or {}
        return {
            "semantic_scholar_id": item.get("paperId", ""),
            "title": item.get("title", ""),
            "authors": authors,
            "year": item.get("year"),
            "doi": external_ids.get("DOI"),
            "abstract": item.get("abstract", "") or "",
            "pdf_url": open_access.get("url"),
            "url": item.get("url", ""),
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def search_by_title(self, title: str, limit: int = 5) -> list[dict]:
        try:
            resp = self.session.get(
                f"{BASE_URL}/paper/search",
                params={"query": title, "fields": FIELDS, "limit": limit},
                timeout=self.timeout,
            )
            if resp.status_code == 429:
                logger.warning("Semantic Scholar rate limit hit (429). Falling back to Crossref.")
                return []
            if resp.status_code == 200:
                data = resp.json()
                return [self._normalize_paper(p) for p in data.get("data", [])]
            logger.warning(f"Semantic Scholar returned status {resp.status_code}")
            return []
        except requests.Timeout:
            logger.warning("Semantic Scholar request timed out.")
            return []
        except Exception as e:
            logger.error(f"Semantic Scholar search exception: {e}")
            return []

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=8), reraise=True)
    def search_by_doi(self, doi: str) -> Optional[dict]:
        try:
            resp = self.session.get(
                f"{BASE_URL}/paper/DOI:{doi}",
                params={"fields": FIELDS},
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                return self._normalize_paper(resp.json())
            if resp.status_code == 404:
                return None
            logger.warning(f"Semantic Scholar DOI lookup returned {resp.status_code}")
            return None
        except requests.Timeout:
            logger.warning("Semantic Scholar DOI lookup timed out.")
            return None
        except Exception as e:
            logger.error(f"DOI lookup exception: {e}")
            return None

    def calculate_title_match_score(self, query: str, result_title: str) -> float:
        if not query or not result_title:
            return 0.0
        return fuzz.token_sort_ratio(query.lower(), result_title.lower()) / 100.0

    def find_best_match(
        self, title: str, authors: str = "", year: Optional[int] = None
    ) -> Optional[dict]:
        results = self.search_by_title(title, limit=5)
        if not results:
            logger.info(f"No Semantic Scholar matches for: {title[:60]}")
            return None

        scored = []
        for result in results:
            title_score = self.calculate_title_match_score(title, result.get("title", ""))
            author_score = 0.0
            if authors and result.get("authors"):
                result_authors_str = " ".join(result["authors"])
                author_score = fuzz.token_set_ratio(authors.lower(), result_authors_str.lower()) / 100.0
            year_bonus = 0.05 if (year and result.get("year") == year) else 0.0

            combined = title_score * 0.70 + author_score * 0.25 + year_bonus
            scored.append((result, combined))

        scored.sort(key=lambda x: x[1], reverse=True)
        best, best_score = scored[0]

        if best_score < 0.65:
            logger.info(f"Top match score ({best_score:.2f}) below threshold for query '{title[:60]}'")
            return None

        logger.info(f"Found matched paper ({best_score:.2f}): {best.get('title', '')[:60]}")
        return best
