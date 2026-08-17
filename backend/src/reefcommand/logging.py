"""Structured logging setup.

Every external fetch logs whether the value came from a live call or from cache,
so the team can honestly answer "is this live right now" during a demo.
"""

from __future__ import annotations

from typing import Any


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog processors and stdlib bridging."""
    raise NotImplementedError


def get_logger(name: str) -> Any:
    """Return a bound structured logger."""
    raise NotImplementedError
