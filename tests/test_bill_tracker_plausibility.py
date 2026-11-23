"""The bill tracker's plausibility checks, on the readings the live site showed on 23 Nov 2026."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from bill_tracker.ingestor import looks_fiscal
from bill_tracker.plausibility import (
    MAX_LLM_TEN_YEAR_BILLIONS,
    provision_problems,
    reading_problems,
)

CLERGY_ACT = {
    "policy_type": "payroll",
    "parameters": {"rate_change": 0.153, "cap_change": 0},
    "confidence": "medium",
    "provision_text": (
        "This act establishes a two-year window for members of the clergy who have opted out of Social "
        "Security and Medicare taxes to opt back in."
    ),
}
BORDER_FUNDING = {
    "policy_type": "spending",
    "parameters": {"spending_change_billions": 70, "multiplier": None},
    "confidence": "high",
    "provision_text": (
        "This act provides $70 billion in funding to the Department of Homeland Security through FY2029 "
        "for immigration enforcement."
    ),
}
EV_CREDIT_REPEAL = {
    "policy_type": "credits",
    "parameters": {"credit_type": "new_clean_vehicle", "credit_amount_billions": -7.5},
    "confidence": "high",
    "provision_text": "repeals the federal tax credits for the purchase of a qualified new clean vehicle (tax credit of up to $7,500)",
}
SE_DEDUCTION_AS_RATE = {
    "policy_type": "income_tax",
    "parameters": {"rate_change": 0.25, "affected_income_threshold": 400000},
    "confidence": "high",
    "provision_text": (
        "The bill increases the tax deduction for self-employment taxes for individuals with an adjusted "
        "gross income of less than $400,000."
    ),
}
CAMT_REPEAL = {
    "policy_type": "corporate",
    "parameters": {"rate_change": -0.15},
    "confidence": "high",
    "provision_text": "This bill repeals the corporate alternative minimum tax (CAMT).",
}
CLEAN_RATE_RISE = {
    "policy_type": "corporate",
    "parameters": {"rate_change": 0.07},
    "confidence": "high",
    "provision_text": "increases the corporate income tax rate to 28% (from 21%)",
}


@pytest.mark.parametrize(
    "policy, phrase",
    [
        (CLERGY_ACT, "larger than any payroll"),
        (CLERGY_ACT, "does not mention a rate"),
        (BORDER_FUNDING, "as a total"),
        (EV_CREDIT_REPEAL, "per-person or per-item"),
        (SE_DEDUCTION_AS_RATE, "larger than any income tax"),
        (CAMT_REPEAL, "larger than any corporate"),
    ],
)
def test_each_live_misreading_is_caught(policy, phrase):
    assert any(phrase in p for p in provision_problems(policy)), provision_problems(policy)


def test_a_clean_rate_change_passes():
    assert provision_problems(CLEAN_RATE_RISE) == []
    assert reading_problems([CLEAN_RATE_RISE], -1_000.0 + 1) == ["the reading totals $999B over ten years, above the $500B this automated path is trusted to report"]
    assert reading_problems([CLEAN_RATE_RISE], -400.0) == []


def test_sign_contradicting_the_text_is_caught():
    cut_read_as_rise = {**CLEAN_RATE_RISE, "provision_text": "reduces the corporate income tax rate to 18%"}
    assert any("lowers a tax but the reading raises" in p for p in provision_problems(cut_read_as_rise))


def test_yearly_amounts_stated_as_yearly_pass():
    yearly = {
        "policy_type": "spending",
        "parameters": {"spending_change_billions": 5},
        "provision_text": "authorizes $5 billion for each fiscal year 2026 through 2035",
    }
    assert provision_problems(yearly) == []


def test_large_totals_are_withheld_but_manual_mappings_are_not():
    assert reading_problems([], MAX_LLM_TEN_YEAR_BILLIONS + 1)
    assert reading_problems([CLERGY_ACT], -14_184.8, manual=True) == []


def test_mapper_downgrades_any_warning_to_low():
    from bill_tracker.provision_mapper import ProvisionMapper

    client = MagicMock()
    message = MagicMock()
    message.content = [MagicMock(text=json.dumps([CLERGY_ACT]))]
    client.messages.create.return_value = message
    result = ProvisionMapper(anthropic_client=client).map_bill("hr-99999-119", CLERGY_ACT["provision_text"])
    assert result.confidence == "low"
    assert result.validation_warnings


def test_prompt_states_signs_and_yearly_units():
    from bill_tracker.provision_mapper import LLM_EXTRACTION_PROMPT

    assert "POSITIVE when the bill raises a tax rate" in LLM_EXTRACTION_PROMPT
    assert "per-vehicle" in LLM_EXTRACTION_PROMPT
    assert "trade, tcja_extension" not in LLM_EXTRACTION_PROMPT  # the scorer has no trade path


def test_auto_scorer_downgrades_an_implausible_total():
    from bill_tracker.auto_scorer import AutoScorer
    from bill_tracker.provision_mapper import MappingResult

    scorer = MagicMock()
    result = MagicMock(static_revenue_effect=0.0, behavioral_offset=0.0, final_deficit_effect=[-100.0] * 10)
    scorer.score_policy.return_value = result
    mapping = MappingResult(
        bill_id="s-1-119", policies=[CLEAN_RATE_RISE], confidence="high", confidence_reason="", extraction_method="llm"
    )
    score = AutoScorer(scorer=scorer).score(mapping)
    assert score is not None and score.confidence == "low"
    assert "above the $500B" in score.notes


def test_looks_fiscal_gates_the_extractor():
    assert looks_fiscal("Increases the income tax rate on wages above $400,000.")
    assert not looks_fiscal("Designates the facility of the Postal Service at 12 Main Street as the Jane Doe Post Office.")
    assert not looks_fiscal(None)
    assert not looks_fiscal("Imposes a tax on widgets.", ["Commemorations"])


def test_export_withholds_the_clergy_act_tonight():
    """The live index carries the withholding, so the site no longer prints -$14,184.8B."""
    from pathlib import Path

    index = json.loads((Path(__file__).resolve().parents[1] / "site_data" / "tracker" / "index.json").read_text())
    row = next((r for r in index["rows"] if r["id"] == "hr-227-119"), None)
    if row is None or row["auto_ten_year_billions"] is None:
        pytest.skip("H.R. 227 has no automated reading in this export")
    assert row["auto_confidence"] == "low"
    assert row["auto_withheld"]
