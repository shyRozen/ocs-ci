# Architecture

**Analysis Date:** 2026-04-23

## Pattern Overview

**Overall:** Three-tier classification pipeline with pluggable AI backends

**Key Characteristics:**
- Modular backend abstraction for swappable AI providers (Claude Code CLI, Anthropic API, or regex-only)
- Deterministic failure signature generation for caching and deduplication across runs
- Multi-layer classification with fast-path fallbacks (regex → cache → AI)
- Evidence-based AI investigation with pre-resolved paths to minimize Claude's navigation overhead
- Event recording and replay for transparency and debugging

## Layers / Modules

**Entry Point Layer:**
- Purpose: CLI and Python API interfaces
- Location: `cli.py`, `__init__.py`
- Contains: `analyze_run()` function and two CLI commands (`analyze-logs`, `analyze-trends`)
- Depends on: Parsers, Classifiers, Reporters
- Used by: End users, CI hook systems, dashboards

**Parsing Layer:**
- Purpose: Discover and extract artifacts (JUnit, config, logs, must-gather)
- Location: `parsers/`
- Contains: `artifact_fetcher.py`, `junit_parser.py`, `config_parser.py`, `test_log_parser.py`, `must_gather_parser.py`
- Depends on: Requests, BeautifulSoup, XML parsing libs
- Used by: Classification pipeline (needs test results and metadata)

**Data Models Layer:**
- Purpose: Structured representations of tests, failures, and analyses
- Location: `models.py`
- Contains: `TestResult`, `FailureAnalysis`, `FailureSignature`, `RunAnalysis`, `RunMetadata`, `FailureCategory` enum
- Depends on: Dataclasses, enums
- Used by: All layers (universal DTO)

**Classification Pipeline Layer:**
- Purpose: Orchestrate multi-tier failure classification (regex → cache → AI)
- Location: `analysis/failure_classifier.py`
- Contains: `FailureClassifier` orchestrator
- Depends on: AI backends, known issues matcher, caching layer
- Used by: Entry point layer

**Known Issues Matcher:**
- Purpose: Instant regex-based failure categorization
- Location: `analysis/known_issues.py`
- Contains: `KnownIssuesMatcher` with YAML pattern loading
- Depends on: Regex compilation
- Used by: Classification pipeline (first-tier fast path)

**AI Backends Layer:**
- Purpose: Abstract interface for pluggable AI providers
- Location: `ai/`
- Contains: `base.py` (abstract `AIBackend`), `claude_code_backend.py`, `anthropic_backend.py`
- Depends on: JSON schema, subprocess (Claude Code), SDK/API (Anthropic)
- Used by: Classification pipeline (third-tier when no regex match/cache hit)

**Caching Layer:**
- Purpose: Avoid re-analyzing identical failure signatures
- Location: `cache.py`
- Contains: `AnalysisCache` with JSON file persistence and TTL management
- Depends on: File I/O, JSON
- Used by: Classification pipeline (second-tier after regex, before AI)

**History & Pattern Detection Layer:**
- Purpose: Track test outcomes across runs, detect flaky/regressing tests
- Location: `analysis/history_store.py`, `analysis/pattern_detector.py`
- Contains: `RunHistoryStore` (JSON file persistence), `PatternDetector` (flakiness/regression analysis)
- Depends on: File I/O, JSON
- Used by: Entry point (optional, when `--record-history` enabled)

**Jira Integration Layer:**
- Purpose: Search Jira for matching bugs based on failure context
- Location: `integrations/jira_search.py`
- Contains: `JiraSearchIntegration` with JQL query building
- Depends on: JIRA SDK
- Used by: Entry point (optional, when Jira enabled)

**Reporting Layer:**
- Purpose: Generate human-readable reports in multiple formats
- Location: `reporting/`
- Contains: `ReportBuilder` with Jinja2 template rendering
- Depends on: Jinja2
- Used by: Entry point and CLI

**CI Integration Layer:**
- Purpose: Automatic post-run analysis as pytest plugin
- Location: `integrations/ci_hook.py`
- Contains: Pytest plugin that triggers analysis after test completion
- Depends on: Pytest hooks
- Used by: CI/CD systems (optional)

## Data Flow

**Single-Run Analysis:**

1. **User Input** → `analyze_run(source, ai_backend, ...)`
   - Source is URL (HTTP) or local path
   - Options: AI backend choice, Jira enabled, caching, history recording, etc.

