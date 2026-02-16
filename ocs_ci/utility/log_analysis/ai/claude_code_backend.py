"""
Claude Code CLI backend for AI-powered log analysis.

Calls `claude -p` via subprocess with --output-format json
and --json-schema for structured output. Requires no API key --
uses Claude Code's own authentication.
"""

import json
import logging
import os
import shutil
import subprocess

from jinja2 import Environment, FileSystemLoader

from ocs_ci.utility.log_analysis.ai.base import AIBackend
from ocs_ci.utility.log_analysis.exceptions import AIBackendError

logger = logging.getLogger(__name__)

PROMPT_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "prompt_templates")

CLASSIFICATION_SCHEMA = json.dumps(
    {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": [
                    "product_bug",
                    "test_bug",
                    "infra_issue",
                    "flaky_test",
                    "unknown",
                ],
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
            },
            "root_cause_summary": {
                "type": "string",
                "description": "One paragraph explaining the root cause",
            },
            "evidence": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Key evidence points supporting the classification",
            },
            "recommended_action": {
                "type": "string",
                "description": "What should be done about this failure",
            },
        },
        "required": [
            "category",
            "confidence",
            "root_cause_summary",
            "evidence",
            "recommended_action",
        ],
    }
)

SUMMARY_SCHEMA = json.dumps(
    {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "2-4 sentence executive summary of the run",
            },
        },
        "required": ["summary"],
    }
)


class ClaudeCodeBackend(AIBackend):
    """
    AI backend that calls Claude Code CLI (`claude -p`) via subprocess.

    This is the default backend. It requires no API key -- it uses
    Claude Code's own authentication (login or ANTHROPIC_API_KEY env var).
    """

    # Timeout for subprocess calls in seconds
    SUBPROCESS_TIMEOUT = 180

    def __init__(self, model="sonnet", max_budget_usd=0.50):
        """
        Args:
            model: Model to use (sonnet, opus, haiku)
            max_budget_usd: Max spend per AI call in USD
        """
        self.model = model
        self.max_budget_usd = max_budget_usd
        self.jinja_env = Environment(
            loader=FileSystemLoader(PROMPT_TEMPLATES_DIR),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def is_available(self) -> bool:
        """Check if claude CLI is installed and accessible."""
        return shutil.which("claude") is not None

    def classify_failure(
        self,
        test_name: str,
        test_class: str,
        duration: float,
        squad: str,
        traceback: str,
        log_excerpt: str = "",
        infra_context: str = "",
    ) -> dict:
        """Classify a test failure using Claude Code CLI."""
        template = self.jinja_env.get_template("classify_failure.j2")
        prompt = template.render(
            test_name=test_name,
            test_class=test_class,
            duration=duration,
            squad=squad or "Unknown",
            traceback=self._truncate(traceback, 4000),
            log_excerpt=self._truncate(log_excerpt, 6000),
            infra_context=self._truncate(infra_context, 4000),
        )

        result = self._call_claude(prompt, CLASSIFICATION_SCHEMA)

        # Validate and provide defaults
        return {
            "category": result.get("category", "unknown"),
            "confidence": float(result.get("confidence", 0.5)),
            "root_cause_summary": result.get("root_cause_summary", ""),
            "evidence": result.get("evidence", []),
            "recommended_action": result.get("recommended_action", ""),
        }

    def generate_run_summary(
        self,
        run_metadata: dict,
        failure_summaries: list,
    ) -> str:
        """Generate an overall run summary using Claude Code CLI."""
        if not failure_summaries:
            return "No failures to summarize."

        template = self.jinja_env.get_template("run_summary.j2")
        prompt = template.render(
            platform=run_metadata.get("platform", "unknown"),
            deployment_type=run_metadata.get("deployment_type", "unknown"),
            ocp_version=run_metadata.get("ocp_version", "unknown"),
            ocs_version=run_metadata.get("ocs_version", "unknown"),
            ocs_build=run_metadata.get("ocs_build", "unknown"),
            total_tests=run_metadata.get("total_tests", 0),
            passed=run_metadata.get("passed", 0),
            failed=run_metadata.get("failed", 0),
            error=run_metadata.get("error", 0),
            skipped=run_metadata.get("skipped", 0),
            failure_summaries=failure_summaries,
        )

        result = self._call_claude(prompt, SUMMARY_SCHEMA)
        return result.get("summary", "")

    def _call_claude(self, prompt: str, json_schema: str) -> dict:
        """
        Call claude CLI in non-interactive mode.

        Args:
            prompt: The prompt text
            json_schema: JSON schema string for structured output

        Returns:
            Parsed structured output dict

        Raises:
            AIBackendError: If the call fails
        """
        cmd = [
            "claude",
            "-p", prompt,
            "--output-format", "json",
            "--json-schema", json_schema,
            "--model", self.model,
            "--max-budget-usd", str(self.max_budget_usd),
        ]

        logger.debug(
            f"Calling Claude Code CLI (model={self.model}, "
            f"prompt_length={len(prompt)})"
        )

        # Remove CLAUDECODE env var to allow launching from within
        # a Claude Code session (nested session guard bypass)
        env = os.environ.copy()
        env.pop("CLAUDECODE", None)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.SUBPROCESS_TIMEOUT,
                env=env,
            )
        except subprocess.TimeoutExpired:
            raise AIBackendError(
                f"Claude Code CLI timed out after {self.SUBPROCESS_TIMEOUT}s"
            )
        except FileNotFoundError:
            raise AIBackendError(
                "Claude Code CLI ('claude') not found. "
                "Install it or use --ai-backend anthropic"
            )
        except OSError as e:
            raise AIBackendError(f"Failed to run Claude Code CLI: {e}")

        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise AIBackendError(
                f"Claude Code CLI exited with code {result.returncode}: {stderr}"
            )

        # Parse the JSON response
        try:
            response = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise AIBackendError(
                f"Failed to parse Claude Code CLI output as JSON: {e}\n"
                f"stdout: {result.stdout[:500]}"
            )

        # Extract structured output from the response
        subtype = response.get("subtype", "")
        structured = response.get("structured_output")

        if subtype == "error_max_turns" and structured is None:
            logger.debug(
                f"Claude Code hit max_turns (num_turns={response.get('num_turns')}). "
                f"Retrying is not supported; raising error."
            )

        if structured is None:
            # Fall back to parsing the result text as JSON
            result_text = response.get("result", "")
            try:
                structured = json.loads(result_text)
            except (json.JSONDecodeError, TypeError):
                raise AIBackendError(
                    f"No structured_output in Claude Code response "
                    f"(subtype={subtype}, num_turns={response.get('num_turns')}). "
                    f"result: {result_text[:500]}"
                )

        # Log cost if available
        cost = response.get("total_cost_usd")
        if cost is not None:
            logger.info(f"Claude Code call cost: ${cost:.4f}")

        return structured

    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        """Truncate text to max_chars, adding a truncation notice."""
        if not text or len(text) <= max_chars:
            return text or ""
        return text[:max_chars] + f"\n... [truncated, {len(text) - max_chars} chars omitted]"
