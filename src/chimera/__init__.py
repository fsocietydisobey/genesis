"""CHIMERA — autonomous multi-model orchestration system."""

import sys


def main() -> None:
    """Top-level entry point.

    Default: launch the MCP server over stdio (chimera).
    `chimera monitor <subcommand>`: route to the LangGraph monitor CLI.
    """
    if len(sys.argv) >= 2 and sys.argv[1] == "monitor":
        # Trim "monitor" from argv so the subcommand parser sees clean args.
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        from .monitor.cli import main as monitor_main

        monitor_main()
        return

    from .server.mcp import main as mcp_main

    mcp_main()


__all__ = ["main"]
