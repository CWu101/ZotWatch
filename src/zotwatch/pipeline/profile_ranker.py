"""Profile-based ranking pipeline."""

import logging
from dataclasses import dataclass
from pathlib import Path

from zotwatch.config.settings import Settings
from zotwatch.core.models import CandidateWork, RankedWork
from zotwatch.infrastructure.embedding import (
    CachingEmbeddingProvider,
    EmbeddingCache,
    FaissIndex,
    VoyageEmbedding,
)
from zotwatch.infrastructure.embedding.base import BaseEmbeddingProvider
from zotwatch.pipeline.journal_scorer import JournalScorer

logger = logging.getLogger(__name__)


@dataclass
class RankerArtifacts:
    """Paths to ranker artifact files."""

    index_path: Path


class ProfileRanker:
    """Ranks candidate works by embedding similarity to user's library profile."""

    def __init__(
        self,
        base_dir: Path | str,
        settings: Settings,
        vectorizer: BaseEmbeddingProvider | None = None,
        embedding_cache: EmbeddingCache | None = None,
    ):
        """Initialize profile ranker.

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
        )
        self.index = FaissIndex.load(self.artifacts.index_path)
        self._journal_scorer = JournalScorer(self.base_dir)

    def rank(self, candidates: list[CandidateWork]) -> list[RankedWork]:
        """Rank candidates by embedding similarity."""
        if not candidates:
            return []

        # Encode candidates using unified interface (caching handled automatically)
        texts = [c.content_for_embedding() for c in candidates]
        vectors = self.vectorizer.encode(texts)
        logger.info("Scoring %d candidate works", len(candidates))

        distances, _ = self.index.search(vectors, top_k=1)
        thresholds = self.settings.scoring.thresholds

        ranked: list[RankedWork] = []
        for candidate, distance in zip(candidates, distances):
            similarity = float(distance[0]) if distance.size else 0.0
            if_score, raw_if, is_cn = self._journal_scorer.compute_score(candidate)

            # Weighted combination: 80% similarity + 20% IF
            score = 0.8 * similarity + 0.2 * if_score

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
                    impact_factor_score=if_score,
                    impact_factor=raw_if,
                    is_chinese_core=is_cn,
                    label=label,
                )
            )

        ranked.sort(key=lambda w: w.score, reverse=True)
        return ranked


__all__ = ["ProfileRanker"]
