"""Main CLI entry point using Click."""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

import click
from dotenv import load_dotenv

from zotwatch import __version__
from zotwatch.config import Settings, load_settings
from zotwatch.core.models import RankedWork
from zotwatch.infrastructure.embedding import VoyageEmbedding
from zotwatch.infrastructure.storage import ProfileStorage
from zotwatch.llm import OpenRouterClient, PaperSummarizer
from zotwatch.output import render_html, write_rss
from zotwatch.output.push import ZoteroPusher
from zotwatch.pipeline import DedupeEngine, ProfileBuilder, WorkRanker
from zotwatch.pipeline.fetch import CandidateFetcher
from zotwatch.sources.zotero import ZoteroIngestor
from zotwatch.utils.logging import setup_logging

logger = logging.getLogger(__name__)


def _get_base_dir() -> Path:
    """Get base directory from current working directory or git root."""
    cwd = Path.cwd()
    # Check for config/config.yaml to identify project root
    if (cwd / "config" / "config.yaml").exists():
        return cwd
    # Try parent directories
    for parent in cwd.parents:
        if (parent / "config" / "config.yaml").exists():
            return parent
    return cwd


@click.group()
@click.option("--base-dir", type=click.Path(exists=True), default=None, help="Repository base directory")
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging")
@click.version_option(version=__version__, prog_name="zotwatch")
@click.pass_context
def cli(ctx: click.Context, base_dir: Optional[str], verbose: bool) -> None:
    """ZotWatch - Personalized academic paper recommendations."""
    ctx.ensure_object(dict)

    base = Path(base_dir) if base_dir else _get_base_dir()
    load_dotenv(base / ".env")
    setup_logging(verbose=verbose)

    ctx.obj["base_dir"] = base
    ctx.obj["verbose"] = verbose

    # Load settings lazily (some commands may not need them)
    ctx.obj["_settings"] = None


def _get_settings(ctx: click.Context) -> Settings:
    """Get or load settings."""
    if ctx.obj["_settings"] is None:
        ctx.obj["_settings"] = load_settings(ctx.obj["base_dir"])
    return ctx.obj["_settings"]


@cli.command()
@click.option("--full", is_flag=True, help="Full rebuild of profile (recompute all embeddings)")
@click.pass_context
def profile(ctx: click.Context, full: bool) -> None:
    """Build or update user research profile.

    By default, only computes embeddings for new or changed items (incremental mode).
    Use --full to force recomputation of all embeddings.
    """
    settings = _get_settings(ctx)
    base_dir = ctx.obj["base_dir"]
    storage = ProfileStorage(base_dir / "data" / "profile.sqlite")

    # Ingest from Zotero
    click.echo("Ingesting items from Zotero...")
    ingestor = ZoteroIngestor(storage, settings)
    stats = ingestor.run(full=full)
    click.echo(f"  Fetched: {stats.fetched}, Updated: {stats.updated}, Removed: {stats.removed}")

    # Check embedding status
    total_items = len(list(storage.iter_items()))
    items_needing_embedding = storage.count_items_needing_embedding()

    if full:
        click.echo("Building profile (full rebuild)...")
    elif items_needing_embedding > 0:
        click.echo(f"Building profile ({items_needing_embedding}/{total_items} items need embedding update)...")
    else:
        click.echo(f"Building profile (all {total_items} embeddings up-to-date)...")

    # Build profile
    vectorizer = VoyageEmbedding(
        model_name=settings.embedding.model,
        api_key=settings.embedding.api_key,
        input_type=settings.embedding.input_type,
        batch_size=settings.embedding.batch_size,
    )
    builder = ProfileBuilder(base_dir, storage, settings, vectorizer=vectorizer)
    artifacts = builder.run(full=full)

    click.echo("Profile built successfully:")
    click.echo(f"  SQLite: {artifacts.sqlite_path}")
    click.echo(f"  FAISS: {artifacts.faiss_path}")
    click.echo(f"  JSON: {artifacts.profile_json_path}")


