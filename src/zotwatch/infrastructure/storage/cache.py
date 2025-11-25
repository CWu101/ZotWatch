"""File-based caching utilities."""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from zotwatch.core.models import CandidateWork
from zotwatch.utils.datetime import ensure_isoformat, iso_to_datetime, utc_now, ensure_aware

logger = logging.getLogger(__name__)


class FileCache:
    """File-based JSON cache for candidates."""

    def __init__(self, cache_path: Path | str, ttl_hours: int = 12):
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)

    def load(self) -> Optional[Tuple[datetime, List[CandidateWork]]]:
        """Load candidates from cache if valid."""
        if not self.cache_path.exists():
            return None

        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to read candidate cache: %s", exc)
            return None

        fetched_at = iso_to_datetime(payload.get("fetched_at"))
        if not fetched_at:
            return None

        items = payload.get("candidates", [])
        candidates: List[CandidateWork] = []
        for item in items:
            published = item.get("published")
            if published:
                item["published"] = ensure_aware(iso_to_datetime(published))
            candidates.append(CandidateWork(**item))

        return fetched_at, candidates

    def load_if_valid(self) -> Optional[List[CandidateWork]]:
        """Load candidates only if cache is still valid."""
        result = self.load()
        if not result:
            return None

        fetched_at, candidates = result
        age = datetime.now(timezone.utc) - fetched_at

        if age <= self.ttl:
            logger.info(
                "Using cached candidate list from %s (age %.1f hours)",
                fetched_at.isoformat(),
                age.total_seconds() / 3600,
            )
            return candidates

        logger.info(
            "Candidate cache is stale (age %.1f hours); refreshing",
            age.total_seconds() / 3600,
        )
        return None

    def save(self, candidates: List[CandidateWork]) -> None:
        """Save candidates to cache."""
        payload = {
            "fetched_at": ensure_isoformat(utc_now()),
            "candidates": [self._serialize_candidate(c) for c in candidates],
        }
        try:
            self.cache_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Failed to write candidate cache: %s", exc)

    @staticmethod
    def _serialize_candidate(candidate: CandidateWork) -> Dict[str, Any]:
        """Serialize candidate for JSON storage."""
        data = candidate.model_dump()
        data["published"] = ensure_isoformat(candidate.published)
        return data


__all__ = ["FileCache"]
