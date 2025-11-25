"""Protocol definitions for ZotWatch components."""

from dataclasses import dataclass
from typing import Iterable, Protocol, runtime_checkable

import numpy as np

from .models import CandidateWork, PaperSummary, ZoteroItem


@dataclass
class LLMResponse:
    """Response from LLM provider."""

    content: str
    model: str
    tokens_used: int
    cached: bool = False


@runtime_checkable
class CandidateSource(Protocol):
    """Protocol for paper sources (arXiv, Crossref, etc.)."""

    @property
    def name(self) -> str:
        """Unique source identifier."""
        ...

    @property
    def enabled(self) -> bool:
        """Whether this source is enabled in config."""
        ...

    def fetch(self, days_back: int = 7) -> list[CandidateWork]:
        """Fetch candidates from this source."""
        ...

    def validate_config(self) -> bool:
        """Validate source-specific configuration."""
        ...


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM providers."""

    @property
    def name(self) -> str:
        """Provider name."""
        ...

    def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> LLMResponse:
        """Generate completion for the given prompt."""
        ...

    def available_models(self) -> list[str]:
        """List available models."""
        ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for text embedding providers."""

    @property
    def model_name(self) -> str:
        """Model identifier."""
        ...

    @property
    def dimensions(self) -> int:
        """Embedding dimensionality."""
        ...

    def encode(self, texts: list[str]) -> np.ndarray:
        """Encode texts to embeddings."""
        ...

    def encode_single(self, text: str) -> np.ndarray:
        """Encode a single text."""
        ...


@runtime_checkable
class ItemStorage(Protocol):
    """Protocol for item storage backends."""

    def initialize(self) -> None:
        """Initialize storage schema."""
        ...

    def upsert_item(self, item: ZoteroItem, content_hash: str | None = None) -> None:
        """Insert or update an item."""
        ...

    def remove_items(self, keys: Iterable[str]) -> None:
        """Remove items by keys."""
        ...

    def iter_items(self) -> Iterable[ZoteroItem]:
        """Iterate over all items."""
        ...

    def get_metadata(self, key: str) -> str | None:
        """Get metadata value by key."""
        ...

    def set_metadata(self, key: str, value: str) -> None:
        """Set metadata value."""
        ...


@runtime_checkable
class SummaryStorage(Protocol):
    """Protocol for LLM summary storage."""

    def get_summary(self, paper_id: str) -> PaperSummary | None:
        """Get cached summary by paper ID."""
        ...

    def save_summary(self, paper_id: str, summary: PaperSummary) -> None:
        """Save summary to cache."""
        ...

    def has_summary(self, paper_id: str) -> bool:
        """Check if summary exists."""
        ...


__all__ = [
    "LLMResponse",
    "CandidateSource",
    "LLMProvider",
    "EmbeddingProvider",
    "ItemStorage",
    "SummaryStorage",
]
