"""Profile building pipeline."""

import logging
from collections import Counter
from pathlib import Path
from typing import List, Optional

import numpy as np

from zotwatch.config.settings import Settings
from zotwatch.core.models import ProfileArtifacts, ZoteroItem
from zotwatch.infrastructure.embedding import FaissIndex, VoyageEmbedding
from zotwatch.infrastructure.storage import ProfileStorage
from zotwatch.utils.datetime import utc_now
from zotwatch.utils.text import json_dumps

logger = logging.getLogger(__name__)


class ProfileBuilder:
    """Builds user research profile from library."""

    def __init__(
        self,
        base_dir: Path | str,
        storage: ProfileStorage,
        settings: Settings,
        vectorizer: Optional[VoyageEmbedding] = None,
    ):
        self.base_dir = Path(base_dir)
        self.storage = storage
        self.settings = settings
        self.vectorizer = vectorizer or VoyageEmbedding(
            model_name=settings.embedding.model,
            api_key=settings.embedding.api_key,
            input_type=settings.embedding.input_type,
            batch_size=settings.embedding.batch_size,
        )
        self.artifacts = ProfileArtifacts(
            sqlite_path=str(self.base_dir / "data" / "profile.sqlite"),
            faiss_path=str(self.base_dir / "data" / "faiss.index"),
            profile_json_path=str(self.base_dir / "data" / "profile.json"),
        )

    def run(self, *, full: bool = False) -> ProfileArtifacts:
        """Build profile from library items.

        Args:
            full: If True, recompute all embeddings. If False (default), only compute
                  embeddings for new or changed items (incremental mode).
        """
        items = list(self.storage.iter_items())
        if not items:
            raise RuntimeError("No items found in storage; run ingest before building profile.")

        # Determine which items need embedding computation
        if full:
            items_to_embed = items
            logger.info("Full rebuild: computing embeddings for all %d items", len(items))
        else:
            items_to_embed = self.storage.fetch_items_needing_embedding()
            if items_to_embed:
                logger.info(
                    "Incremental mode: %d/%d items need embedding update",
                    len(items_to_embed),
                    len(items),
                )
            else:
                logger.info("All %d items have up-to-date embeddings", len(items))

        # Compute and store embeddings for items that need them
        if items_to_embed:
            texts = [item.content_for_embedding() for item in items_to_embed]
            vectors = self.vectorizer.encode(texts)

            for item, vector in zip(items_to_embed, vectors):
                self.storage.set_embedding(
                    item.key,
                    vector.tobytes(),
                    embedding_hash=item.content_hash,
                )
            logger.info("Computed and stored %d embeddings", len(items_to_embed))

        # Rebuild FAISS index from all embeddings in database
        logger.info("Building FAISS index from stored embeddings")
        all_embeddings = self.storage.fetch_all_embeddings()

        if not all_embeddings:
            raise RuntimeError("No embeddings found in storage after computation.")

        # Convert to numpy array
        vectors = np.array([np.frombuffer(vec, dtype=np.float32) for _, vec in all_embeddings])

        index, _ = FaissIndex.from_vectors(vectors)
        index.save(self.artifacts.faiss_path)

        # Generate profile summary using all items
        profile_summary = self._summarize(items, vectors)
        json_path = Path(self.artifacts.profile_json_path)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json_dumps(profile_summary, indent=2), encoding="utf-8")
        logger.info("Wrote profile summary to %s", json_path)

        return self.artifacts

    def _summarize(self, items: List[ZoteroItem], vectors: np.ndarray) -> dict:
        """Generate profile summary."""
        authors = Counter()
        venues = Counter()
        for item in items:
            authors.update(item.creators)
            venue = item.raw.get("data", {}).get("publicationTitle")
            if venue:
                venues.update([venue])

        # Compute centroid
        centroid = np.mean(vectors, axis=0)
        centroid = centroid / (np.linalg.norm(centroid) + 1e-12)

        top_authors = [{"author": k, "count": v} for k, v in authors.most_common(20)]
        top_venues = [{"venue": k, "count": v} for k, v in venues.most_common(20)]

        return {
            "generated_at": utc_now().isoformat(),
            "item_count": len(items),
            "model": self.vectorizer.model_name,
            "centroid": centroid.tolist(),
            "top_authors": top_authors,
            "top_venues": top_venues,
        }


__all__ = ["ProfileBuilder"]
