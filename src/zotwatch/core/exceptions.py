"""Custom exceptions for ZotWatch."""


class ZotWatchError(Exception):
    """Base exception for all ZotWatch errors."""

    pass


class ConfigurationError(ZotWatchError):
    """Raised when configuration is invalid or missing."""

    pass


class SourceFetchError(ZotWatchError):
    """Raised when fetching from a data source fails."""

    def __init__(self, source: str, message: str):
        self.source = source
        super().__init__(f"[{source}] {message}")


class EmbeddingError(ZotWatchError):
    """Raised when embedding generation fails."""

    pass


class LLMError(ZotWatchError):
    """Raised when LLM API call fails."""

    def __init__(self, provider: str, message: str):
        self.provider = provider
        super().__init__(f"[{provider}] {message}")


class StorageError(ZotWatchError):
    """Raised when storage operations fail."""

    pass


__all__ = [
    "ZotWatchError",
    "ConfigurationError",
    "SourceFetchError",
    "EmbeddingError",
    "LLMError",
    "StorageError",
]