2. **Artifact Discovery** → `ArtifactFetcher.discover()`
   - Scans log directory for JUnit XML, config YAML, per-test logs, must-gather
   - Returns `ArtifactManifest` with paths/URLs to each artifact type

3. **Metadata Extraction** → `JUnitResultParser`, `RunConfigParser`
   - Parses JUnit XML → list of `TestResult` objects (pass/fail/skip/error)
   - Parses config YAML → `RunMetadata` (platform, OCS version, etc.)
   - Merges run metadata from JUnit suite properties (preferred over YAML)

4. **Failure Filtering** → Squad/test name/limit filters
   - Extracts only failed/errored tests from results
   - Applies optional filters (squad, test name substring, result limit)

5. **Classification Pipeline** (per failure):
   ```
   For each failure:
      a) Regex Matching (instant)
         - Check traceback against known issue patterns
         - If match: category = "known_issue", skip AI
      b) Signature Computation & Cache Lookup (instant)
         - Normalize traceback, extract exception type/message
         - Compute signature hash as cache key
         - Lookup in cache (check TTL)
         - If hit: reuse cached analysis
      c) Log Preprocessing (seconds)
         - Extract relevant error/warning lines from test log
         - Resolve must-gather paths (if available)
         - Fetch OCS/OCP must-gather directory structure
      d) AI Classification (seconds to minutes)
         - Build prompt with traceback, log excerpt, run metadata
         - If must-gather available: agentic mode (Claude investigates evidence)
         - Call AI backend, get structured response
         - Cache result for future runs
      e) Post-Processing
         - Attach evidence, recommended action, session ID
   ```

6. **Jira Enrichment** → `JiraSearchIntegration.enrich_analyses()`
   - Build JQL queries from failure keywords and evidence
   - Search DFBUGS, RHSTOR, OCSQE
   - Attach matching bug keys to each failure

7. **History Recording** (optional) → `RunHistoryStore.record()`
   - Serialize `RunAnalysis` to JSON file
   - Filename includes run timestamp for sorting
   - Store counts historical test outcomes for trend detection

8. **Report Generation** → `ReportBuilder.build()`
   - Transform `RunAnalysis` into user-friendly format
   - Supported formats: JSON (structured data), Markdown (human-readable), HTML (interactive)
   - HTML includes collapsible cards, color-coded badges, evidence links

9. **Output** → File or stdout
   - Return complete report to CLI or Python caller

**Cross-Run Trend Analysis:**

1. **History Loading** → `RunHistoryStore.get_history()`
   - Scan history directory for JSON files
   - Load all runs (optionally filtered by platform/version/flavour)
   - Sort by timestamp

2. **Pattern Detection** → `PatternDetector.build_trend_report()`
   - Detect flaky tests (high intermittent pass/fail rate)
   - Detect regressions (tests that started failing recently)
   - Compute pass rate trend across runs
   - Rank tests by failure frequency
   - Compute per-squad health metrics

3. **Trend Report Generation** → `ReportBuilder.build_trends_report()`
   - Render trend data into HTML/Markdown tables and charts

## State Management

**Stateless Computation:**
- Classification pipeline is entirely stateless — results depend only on input (failure, run metadata, backend choice)
- No in-memory state shared between failures

**Persistent State:**
- **Cache:** File-based JSON in `~/.ocs-ci/analysis_cache/` (keyed by signature hash)
- **History:** File-based JSON in `~/.ocs-ci/analysis_history/` (one file per run, named by timestamp)
- **Sessions:** Transcript files in `~/.ocs-ci/recorded_sessions/` (one per agentic investigation)
- **Prompts:** Optional debug output in `~/.ocs-ci/prompts/<run_id>/`

**Temporary State:**
- Must-gather extraction: `~/.ocs-ci/must_gather_cache/` (cleaned up unless `--keep-mg`)

## Key Abstractions

**AIBackend (Interface):**
- Purpose: Define contract for pluggable AI providers
- Location: `ai/base.py`
- Implementations: `claude_code_backend.py` (subprocess), `anthropic_backend.py` (SDK), factory method `get_backend()`
- Pattern: Strategy pattern — swappable at runtime based on `--ai-backend` flag

**FailureSignature:**
- Purpose: Deterministic fingerprint of a failure for caching
- Location: `models.py`
- Computation: Hash of exception type, exception message, and normalized traceback
- Usage: Cache key to detect identical failures across runs

