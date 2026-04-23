# Code Conventions

**Analysis Date:** 2026-04-23

## Style

**Formatter:** No explicit formatter detected. Code follows Python PEP 8 conventions.

**Linter:** No linter configuration found (no `.pylintrc`, `.flake8`, or `pyproject.toml` with tool configuration).

**Line length:** Observed 88-character limit in most files (consistent with Black/autopep8 defaults).

**Docstring format:** Module docstrings with triple quotes used consistently.

## Naming

**Variables:** snake_case throughout
- Local variables: `test_results`, `cache_key`, `error_lines`
- Private attributes: `_cached_test_name`, `_compiled`, `_cache_path`
- Constants: `UPPERCASE` (e.g., `MAX_ERROR_LINES`, `MAGNA_MOUNT`, `DEFAULT_SESSIONS_DIR`)

**Functions:** snake_case with descriptive action verbs
- Public: `analyze_run()`, `classify_failures()`, `build_excerpt()`
- Private/internal: `_extract_errors()`, `_enforce_budget()`, `_safe_remove()`
- Factory functions: `get_backend()` in `ai/base.py`

**Classes:** PascalCase for all classes
- Data models: `TestResult`, `FailureAnalysis`, `RunMetadata`
- Service classes: `AnalysisCache`, `KnownIssuesMatcher`, `PatternDetector`
- Abstract base: `AIBackend` in `ai/base.py`
- Enum classes: `FailureCategory`, `TestStatus`

**Files:** snake_case for module names
- Core: `models.py`, `cache.py`, `exceptions.py`
- Subpackages: `failure_classifier.py`, `pattern_detector.py`, `junit_parser.py`
- Suffixes for functionality: `_parser.py`, `_matcher.py`, `_backend.py`

**Directories:** snake_case
- Feature areas: `ai/`, `analysis/`, `parsers/`, `integrations/`, `reporting/`, `scripts/`

## Patterns

**Error handling:**
- Custom exception hierarchy with base `LogAnalysisError` in `exceptions.py`
- Exception classes for specific failure modes: `ArtifactFetchError`, `JUnitParseError`, `AIBackendError`, `CacheError`
- Defensive try-except blocks in cache operations: `cache.py` lines 50-55, 99-136
- Exception info included in logging via `exc_info` parameter: `cli.py` lines 289, 400
- Graceful fallback on non-fatal errors: `__init__.py` lines 59-60, 176-181, 232-233, 305

**Logging:**
- Module-level logger via `logger = logging.getLogger(__name__)` in every module
- Log levels used appropriately:
  - `DEBUG`: Cache hits/misses, regex matches: `cache.py` line 64
  - `INFO`: Major operations (record history, trend analysis): `cli.py` line 271
  - `WARNING`: Recoverable failures (parse failures, missing data): `__init__.py` line 60
  - `ERROR`: Fatal/user-facing errors: `cli.py` line 289
- Structured logging with context: `logger.info(f"Filtered by test name ({', '.join(test_filter)}): {len(filtered)} of {len(failures)} failures")` (`__init__.py` line 137-139)

**Type system:**
- Python 3.7+ type hints used throughout
- Imports from `typing`: `Optional`, `list`, `dict`
- Type hints on function signatures: `def __init__(self, cache_dir: str = "~/.ocs-ci/analysis_cache", ttl_hours: int = 720)` (`cache.py` line 22)
- Return type hints: `-> Optional[tuple]`, `-> dict`, `-> list`
- Dataclass annotations: `@dataclass` decorator from `dataclasses` module for models (`models.py` lines 29-43)

**Module organization:**
- Imports ordered: standard library → third-party → local
- Each module has docstring describing purpose
- Private/public distinction enforced with underscore prefix
- Enum values follow pattern: `ENUM_VALUE = "enum_value"` for string representation

**String handling:**
- F-strings for all formatting: `logger.debug(f"Cached analysis for {signature.cache_key}")`
- String normalization uses `.lower()`, `.strip()` before comparisons
- Regex patterns compiled once and cached: `known_issues.py` lines 52-59

