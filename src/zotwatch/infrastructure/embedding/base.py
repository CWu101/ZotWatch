"""Base embedding provider."""

from abc import ABC, abstractmethod
from typing import Iterable

import numpy as np


class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier."""
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Embedding dimensionality."""
        ...

    @abstractmethod
    def encode(self, texts: Iterable[str]) -> np.ndarray:
        """Encode texts to embeddings."""
        ...

    def encode_single(self, text: str) -> np.ndarray:
        """Encode a single text."""
        return self.encode([text])[0]


__all__ = ["BaseEmbeddingProvider"]
