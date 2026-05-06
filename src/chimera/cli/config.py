"""Configuration for the CLI-based MCP server (env-based)."""

import os
import shutil
from pathlib import Path

import yaml

from chimera.log import get_logger

_log = get_logger("config")

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


# ---------------------------------------------------------------------------
# Project-roots registry
# ---------------------------------------------------------------------------
# Spawned claude/gemini subprocesses are scoped to a primary `cwd` (where
# files get written). The roots registry expands their READ scope: every
# registered root is passed via --add-dir / --include-directories so the
# subprocess can grep across all known projects regardless of which one is
# currently cwd. Lets a single `/chimera-research` call ground itself
# against multiple repos without per-call context plumbing.

# Chimera's own repo, always included so chimera can introspect itself.
_CHIMERA_REPO_ROOT = str(Path(__file__).resolve().parents[3])

# Resolution order for the registry file:
#   1. CHIMERA_ROOTS_FILE env var (explicit override)
#   2. $XDG_CONFIG_HOME/chimera/roots.yaml
#   3. ~/.config/chimera/roots.yaml
_DEFAULT_ROOTS_FILE = (
    Path(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))) / "chimera" / "roots.yaml"
)
ROOTS_FILE = Path(os.environ.get("CHIMERA_ROOTS_FILE", _DEFAULT_ROOTS_FILE))


def _load_roots(roots_file: Path = ROOTS_FILE, *, chimera_repo: str = _CHIMERA_REPO_ROOT) -> list[str]:
    """Load the project-roots registry.

    Returns a deduplicated list of absolute paths that exist on disk.
    Always includes the chimera repo. Missing/malformed config is non-fatal
    — the function logs a warning and falls back to just the chimera repo.
    """
    seen: set[str] = set()
    out: list[str] = []

    def _add(path_str: str) -> None:
        resolved = str(Path(os.path.expanduser(path_str)).resolve())
        if resolved in seen:
            return
        if not Path(resolved).is_dir():
            _log.warning("roots: skipping %s — not a directory", path_str)
            return
        seen.add(resolved)
        out.append(resolved)

    _add(chimera_repo)

    if not roots_file.exists():
        _log.info("roots: no registry at %s — using chimera repo only", roots_file)
        return out

    try:
        data = yaml.safe_load(roots_file.read_text()) or {}
    except yaml.YAMLError as e:
        _log.warning("roots: failed to parse %s (%s) — using chimera repo only", roots_file, e)
        return out

    raw_roots = data.get("roots") if isinstance(data, dict) else None
    if not isinstance(raw_roots, list):
        _log.warning("roots: %s missing top-level `roots:` list — using chimera repo only", roots_file)
        return out

    for entry in raw_roots:
        if isinstance(entry, str) and entry.strip():
            _add(entry.strip())

    return out


# Loaded once at import time. To pick up registry changes, restart chimera.
ROOTS = _load_roots()
