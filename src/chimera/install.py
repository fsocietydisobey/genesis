"""`chimera install` — copy the chimera skill bundle into a project's
`.claude/` directory so Claude Code picks them up.

Mental model: chimera ships skills (markdown files in this repo's
`.claude/skills/`) that turn Claude Code into a chimera-flavored
LangGraph dev environment. This command is the one-shot installer
that drops those skills into any project the user wants them in.

Idempotent — re-running overwrites with the latest version (with a
backup of the previous one). Skill files are versioned in chimera's
git history; users opt into updates by re-running install.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

# Source of truth — the skills shipped with this chimera repo.
_CHIMERA_REPO = Path(__file__).resolve().parents[2]
_BUNDLE_SOURCE = _CHIMERA_REPO / ".claude" / "skills"


def _cmd_install(args: argparse.Namespace) -> int:
    target_root = Path(args.target).resolve()
    if not target_root.is_dir():
        print(f"chimera install: not a directory: {target_root}", file=sys.stderr)
        return 1

    target_skills = target_root / ".claude" / "skills"
    target_skills.mkdir(parents=True, exist_ok=True)

    if not _BUNDLE_SOURCE.is_dir():
        print(
            f"chimera install: bundle not found at {_BUNDLE_SOURCE}\n"
            "This usually means chimera was installed without the skill bundle.\n"
            "Re-clone or pull the latest from "
            "https://github.com/fsocietydisobey/chimera",
            file=sys.stderr,
        )
        return 1

    skills = sorted(_BUNDLE_SOURCE.glob("*.md"))
    if not skills:
        print(f"chimera install: no skills in {_BUNDLE_SOURCE}", file=sys.stderr)
        return 1

    installed: list[str] = []
    backed_up: list[str] = []
    for src in skills:
        dst = target_skills / src.name
        if dst.exists() and not args.force:
            # Compare contents — only back up if actually different
            if dst.read_text(encoding="utf-8") == src.read_text(encoding="utf-8"):
                installed.append(f"  = {src.name} (unchanged)")
                continue
            backup = dst.with_suffix(dst.suffix + ".bak")
            shutil.copy2(dst, backup)
            backed_up.append(backup.name)
        shutil.copy2(src, dst)
        installed.append(f"  ✓ {src.name}")

    print(f"chimera install: bundled {len(skills)} skill(s) → {target_skills}")
    for line in installed:
        print(line)
    if backed_up:
        print(f"\nBacked up {len(backed_up)} pre-existing skill(s) with .bak suffix.")

    # Helpful next steps.
    print(
        "\nNext:\n"
        f"  cd {target_root}\n"
        "  claude\n"
        "  → skills auto-trigger on relevant phrases, or invoke explicitly:\n"
        "    /debug-runtime-issue, /feature-impact-analysis, /full-stack-trace\n"
    )
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    """Report which MCP servers chimera's skills can compose with.

    Doesn't mutate anything — just probes the user's setup and tells
    them which skills will be fully usable, which will be partial,
    and which need missing tools installed.
    """
    target = Path(args.target).resolve() if args.target else Path.cwd()

    print(f"chimera doctor: probing {target}\n")

    # 1. Skills installed?
    skills_dir = target / ".claude" / "skills"
    chimera_skills = ["debug-runtime-issue.md", "feature-impact-analysis.md", "full-stack-trace.md"]
    skill_status: dict[str, bool] = {}
    if skills_dir.is_dir():
        for s in chimera_skills:
            skill_status[s] = (skills_dir / s).exists()
    else:
        for s in chimera_skills:
            skill_status[s] = False

    print("Skills (run `chimera install <project>` to install):")
    for s, ok in skill_status.items():
        print(f"  {'✓' if ok else '✗'} {s}")

    # 2. Monitor daemon up?
    print("\nMonitor daemon (chimera monitor start):")
    try:
        import urllib.request

        with urllib.request.urlopen("http://127.0.0.1:8740/api/projects", timeout=2) as resp:
            ok = resp.status == 200
    except Exception:
        ok = False
    print(f"  {'✓' if ok else '✗'} http://127.0.0.1:8740 reachable")

    # 3. Optional MCP servers — best-effort discovery via .claude/mcp.json
    # or environment hints. We can't reliably introspect from here, so
    # surface what the skills WANT and let the user verify.
    print("\nMCP servers chimera's skills compose with:")
    optional = [
        ("séance",  "Semantic code search — used by all skills for finding anchor patterns"),
        ("scarlet", "Codebase cartography — used by feature-impact-analysis"),
        ("specter", "Browser eyes — used by full-stack-trace"),
        ("postgres", "DB queries — used by full-stack-trace, feature-impact-analysis"),
    ]
    for name, desc in optional:
        print(f"  ? {name}  — {desc}")
    print(
        "\nCan't auto-detect MCP servers from here. If you've configured them in\n"
        "Claude Code (~/.config/claude-desktop or .mcp.json), the skills will\n"
        "compose them. If not, the skills fall back to bash/grep/curl where\n"
        "possible — degraded but still useful."
    )

    fully_ready = all(skill_status.values()) and ok
    print(f"\n{'READY' if fully_ready else 'PARTIAL'}: chimera skill pack")
    return 0 if fully_ready else 0  # non-fatal — partial is OK


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="chimera install")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_install = sub.add_parser(
        "install",
        help="Copy chimera's skill bundle into a project's .claude/skills/",
    )
    p_install.add_argument(
        "target",
        nargs="?",
        default=str(Path.cwd()),
        help="Target project directory (default: current directory)",
    )
    p_install.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing skills without backup",
    )
    p_install.set_defaults(func=_cmd_install)

    p_doctor = sub.add_parser(
        "doctor",
        help="Check which MCP servers + skills are available",
    )
    p_doctor.add_argument(
        "target",
        nargs="?",
        default=None,
        help="Target project directory (default: current directory)",
    )
    p_doctor.set_defaults(func=_cmd_doctor)

    args = parser.parse_args(argv)
    sys.exit(args.func(args))
