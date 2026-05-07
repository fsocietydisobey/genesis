#!/usr/bin/env python3
"""Check whether jeevy's upstream debugger components have drifted from
chimera-monitor's lifted copies.

Locked decision (2026-05-06): re-port jeevy's debugger components at every
chimera-monitor phase boundary instead of vendoring as an npm package.
This script makes the re-port cheap by surfacing what's changed since
the last lift.

Run pre-ship for each phase:

    uv run python scripts/check_jeevy_drift.py

Reports unified diffs of upstream changes per file. Exit 0 if no drift
or jeevy isn't checked out locally; exit 1 if any tracked file has
drifted (so this can gate CI later).
"""

from __future__ import annotations

import difflib
import sys
from dataclasses import dataclass
from pathlib import Path

CHIMERA_REPO = Path(__file__).resolve().parent.parent
JEEVY_DEBUGGER = Path("/home/_3ntropy/work/jeevy_portal/frontend/src/features/ai-debugger")


@dataclass(frozen=True)
class LiftedFile:
    """A file in chimera-monitor that was originally lifted from jeevy."""

    chimera_rel: str  # path relative to chimera repo root
    jeevy_rel: str    # path relative to JEEVY_DEBUGGER

    def chimera_path(self) -> Path:
        return CHIMERA_REPO / self.chimera_rel

    def jeevy_path(self) -> Path:
        return JEEVY_DEBUGGER / self.jeevy_rel


# Phase 1 ports. Add entries as more components are lifted.
#
# StateTab was lifted initially but dropped during the unified-view rebuild
# (the new NodeInspector renders state directly via JsonTree). MonitorShell
# diverged hard from jeevy's AIDebuggerShell — registry pattern was replaced
# by React Router routing — so it is intentionally untracked.
TRACKED: list[LiftedFile] = [
    LiftedFile(
        chimera_rel="monitor_ui/src/components/threads/JsonTree.tsx",
        jeevy_rel="views/langgraph/JsonTree.js",
    ),
]


def main() -> int:
    if not JEEVY_DEBUGGER.is_dir():
        print(f"jeevy debugger not found at {JEEVY_DEBUGGER} — skipping drift check")
        return 0

    drifted: list[LiftedFile] = []
    for entry in TRACKED:
        chimera = entry.chimera_path()
        jeevy = entry.jeevy_path()

        if not jeevy.is_file():
            print(f"upstream missing: {entry.jeevy_rel} (was it renamed?)")
            drifted.append(entry)
            continue

        if not chimera.is_file():
            print(f"local missing (not yet ported): {entry.chimera_rel}")
            continue

        diff = _diff(chimera, jeevy)
        if diff:
            print(f"\n=== drift: {entry.chimera_rel} vs {entry.jeevy_rel} ===")
            print(diff)
            drifted.append(entry)

    if drifted:
        print(f"\n{len(drifted)} file(s) have drifted — re-port before shipping the next phase.")
        return 1

    print("no drift detected.")
    return 0


def _diff(local: Path, upstream: Path) -> str:
    """Return a unified diff of `upstream` against `local`, or empty if identical
    after normalization.

    Normalization is intentionally minimal — just strip leading/trailing
    whitespace per line so JS-vs-TS formatting tweaks don't produce false
    positives. The diff is a hint, not a contract.
    """
    local_lines = [line.rstrip() + "\n" for line in local.read_text(encoding="utf-8").splitlines()]
    upstream_lines = [line.rstrip() + "\n" for line in upstream.read_text(encoding="utf-8").splitlines()]
    if local_lines == upstream_lines:
        return ""
    diff = difflib.unified_diff(
        local_lines,
        upstream_lines,
        fromfile=str(local),
        tofile=str(upstream),
        n=2,
    )
    return "".join(diff)


if __name__ == "__main__":
    sys.exit(main())
