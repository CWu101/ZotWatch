"""OpenRouter LLM provider implementation."""

import logging
from typing import List, Optional

import requests

from zotwatch.config.settings import LLMConfig

from .base import BaseLLMProvider, LLMResponse
from .retry import with_retry

logger = logging.getLogger(__name__)


class OpenRouterClient(BaseLLMProvider):
    """OpenRouter API client supporting multiple LLM providers."""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: str,
        default_model: str = "anthropic/claude-3.5-sonnet",
        site_url: str = "https://github.com/zotwatch/zotwatch",
        app_name: str = "ZotWatch",
        timeout: float = 60.0,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
    ):
        self.api_key = api_key
        self.default_model = default_model
        self.site_url = site_url
        self.app_name = app_name
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._session = requests.Session()

    @classmethod
    def from_config(cls, config: LLMConfig) -> "OpenRouterClient":
        """Create client from LLM configuration."""
        return cls(
            api_key=config.api_key,
            default_model=config.model,
            max_retries=config.retry.max_attempts,
            backoff_factor=config.retry.backoff_factor,
        )

    @property
    def name(self) -> str:
        return "openrouter"

    def complete(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> LLMResponse:
        """Send completion request to OpenRouter."""
        return self._complete_with_retry(
            prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    @with_retry(max_attempts=3, backoff_factor=2.0, initial_delay=1.0)
    def _complete_with_retry(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> LLMResponse:
        """Internal completion with retry logic."""
        use_model = model or self.default_model

        response = self._session.post(
            f"{self.BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": self.site_url,
                "X-Title": self.app_name,
                "Content-Type": "application/json",
            },
            json={
                "model": use_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        tokens_used = data.get("usage", {}).get("total_tokens", 0)

        return LLMResponse(
            content=content,
            model=data.get("model", use_model),
            tokens_used=tokens_used,
        )

    def available_models(self) -> List[str]:
        """Get available models from OpenRouter."""
        try:
            response = self._session.get(
                f"{self.BASE_URL}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception as e:
            logger.warning("Failed to fetch available models: %s", e)
            return []


__all__ = ["OpenRouterClient"]
