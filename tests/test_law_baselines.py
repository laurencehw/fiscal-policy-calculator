"""Three current-law yardsticks, and how Explore presents a preset on each."""

from __future__ import annotations

import json
from pathlib import Path

from fiscal_model.law_baselines import (
    ALREADY_LAW_PRESETS,
    DEFAULT_LAW,
    HOUSE_PASSED_TEMPS,
    LAW_BASELINES,
    LAW_IDS,
    PL119_21_CONVENTIONAL,
    PL119_21_OUTLOOK,
    REMAINDER_UNSCORED_PRESETS,
    TEMPS_EXTENDED_PRIMARY,
    WORKED_EXAMPLE,
    parse_law,
    present_preset,
    role_of,
    to_export,
)
from fiscal_model.policy_status import POLICY_STATUS_MAP
from fiscal_model.preset_ids import CATALOG_PRESET_IDS


def test_the_three_laws_and_the_default():
    assert LAW_IDS == ("current", "pre2025", "extended")
    assert DEFAULT_LAW == "current"
    assert parse_law(None) == "current"
    assert parse_law("") == "current"
    assert parse_law("PRE2025") == "pre2025"
    assert parse_law("nope") == "current"
    assert set(LAW_BASELINES) == set(LAW_IDS)


def test_every_classified_preset_is_a_real_catalog_id():
    classified = ALREADY_LAW_PRESETS | REMAINDER_UNSCORED_PRESETS
    unknown = classified - set(CATALOG_PRESET_IDS)
    assert unknown == set()
    overlap = ALREADY_LAW_PRESETS & REMAINDER_UNSCORED_PRESETS
    assert overlap == set()


def test_classified_presets_are_exactly_the_off_current_baseline_ones():
    off = {
        preset_id
        for preset_id, status in POLICY_STATUS_MAP.items()
        if not status.on_current_baseline
    }
    assert ALREADY_LAW_PRESETS | REMAINDER_UNSCORED_PRESETS == off
    assert role_of("tcja-full-extension") == "already_law"
    assert role_of("ev-credit-repeal") == "already_law"
    assert role_of("ira-clean-energy-repeal") == "remainder_unscored"
    assert role_of("tcja-extension-no-salt-cap") == "remainder_unscored"
    assert role_of("corporate-28pct") == "live"
    assert role_of("salt-cap-repeal") == "live"


def test_already_law_is_zero_on_current_and_stored_on_pre2025():
    shown = present_preset("tcja-full-extension", "current")
    assert shown["kind"] == "already_law"
    assert shown["display_score"] == 0
    assert shown["show_published"] is False
    assert shown["score_is_on_this_law"] is True
    assert "double-count" in shown["explanation"]
    assert "CBO Feb 2026" in shown["identity_baseline"]

    reconstruction = present_preset("tcja-full-extension", "pre2025")
    assert reconstruction["kind"] == "reconstruction"
    assert reconstruction["display_score"] == "stored"
    assert reconstruction["score_is_on_this_law"] is True
    assert reconstruction["identity_baseline"] == "pre-2025 law"

    extended = present_preset("tcja-full-extension", "extended")
    assert extended["kind"] == "already_law"
    assert extended["display_score"] == 0


def test_a_live_proposal_keeps_its_stored_score_and_says_when_it_is_not_on_the_yardstick():
    current = present_preset("corporate-28pct", "current")
    assert current["kind"] == "live"
    assert current["display_score"] == "stored"
    assert current["score_is_on_this_law"] is True
    assert current["explanation"] is None

    pre = present_preset("corporate-28pct", "pre2025")
    assert pre["kind"] == "current_law_score_on_other_yardstick"
    assert pre["display_score"] == "stored"
    assert pre["score_is_on_this_law"] is False
    assert "not yet computed" in pre["explanation"]
    assert "CBO Feb 2026" in pre["identity_baseline"]

    extended = present_preset("corporate-28pct", "extended")
    assert extended["score_is_on_this_law"] is False
    assert extended["display_score"] == "stored"


def test_a_partial_repeal_is_not_printed_as_current_law():
    shown = present_preset("ira-clean-energy-repeal", "current")
    assert shown["kind"] == "remainder_unscored"
    assert shown["display_score"] is None
    assert shown["show_published"] is False
    pre = present_preset("ira-clean-energy-repeal", "pre2025")
    assert pre["display_score"] == "stored"
    assert pre["kind"] == "reconstruction"


def test_sourced_figures_are_published_and_the_extension_figure_is_marked_approximated():
    assert PL119_21_CONVENTIONAL.billions == 3400.0
    assert PL119_21_CONVENTIONAL.window == "FY2025-2034"
    assert PL119_21_CONVENTIONAL.approximated is False
    assert "61570" in PL119_21_CONVENTIONAL.url
    assert PL119_21_OUTLOOK.billions == 4700.0
    assert PL119_21_OUTLOOK.window == "FY2026-2035"
    assert "62105" in PL119_21_OUTLOOK.url
    assert TEMPS_EXTENDED_PRIMARY.billions == 1900.0
    assert TEMPS_EXTENDED_PRIMARY.approximated is True
    assert TEMPS_EXTENDED_PRIMARY.window == "FY2026-2036"
    assert "crfb.org" in TEMPS_EXTENDED_PRIMARY.url
    assert HOUSE_PASSED_TEMPS.approximated is True
    assert "61471" in HOUSE_PASSED_TEMPS.url
    assert "House-passed" in HOUSE_PASSED_TEMPS.note


def test_the_lesson_states_why_the_same_policy_scores_differently():
    assert "$0" in WORKED_EXAMPLE
    assert "pre-2025" in WORKED_EXAMPLE
    assert "temporary" in WORKED_EXAMPLE.lower()
    current = LAW_BASELINES["current"]
    assert "P.L. 119-21" in current.lesson
    assert current.versus_current is None
    assert LAW_BASELINES["pre2025"].versus_current is PL119_21_OUTLOOK
    assert LAW_BASELINES["extended"].versus_current is TEMPS_EXTENDED_PRIMARY
    assert LAW_BASELINES["extended"].versus_current.approximated is True


def test_the_export_is_the_catalog_the_site_reads():
    payload = to_export()
    assert payload["default"] == "current"
    assert payload["param"] == "law"
    assert [row["id"] for row in payload["laws"]] == list(LAW_IDS)
    assert payload["preset_roles"]["tcja-full-extension"] == "already_law"
    assert payload["preset_roles"]["ira-clean-energy-repeal"] == "remainder_unscored"
    assert "tcja-full-extension" in payload["worked_example"].lower() or "TCJA" in payload["worked_example"]
    assert payload["figures"]["pl119_21_outlook"]["billions"] == 4700.0
    assert payload["figures"]["temps_extended_primary"]["approximated"] is True
    assert payload["classified"]["tcja-full-extension"]["current"]["display_score"] == 0
    assert payload["classified"]["tcja-full-extension"]["pre2025"]["display_score"] == "stored"
    assert payload["live"]["current"]["kind"] == "live"
    assert payload["live"]["pre2025"]["score_is_on_this_law"] is False
    committed = json.loads(
        (Path(__file__).resolve().parents[1] / "site_data" / "law-baselines.json").read_text(
            encoding="utf-8"
        )
    )
    assert committed == payload
