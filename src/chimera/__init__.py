"""CHIMERA — autonomous multi-model orchestration system."""

import sys


def main() -> None:
    """Top-level entry point.

    Default: launch the MCP server over stdio (chimera).
    `chimera monitor <subcommand>`:  route to the LangGraph monitor CLI
    `chimera install [target]`:      copy skill bundle into a project's .claude/
    `chimera doctor [target]`:       probe what's installed + reachable
    """
    if len(sys.argv) >= 2 and sys.argv[1] == "monitor":
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        from .monitor.cli import main as monitor_main

        monitor_main()
        return

    if len(sys.argv) >= 2 and sys.argv[1] in ("install", "doctor"):
        # Pass-through to install module's argparse (it expects the
        # subcommand name as the first positional arg)
        from .install import main as install_main

        install_main(sys.argv[1:])
        return

    from .server.mcp import main as mcp_main

    mcp_main()


__all__ = ["main"]
