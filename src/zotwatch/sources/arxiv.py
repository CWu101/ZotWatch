"""arXiv source implementation."""

import logging
from datetime import datetime, timedelta, timezone
from typing import List

import feedparser
import requests

from zotwatch.config.settings import Settings
from zotwatch.core.models import CandidateWork

from .base import BaseSource, SourceRegistry, clean_title, parse_date

logger = logging.getLogger(__name__)


@SourceRegistry.register
class ArxivSource(BaseSource):
    """arXiv preprint source."""

    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.config = settings.sources.arxiv
        self.session = requests.Session()

    @property
    def name(self) -> str:
        return "arxiv"

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    def fetch(self, days_back: int | None = None) -> List[CandidateWork]:
        """Fetch arXiv entries."""
        if days_back is None:
            days_back = self.config.days_back

        categories = self.config.categories
        to_date = datetime.now(timezone.utc)
        from_date = to_date - timedelta(days=days_back)

        # Use submittedDate filter for date range
        date_filter = f"submittedDate:[{from_date:%Y%m%d}0000+TO+{to_date:%Y%m%d}2359]"
        cat_query = " OR ".join(f"cat:{cat}" for cat in categories)
        query = f"({cat_query})+AND+{date_filter}"

        url = "https://export.arxiv.org/api/query"
        params = {
            "search_query": query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": self.config.max_results,
        }

        logger.info(
            "Fetching arXiv entries for categories: %s (last %d days, max %d)",
            ", ".join(categories),
            days_back,
            self.config.max_results,
        )

        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)

        results = []
        for entry in feed.entries:
            title = clean_title(entry.get("title"))
            if not title:
                continue
            identifier = entry.get("id")
            published = parse_date(entry.get("published"))
            results.append(
                CandidateWork(
                    source="arxiv",
                    identifier=identifier or title,
                    title=title,
                    abstract=(entry.get("summary") or "").strip() or None,
                    authors=[a.get("name") for a in entry.get("authors", [])],
                    doi=entry.get("arxiv_doi"),
                    url=entry.get("link"),
                    published=published,
                    venue="arXiv",
                    extra={"primary_category": entry.get("arxiv_primary_category", {}).get("term")},
                )
            )

        logger.info("Fetched %d arXiv entries", len(results))
        return results


__all__ = ["ArxivSource"]