**ArtifactFetcher:**
- Purpose: Unified interface to log artifacts (HTTP or local)
- Location: `parsers/artifact_fetcher.py`
- Features: HTTP directory listing parsing (Apache/nginx), local filesystem traversal, session management
- Usage: All parsers depend on this to access logs

**RunAnalysis:**
- Purpose: Complete analysis of one test run
- Location: `models.py`
- Contains: Metadata, aggregate stats (total/passed/failed), failure analyses list, AI-generated summary
- Usage: Primary output of `analyze_run()`, serialized to JSON/Markdown/HTML

**FailureAnalysis:**
- Purpose: Result of classifying one test failure
- Location: `models.py`
- Contains: Category, confidence, root cause, evidence, suggested Jira issues, Jira issues, session ID
- Variants: Product bugs include `bug_details` (pre-filled form fields), test bugs include `suggested_fix` (code patch)

**PatternDetector:**
- Purpose: Cross-run analysis engine
- Location: `analysis/pattern_detector.py`
- Features: Flakiness detection, regression detection, trend computation
- Usage: Trend report generation

## Entry Points

**CLI: `analyze-logs`**
- Location: `cli.py:main()`
- Invoked via: `python -m ocs_ci.utility.log_analysis.cli <source> [options]`
- Responsibilities: Parse args, configure logging, call `analyze_run()`, render report, exit with appropriate status code

**CLI: `analyze-trends`**
- Location: `cli.py:trends_main()`
- Invoked via: `python3 -c "from ocs_ci.utility.log_analysis.cli import trends_main; trends_main([...])"`
- Responsibilities: Load history, detect patterns, generate trend report

**Python API: `analyze_run()`**
- Location: `__init__.py:analyze_run()`
- Invoked by: Other Python code, pytest plugin, dashboards
- Returns: `RunAnalysis` object
- Responsibilities: Orchestrate full pipeline (parse → classify → enrich → generate summary)

**Pytest Plugin: `ci_hook`**
- Location: `integrations/ci_hook.py`
- Triggered: After pytest finishes (via pytest hook)
- Responsibilities: Find JUnit XML, call `analyze_run()`, write reports to log directory

## Error Handling

**Strategy:** Fail fast for critical errors, non-fatal for optional features

**Critical Errors (exit immediately):**
- No log directory/artifacts found: `ValueError` → CLI exit(1)
- JUnit XML missing/unparseable: `JUnitParseError` → CLI exit(1)
- AI backend unavailable and non-optional: falls back to regex-only

**Non-Fatal Errors (logged, continue):**
- Config YAML parse fails: log warning, use default metadata
- Jira integration fails: log debug, continue (non-critical enrichment)
- History recording fails: log warning, continue (optional feature)
- Cache read fails: log debug, treat as cache miss (clean up corrupt file)
- Individual AI calls exceed budget: skip that failure, continue with next

**Error Types:**
- `LogAnalysisError`: Base exception
- `ArtifactFetchError`: Failed to discover/fetch logs
- `JUnitParseError`: Invalid XML
- `AIBackendError`: AI backend call failed
- `CacheError`: Cache I/O failed

## Cross-Cutting Concerns

**Logging:** 
- Uses Python `logging` module (standard `logging.getLogger(__name__)`)
- Levels: DEBUG (detailed state, cache hits), INFO (progress), WARNING (non-fatal issues), ERROR (failures)
- Third-party noise suppressed: atlassian (Jira client), urllib3

**Validation:**
- Traceback/log text: minimal — passed as-is to AI (Claude handles noise)
- Run metadata: optional fallbacks (unknown platform, default version)
- AI responses: schema validation if using structured output (JSON schema in Claude Code backend)

**Authentication:**
- Jira: loaded from `ocs_ci.framework.config.AUTH["jira"]` or `--jira-config` INI file
- AI backends: 
  - Claude Code CLI: uses local `claude` command (no auth needed)
  - Anthropic API: requires `ANTHROPIC_API_KEY` environment variable
- HTTP logs: verify=False for self-signed certificates (magna002 uses self-signed)

**Cost Control:**
- Known issues bypass AI (free)
- Cache reuse (free)
- Signature deduplication (combine identical failures into one AI call)
- Max failures cap (limit unique AI calls per run)
- Budget cap (max USD per AI call)

**Performance Optimizations:**
- Parallel batch processing possible but not implemented (sequential per-failure processing)
- Must-gather path pre-resolution (avoid Claude navigating directory tree)
- Cache hit check before expensive AI calls
- Early exit if all failures matched known issues

---

*Architecture analysis: 2026-04-23*
