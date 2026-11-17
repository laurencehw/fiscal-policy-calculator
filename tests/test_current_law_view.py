"""The current-law answers for the pre-2025-law presets (lane BET1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fiscal_model.current_law_view import CURRENT_LAW_VIEW, current_law_answer, pre_2025_labels
from fiscal_model.preset_ids import PRESET_ID_BY_LABEL

ROOT = Path(__file__).resolve().parents[1]
LINE_ITEMS = ROOT / "fiscal_model" / "data_files" / "validation" / "pl119_21_jct_line_items.csv"


def test_every_pre_2025_law_preset_has_a_current_law_answer_and_nothing_else_does():
    assert set(CURRENT_LAW_VIEW) == pre_2025_labels()


@pytest.mark.parametrize("label", sorted(CURRENT_LAW_VIEW))
def test_each_answer_is_internally_consistent(label):
    answer = CURRENT_LAW_VIEW[label]
    assert answer.reason and answer.source and answer.url
    if answer.kind == "already_law":
        assert answer.billions == 0.0
        assert answer.same_as is None and answer.already_ended_billions is None
    elif answer.kind == "same_as":
        assert answer.billions is None
        assert answer.same_as in set(PRESET_ID_BY_LABEL.values())
        assert answer.url == f"/explore/{answer.same_as}"
    else:
        assert answer.kind == "not_computed"
        assert answer.billions is None and answer.same_as is None


def test_the_no_salt_cap_answer_is_the_salt_cap_repeal_preset_on_current_law():
    from fiscal_model.policy_status import get_policy_status

    answer = current_law_answer("🏛️ TCJA Extension (No SALT Cap)")
    assert answer is not None and answer.same_as == "salt-cap-repeal"
    label = next(lbl for lbl, pid in PRESET_ID_BY_LABEL.items() if pid == "salt-cap-repeal")
    status = get_policy_status(label)
    # The preset it points at must itself be scored on current law.
    assert status is not None and status.pre_2025_law is False


def test_the_ira_already_ended_figure_is_jcts_subchapter_a_row():
    for line in LINE_ITEMS.read_text(encoding="utf-8").splitlines():
        if line.startswith("pl119_21_energy_credit_terminations,"):
            break
    else:  # pragma: no cover
        raise AssertionError("subchapter A row missing")
    answer = current_law_answer("🌱 Repeal IRA Clean Energy Credits (-$851B)")
    assert answer is not None and answer.kind == "not_computed"
    assert ",542653," in line
    assert answer.already_ended_billions == pytest.approx(-542.653)


def test_the_export_carries_the_answer_only_for_pre_2025_law_presets():
    index = json.loads((ROOT / "site_data" / "presets" / "index.json").read_text(encoding="utf-8"))
    for info in index["presets"]:
        status = info.get("status")
        if not status:
            continue
        if status["pre_2025_law"]:
            assert status["current_law"]["kind"] in {"already_law", "same_as", "not_computed"}
        else:
            assert status["current_law"] is None
