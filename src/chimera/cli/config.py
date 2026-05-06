"""Configuration for the CLI-based MCP server (env-based)."""

import os
import shutil

# Project root resolution:
#   1. PROJECT_ROOT env var (explicit override)
#   2. PWD env var (preserved across `uv --directory` chdir; this is the
#      cwd of whoever launched chimera — typically the calling Claude Code
#      session's project directory)
#   3. os.getcwd() (chimera's own dir if launched via `uv --directory`)
PROJECT_ROOT = os.environ.get("PROJECT_ROOT") or os.environ.get("PWD") or os.getcwd()

# Subprocess timeout in seconds (5 minutes default — heartbeats keep MCP alive)
CLI_TIMEOUT = int(os.environ.get("CLI_TIMEOUT", "300"))

# Models — override via env vars
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-6")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


def _resolve_cli(env_var: str, name: str, *fallbacks: str) -> str:
    """Resolve a CLI binary path with self-healing precedence:

    1. Explicit env var override (e.g. CLAUDE_CMD, GEMINI_CMD).
    2. shutil.which(name) — picks up whatever's on PATH right now.
       Survives nvm version bumps, Homebrew migrations, etc.
    3. Hardcoded fallback paths, in order. First one that exists wins.
    4. Bare name — let the subprocess fail with a clear error if it's
       genuinely missing.
    """
    if v := os.environ.get(env_var):
        return v
    if found := shutil.which(name):
        return found
    for path in fallbacks:
        if os.path.isfile(path):
            return path
    return name


# CLI paths — override via env vars or rely on PATH discovery
CLAUDE_CMD = _resolve_cli("CLAUDE_CMD", "claude")

# Gemini CLI — installed globally via: npm install -g @google/gemini-cli
# NVM_NODE_VERSION fallback is a last-resort hint; PATH-based discovery
# (shutil.which) is preferred and self-heals across nvm version bumps.
_NVM_NODE_VERSION = os.environ.get("NVM_NODE_VERSION", "24.14.1")
_NVM_GEMINI_PATH = os.path.expanduser(f"~/.nvm/versions/node/v{_NVM_NODE_VERSION}/bin/gemini")
GEMINI_CMD = _resolve_cli("GEMINI_CMD", "gemini", _NVM_GEMINI_PATH)

# Total timeout for the entire orchestration pipeline (default 10 minutes)
ORCHESTRATE_TIMEOUT = int(os.environ.get("ORCHESTRATE_TIMEOUT", "600"))
