"""Run Gemini and Claude CLI subprocesses with session continuity."""

import json
from typing import TYPE_CHECKING

from chimera.log import get_logger
from chimera.cli import config
from chimera.cli.cli import cli_available, run_cli
from chimera.cli import state

if TYPE_CHECKING:
    from mcp.server.fastmcp import Context

log = get_logger("runners")


async def run_gemini(
    prompt: str, timeout: int | None = None, ctx: "Context | None" = None
) -> str:
    """Run a prompt through Gemini CLI, continuing the session if one exists."""
    if not cli_available(config.GEMINI_CMD):
        return f"Error: Gemini CLI not found at `{config.GEMINI_CMD}`. Install with: npm install -g @google/gemini-cli"

    cmd = [config.GEMINI_CMD, "-m", config.GEMINI_MODEL, "-p", prompt, "-o", "json"]
    if state.gemini_session_id:
        cmd.extend(["--resume", state.gemini_session_id])

    log.info("gemini: sending prompt (%d chars), session=%s", len(prompt), state.gemini_session_id or "new")

    try:
        raw = await run_cli(cmd, timeout=timeout, ctx=ctx, label="gemini")
    except (TimeoutError, RuntimeError) as e:
        log.error("gemini: %s", e)
        return f"Error: {e}"

    try:
        data = json.loads(raw)
        session_id = data.get("session_id") or data.get("sessionId")
        if session_id:
            state.gemini_session_id = session_id

        result = data.get("result", "") or data.get("response", "") or data.get("text", "")
        if not result:
            for block in data.get("content", []):
                if isinstance(block, dict) and block.get("type") == "text":
                    result += block.get("text", "")
        log.info("gemini: got %d chars, session=%s", len(result or raw), state.gemini_session_id)
        return result or raw
    except (json.JSONDecodeError, TypeError):
        log.warning("gemini: response was not valid JSON (%d chars)", len(raw))
        return raw


async def run_claude(
    prompt: str, timeout: int | None = None, ctx: "Context | None" = None,
    permission_mode: str | None = None,
) -> str:
    """Run a prompt through Claude Code CLI, continuing the session if one exists.

    Args:
        prompt: The prompt to send.
        timeout: Max seconds to wait.
        ctx: Optional MCP context for heartbeats.
        permission_mode: Claude permission mode. None = default (prompts for permissions).
            "acceptEdits" = auto-accept file writes (for implement node).
    """
    if not cli_available(config.CLAUDE_CMD):
        return f"Error: Claude CLI not found at `{config.CLAUDE_CMD}`. Set CLAUDE_CMD env var or install Claude Code."

    cmd = [config.CLAUDE_CMD, "--model", config.CLAUDE_MODEL, "--effort", "medium",
           "-p", prompt, "--output-format", "json"]
    if permission_mode:
        cmd.extend(["--permission-mode", permission_mode])
    if state.claude_session_id:
        cmd.extend(["--resume", state.claude_session_id])

    log.info("claude: sending prompt (%d chars), session=%s", len(prompt), state.claude_session_id or "new")

    try:
        raw = await run_cli(cmd, timeout=timeout, ctx=ctx, label="claude")
    except (TimeoutError, RuntimeError) as e:
        log.error("claude: %s", e)
        return f"Error: {e}"

    try:
        data = json.loads(raw)
        session_id = data.get("session_id") or data.get("sessionId")
        if session_id:
            state.claude_session_id = session_id

        result = data.get("result", "")
        if not result:
            for block in data.get("content", []):
                if isinstance(block, dict) and block.get("type") == "text":
                    result += block.get("text", "")
        log.info("claude: got %d chars, session=%s", len(result or raw), state.claude_session_id)
        return result or raw
    except (json.JSONDecodeError, TypeError):
        log.warning("claude: response was not valid JSON (%d chars)", len(raw))
        return raw
