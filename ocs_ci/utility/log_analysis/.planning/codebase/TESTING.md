# Testing

**Analysis Date:** 2026-04-23

## Framework

**Test runner:** No unit test framework detected. This module does not contain pytest/unittest test files.

**Assertion library:** Not applicable — no test code found.

**Integration point:** The module includes a pytest plugin hook in `integrations/ci_hook.py` for integration with the OCS-CI test suite, but does not test itself via automated tests.

## Test File Organization

**Status:** No dedicated test suite exists in this module.

**Finding:** Searched for:
- `test_*.py` files: Only found `parsers/test_log_parser.py` (which is a production parser, not test code)
- `*_test.py` files: None found
- `conftest.py`: None found
- pytest fixtures: No pytest imports found (except in CI hook documentation)
- unittest classes: No `unittest.TestCase` subclasses

This is a library/utility module without internal test coverage. Testing is performed externally by:
1. The OCS-CI test suite that uses this log analysis module
2. The CI hook integration (`integrations/ci_hook.py`) which integrates with pytest session completion

## Test Structure

Not applicable — no test code.

## Manual Testing / Verification Approach

Based on code inspection, the module appears to be tested through:

**CLI integration:** Two entry points are testable via command line:
- `analyze-logs` command in `cli.py:main()` — full log analysis pipeline
- `analyze-trends` command in `cli.py:trends_main()` — cross-run trend analysis

**Backend selection:** Multiple backends can be swapped to verify correctness:
- `"none"` backend: `ai/base.py:NoOpBackend` returns empty results (verify regex-only analysis)
- `"claude-code"` backend: `ai/claude_code_backend.py` calls Claude Code CLI
- `"anthropic"` backend: `ai/anthropic_backend.py` calls Anthropic API

**Cache verification:** Cache behavior can be tested by:
- Running analysis with `--cache-enabled` (default) and observing hits
- Running with `--cache-dir` pointing to a test directory
- Clearing cache manually via `AnalysisCache.clear()` in `cache.py:139`

## Mocking

**Not applicable** — no test framework present.

**For future implementation:** If tests are added, the module is designed for mocking:
- `AIBackend` is abstract (`ai/base.py` lines 14-100), can be subclassed
- `ArtifactFetcher` interface in `parsers/artifact_fetcher.py` could be mocked to avoid network calls
- `AnalysisCache` stores to filesystem — can be mocked with in-memory storage or temp directories

## Fixtures and Factories

**Not present** — no test framework.

**For future test development:**
- Dataclass models are self-contained: `TestResult`, `FailureAnalysis`, `RunAnalysis` in `models.py`
- Can create test instances directly: `TestResult(classname="test_pkg.TestClass", name="test_foo", status=TestStatus.FAILED, duration=5.0, traceback="...")`
- Factory: `FailureSignature.from_test_result()` in `models.py:71` creates signatures for testing cache behavior

## Coverage

**Status:** No coverage configuration found.

**Rationale:** This module serves as a utility/library for log analysis. The main `analyze_run()` function is tested indirectly through:
1. OCS-CI test suite execution and log analysis
2. CLI invocations in CI pipelines
3. Integration with pytest via the `ci_hook.py` pytest plugin

## Running Tests

**No local tests to run.** The module is tested through external integration.

**CLI-based smoke testing:**
```bash
# Test with known_issues_only mode (no AI cost, fast)
analyze-logs /path/to/logs --known-issues-only --format json -o test_output.json

# Test with local directory
analyze-logs /tmp/test_logs --ai-backend none --format markdown

# Test trend analysis
analyze-trends --history-dir ~/.ocs-ci/analysis_history --max-runs 10 --format json
```

## Test Types

**Unit testing:** Not implemented internally.

**Integration testing:** External — the OCS-CI test suite calls `analyze_run()` function:
- From `cli.py:main()` which parses CLI arguments and produces reports
- End-to-end: artifact discovery → JUnit parsing → failure analysis → report generation

**E2E testing:** Not automated in this module.
- Manual testing via CLI commands
- Integration with OCS-CI CI/CD pipelines produces test data

## Verifiable Behaviors

Code can be verified without tests via inspection:

**Caching logic** (`cache.py`):
- TTL enforcement: `cache.py:59` — checks timestamp against TTL seconds
- Cache key derivation: `cache.py:148` — consistent hashing via `signature.cache_key`
- Safe file operations: `cache.py:152-156` — exception handling on remove

**Failure signature** (`models.py`):
- Normalization: `models.py:87-88` — regex removes memory addresses and line numbers
- Hash consistency: Same exception message/traceback produces same signature

**Log parsing** (`parsers/test_log_parser.py`):
- Budget enforcement: `test_log_parser.py:202-220` — truncates to `MAX_TOTAL_CHARS`
- Error extraction: `test_log_parser.py:147-161` — filters noise patterns
- Ceph health detection: `test_log_parser.py:167-185` — contextual extraction

**Known issues matching** (`analysis/known_issues.py`):
- Pattern compilation: `known_issues.py:52-59` — pre-compiled for performance
- Match detection: `known_issues.py:62-80` — case-insensitive search

## Code Patterns for Testing (if tests are added)

**Dependency injection pattern:** Already present for AI backends:
```python
# In __init__.py:173
backend = get_backend(ai_backend, **backend_kwargs)

# For testing, pass mock backend:
mock_backend = NoOpBackend()
classifier = FailureClassifier(ai_backend=mock_backend, ...)
```

**Dataclass instantiation for test data:**
```python
# From models.py
test_result = TestResult(
    classname="test_pkg",
    name="test_failure",
    status=TestStatus.FAILED,
    duration=10.5,
    traceback="AssertionError: expected 5, got 3"
)
```

**Cache testing approach:**
```python
# From cache.py
cache = AnalysisCache(cache_dir="/tmp/test_cache")
signature = FailureSignature.from_test_result(test_result)
cache.put(signature, {"analysis": "data"})
result = cache.get(signature)
assert result is not None
```

---

**Note:** This module prioritizes **production reliability** over internal test coverage, relying on integration tests within the OCS-CI suite. The code is highly modular and testable (abstract backends, clear interfaces, minimal side effects) to support this approach.
