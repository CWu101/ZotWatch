#!/usr/bin/env python3
"""Test script for Camoufox-based Cloudflare bypass."""

import logging
import sys
import re

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_camoufox")


def extract_abstract(html: str) -> str:
    """Extract abstract from ACM Digital Library page."""
    if not html:
        return ""

    # Method 1: Look for abstract section
    abstract_match = re.search(
        r'<section[^>]*class="[^"]*abstract[^"]*"[^>]*>(.*?)</section>',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    if abstract_match:
        abstract_html = abstract_match.group(1)
        # Remove HTML tags
        abstract = re.sub(r"<[^>]+>", " ", abstract_html)
        abstract = re.sub(r"\s+", " ", abstract).strip()
        return abstract

    # Method 2: Look for div with role="paragraph" inside abstract
    abstract_match = re.search(
        r'<div[^>]*role="paragraph"[^>]*>(.*?)</div>',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    if abstract_match:
        abstract = re.sub(r"<[^>]+>", " ", abstract_match.group(1))
        abstract = re.sub(r"\s+", " ", abstract).strip()
        return abstract

    # Method 3: Look for meta description
    meta_match = re.search(
        r'<meta[^>]*name="description"[^>]*content="([^"]+)"',
        html,
        re.IGNORECASE,
    )
    if meta_match:
        return meta_match.group(1).strip()

    return ""


def main():
    from zotwatch.infrastructure.enrichment.stealth_browser import StealthBrowser

    # Test URL - ACM Digital Library paper
    url = "https://doi.org/10.1145/3528233.3530757"

    logger.info("=" * 60)
    logger.info("Testing Camoufox Cloudflare bypass")
    logger.info("URL: %s", url)
    logger.info("=" * 60)

    try:
        logger.info("Fetching page...")
        html, final_url = StealthBrowser.fetch_page(url)

        if html:
            logger.info("SUCCESS! Page fetched")
            logger.info("Final URL: %s", final_url)
            logger.info("HTML length: %d characters", len(html))

            # Check if still on challenge page
            if "Just a moment" in html or "Verify you are human" in html:
                logger.warning("Still on Cloudflare challenge page!")
            else:
                logger.info("Cloudflare bypass confirmed!")

                # Extract and print abstract
                abstract = extract_abstract(html)
                if abstract:
                    logger.info("")
                    logger.info("=" * 60)
                    logger.info("ABSTRACT:")
                    logger.info("=" * 60)
                    print(abstract[:1000] + "..." if len(abstract) > 1000 else abstract)
                    logger.info("=" * 60)
                else:
                    logger.warning("Could not extract abstract from page")

                # Check for title
                title_match = re.search(r"<title>([^<]+)</title>", html)
                if title_match:
                    logger.info("Page title: %s", title_match.group(1))
        else:
            logger.error("Failed to fetch page")
            sys.exit(1)

    except Exception as e:
        logger.error("Error: %s", e)
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        logger.info("Closing browser...")
        StealthBrowser.close()


if __name__ == "__main__":
    main()
