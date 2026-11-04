"""The gains-at-death memo quotes the script, and the script moves no score."""

from __future__ import annotations

from pathlib import Path

from scripts.gains_at_death_level import measure

ROOT = Path(__file__).resolve().parents[1]
MEMO = ROOT / "planning" / "memos" / "GAINS_AT_DEATH_LEVEL.md"


def test_the_memo_quotes_the_measured_factor_and_does_not_rescale():
    recorded = measure()
    text = MEMO.read_text(encoding="utf-8")
    assert f"{recorded['factor']:.2f}" in text
    assert f"{recorded['flow_billions']:.1f}" in text
    assert "The level is not changed." in text
    assert abs(recorded["death_exit_rate"] / recorded["implied_exit_of_stock"] - recorded["factor"]) < 1e-9
    assert recorded["factor"] > 7
