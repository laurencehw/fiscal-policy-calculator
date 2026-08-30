"""
TPC-style winners/losers narrative for distributional analysis results.

Pulls signal out of a ``DistributionalAnalysis`` and turns it into the
short, plain-language summary that headlines a TPC tax-policy brief:

- Top vs bottom comparison sentence
- Winners list (groups that net out a tax cut) with avg $ change and % of income
- Losers list (groups that face a tax increase)
- "What's the headline?" badge: net distributive direction

The Streamlit tab consumes these via ``render_winners_losers_callout``;
the pure-data helpers underneath are exercised by unit tests so the
message stays consistent as the engine evolves.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fiscal_model.ui.helpers import escape_markdown_dollars


@dataclass(frozen=True)
class GroupSummary:
    """One row in the winners/losers list."""

    name: str
    avg_tax_change: float          # signed dollars per filer
    pct_of_income: float           # signed % of pre-tax income
    share_of_total: float          # signed share of total $ change (-1..1)


@dataclass(frozen=True)
class WinnersLosersSummary:
    """Narrative-ready breakdown of who pays / who saves."""

    winners: list[GroupSummary]    # avg_tax_change < 0
    losers: list[GroupSummary]     # avg_tax_change > 0
    top_group: GroupSummary | None
    bottom_group: GroupSummary | None
    total_change_billions: float

    @property
    def headline_direction(self) -> str:
        """One of ``progressive``, ``regressive``, ``mixed`` or ``flat``."""
        top = self.top_group
        bot = self.bottom_group
        if top is None or bot is None:
            return "flat"
        # Progressive = top pays more (or saves less) than bottom in % terms.
        # We compare share of total burden change in pct_of_income to keep
        # the comparison scale-invariant.
        if abs(top.pct_of_income - bot.pct_of_income) < 0.01:
            return "flat"
        if top.pct_of_income > bot.pct_of_income:
            return "progressive"
        if top.pct_of_income < bot.pct_of_income:
            return "regressive"
        return "mixed"


def _result_to_group(result: Any) -> GroupSummary:
    return GroupSummary(
        name=result.income_group.name,
        avg_tax_change=float(result.tax_change_avg),
        pct_of_income=float(result.tax_change_pct_income),
        share_of_total=float(result.share_of_total_change),
    )


def _income_floor(result: Any) -> float:
    """Return the income-group floor for sorting; tolerates missing fields."""
    floor = getattr(getattr(result, "income_group", None), "floor", None)
    try:
        return float(floor) if floor is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def build_winners_losers(analysis: Any) -> WinnersLosersSummary:
    """Translate a ``DistributionalAnalysis`` into a narrative summary.

    Winners and losers are sorted by magnitude of average tax change so
    the most impacted groups appear first — matching how TPC tables are
    typically read. Top/bottom groups are picked after explicitly
    sorting by income-group floor so the headline doesn't flip if the
    engine returns groups in a different order (e.g., JCT dollar
    brackets vs. quintiles vs. deciles).
    """
    raw_results = list(getattr(analysis, "results", []))
    by_income = sorted(raw_results, key=_income_floor)
    groups = [_result_to_group(r) for r in by_income]

    winners = [g for g in groups if g.avg_tax_change < 0]
    losers = [g for g in groups if g.avg_tax_change > 0]
    winners.sort(key=lambda g: g.avg_tax_change)            # most-negative first
    losers.sort(key=lambda g: -g.avg_tax_change)             # most-positive first

    top_group = groups[-1] if groups else None
    bottom_group = groups[0] if groups else None

    return WinnersLosersSummary(
        winners=winners,
        losers=losers,
        top_group=top_group,
        bottom_group=bottom_group,
        total_change_billions=float(getattr(analysis, "total_tax_change", 0.0)),
    )


def _format_signed_dollars(value: float) -> str:
    sign = "+" if value > 0 else ("−" if value < 0 else "")
    return f"{sign}${abs(value):,.0f}"


def _format_signed_pct(value: float) -> str:
    sign = "+" if value > 0 else ("−" if value < 0 else "")
    return f"{sign}{abs(value):.2f}%"


def headline_sentence(summary: WinnersLosersSummary) -> str:
    """Generate a one-line top-vs-bottom comparison.

    Example: "The top quintile sees an average tax cut of $4,250
    (-1.2% of income); the bottom quintile sees +$30 (+0.1%)."
    """
    top = summary.top_group
    bot = summary.bottom_group
    if top is None or bot is None:
        return "No distributional impact computed."

    def _phrase(group: GroupSummary) -> str:
        verb = "tax cut of" if group.avg_tax_change < 0 else "tax increase of"
        return (
            f"the {group.name.lower()} sees an average {verb} "
            f"{_format_signed_dollars(group.avg_tax_change)} "
            f"({_format_signed_pct(group.pct_of_income)} of income)"
        )

    return f"{_phrase(top).capitalize()}; {_phrase(bot)}."


def direction_caption(summary: WinnersLosersSummary) -> str:
    """One-line verdict whose explanation matches the sign of the change.

    "Regressive" covers both a tax increase that hits the bottom relatively
    harder and a tax cut that benefits the top relatively more; the old
    burden-only wording claimed lower-income groups "bear a larger share of
    the burden" even for top-heavy tax cuts, contradicting the table above it.
    """
    direction = summary.headline_direction
    top = summary.top_group

    if direction == "progressive":
        if top is not None and top.pct_of_income > 0:
            detail = "higher-income groups bear a larger share of the tax increase"
        else:
            detail = "lower-income groups receive the larger benefit"
        return f"📈 **Net effect: progressive** — {detail} (in % of income terms)."
    if direction == "regressive":
        if top is not None and top.pct_of_income < 0:
            detail = "higher-income groups receive the larger benefit"
        else:
            detail = "lower-income groups bear a larger share of the tax increase"
        return f"📉 **Net effect: regressive** — {detail} (in % of income terms)."
    return (
        "➡️ **Net effect: roughly flat** — burden change is similar "
        "across income groups (in % of income terms)."
    )


def render_winners_losers_callout(st_module: Any, analysis: Any) -> None:
    """Render a TPC-style winners/losers narrative panel.

    Sits at the top of the Distribution tab so the most important
    take-away — *who actually wins and loses* — leads, with the detail
    tables and charts following below.
    """
    summary = build_winners_losers(analysis)

    st_module.markdown(escape_markdown_dollars(f"> {headline_sentence(summary)}"))

    st_module.caption(direction_caption(summary))

    win_col, lose_col = st_module.columns(2)

    with win_col, st_module.container(border=True):
        if summary.winners:
            st_module.markdown("### 🟢 Winners")
            n_winners = len(summary.winners)
            st_module.caption(
                f"{n_winners} group{'s' if n_winners != 1 else ''} "
                f"receive{'' if n_winners != 1 else 's'} a net tax cut"
            )
            for group in summary.winners[:5]:
                st_module.markdown(
                    escape_markdown_dollars(
                        f"**{group.name}** — avg "
                        f"{_format_signed_dollars(group.avg_tax_change)} "
                        f"({_format_signed_pct(group.pct_of_income)})"
                    )
                )
        else:
            st_module.markdown("### 🟢 Winners")
            st_module.caption("No income group nets out a tax cut.")

    with lose_col, st_module.container(border=True):
        if summary.losers:
            st_module.markdown("### 🔴 Losers")
            n_losers = len(summary.losers)
            st_module.caption(
                f"{n_losers} group{'s' if n_losers != 1 else ''} "
                f"face{'' if n_losers != 1 else 's'} a net tax increase"
            )
            for group in summary.losers[:5]:
                st_module.markdown(
                    escape_markdown_dollars(
                        f"**{group.name}** — avg "
                        f"{_format_signed_dollars(group.avg_tax_change)} "
                        f"({_format_signed_pct(group.pct_of_income)})"
                    )
                )
        else:
            st_module.markdown("### 🔴 Losers")
            st_module.caption("No income group faces a net tax increase.")


__all__ = [
    "GroupSummary",
    "WinnersLosersSummary",
    "build_winners_losers",
    "direction_caption",
    "headline_sentence",
    "render_winners_losers_callout",
]
