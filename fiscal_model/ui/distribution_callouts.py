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


def build_winners_losers(analysis: Any) -> WinnersLosersSummary:
    """Translate a ``DistributionalAnalysis`` into a narrative summary.

    Winners and losers are sorted by magnitude of average tax change so
    the most impacted groups appear first — matching how TPC tables are
    typically read.
    """
    groups = [_result_to_group(r) for r in getattr(analysis, "results", [])]

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


def render_winners_losers_callout(st_module: Any, analysis: Any) -> None:
    """Render a TPC-style winners/losers narrative panel.

    Sits at the top of the Distribution tab so the most important
    take-away — *who actually wins and loses* — leads, with the detail
    tables and charts following below.
    """
    summary = build_winners_losers(analysis)

    st_module.markdown(f"> {headline_sentence(summary)}")

    direction = summary.headline_direction
    if direction == "progressive":
        st_module.caption(
            "📈 **Net effect: progressive** — higher-income groups bear a "
            "larger share of the burden change (in % of income terms)."
        )
    elif direction == "regressive":
        st_module.caption(
            "📉 **Net effect: regressive** — lower-income groups bear a "
            "larger share of the burden change (in % of income terms)."
        )
    elif direction == "flat":
        st_module.caption(
            "➡️ **Net effect: roughly flat** — burden change is similar "
            "across income groups (in % of income terms)."
        )

    win_col, lose_col = st_module.columns(2)

    with win_col, st_module.container(border=True):
        if summary.winners:
            st_module.markdown("### 🟢 Winners")
            st_module.caption(
                f"{len(summary.winners)} groups receive a net tax cut"
            )
            for group in summary.winners[:5]:
                st_module.markdown(
                    f"**{group.name}** — avg "
                    f"{_format_signed_dollars(group.avg_tax_change)} "
                    f"({_format_signed_pct(group.pct_of_income)})"
                )
        else:
            st_module.markdown("### 🟢 Winners")
            st_module.caption("No income group nets out a tax cut.")

    with lose_col, st_module.container(border=True):
        if summary.losers:
            st_module.markdown("### 🔴 Losers")
            st_module.caption(
                f"{len(summary.losers)} groups face a net tax increase"
            )
            for group in summary.losers[:5]:
                st_module.markdown(
                    f"**{group.name}** — avg "
                    f"{_format_signed_dollars(group.avg_tax_change)} "
                    f"({_format_signed_pct(group.pct_of_income)})"
                )
        else:
            st_module.markdown("### 🔴 Losers")
            st_module.caption("No income group faces a net tax increase.")


__all__ = [
    "GroupSummary",
    "WinnersLosersSummary",
    "build_winners_losers",
    "headline_sentence",
    "render_winners_losers_callout",
]