## Import Organization

**Order:**
1. Standard library (json, logging, os, re, time, etc.)
2. Third-party (yaml, jinja2, requests)
3. Local OCS-CI imports (ocs_ci.utility.log_analysis.*)

**Examples from codebase:**
- `cache.py`: json, logging, os, time → typing → local imports
- `__init__.py`: logging, datetime → models imports → lazy imports within functions for optional backends
- `cli.py`: argparse, logging, os, sys, urllib3 → local imports → conditional imports for Jira config

**Lazy imports:**
- Used for optional backends and integrations in main analysis function: `__init__.py` lines 42-44, 156-161, 223-226, 288-293
- Prevents hard dependencies on rarely-used features

**Path aliases:**
- No explicit path aliases (no @ shortcuts)
- Absolute imports from `ocs_ci` package root throughout

## Function Design

**Size:** Functions typically 15-50 lines for complex operations
- Larger orchestration functions: `analyze_run()` (100+ lines, well-commented)
- Small utility functions: `_safe_remove()` (4 lines, `cache.py`)
- Parser functions: 20-40 lines with focused responsibility

**Parameters:**
- Use of dataclass/model objects for groups of related parameters: `TestResult`, `RunMetadata` passed as single units
- `**kwargs` used for optional feature flags in `analyze_run()`: enables flexible configuration without signature bloat
- Default values for optional parameters: `ttl_hours: int = 720`, `max_failures: int = 30`

**Return values:**
- Single return value per function (no tuples of unrelated types)
- Return tuples only for cohesive pairs: `(analysis_dict, cache_file_path)` in `cache.py` line 35
- Dataclass instances for complex returns: `FailureAnalysis` contains all result data
- Explicit None returns for cache miss: `cache.py` line 47

## Comments

**When to comment:**
- Regex patterns explained inline: `# Patterns indicating Ceph health output` (`test_log_parser.py` line 28)
- Algorithm tradeoffs: `# Prioritize: errors > cmd_errors > ceph_health > tail` (`test_log_parser.py` line 209)
- Non-obvious parameter meanings: `# Prefer full nightly OCP version from JUnit over short YAML version` (`__init__.py` line 78)

**Module docstrings:**
- All modules have docstring at top explaining purpose and usage
- Example: `ai/claude_code_backend.py` lines 1-5 explain the backend approach
- Includes context about dependencies and requirements

**Docstring usage:**
- Classes and methods use triple-quote docstrings with Args/Returns sections
- Example: `AnalysisCache.get()` docstring (`cache.py` lines 36-44) documents parameters, return type, and semantics
- Functions rarely have detailed docstrings (implied by clear naming and type hints)

## Module Design

**Exports:**
- Modules export their main public class/function
- `models.py` exports: `TestResult`, `FailureAnalysis`, `RunAnalysis`, enums
- `cache.py` exports: `AnalysisCache`
- `__init__.py` exports: `analyze_run()` as main entry point

**Barrel files:**
- `__init__.py` files are minimal: import and re-export or add module-level `logger`
- No star imports used throughout codebase
- Explicit imports in other modules: `from ocs_ci.utility.log_analysis.models import TestResult`

**Data flow:**
- Dataclass models flow through layers: `TestResult` → `FailureAnalysis` → `RunAnalysis`
- Dictionaries used for serialization: `.to_dict()` methods on all models
- JSON used for cache persistence and reporting

## Anti-patterns to Avoid

**Do NOT:**
- Use bare `except Exception` — always specify exception types (seen pattern in most modules)
- Hardcode strings that should be constants or enums (e.g., failure categories defined in `FailureCategory` enum)
- Mix logging levels — debug for debug, warning for recoverable errors, error for failures
- Perform expensive operations (AI calls, downloads) before checking cache
- Pass raw string arguments that could be typed models (use dataclasses)
- Use global state except for module-level `logger`
