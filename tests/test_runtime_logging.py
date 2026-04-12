"""
Tests for Streamlit runtime logging helpers.
"""

from __future__ import annotations

import logging

from fiscal_model.ui.runtime_logging import (
    build_runtime_metadata,
    configure_runtime_logger,
    log_runtime_event,
)


def test_configure_runtime_logger_returns_named_logger():
    logger = configure_runtime_logger("fiscal_model.test.runtime")

    assert isinstance(logger, logging.Logger)
    assert logger.name == "fiscal_model.test.runtime"


def test_build_runtime_metadata_defaults_mode():
    metadata = build_runtime_metadata(entrypoint="app.py")

    assert metadata["entrypoint"] == "app.py"
    assert metadata["mode"] == "default"
    assert isinstance(metadata["python_version"], str)
    assert metadata["python_version"]


def test_log_runtime_event_sorts_fields_stably(caplog):
    logger = logging.getLogger("fiscal_model.test.runtime_event")

    with caplog.at_level(logging.INFO, logger=logger.name):
        log_runtime_event(logger, "app_boot", zeta=2, alpha="calculator")

    assert caplog.records[0].getMessage() == 'app_boot alpha="calculator" zeta=2'
