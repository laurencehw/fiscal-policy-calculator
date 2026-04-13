"""
Custom exception hierarchy for the fiscal model.

Provides specific exception types so callers can distinguish transient
problems (e.g. FRED unavailable) from fatal ones (e.g. invalid policy
inputs) and respond appropriately.
"""

from __future__ import annotations


class FiscalModelError(Exception):
    """Base class for all fiscal_model errors."""


# ---------------------------------------------------------------------------
# Validation errors — fatal, caller-induced
# ---------------------------------------------------------------------------


class PolicyValidationError(FiscalModelError, ValueError):
    """Raised when a policy is constructed or scored with invalid parameters.

    Subclasses ``ValueError`` so existing ``except ValueError`` handlers still
    catch it, but callers that want finer control can target this type.
    """


class ScoringBoundsError(PolicyValidationError):
    """Raised when a scoring result falls outside plausible numeric bounds."""


# ---------------------------------------------------------------------------
# Data access errors — often transient
# ---------------------------------------------------------------------------


class DataSourceError(FiscalModelError):
    """Base class for problems reaching an external data source."""


class FREDUnavailableError(DataSourceError):
    """Raised when the FRED API is unreachable or returns no usable data.

    This is typically transient — callers may retry with backoff or fall back
    to cached values.
    """


class BaselineStaleError(DataSourceError):
    """Raised when the CBO baseline is older than the configured freshness
    threshold.

    Not fatal by default — the app surfaces this as a warning rather than
    blocking scoring — but tests and CI can elevate it to a hard error.
    """


__all__ = [
    "BaselineStaleError",
    "DataSourceError",
    "FREDUnavailableError",
    "FiscalModelError",
    "PolicyValidationError",
    "ScoringBoundsError",
]
