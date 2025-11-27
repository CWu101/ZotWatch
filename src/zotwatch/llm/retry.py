"""Retry logic for LLM API calls."""

import functools
import logging
import time
from typing import Callable, ParamSpec, TypeVar

import requests

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def with_retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator for retry logic with exponential backoff."""

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception = None
            delay = initial_delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.HTTPError as e:
                    if e.response is not None and e.response.status_code not in RETRYABLE_STATUS_CODES:
                        raise
                    last_exception = e
                    logger.warning(
                        "Attempt %d/%d failed with status %s, retrying in %.1fs",
                        attempt + 1,
                        max_attempts,
                        e.response.status_code if e.response else "unknown",
                        delay,
                    )
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                    last_exception = e
                    logger.warning(
                        "Attempt %d/%d failed with %s, retrying in %.1fs",
                        attempt + 1,
                        max_attempts,
                        type(e).__name__,
                        delay,
                    )

                if attempt < max_attempts - 1:
                    time.sleep(delay)
                    delay *= backoff_factor

            # All retries exhausted - last_exception is guaranteed to be set
            # since we only reach here after catching retryable exceptions
            assert last_exception is not None
            raise last_exception

        return wrapper

    return decorator


__all__ = ["with_retry"]
