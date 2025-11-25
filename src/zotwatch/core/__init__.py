"""Core domain models and interfaces."""

from .models import (
    ZoteroItem,
    CandidateWork,
    RankedWork,
    ProfileArtifacts,
    BulletSummary,
    DetailedAnalysis,
    PaperSummary,
)
from .protocols import (
    CandidateSource,
    LLMProvider,
    LLMResponse,
    EmbeddingProvider,
    ItemStorage,
    SummaryStorage,
)
from .exceptions import (
    ZotWatchError,
    ConfigurationError,
    SourceFetchError,
    EmbeddingError,
    LLMError,
)

__all__ = [
    # Models
    "ZoteroItem",
    "CandidateWork",
    "RankedWork",
    "ProfileArtifacts",
    "BulletSummary",
    "DetailedAnalysis",
    "PaperSummary",
    # Protocols
    "CandidateSource",
    "LLMProvider",
    "LLMResponse",
    "EmbeddingProvider",
    "ItemStorage",
    "SummaryStorage",
    # Exceptions
    "ZotWatchError",
    "ConfigurationError",
    "SourceFetchError",
    "EmbeddingError",
    "LLMError",
]
