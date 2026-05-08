# Contributing to chimera

Thanks for your interest. chimera is the personal project of Joseph
(`@fsocietydisobey`); pull requests and issues are welcome but the
overall direction stays with the maintainer.

## What this project is (and isn't)

chimera is two things:
1. An **MCP server** exposing autonomous orchestration patterns
   (chain pipelines, swarms, refiners, hypervisor) — one tool per
   pattern.
2. A **LangGraph observability + dev assistant**: chimera-monitor
   (web dashboard) plus a skill pack that turns Claude Code into a
   LangGraph-aware development environment.

It is not:
- A general-purpose framework — it's opinionated, scoped to LangGraph
- A replacement for Claude Code — it composes on top of it
- Stable in API — version bumps may rename tools or change schemas
  if the maintainer thinks they're better named differently

## How to file an issue

Reproducible bugs > feature requests. Include:
- What you expected to happen
- What actually happened (logs, screenshots, error text)
- What chimera version (commit SHA) you're on
- What MCP servers you have configured if it's a skill issue
- For monitor issues: `chimera doctor` output

## How to PR

Small, focused changes are easier to review and merge:
- One concern per PR (a bug fix OR a feature, not both)
- Tests for any logic change — `tests/test_implementation_loop.py` is
  a good template for behavior-locking tests
- Run `uv run pytest tests/` before sending; all green or document
  what's expected to fail

For larger changes (new graph patterns, new skill, new monitor
feature), open an issue first to align on the design.

## Skill contributions

Each skill is a markdown file in `.claude/skills/` with:
- YAML frontmatter (name, description, trigger patterns)
- Investigation procedure (numbered steps)
- Synthesis format (what the output should look like)
- Known patterns / failure modes (institutional memory)

When you diagnose a bug using a skill, consider adding the pattern
to that skill's "known shapes" section so the next person doesn't
have to re-derive it. The skills are a growing knowledge base.

## Code style

- Python: Black + ruff. Type hints on public APIs.
- TypeScript (monitor frontend): Prettier defaults.
- Don't add dependencies casually — chimera is light on deps and
  most things have an existing equivalent already pulled in.
- Comments explain WHY, not WHAT. Save WHAT for the variable name.

## Testing chimera-monitor changes

Backend changes:
```bash
uv run pytest tests/monitor/   # 48 tests for the monitor module
chimera monitor restart        # daemon reload — easy to forget
```

Frontend changes:
```bash
cd monitor_ui
npm run build                  # type-check + bundle
chimera monitor restart        # daemon serves the dist/
```

The daemon won't pick up backend changes without restart — `chimera
monitor restart` is your friend.

## License

MIT. By contributing, you agree your contributions are licensed
under the same.
