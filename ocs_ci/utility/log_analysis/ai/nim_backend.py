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

NIM_ENV_VARS = {
    "ANTHROPIC_BASE_URL": "http://localhost:4000",
    "ANTHROPIC_API_KEY": "sk-litellm-local",
    "ANTHROPIC_MODEL": "claude-sonnet-4-6",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "claude-opus-4-6",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-sonnet-4-6",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-haiku-4-5",
}


class NimBackend(ClaudeCodeBackend):
    """
    AI backend that routes Claude Code CLI through a LiteLLM proxy to NVIDIA NIM.

    Inherits all behavior from ClaudeCodeBackend (prompts, JSON schemas, cost
    tracking). The only change is injecting NIM_ENV_VARS into os.environ before
    each subprocess call so the claude CLI connects to the LiteLLM proxy
    instead of the Anthropic API directly.
    """

    def __init__(self, model="sonnet", max_budget_usd=0.50, save_prompts_dir=None):
        """
        Args:
            model: Model to use (sonnet, opus, haiku)
            max_budget_usd: Max spend per AI call in USD
            save_prompts_dir: Directory to save prompts for debugging (None = disabled)
        """
        super().__init__(
            model=model,
            max_budget_usd=max_budget_usd,
            save_prompts_dir=save_prompts_dir,
        )

    def is_available(self) -> bool:
        """Check if claude CLI is installed and LiteLLM proxy is reachable."""
        if not super().is_available():
            return False

        try:
            response = requests.get("http://localhost:4000/health", timeout=2)
            return response.ok
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
        saved = {k: os.environ.get(k) for k in NIM_ENV_VARS}
        try:
            for k, v in NIM_ENV_VARS.items():
                os.environ[k] = v
            return super()._call_claude(prompt, json_schema, context)
        finally:
            for k, original in saved.items():
                if original is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = original

    def _call_claude_agentic(
        self, prompt: str, context: str = "", allowed_tools: str = "Bash"
    ) -> dict:
        """Call claude CLI in agentic mode with NIM proxy env vars injected."""
        saved = {k: os.environ.get(k) for k in NIM_ENV_VARS}
        try:
            for k, v in NIM_ENV_VARS.items():
                os.environ[k] = v
            return super()._call_claude_agentic(prompt, context, allowed_tools)
        finally:
            for k, original in saved.items():
                if original is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = original
