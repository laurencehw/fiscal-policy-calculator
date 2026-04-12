"""
Tests for fiscal_model.api_serialization helper functions.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from fiscal_model.api_serialization import (
    _as_float_array,
    _extract_dynamic_series,
    _sum_float,
    _value_at,
)


def test_as_float_array_handles_none_scalar_and_invalid():
    assert _as_float_array(None) is None

    scalar = _as_float_array(3)
    assert scalar is not None
    assert scalar.shape == (1,)
    assert scalar[0] == 3.0

    assert _as_float_array(object()) is None


def test_sum_float_and_value_at_handle_empty_inputs():
    assert _sum_float(None) == 0.0
    assert _value_at(np.array([]), 0) == 0.0
    assert _value_at(np.array([1.5]), 3) == 1.5


def test_extract_dynamic_series_supports_legacy_result_shape():
    legacy_result = SimpleNamespace(
        revenue_feedback=[0.5, 0.75],
        gdp_effect=[0.1, 0.2],
        employment_effect=[100.0, 120.0],
    )

    dynamic = _extract_dynamic_series(legacy_result)

    assert np.allclose(dynamic["revenue_feedback"], [0.5, 0.75])
    assert np.allclose(dynamic["gdp_percent_change"], [0.1, 0.2])
    assert np.allclose(dynamic["employment_change"], [100.0, 120.0])