@cli.command()
@click.option("--rss", is_flag=True, help="Generate RSS feed")
@click.option("--report", is_flag=True, help="Generate HTML report")
@click.option("--top", type=int, default=50, help="Number of top results to keep")
@click.option("--summarize", is_flag=True, help="Generate AI summaries for top papers")
@click.option("--push", is_flag=True, help="Push recommendations to Zotero")
@click.pass_context
def watch(
    ctx: click.Context,
    rss: bool,
    report: bool,
    top: int,
    summarize: bool,
    push: bool,
) -> None:
    """Fetch, score, and output paper recommendations."""
    settings = _get_settings(ctx)
    base_dir = ctx.obj["base_dir"]
    storage = ProfileStorage(base_dir / "data" / "profile.sqlite")

    # Incremental ingest
    click.echo("Syncing with Zotero...")
    ingestor = ZoteroIngestor(storage, settings)
    ingestor.run(full=False)

    # Fetch candidates
    click.echo("Fetching candidates from sources...")
    fetcher = CandidateFetcher(settings, base_dir)
    candidates = fetcher.fetch_all()
    click.echo(f"  Found {len(candidates)} candidates")

    # Deduplicate
    dedupe = DedupeEngine(storage)
    filtered = dedupe.filter(candidates)
    click.echo(f"  After dedup: {len(filtered)} candidates")

    # Rank
    click.echo("Ranking candidates...")
    vectorizer = VoyageEmbedding(
        model_name=settings.embedding.model,
        api_key=settings.embedding.api_key,
        input_type=settings.embedding.input_type,
        batch_size=settings.embedding.batch_size,
    )
    ranker = WorkRanker(base_dir, settings, vectorizer=vectorizer)
    ranked = ranker.rank(filtered)

    # Filter
    ranked = _filter_recent(ranked, days=7)
    ranked = _limit_preprints(ranked, max_ratio=0.3)

    if top and len(ranked) > top:
        ranked = ranked[:top]

    if not ranked:
        click.echo("No recommendations found")
        if rss:
            write_rss([], base_dir / "reports" / "feed.xml")
        if report:
            render_html([], base_dir / "reports" / "report-empty.html")
        return

    click.echo(f"\nTop {min(10, len(ranked))} recommendations:")
    for idx, work in enumerate(ranked[:10], start=1):
        click.echo(f"  {idx:02d} | {work.score:.3f} | {work.label} | {work.title[:60]}...")

    # Generate summaries if requested
    if summarize and settings.llm.enabled:
        click.echo("\nGenerating AI summaries...")
        llm_client = OpenRouterClient.from_config(settings.llm)
        summarizer = PaperSummarizer(llm_client, storage, model=settings.llm.model)
        top_n = settings.llm.summarize.top_n
        summaries = summarizer.summarize_batch(ranked[:top_n])
        click.echo(f"  Generated {len(summaries)} summaries")

        # Attach summaries to ranked works
        summary_map = {s.paper_id: s for s in summaries}
        for work in ranked:
            if work.identifier in summary_map:
                work.summary = summary_map[work.identifier]

    # Generate outputs
    if rss:
        rss_path = base_dir / "reports" / "feed.xml"
        write_rss(
            ranked,
            rss_path,
            title=settings.output.rss.title,
            link=settings.output.rss.link,
            description=settings.output.rss.description,
        )
        click.echo(f"RSS feed: {rss_path}")

    if report:
        report_name = "report.html"
        if ranked and ranked[0].published:
            report_name = f"report-{ranked[0].published:%Y%m%d}.html"
        report_path = base_dir / "reports" / report_name
        template_dir = base_dir / "templates"
        render_html(
            ranked,
            report_path,
            template_dir=template_dir if template_dir.exists() else None,
        )
        click.echo(f"HTML report: {report_path}")

    if push:
        pusher = ZoteroPusher(settings)
        pusher.push(ranked)
        click.echo("Pushed recommendations to Zotero")


@cli.command()
@click.option("--top", type=int, default=20, help="Number of papers to summarize")
@click.option("--force", is_flag=True, help="Regenerate existing summaries")
@click.option("--model", type=str, help="Override LLM model")
@click.pass_context
def summarize(ctx: click.Context, top: int, force: bool, model: Optional[str]) -> None:
    """Generate AI summaries for recent recommendations."""
    settings = _get_settings(ctx)
    base_dir = ctx.obj["base_dir"]

    if not settings.llm.enabled:
        click.echo("LLM is disabled in configuration")
        return

    storage = ProfileStorage(base_dir / "data" / "profile.sqlite")

    # Load recent ranked works from cache
    from zotwatch.infrastructure.storage.cache import FileCache

    cache_path = base_dir / "data" / "cache" / "candidate_cache.json"
    cache = FileCache(cache_path)
    result = cache.load()

    if not result:
        click.echo("No cached candidates found. Run 'zotwatch watch' first.")
        return

    _, candidates = result

    # Re-rank to get scores
    click.echo("Re-ranking candidates...")
    vectorizer = VoyageEmbedding(
        model_name=settings.embedding.model,
        api_key=settings.embedding.api_key,
        input_type=settings.embedding.input_type,
        batch_size=settings.embedding.batch_size,
    )
    ranker = WorkRanker(base_dir, settings, vectorizer=vectorizer)

    dedupe = DedupeEngine(storage)
    filtered = dedupe.filter(candidates)
    ranked = ranker.rank(filtered)

    if not ranked:
        click.echo("No papers to summarize")
        return

    # Generate summaries
    click.echo(f"Generating summaries for top {top} papers...")
    llm_client = OpenRouterClient.from_config(settings.llm)
    use_model = model or settings.llm.model
    summarizer = PaperSummarizer(llm_client, storage, model=use_model)

    summaries = summarizer.summarize_batch(ranked[:top], force=force)
    click.echo(f"Generated {len(summaries)} summaries using {use_model}")


def _filter_recent(ranked: List[RankedWork], *, days: int) -> List[RankedWork]:
    """Filter to recent papers only."""
    if days <= 0:
        return ranked
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    kept = [work for work in ranked if work.published and work.published >= cutoff]
    removed = len(ranked) - len(kept)
    if removed > 0:
        logger.info("Dropped %d items older than %d days", removed, days)
    return kept


def _limit_preprints(ranked: List[RankedWork], *, max_ratio: float) -> List[RankedWork]:
    """Limit preprints to a maximum ratio."""
    if not ranked or max_ratio <= 0:
        return ranked
    preprint_sources = {"arxiv", "biorxiv", "medrxiv"}
    filtered: List[RankedWork] = []
    preprint_count = 0
    for work in ranked:
        source = work.source.lower()
        proposed_total = len(filtered) + 1
        if source in preprint_sources:
            proposed_preprints = preprint_count + 1
            if (proposed_preprints / proposed_total) > max_ratio:
                continue
            preprint_count = proposed_preprints
        filtered.append(work)
    removed = len(ranked) - len(filtered)
    if removed > 0:
        logger.info("Preprint cap removed %d items to respect %.0f%% limit", removed, max_ratio * 100)
    return filtered


if __name__ == "__main__":
    cli()
