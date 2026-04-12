"""
Runtime logging helpers for Streamlit entrypoints.
"""

from __future__ import annotations

import json
import logging
import platform
from typing import Any


def configure_runtime_logger(name: str) -> logging.Logger:
    """Return a logger with a basic process-wide configuration when needed."""
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )

    return logging.getLogger(name)


def log_runtime_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Emit a structured runtime log line with stable key ordering."""
    payload = " ".join(
        f"{key}={json.dumps(value, default=str, sort_keys=True)}"
        for key, value in sorted(fields.items())
    )
    logger.info("%s %s", event, payload)


def build_runtime_metadata(*, entrypoint: str, mode: str | None = None) -> dict[str, Any]:
    """Build common boot metadata for app entrypoints."""
    return {
        "entrypoint": entrypoint,
        "mode": mode or "default",
        "python_version": platform.python_version(),
    }
