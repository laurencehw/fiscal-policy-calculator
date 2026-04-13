"""Tests for the custom exception hierarchy."""

from __future__ import annotations

import pytest

from fiscal_model import (
    BaselineStaleError,
    DataSourceError,
    FiscalModelError,
    FREDUnavailableError,
    PolicyValidationError,
    ScoringBoundsError,
)


def test_policy_validation_error_is_value_error():
    """Existing ``except ValueError`` handlers must continue to catch policy
    validation errors."""
    with pytest.raises(ValueError):
        raise PolicyValidationError("bad")


def test_scoring_bounds_is_policy_validation():
    with pytest.raises(PolicyValidationError):
        raise ScoringBoundsError("too big")


def test_fred_unavailable_is_data_source_error():
    with pytest.raises(DataSourceError):
        raise FREDUnavailableError("no api key")


def test_baseline_stale_is_data_source_error():
    with pytest.raises(DataSourceError):
        raise BaselineStaleError("too old")


def test_all_errors_inherit_fiscal_model_error():
    for exc_cls in (
        PolicyValidationError,
        ScoringBoundsError,
        FREDUnavailableError,
        BaselineStaleError,
        DataSourceError,
    ):
        assert issubclass(exc_cls, FiscalModelError)
