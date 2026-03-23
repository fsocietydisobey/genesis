"""Configuration for the CLI-based MCP server (env-based)."""

import os

# Project root defaults to cwd; override with PROJECT_ROOT env var
PROJECT_ROOT = os.environ.get("PROJECT_ROOT", os.getcwd())

# Subprocess timeout in seconds (5 minutes default — heartbeats keep MCP alive)
CLI_TIMEOUT = int(os.environ.get("CLI_TIMEOUT", "300"))

# Models — override via env vars
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-6")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# CLI paths — override via env vars if needed
CLAUDE_CMD = os.environ.get("CLAUDE_CMD", "claude")

# Gemini CLI — installed globally via: npm install -g @google/gemini-cli
_NVM_NODE_VERSION = os.environ.get("NVM_NODE_VERSION", "24.14.0")
_NVM_BIN = os.path.expanduser(f"~/.nvm/versions/node/v{_NVM_NODE_VERSION}/bin")
GEMINI_CMD = os.environ.get("GEMINI_CMD", os.path.join(_NVM_BIN, "gemini"))

# Total timeout for the entire orchestration pipeline (default 10 minutes)
ORCHESTRATE_TIMEOUT = int(os.environ.get("ORCHESTRATE_TIMEOUT", "600"))
