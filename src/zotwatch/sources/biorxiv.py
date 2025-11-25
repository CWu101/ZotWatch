"""bioRxiv and medRxiv source implementations."""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import requests

from zotwatch.config.settings import Settings
from zotwatch.core.models import CandidateWork

from .base import BaseSource, SourceRegistry, clean_title, parse_date

logger = logging.getLogger(__name__)


class BasePreprintSource(BaseSource):
    """Base class for preprint servers (bioRxiv/medRxiv)."""

    def __init__(self, settings: Settings, server: str):
        super().__init__(settings)
        self.server = server
        self.session = requests.Session()

    def _fetch_preprints(self, days_back: int) -> List[CandidateWork]:
        """Fetch preprints from the server."""
        to_date = datetime.now(timezone.utc)
        from_date = to_date - timedelta(days=days_back)
        url = f"https://api.biorxiv.org/details/{self.server}/{from_date:%Y-%m-%d}/{to_date:%Y-%m-%d}"

        logger.info(
            "Fetching %s preprints from %s to %s",
            self.server,
            from_date.date(),
            to_date.date(),
        )

        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for entry in data.get("collection", []):
            work = self._parse_preprint(entry)
            if work:
                results.append(work)

        logger.info("Fetched %d %s preprints", len(results), self.server)
        return results

    def _parse_preprint(self, entry: dict) -> Optional[CandidateWork]:
        """Parse preprint entry to CandidateWork."""
        title = clean_title(entry.get("title"))
        if not title:
            return None

        doi = entry.get("doi")
        rel_link = entry.get("rel_link") or entry.get("url")
        if not rel_link and doi:
            rel_link = f"https://doi.org/{doi}"

        return CandidateWork(
            source=self.server,
            identifier=doi or entry.get("biorxiv_id") or title,
            title=title,
            abstract=entry.get("abstract"),
            authors=[a.strip() for a in entry.get("authors", "").split(";") if a.strip()],
            doi=doi,
            url=rel_link,
            published=parse_date(entry.get("date")),
            venue=self.server,
            extra={
                "category": entry.get("category"),
                "version": entry.get("version"),
            },
        )


@SourceRegistry.register
class BiorxivSource(BasePreprintSource):
    """bioRxiv preprint source."""

    def __init__(self, settings: Settings):
        super().__init__(settings, "biorxiv")
        self.config = settings.sources.biorxiv

    @property
    def name(self) -> str:
        return "biorxiv"

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    def fetch(self, days_back: int | None = None) -> List[CandidateWork]:
        """Fetch bioRxiv preprints."""
        if days_back is None:
            days_back = self.config.days_back
        return self._fetch_preprints(days_back)


@SourceRegistry.register
class MedrxivSource(BasePreprintSource):
    """medRxiv preprint source."""

    def __init__(self, settings: Settings):
        super().__init__(settings, "medrxiv")
        self.config = settings.sources.medrxiv

    @property
    def name(self) -> str:
        return "medrxiv"

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    def fetch(self, days_back: int | None = None) -> List[CandidateWork]:
        """Fetch medRxiv preprints."""
        if days_back is None:
            days_back = self.config.days_back
        return self._fetch_preprints(days_back)


__all__ = ["BiorxivSource", "MedrxivSource"]
