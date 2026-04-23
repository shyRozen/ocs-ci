# OCS-CI Log Analysis — NVIDIA NIM Backend

## What This Is

Adding a `nim` AI backend to the OCS-CI log analysis tool. It subclasses the existing `ClaudeCodeBackend`, injecting LiteLLM proxy environment variables so the same `claude` CLI subprocess routes through NVIDIA NIM models. Both agentic and non-agentic modes work unchanged — same prompts, same JSON schema, same flags.

## Core Value

Run the full log analysis pipeline (including agentic must-gather investigation) through NVIDIA NIM models via `--ai-backend nim`, with zero changes to prompts, classification logic, or tool use.

## Requirements

### Validated

- ✓ Pluggable AI backend system (`ai/base.py` factory pattern) — existing
- ✓ Claude Code CLI subprocess backend with agentic + non-agentic modes — existing
- ✓ Anthropic SDK backend (single-turn) — existing
- ✓ Three-tier classification pipeline (regex → cache → AI) — existing
- ✓ Structured JSON output via `--json-schema` — existing
- ✓ Agentic investigation with Bash/Read tool use — existing
- ✓ Session recording and audit trails — existing
- ✓ Cost control (budget caps, caching, dedup) — existing
- ✓ CLI (`--ai-backend`, `--model`) and framework config switching — existing

### Active

- [ ] `NimBackend` class that subclasses `ClaudeCodeBackend` and injects LiteLLM proxy env vars
- [ ] Register `nim` in backend factory and CLI `--ai-backend` choices
- [ ] Framework config support (`ai_backend: "nim"`)
- [ ] Agentic mode working through NIM (same tool use, same prompts)
- [ ] Non-agentic structured JSON output working through NIM
- [ ] Run summary generation working through NIM

### Out of Scope

- LiteLLM proxy setup/deployment — user manages separately
- Docker configuration for LiteLLM — already handled
- Prompt modifications for NIM models — `drop_params: true` handles differences
- Anthropic SDK backend migration — only Claude Code CLI path
- New agentic loop — reusing existing Claude Code CLI approach

## Context

- LiteLLM proxy on `localhost:4000` via Docker, config at `/home/srozen/nvidia/config.yaml`
- Proxy model mapping:
  - `claude-sonnet-4-6` → `nvidia_nim/qwen/qwen3.5-122b-a10b`
  - `claude-opus-4-6` → `nvidia_nim/z-ai/glm5`
  - `claude-haiku-4-5` → `nvidia_nim/moonshotai/kimi-k2.5`
- Master key: `sk-litellm-local`
- `drop_params: true` silently drops unsupported Claude-specific parameters
- The `claude-nim` bash alias shows the exact env vars needed:
  ```
  ANTHROPIC_BASE_URL=http://localhost:4000
  ANTHROPIC_API_KEY=sk-litellm-local
  ANTHROPIC_MODEL=claude-sonnet-4-6
  ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-4-6
  ANTHROPIC_DEFAULT_SONNET_MODEL=claude-sonnet-4-6
  ANTHROPIC_DEFAULT_HAIKU_MODEL=claude-haiku-4-5
  ```
- `claude_code_backend.py` already manages subprocess environment (removes `CLAUDECODE` var)
- `--model` flag (sonnet/haiku/opus) stays the same — proxy handles the mapping

## Constraints

- **Proxy dependency**: NIM backend requires LiteLLM proxy running on `localhost:4000`
- **No prompt changes**: Same Jinja2 templates for both Claude and NIM
- **Existing backends untouched**: Must not break `claude-code` or `anthropic` paths

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Subclass `ClaudeCodeBackend` | Same code path, only env vars differ — minimal code addition | — Pending |
| New `--ai-backend nim` value | Clean separation, existing backends untouched | — Pending |
| Inject env vars in subprocess only | Avoid affecting other processes or user's shell | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-23 after initialization*
