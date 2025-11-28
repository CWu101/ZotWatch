"""Processing pipeline components."""

from .dedupe import DedupeEngine
from .enrich import AbstractEnricher, EnrichmentStats, enrich_candidates
from .fetch import fetch_candidates
from .ingest import ingest_zotero
from .interest_ranker import InterestRanker
from .journal_scorer import JournalScorer
from .profile import ProfileBuilder
from .profile_ranker import ProfileRanker
from .profile_stats import ProfileStatsExtractor

__all__ = [
    "ingest_zotero",
    "ProfileBuilder",
    "ProfileStatsExtractor",
    "fetch_candidates",
    "AbstractEnricher",
    "EnrichmentStats",
    "enrich_candidates",
    "DedupeEngine",
    "ProfileRanker",
    "InterestRanker",
    "JournalScorer",
]
