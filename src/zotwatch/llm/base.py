"""LLM provider base classes."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class LLMResponse:
    """Response from LLM provider."""

    content: str
    model: str
    tokens_used: int
    cached: bool = False


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        ...

    @abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> LLMResponse:
        """Generate completion for the given prompt."""
        ...

    def available_models(self) -> List[str]:
        """List available models."""
        return []


__all__ = ["LLMResponse", "BaseLLMProvider"]
