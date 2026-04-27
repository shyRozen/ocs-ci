"""
NIM backend for AI-powered log analysis via LiteLLM proxy.

Routes Claude Code CLI subprocess calls through a LiteLLM proxy
running on localhost:4000 that maps Anthropic model names to
NVIDIA NIM endpoints. Subclasses ClaudeCodeBackend and overrides
only the subprocess call methods to inject proxy environment variables.

Same prompts, same JSON schema, same flags -- the only difference
is the ANTHROPIC_BASE_URL pointing at the local LiteLLM proxy.

Requires:
    - Claude Code CLI (`claude`) installed
    - LiteLLM proxy running on localhost:4000
"""

import logging
import os

import requests

from ocs_ci.utility.log_analysis.ai.claude_code_backend import ClaudeCodeBackend

logger = logging.getLogger(__name__)

NIM_MODEL_MAP = {
    "opus": "claude-opus-4-6",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5",
}

NIM_ENV_SET = {
    "ANTHROPIC_BASE_URL": "http://localhost:4000",
    "ANTHROPIC_API_KEY": "sk-litellm-local",
    "ANTHROPIC_MODEL": NIM_MODEL_MAP["sonnet"],
    "ANTHROPIC_DEFAULT_OPUS_MODEL": NIM_MODEL_MAP["opus"],
    "ANTHROPIC_DEFAULT_SONNET_MODEL": NIM_MODEL_MAP["sonnet"],
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": NIM_MODEL_MAP["haiku"],
}

# Vars that conflict with LiteLLM proxy routing — must be unset during NIM calls
NIM_ENV_UNSET = [
    "CLAUDE_CODE_USE_VERTEX",
    "ANTHROPIC_VERTEX_PROJECT_ID",
]


class NimBackend(ClaudeCodeBackend):
    """
    AI backend that routes Claude Code CLI through a LiteLLM proxy to NVIDIA NIM.

    Inherits all behavior from ClaudeCodeBackend (prompts, JSON schemas, cost
    tracking). Builds a clean subprocess environment with NIM_ENV_SET injected
    and Vertex-related vars removed so the claude CLI connects to the LiteLLM
    proxy instead of Vertex or the Anthropic API directly.
    """

    # Proxy adds latency — give more headroom than the direct-API defaults
    SUBPROCESS_TIMEOUT = 500
    AGENTIC_TIMEOUT = 1500

    def __init__(self, model="sonnet", max_budget_usd=0.50, save_prompts_dir=None):
        super().__init__(
            model=model,
            max_budget_usd=max_budget_usd,
            save_prompts_dir=save_prompts_dir,
        )

    def _nim_env(self) -> None:
        """Inject NIM vars and remove conflicting Vertex vars from os.environ."""
        for k, v in NIM_ENV_SET.items():
            os.environ[k] = v
        for k in NIM_ENV_UNSET:
            os.environ.pop(k, None)

    def _save_env(self) -> dict:
        """Snapshot env vars that will be modified."""
        keys = list(NIM_ENV_SET.keys()) + NIM_ENV_UNSET
        return {k: os.environ.get(k) for k in keys}

    def _restore_env(self, saved: dict) -> None:
        """Restore env vars from snapshot."""
        for k, original in saved.items():
            if original is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = original

    def is_available(self) -> bool:
        """Check if claude CLI is installed and LiteLLM proxy is reachable."""
        if not super().is_available():
            return False

        try:
            requests.get("http://localhost:4000/health", timeout=2)
            return True
        except requests.ConnectionError:
            logger.warning(
                "LiteLLM proxy not reachable at localhost:4000. "
                "Start the proxy before using --ai-backend nim."
            )
            return False
        except requests.Timeout:
            logger.warning(
                "LiteLLM proxy health check timed out at localhost:4000."
            )
            return False

    def _call_claude(self, prompt: str, json_schema: str, context: str = "") -> dict:
        """Call claude CLI with NIM proxy env vars injected."""
        saved = self._save_env()
        try:
            self._nim_env()
            return super()._call_claude(prompt, json_schema, context)
        finally:
            self._restore_env(saved)

    def _call_claude_agentic(
        self, prompt: str, context: str = "", allowed_tools: str = "Bash"
    ) -> dict:
        """Call claude CLI in agentic mode with NIM proxy env vars injected."""
        saved = self._save_env()
        try:
            self._nim_env()
            return super()._call_claude_agentic(prompt, context, allowed_tools)
        finally:
            self._restore_env(saved)

