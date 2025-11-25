"""Embedding providers."""

from .voyage import VoyageEmbedding
from .faiss_index import FaissIndex

__all__ = ["VoyageEmbedding", "FaissIndex"]
