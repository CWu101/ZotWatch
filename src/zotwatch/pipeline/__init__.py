"""Processing pipeline components."""

from .ingest import ingest_zotero
from .profile import ProfileBuilder
from .fetch import fetch_candidates
from .dedupe import DedupeEngine
from .score import WorkRanker

__all__ = [
    "ingest_zotero",
    "ProfileBuilder",
    "fetch_candidates",
    "DedupeEngine",
    "WorkRanker",
]
