"""
Tests for the bill-tracker calibration band integration.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from fiscal_model.ui.confidence_band import reset_confidence_cache
from fiscal_model.ui.tabs.bill_tracker import (
    _dominant_provision_policy_type,
    _render_bill_calibration_band,
)


def test_dominant_picks_highest_confidence_provision():
    auto_score = {
        "policies_json": json.dumps([
            {"policy_type": "income_tax", "confidence": "low"},
            {"policy_type": "corporate_tax", "confidence": "high"},
            {"policy_type": "estate_tax", "confidence": "medium"},
        ]),
    }
    assert _dominant_provision_policy_type(auto_score) == "corporate_tax"


def test_dominant_returns_none_for_empty_or_malformed():
    assert _dominant_provision_policy_type({}) is None
    assert _dominant_provision_policy_type({"policies_json": ""}) is None
    assert _dominant_provision_policy_type({"policies_json": "{not valid"}) is None
    assert _dominant_provision_policy_type({"policies_json": "[]"}) is None


def test_dominant_handles_unranked_confidence():
    """Provisions without a confidence label still resolve to *some* type."""
    auto_score = {
        "policies_json": json.dumps([
            {"policy_type": "estate_tax"},
            {"policy_type": "income_tax"},
        ]),
    }
    # `max` with all-equal keys returns the first element.
    assert _dominant_provision_policy_type(auto_score) == "estate_tax"


def test_render_bill_calibration_band_emits_caption_for_known_type():
    reset_confidence_cache()
    st = MagicMock()
    auto_score = {
        "policies_json": json.dumps([
            {"policy_type": "corporate_tax", "confidence": "high"},
        ]),
    }
    _render_bill_calibration_band(st, auto_score, total_billions=-1347.0)

    assert st.caption.called
    caption_text = st.caption.call_args[0][0]
    assert "Corporate" in caption_text
    assert "calibrated run" in caption_text


def test_render_bill_calibration_band_silent_when_no_provisions():
    """Bills without parsed provisions should not crash or emit a band."""
    reset_confidence_cache()
    st = MagicMock()
    _render_bill_calibration_band(st, {}, total_billions=100.0)
    assert not st.caption.called


def test_render_bill_calibration_band_silent_on_compute_failure(monkeypatch):
    """A scorecard failure must produce no band rather than a 500."""
    from fiscal_model.ui import confidence_band as cb_module

    def _boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(cb_module, "_category_index", _boom)
    reset_confidence_cache()

    st = MagicMock()
    auto_score = {"policies_json": json.dumps([{"policy_type": "corporate_tax"}])}
    _render_bill_calibration_band(st, auto_score, total_billions=-1347.0)
    assert not st.caption.called
