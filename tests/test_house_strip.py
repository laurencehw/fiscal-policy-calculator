"""The proposal-page strip reports estimator_ranges, not a second copy of it."""

from __future__ import annotations

import json
from pathlib import Path

import api
from fiscal_model.preset_ids import resolve_preset
from fiscal_model.ui.estimator_ranges import corporate_estimator_range, house_strip
from fiscal_model.ui.preset_validation import TIER_FITTED, get_validation_badge

ROOT = Path(__file__).resolve().parents[1]


def _policy(preset_id: str):
    label = resolve_preset(preset_id) or preset_id
    policy, _use_real_data = api._build_preset_policy(label)
    return policy


def _headline(preset_id: str) -> float:
    path = ROOT / "site_data" / "presets" / f"{preset_id}.json"
    return float(json.loads(path.read_text(encoding="utf-8"))["conventional"]["ten_year_deficit_impact"])


def test_the_corporate_strip_equals_the_converted_range():
    policy = _policy("corporate-28pct")
    model = _headline("corporate-28pct")
    badge = get_validation_badge("corporate-28pct")
    assert badge is not None and badge["tier"] == TIER_FITTED
    strip = house_strip(
        policy_id="biden_corporate_28",
        policy=policy,
        model_billions=model,
        fitted_target_billions=float(badge["official"]),
    )
    assert strip is not None
    rate = (float(policy._get_reform_rate()) - float(policy.baseline_rate)) * 100.0
    converted = corporate_estimator_range(rate_change_pp=rate, model_billions=model)
    assert converted is not None
    assert [row["value_billions"] for row in strip["estimates"]] == [
        estimate.value_billions for estimate in converted.estimates
    ]
    assert strip["model_billions"] == model
    assert any(row["fitted"] for row in strip["estimates"])


def test_the_15pct_strip_is_the_published_range_not_a_scaled_28pct():
    """A scaled 28% yield and Tax Foundation's own 15% score must not share a strip."""
    from fiscal_model.ui.estimator_ranges import published_range_for

    policy = _policy("corporate-15pct")
    strip = house_strip(
        policy_id="trump_corporate_15",
        policy=policy,
        model_billions=_headline("corporate-15pct"),
    )
    published = published_range_for("trump_corporate_15")
    assert strip is not None and published is not None
    names = {row["estimator"] for row in strip["estimates"]}
    assert names == {"Tax Foundation", "Penn Wharton Budget Model"}
    assert "JCT" not in names and "Treasury OTA" not in names
    assert {row["value_billions"] for row in strip["estimates"]} == {
        published.low_billions,
        published.high_billions,
    }
    assert strip["range"]["label"] == "Tax Foundation–PWBM range"
    assert strip["basis"] == ""


def test_a_published_range_is_exported_for_the_three_range_rows():
    for preset_id, policy_id in (
        ("corporate-15pct", "trump_corporate_15"),
        ("pillar-two-adoption", "pillar_two_adoption"),
        ("tariff-reciprocal", "reciprocal_tariffs"),
    ):
        strip = house_strip(
            policy_id=policy_id,
            policy=_policy(preset_id),
            model_billions=_headline(preset_id),
        )
        assert strip is not None and strip["range"] is not None, preset_id
        assert strip["range"]["low_billions"] < strip["range"]["high_billions"]
