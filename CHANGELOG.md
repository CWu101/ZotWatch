# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2025-12-01

### Changed

- **BREAKING**: Removed `scoring.rerank.enabled` configuration flag. Reranking is now automatically enabled when `scoring.interests.enabled=true` and disabled otherwise. This simplifies configuration by eliminating redundant flags.

**Migration:**

Remove the `enabled` field from your `config.yaml`:

**Before:**
```yaml
scoring:
  rerank:
    enabled: true  # Remove this line
    provider: "voyage"
    model: "rerank-2.5"
```

**After:**
```yaml
scoring:
  rerank:
    provider: "voyage"
    model: "rerank-2.5"
```

**Impact:**
- Provider coupling validation now only runs when `interests.enabled=true`
- Configs with `interests.enabled=false` no longer require matching providers
- This eliminates confusing validation errors for unused rerank configurations

- **Performance**: InterestRanker now uses `CachingEmbeddingProvider` to share embedding cache with ProfileRanker, reducing API calls by ~50% and improving execution time by ~45% when interest-based recommendations are enabled
- **Documentation**: Updated README to clarify that embedding provider/model changes are automatically detected and trigger profile rebuild without manual cache deletion

## [0.3.0] - 2025-11-29

### Added

- RSS feed with Dublin Core and PRISM namespaces for improved Zotero compatibility
- Publication year distribution chart in HTML report
- Title translation feature for non-English papers
- Dynamic threshold configuration for paper labeling (`scoring.thresholds.mode: dynamic`)
- Researcher profile analysis with LLM-generated insights
- Collection duration display in user reports
- Interest-based paper recommendations with InterestRanker
- Journal impact factor scoring integration
- Topic-based summary grouping (TopicSummary model)
- ScienceDirect abstract extraction from embedded JSON
- Zotero ingestion progress callbacks

### Changed

- Refactored watch command into WatchPipeline architecture
- Updated type annotations to Python 3.10+ syntax (`list`, `dict`, `X | None`)
- Improved HTML template layout (2-column charts, full-width year distribution)
- Enhanced interest refinement process with exclude_keywords logging
- Timezone conversion for profile generation timestamps

### Removed

- Obsolete test scripts and pytest configurations
- Legacy test utilities and fixtures

## [0.2.0] - 2025-11-26

### Added

- OpenRouter API integration for AI summarization
- Unified embedding caching system (EmbeddingCache)
- Abstract scraping with Camoufox browser automation
- Kimi (Moonshot AI) API support for LLM summarization
- Metadata caching for improved abstract storage
- Journal whitelist with ISSN filtering

### Changed

- Restructured CLI commands for better user interaction
- Simplified scoring to focus on embedding similarity
- Sequential abstract fetching with rate limiting

### Removed

- Legacy OpenAlex and bioRxiv sources
- Optional journal metrics scoring
- Semantic Scholar integration (replaced by Camoufox scraper)

## [0.1.0] - Initial Release

- Initial implementation of ZotWatch
- Zotero library integration
- Crossref and arXiv paper fetching
- FAISS-based similarity search
- Basic RSS and HTML output generation
