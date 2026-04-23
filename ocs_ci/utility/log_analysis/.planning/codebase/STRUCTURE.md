# Codebase Structure

**Analysis Date:** 2026-04-23

## Directory Layout

```
ocs_ci/utility/log_analysis/
├── ai/                              AI backend implementations
│   ├── __init__.py
│   ├── base.py                      AIBackend abstract class, factory
│   ├── anthropic_backend.py         Anthropic API implementation
│   ├── claude_code_backend.py       Claude Code CLI subprocess
│   └── prompt_templates/            Jinja2 prompts
│       ├── classify_failure.j2
│       ├── classify_failure_agentic.j2
│       ├── classify_failure_ui.j2
│       └── run_summary.j2
│
├── analysis/                        Analysis engines
│   ├── __init__.py
│   ├── failure_classifier.py        Classification pipeline orchestrator
│   ├── known_issues.py              Regex pattern matching
│   ├── history_store.py             Run history persistence
│   └── pattern_detector.py          Trend detection
│
├── integrations/                    External integrations
│   ├── __init__.py
│   ├── ci_hook.py                   Pytest plugin
│   ├── jira_search.py               Jira integration
│   ├── scanner.py                   CI scanner
│   └── SCANNER_DEPLOYMENT.md
│
├── parsers/                         Input parsing
│   ├── __init__.py
│   ├── artifact_fetcher.py          Log discovery
│   ├── config_parser.py             Run metadata extraction
│   ├── junit_parser.py              Test results parsing
│   ├── must_gather_parser.py        Cluster state parsing
│   └── test_log_parser.py           Test log extraction
│
├── reporting/                       Report generation
│   ├── __init__.py
│   ├── report_builder.py            Output builder
│   └── templates/                   Jinja2 templates
│       ├── analysis_report.md.j2
│       ├── analysis_report.html.j2
│       ├── jira_comment.j2
│       ├── trends_report.md.j2
│       └── trends_report.html.j2
│
├── scripts/                         Utility scripts
│   ├── __init__.py
│   ├── backfill_cache.py            Cache warm-up
│   └── README.md
│
├── __init__.py                      Main entry point: analyze_run()
├── cache.py                         Result caching
├── cli.py                           CLI: analyze-logs, analyze-trends
├── exceptions.py                    Exception hierarchy
├── models.py                        Data models
└── README.md                        Module documentation
```

## Directory Purposes

