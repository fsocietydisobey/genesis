"""Structured logging for the orchestrator.

Logs to stderr (MCP uses stdout for protocol messages).
Configure level via LOG_LEVEL env var (default: INFO).
"""

import logging
import os
import sys


def setup_logging() -> None:
    """Configure the root orchestrator logger. Call once at startup."""
    level = os.environ.get("LOG_LEVEL", "INFO").upper()

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
    )

    root = logging.getLogger("orchestrator")
    root.setLevel(getattr(logging, level, logging.INFO))
    root.addHandler(handler)
    root.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the orchestrator namespace."""
    return logging.getLogger(f"orchestrator.{name}")
