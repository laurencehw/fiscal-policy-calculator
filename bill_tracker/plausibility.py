"""
Plausibility checks for the bill tracker's language-model readings.

The tracker's automated path asks a language model to turn a CRS summary into
calculator parameters, then scores them. On 23 Nov 2026 the live list showed
H.R. 227 (the Clergy Act, a two-year opt-in window for clergy who left Social
Security) at -$14,184.8B, because the model read the opt-in as a 15.3-point
payroll tax increase on every worker in the country. The same night showed a
$70B border appropriation spread over four years scored as $70B a year for ten,
and a repeal of two clean-vehicle credits scored by treating the $4,000 and
$7,500 per-vehicle amounts as $4B and $7.5B a year.

None of those are bugs in the engine. They are readings the engine cannot tell
are wrong. This module looks for the specific ways the extraction goes wrong,
from the extracted parameters, the provision text the model quoted, and the
scored total, and returns plain-language reasons. Any reason withholds the
figure from the public list and forces the reading's confidence to "low".

Manual mappings (``manual_mappings.json``) are checked by a person and are not
run through these rules.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

#: A language-model reading above this many billions over ten years is withheld.
#: Few bills outside a reconciliation package move the deficit by half a
#: trillion, and a reconciliation package is an omnibus the extraction maps
#: only in part (``covers_part_of_bill``). A large figure from this path is
#: much more likely to be a misreading than a finding.
MAX_LLM_TEN_YEAR_BILLIONS = 500.0

#: Largest rate change, as a decimal, a reading may carry for each type before
#: it is treated as a misreading. Set above every rate change in the
#: repository's preset catalogue and CBO's Options volumes for that type.
MAX_RATE_CHANGE: dict[str, float] = {
    "income_tax": 0.10,
    "capital_gains": 0.20,
    "corporate": 0.10,
    "payroll": 0.05,
    "estate": 0.25,
}

#: Largest yearly dollar amount, in billions, for a spending, transfer or credit
#: provision read from one bill. All federal nondefense discretionary spending
#: is about $750B a year.
MAX_ANNUAL_BILLIONS = 300.0

_RATE_WORD = re.compile(r"\brates?\b|\bpercent(?:age)?\b|%", re.IGNORECASE)
_LOWERS = re.compile(r"\b(reduc\w*|lower\w*|cut\w*|decreas\w*)\b", re.IGNORECASE)
_RAISES = re.compile(r"\b(increas\w*|rais\w*|higher)\b", re.IGNORECASE)
_EVERY_YEAR = re.compile(
    r"\b(annually|each\s+(?:fiscal\s+)?year|per\s+year|a\s+year|every\s+year|for\s+each\s+of\s+fiscal\s+years)\b",
    re.IGNORECASE,
)
#: Dollar figures written in units (not billions): "$4,000", "$7,500", "$2,000 per child".
_UNIT_DOLLARS = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+|\d+)(?!\s*(?:million|billion|trillion))", re.IGNORECASE)
#: Dollar figures written in billions or millions: "$70 billion", "$26.367 billion".
_BIG_DOLLARS = re.compile(r"\$\s?(\d+(?:\.\d+)?)\s*(billion|million|trillion)", re.IGNORECASE)


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out else None  # NaN is not a number here


def _unit_amounts(text: str) -> set[float]:
    """Dollar amounts in the text written in plain dollars, in thousands: "$7,500" -> 7.5."""
    found = set()
    for match in _UNIT_DOLLARS.finditer(text):
        dollars = float(match.group(1).replace(",", ""))
        if dollars >= 100:
            found.add(round(dollars / 1000, 3))
    return found


def _billion_amounts(text: str) -> set[float]:
    scale = {"million": 0.001, "billion": 1.0, "trillion": 1000.0}
    return {round(float(m.group(1)) * scale[m.group(2).lower()], 3) for m in _BIG_DOLLARS.finditer(text)}


def provision_problems(policy: dict[str, Any]) -> list[str]:
    """Reasons one extracted provision looks misread. Empty when none apply."""
    kind = str(policy.get("policy_type") or "")
    params = policy.get("parameters") or {}
    if not isinstance(params, dict):
        return [f"{kind}: parameters are not a mapping"]
    text = str(policy.get("provision_text") or "")
    problems: list[str] = []

    rate = _number(params.get("rate_change"))
    if kind in MAX_RATE_CHANGE and "rate_change" in params and rate is None:
        problems.append(f"{kind}: no rate change was read, so the provision was not scored as written")
    if rate is not None and rate != 0 and kind in MAX_RATE_CHANGE:
        cap = MAX_RATE_CHANGE[kind]
        if abs(rate) > cap:
            problems.append(
                f"{kind}: a rate change of {rate * 100:+.1f} points is larger than any {kind.replace('_', ' ')} "
                f"change the calculator has been checked on ({cap * 100:.0f} points)"
            )
        if text and not _RATE_WORD.search(text):
            problems.append(
                f"{kind}: scored as a change in a tax rate, but the provision text does not mention a rate"
            )
        lowers, raises = bool(_LOWERS.search(text)), bool(_RAISES.search(text))
        if rate > 0 and lowers and not raises:
            problems.append(f"{kind}: the text lowers a tax but the reading raises the rate")
        if rate < 0 and raises and not lowers:
            problems.append(f"{kind}: the text raises a tax but the reading lowers the rate")

    for key in ("spending_change_billions", "transfer_change_billions", "credit_amount_billions"):
        amount = _number(params.get(key))
        if amount is None or amount == 0:
            continue
        if abs(amount) > MAX_ANNUAL_BILLIONS:
            problems.append(f"{kind}: ${abs(amount):,.0f}B a year is larger than one bill plausibly moves")
        if text and round(abs(amount), 3) in _unit_amounts(text) and round(abs(amount), 3) not in _billion_amounts(text):
            problems.append(
                f"{kind}: ${abs(amount):g}B a year matches a per-person or per-item dollar amount in the text, "
                "not a budget total"
            )
        if (
            key != "credit_amount_billions"
            and text
            and round(abs(amount), 3) in _billion_amounts(text)
            and not _EVERY_YEAR.search(text)
        ):
            problems.append(
                f"{kind}: the text states ${abs(amount):g}B as a total, and the reading spends it every year for ten years"
            )

    if kind in ("income_tax", "capital_gains") and rate and "affected_income_threshold" not in params:
        problems.append(f"{kind}: no income threshold was read, so the calculator assumed $400,000")
    if kind == "trade":
        problems.append("trade: the tracker cannot score tariff provisions, so this one was dropped")
    return problems


def reading_problems(
    policies: Iterable[dict[str, Any]],
    ten_year_billions: float | None,
    *,
    manual: bool = False,
) -> list[str]:
    """Reasons a whole bill reading should be withheld. Empty means it may be shown.

    ``manual`` readings were mapped by a person and are not second-guessed here.
    """
    if manual:
        return []
    problems: list[str] = []
    for policy in policies:
        if isinstance(policy, dict):
            problems.extend(provision_problems(policy))
    total = _number(ten_year_billions)
    if total is not None and abs(total) > MAX_LLM_TEN_YEAR_BILLIONS:
        problems.append(
            f"the reading totals ${abs(total):,.0f}B over ten years, above the "
            f"${MAX_LLM_TEN_YEAR_BILLIONS:,.0f}B this automated path is trusted to report"
        )
    # One reason per distinct sentence, in order.
    return list(dict.fromkeys(problems))
