"""Scoring and ranking pipeline."""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import numpy as np

from zotwatch.config.settings import Settings
from zotwatch.core.models import CandidateWork, RankedWork
from zotwatch.infrastructure.embedding import (
    CachingEmbeddingProvider,
    EmbeddingCache,
    FaissIndex,
    VoyageEmbedding,
)
from zotwatch.infrastructure.embedding.base import BaseEmbeddingProvider

logger = logging.getLogger(__name__)


@dataclass
class RankerArtifacts:
    """Paths to ranker artifact files."""

    index_path: Path
    profile_path: Path


class WorkRanker:
    """Ranks candidate works using multi-factor scoring."""

    def __init__(
        self,
        base_dir: Path | str,
        settings: Settings,
        vectorizer: Optional[BaseEmbeddingProvider] = None,
        embedding_cache: Optional[EmbeddingCache] = None,
    ):
        """Initialize work ranker.

        Args:
            base_dir: Base directory for data files.
            settings: Application settings.
            vectorizer: Optional base embedding provider (defaults to VoyageEmbedding).
            embedding_cache: Optional embedding cache. If provided, wraps vectorizer
                            with CachingEmbeddingProvider for candidate source type.
        """
        self.base_dir = Path(base_dir)
        self.settings = settings
        self._cache = embedding_cache

        # Create base vectorizer
        base_vectorizer = vectorizer or VoyageEmbedding(
            model_name=settings.embedding.model,
            api_key=settings.embedding.api_key,
            input_type=settings.embedding.input_type,
            batch_size=settings.embedding.batch_size,
        )

        # Wrap with cache if provided
        if embedding_cache is not None:
            self.vectorizer: BaseEmbeddingProvider = CachingEmbeddingProvider(
                provider=base_vectorizer,
                cache=embedding_cache,
                source_type="candidate",
                ttl_days=settings.embedding.candidate_ttl_days,
            )
        else:
            self.vectorizer = base_vectorizer

        self.artifacts = RankerArtifacts(
            index_path=self.base_dir / "data" / "faiss.index",
            profile_path=self.base_dir / "data" / "profile.json",
        )
        self.index = FaissIndex.load(self.artifacts.index_path)
        self.profile = self._load_profile()

    def _load_profile(self) -> dict:
        """Load profile JSON."""
        path = self.artifacts.profile_path
        if not path.exists():
            raise FileNotFoundError("Profile JSON not found; run profile build first.")
        return json.loads(path.read_text(encoding="utf-8"))

    def rank(self, candidates: List[CandidateWork]) -> List[RankedWork]:
        """Rank candidates and return sorted results."""
        if not candidates:
            return []

        # Encode candidates using unified interface (caching handled automatically)
        texts = [c.content_for_embedding() for c in candidates]
        vectors = self.vectorizer.encode(texts)
        logger.info("Scoring %d candidate works", len(candidates))

        distances, _ = self.index.search(vectors, top_k=1)
        weights = self.settings.scoring.weights
        thresholds = self.settings.scoring.thresholds

        ranked: List[RankedWork] = []
        for candidate, vector, distance in zip(candidates, vectors, distances):
            similarity = float(distance[0]) if distance.size else 0.0
            recency_score = _compute_recency(candidate.published, self.settings)
            citation_score = _compute_citation_score(candidate)
            author_bonus = _bonus(candidate.authors, self.settings.scoring.whitelist_authors)
            venue_bonus = _bonus(
                [candidate.venue] if candidate.venue else [],
                self.settings.scoring.whitelist_venues,
            )

            score = (
                similarity * weights.similarity
                + recency_score * weights.recency
                + citation_score * weights.citations
                + author_bonus * weights.author_bonus
                + venue_bonus * weights.venue_bonus
            )

            label = "ignore"
            if score >= thresholds.must_read:
                label = "must_read"
            elif score >= thresholds.consider:
                label = "consider"

            ranked.append(
                RankedWork(
                    **candidate.model_dump(),
                    score=score,
                    similarity=similarity,
                    recency_score=recency_score,
                    metric_score=citation_score,
                    author_bonus=author_bonus,
                    venue_bonus=venue_bonus,
                    label=label,
                )
            )

        ranked.sort(key=lambda w: w.score, reverse=True)
        return ranked


def _bonus(values: List[str], whitelist: List[str]) -> float:
    """Calculate whitelist bonus."""
    whitelist_lower = {v.lower() for v in whitelist}
    for value in values:
        if value and value.lower() in whitelist_lower:
            return 1.0
    return 0.0


def _compute_recency(published: datetime | None, settings: Settings) -> float:
    """Calculate recency score."""
    if not published:
        return 0.0
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta_days = max((now - published).days, 0)
    decay = settings.scoring.decay_days
    if delta_days <= decay.get("fast", 3):
        return 1.0
    if delta_days <= decay.get("medium", 7):
        return 0.7
    if delta_days <= decay.get("slow", 30):
        return 0.4
    return 0.1


def _compute_citation_score(candidate: CandidateWork) -> float:
    """Calculate citation score."""
    citations = float(candidate.metrics.get("cited_by", candidate.metrics.get("is-referenced-by", 0.0)))
    return float(np.log1p(citations)) if citations else 0.0


__all__ = ["WorkRanker"]
