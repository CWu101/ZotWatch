"""Semantic Scholar API client for paper metadata enrichment."""

import logging
import time
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class SemanticScholarClient:
    """Semantic Scholar API client for paper metadata enrichment.

    Supports both single paper lookup and batch queries.
    Implements rate limiting and retry logic.
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    DEFAULT_FIELDS = "title,abstract,year,citationCount,authors"
    MAX_BATCH_SIZE = 500  # S2 batch endpoint limit

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        rate_limit_delay: float = 1.0,
    ):
        """Initialize the client.

        Args:
            api_key: Optional API key for higher rate limits.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries on failure.
            backoff_factor: Exponential backoff factor for retries.
            rate_limit_delay: Minimum delay between requests in seconds.
        """
        self._session = requests.Session()
        self._api_key = api_key
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._rate_limit_delay = rate_limit_delay
        self._last_request_time = 0.0

        # Set headers
        # Check for non-empty API key (env var expansion may result in empty string)
        has_valid_key = api_key and api_key.strip() and not api_key.startswith("${")
        if has_valid_key:
            self._session.headers["x-api-key"] = api_key
            logger.debug("Semantic Scholar client initialized with API key")
        else:
            logger.warning(
                "Semantic Scholar client initialized without API key. "
                "API access may be limited. Get a free key at: https://www.semanticscholar.org/product/api"
            )

    def _wait_for_rate_limit(self) -> None:
        """Wait to respect rate limit."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._rate_limit_delay:
            sleep_time = self._rate_limit_delay - elapsed
            logger.debug("Rate limiting: sleeping %.2f seconds", sleep_time)
            time.sleep(sleep_time)

    def _request(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> requests.Response:
        """Make HTTP request with rate limiting and retries.

        Args:
            method: HTTP method.
            url: Request URL.
            **kwargs: Additional request arguments.

        Returns:
            Response object.

        Raises:
            requests.RequestException: If all retries fail.
        """
        kwargs.setdefault("timeout", self._timeout)

        last_exception = None
        for attempt in range(self._max_retries):
            self._wait_for_rate_limit()

            try:
                response = self._session.request(method, url, **kwargs)
                self._last_request_time = time.time()

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning("Rate limited by Semantic Scholar, waiting %d seconds", retry_after)
                    time.sleep(retry_after)
                    continue

                # Handle 403 Forbidden - likely missing or invalid API key
                if response.status_code == 403:
                    logger.warning(
                        "Semantic Scholar API returned 403 Forbidden. "
                        "This usually means an API key is required. "
                        "Get a free key at: https://www.semanticscholar.org/product/api"
                    )
                    return response

                # Success or other client error (4xx)
                if response.status_code < 500:
                    return response

                # Server error, retry
                logger.warning(
                    "Semantic Scholar server error %d, attempt %d/%d",
                    response.status_code,
                    attempt + 1,
                    self._max_retries,
                )

            except requests.RequestException as e:
                last_exception = e
                logger.warning(
                    "Semantic Scholar request failed: %s, attempt %d/%d",
                    e,
                    attempt + 1,
                    self._max_retries,
                )

            # Exponential backoff
            if attempt < self._max_retries - 1:
                sleep_time = self._backoff_factor**attempt
                logger.debug("Backing off for %.1f seconds", sleep_time)
                time.sleep(sleep_time)

        if last_exception:
            raise last_exception
        raise requests.RequestException("Max retries exceeded")

    def get_paper_by_doi(self, doi: str) -> Optional[Dict]:
        """Fetch single paper by DOI.

        Args:
            doi: Digital Object Identifier.

        Returns:
            Paper data dict if found, None otherwise.
        """
        url = f"{self.BASE_URL}/paper/DOI:{doi}"
        params = {"fields": self.DEFAULT_FIELDS}

        try:
            response = self._request("GET", url, params=params)

            if response.status_code == 404:
                logger.debug("Paper not found in Semantic Scholar: %s", doi)
                return None

            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            logger.warning("Failed to fetch paper %s from Semantic Scholar: %s", doi, e)
            return None

    def get_papers_batch(self, dois: List[str]) -> Dict[str, Dict]:
        """Fetch multiple papers by DOI using batch endpoint.

        Args:
            dois: List of DOIs to fetch.

        Returns:
            Dict mapping DOI to paper data for found papers.
        """
        if not dois:
            return {}

        results: Dict[str, Dict] = {}

        # Process in batches
        for i in range(0, len(dois), self.MAX_BATCH_SIZE):
            batch_dois = dois[i : i + self.MAX_BATCH_SIZE]
            batch_results = self._fetch_batch(batch_dois)
            results.update(batch_results)

        return results

    def _fetch_batch(self, dois: List[str]) -> Dict[str, Dict]:
        """Fetch a single batch of papers.

        Args:
            dois: List of DOIs (max MAX_BATCH_SIZE).

        Returns:
            Dict mapping DOI to paper data.
        """
        url = f"{self.BASE_URL}/paper/batch"
        params = {"fields": self.DEFAULT_FIELDS}
        # S2 expects IDs in format: ["DOI:xxx", "DOI:yyy"]
        body = {"ids": [f"DOI:{doi}" for doi in dois]}

        try:
            response = self._request("POST", url, params=params, json=body)

            # Handle 403 - don't retry individual requests (API key required)
            if response.status_code == 403:
                logger.warning("Batch request returned 403, skipping individual fallback")
                return {}

            # Handle 400 - "No valid paper ids given" means none of the papers are indexed yet
            # This is expected for very new papers, treat as empty result
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", "")
                    if "No valid paper ids" in error_msg:
                        logger.info(
                            "None of the %d papers are indexed in Semantic Scholar yet "
                            "(common for newly published papers)",
                            len(dois),
                        )
                        return {}
                except (ValueError, KeyError):
                    pass
                # Other 400 errors - log and return empty
                logger.warning("Batch request returned 400: %s", response.text[:200])
                return {}

            response.raise_for_status()

            papers = response.json()
            results: Dict[str, Dict] = {}

            # Response is a list in same order as input, with null for not found
            for doi, paper in zip(dois, papers):
                if paper is not None:
                    results[doi] = paper

            logger.debug("Fetched %d/%d papers from Semantic Scholar batch", len(results), len(dois))
            return results

        except requests.RequestException as e:
            logger.warning("Batch request to Semantic Scholar failed: %s", e)
            # Check if it's a 400/403-related error before falling back
            error_str = str(e)
            if "403" in error_str or "400" in error_str:
                logger.debug("Skipping individual fallback due to client error")
                return {}
            # Fall back to individual requests for other errors (e.g., network issues)
            return self._fetch_individually(dois)

    def _fetch_individually(self, dois: List[str]) -> Dict[str, Dict]:
        """Fetch papers individually as fallback.

        Args:
            dois: List of DOIs to fetch.

        Returns:
            Dict mapping DOI to paper data.
        """
        results: Dict[str, Dict] = {}
        for doi in dois:
            paper = self.get_paper_by_doi(doi)
            if paper:
                results[doi] = paper
        return results

    def get_abstracts_batch(self, dois: List[str]) -> Dict[str, str]:
        """Fetch abstracts for multiple papers.

        Convenience method that extracts just abstracts from batch results.

        Args:
            dois: List of DOIs to fetch.

        Returns:
            Dict mapping DOI to abstract for papers with abstracts.
        """
        papers = self.get_papers_batch(dois)
        return {doi: paper.get("abstract") for doi, paper in papers.items() if paper.get("abstract")}

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()


__all__ = ["SemanticScholarClient"]