**ai/**
- Purpose: Pluggable AI backend implementations
- Contains: Abstract base class, concrete implementations, prompt templates
- Key files: base.py (interface), claude_code_backend.py, anthropic_backend.py

**analysis/**
- Purpose: Core analysis engines
- Contains: Classification orchestrator, regex matcher, history store, pattern detector
- Key files: failure_classifier.py, known_issues.py, history_store.py

**integrations/**
- Purpose: External system integrations
- Contains: Jira search, pytest plugin, CI scanner
- Key files: jira_search.py, ci_hook.py

**parsers/**
- Purpose: Parse test run artifacts from HTTP URLs or local paths
- Contains: Artifact discovery, JUnit parsing, config parsing, log extraction
- Key files: artifact_fetcher.py, junit_parser.py, config_parser.py

**reporting/**
- Purpose: Generate human-readable reports
- Contains: Report builder, Jinja2 templates
- Key files: report_builder.py, templates directory

**scripts/**
- Purpose: Utility scripts
- Contains: Bulk cache warm-up tool
- Key files: backfill_cache.py

## Key File Locations

**Entry Points:**
- `__init__.py`: Main analyze_run() function
- `cli.py`: CLI commands (main(), trends_main())
- `integrations/ci_hook.py`: Pytest plugin

**Core Logic:**
- `models.py`: Data structures (TestResult, FailureAnalysis, RunAnalysis)
- `cache.py`: File-based caching
- `exceptions.py`: Exception hierarchy
- `analysis/failure_classifier.py`: Classification pipeline orchestrator
- `ai/base.py`: AIBackend abstract class and factory

**Configuration:**
- No config files in module (config passed via CLI args, kwargs, or environment variables)
- Jira config INI file: optional, via --jira-config flag
- Known issues YAML file: optional, via --known-issues-file flag

## Naming Conventions

**Files:**
- Python modules: snake_case.py (e.g., failure_classifier.py)
- Jinja2 templates: snake_case.j2 (e.g., analysis_report.md.j2)
- Directories: snake_case (e.g., ai, parsers)

**Classes:**
- PascalCase (e.g., TestResult, FailureAnalysis, ArtifactFetcher)
- Exceptions: PascalCase ending in Error (e.g., AIBackendError, JUnitParseError)

**Functions/Methods:**
- snake_case (e.g., analyze_run(), classify_failure(), build_trend_report())
- Private: Leading underscore (e.g., _list_remote(), _safe_remove())

**Constants:**
- UPPER_SNAKE_CASE (e.g., MAGNA_MOUNT, DEFAULT_SESSIONS_DIR)

**Variables:**
- snake_case (e.g., failure_analyses, run_metadata, cache_dir)

## Where to Add New Code

**New Analysis Stage:**
- Primary code: `analysis/` subdirectory
- Example: Create `analysis/ml_classifier.py`
- Called from: `analysis/failure_classifier.py`

**New AI Backend:**
- Implementation: `ai/<provider>_backend.py`
- Inherit from: `ai/base.py` AIBackend
- Register in: `ai/base.py` get_backend() factory
- Add prompts: `ai/prompt_templates/` directory

**New Integration:**
- Implementation: `integrations/<system>.py`
- Call from: `__init__.py` analyze_run() (optional, gated by config)
- Example: Create `integrations/slack_notifier.py`

**New Report Format:**
- Add method to: `reporting/report_builder.py`
- Signature: def build_<format>(self, run_analysis RunAnalysis) -> str
- Add template: `reporting/templates/` if Jinja2

**New Parser:**
- Implementation: `parsers/<format>_parser.py`
- Call from: Artifact discovery in `__init__.py` or `ArtifactFetcher`
- Example: Create `parsers/html_test_parser.py`

**New Trend Analysis:**
- Add method to: PatternDetector in `analysis/pattern_detector.py`
- Call from: `__init__.py` trends_main() or report generation
- Example: Add detect_performance_regressions()

## Special Directories

**ai/prompt_templates/**
- Purpose: Store Jinja2 prompts for AI backends
- Generated: No (hand-authored)
- Committed: Yes
- Content:
  - classify_failure.j2: Standard non-agentic classification
  - classify_failure_agentic.j2: Agentic mode with evidence investigation
  - classify_failure_ui.j2: UI test variant
  - run_summary.j2: Run summary prompt

**reporting/templates/**
- Purpose: Store Jinja2 report templates
- Generated: No (hand-authored)
- Committed: Yes
- Content:
  - *.md.j2 files: Markdown format
  - *.html.j2 files: HTML format with CSS and Chart.js
  - jira_comment.j2: Jira comment format

**~/.ocs-ci/analysis_cache/** (user home)
- Purpose: File-based cache of analysis results
- Generated: Yes (created by AnalysisCache)
- Committed: No (user-specific)
- TTL: 30 days default (configurable via --cache-ttl)

**~/.ocs-ci/analysis_history/** (user home)
- Purpose: Cross-run history for trend detection
- Generated: Yes (when --record-history used)
- Committed: No (user-specific)
- Lifecycle: Indefinite (preserved for trend analysis)

**~/.ocs-ci/recorded_sessions/** (user home)
- Purpose: Agentic investigation transcripts
- Generated: Yes (created by agentic backend)
- Committed: No (user-specific)
- Lifecycle: Indefinite (preserved for audit)

**~/.ocs-ci/must_gather_cache/** (user home)
- Purpose: Extracted must-gather archives
- Generated: Yes (extracted by must_gather_parser.py)
- Committed: No (binary files)
- Cleaned up: After analysis unless --keep-mg flag

## Import Organization

**Pattern:** Lazy imports inside functions to minimize startup time

**Reason:** Allows analysis to start even if optional dependencies are missing (Jira SDK, etc.)

**Path aliases:** None configured (uses absolute imports)

## Dependency Summary

**analyze_run()** depends on:
- parsers/ for artifact fetching and parsing
- analysis/failure_classifier.py for classification pipeline
- reporting/report_builder.py for output generation
- Optional: integrations/jira_search.py, analysis/history_store.py

**Classification pipeline** depends on:
- analysis/known_issues.py for regex matching
- cache.py for result caching
- ai/base.py and concrete AI backends
- parsers/ for log parsing

**CLI entry points** depend on:
- analyze_run() for analysis
- reporting/report_builder.py for output
- analysis/history_store.py and pattern_detector.py for trends

---

*Structure analysis: 2026-04-23*
