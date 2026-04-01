"""
Streamlit tab: Real-Time Bill Tracker.

Displays active legislation with CBO scores, calculator estimates,
and freshness indicators. Connects to SQLite bill database.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bill_tracker.freshness import FreshnessStatus

DEFAULT_DB_PATH = Path(__file__).parent.parent.parent.parent / "fiscal_model" / "data_files" / "bills.db"


def render_bill_tracker_tab(st_module: Any, db_path: str | None = None) -> None:
    """
    Main entry point for the Bill Tracker tab.

    Args:
        st_module: Streamlit module (injected for testability).
        db_path: Path to bills.db. Defaults to fiscal_model/data_files/bills.db.
    """
    st_module.header("Active Legislation Tracker")
    st_module.caption("119th Congress (2025–2027) · Fiscal bills tracked daily from congress.gov")

    # Load database
    db = _get_database(db_path)

    if db is None:
        _render_no_db_state(st_module)
        return

    # Pipeline status bar
    _render_status_bar(st_module, db)

    # Filters
    filters = _render_filters(st_module)

    # Bill list
    bills = _get_filtered_bills(db, filters)

    if not bills:
        st_module.info(
            "No bills match the current filters. "
            "Try widening the filter criteria or running the update pipeline."
        )
        _render_update_instructions(st_module)
        return

    # Render each bill card
    for bill in bills[:100]:  # cap at 100 for performance
        _render_bill_card(st_module, bill, db)

    if len(bills) > 100:
        st_module.caption(f"Showing 100 of {len(bills)} matching bills.")


# ------------------------------------------------------------------
# Sub-renderers
# ------------------------------------------------------------------

def _render_no_db_state(st_module: Any) -> None:
    """Shown when the database hasn't been populated yet."""
    st_module.warning(
        "Bill database not found. "
        "Run the update pipeline to populate it with live data from congress.gov."
    )
    _render_update_instructions(st_module)


def _render_update_instructions(st_module: Any) -> None:
    """Show instructions for running the update pipeline."""
    with st_module.expander("How to populate the bill database"):
        st_module.markdown(
            """
**1. Get a congress.gov API key** (free):
   Register at [api.congress.gov/sign-up](https://api.congress.gov/sign-up/)

**2. Set environment variables:**
```bash
export CONGRESS_API_KEY=your_key_here
export ANTHROPIC_API_KEY=your_key_here  # for provision extraction
```

**3. Run the update pipeline:**
```bash
python scripts/update_bills.py --verbose
```

This fetches ~100–250 fiscal bills from the 119th Congress, runs LLM-based
provision extraction (Claude Haiku, ~$0.001/bill), and scores each bill
using the calculator's existing pipeline.

**For daily updates**, set a cron job:
```
0 6 * * * cd /path/to/app && python scripts/update_bills.py
```
            """
        )


def _render_status_bar(st_module: Any, db: Any) -> None:
    """Show pipeline status: last updated, total bills tracked."""
    col1, col2, col3 = st_module.columns([2, 1, 1])
    with col1:
        last_update = db.get_last_update()
        if last_update:
            st_module.caption(f"Last updated: {last_update.strftime('%b %d, %Y %I:%M %p UTC')}")
        else:
            st_module.caption("Last updated: never")
    with col2:
        total = db.count_bills()
        st_module.caption(f"{total} bills tracked")
    with col3:
        if st_module.button("🔄 Refresh", key="bt_refresh"):
            st_module.cache_data.clear()
            st_module.rerun()


def _render_filters(st_module: Any) -> dict:
    """Render filter controls and return current filter state."""
    with st_module.expander("Filters", expanded=True):
        col1, col2, col3 = st_module.columns(3)

        with col1:
            status_filter = st_module.selectbox(
                "Status",
                ["All", "introduced", "committee", "passed_chamber", "enacted"],
                key="bt_status_filter",
            )
        with col2:
            cbo_filter = st_module.checkbox("Has CBO score", key="bt_cbo_filter")
        with col3:
            chamber_filter = st_module.selectbox(
                "Chamber",
                ["All", "house", "senate"],
                key="bt_chamber_filter",
            )

        search_query = st_module.text_input(
            "Search title/sponsor",
            key="bt_search",
            placeholder="e.g. 'tax relief' or 'Smith'",
        )

    return {
        "status": status_filter if status_filter != "All" else None,
        "has_cbo_score": cbo_filter if cbo_filter else None,
        "chamber": chamber_filter if chamber_filter != "All" else None,
        "search": search_query.strip().lower() if search_query else None,
    }


def _get_filtered_bills(db: Any, filters: dict) -> list[dict]:
    """Retrieve bills from database applying filters."""
    bills = db.get_all_bills(
        status=filters.get("status"),
        has_cbo_score=filters.get("has_cbo_score"),
        limit=500,
    )

    # Apply chamber and search filters (not in DB query)
    result = []
    for bill in bills:
        if filters.get("chamber") and bill.get("chamber") != filters["chamber"]:
            continue
        if filters.get("search"):
            query = filters["search"]
            title_match = query in (bill.get("title") or "").lower()
            sponsor_match = query in (bill.get("sponsor") or "").lower()
            if not title_match and not sponsor_match:
                continue
        result.append(bill)

    return result


def _render_bill_card(st_module: Any, bill: dict, db: Any) -> None:
    """Render a single bill card with key metadata and scores."""
    from bill_tracker.freshness import freshness_from_db_row

    bill_id = bill.get("bill_id", "")
    title = bill.get("title", "Unknown Title")
    sponsor = bill.get("sponsor", "Unknown")
    status = bill.get("status", "introduced")
    url = bill.get("url", "")
    bill_type = (bill.get("bill_type") or "").upper()
    number = bill.get("number", "")
    introduced = bill.get("introduced_date", "")[:10]

    freshness = freshness_from_db_row(bill)
    cbo_score = db.get_cbo_score(bill_id)
    auto_score = db.get_auto_score(bill_id)

    # Card container
    with st_module.container(border=True):
        col_title, col_badge = st_module.columns([5, 1])

        with col_title:
            if url:
                st_module.markdown(f"**[{title}]({url})**")
            else:
                st_module.markdown(f"**{title}**")
            st_module.caption(
                f"{bill_type} {number} · {sponsor} · Introduced {introduced} · "
                f"Status: {_status_label(status)}"
            )

        with col_badge:
            _render_freshness_badge(st_module, freshness)

        # Scores row
        col_cbo, col_calc, col_btn = st_module.columns([2, 2, 1])

        with col_cbo:
            if cbo_score:
                cost = cbo_score.get("ten_year_cost_billions", 0)
                cost_str = _format_cost(cost)
                st_module.markdown(f"**CBO Score:** {cost_str} (10yr)")
            else:
                st_module.caption("CBO Score: not published")

        with col_calc:
            if auto_score:
                cost = auto_score.get("ten_year_cost_billions", 0)
                conf = auto_score.get("confidence", "low")
                cost_str = _format_cost(cost)
                st_module.markdown(f"**Calc. Estimate:** {cost_str}")
                st_module.caption(f"Confidence: {conf} · Auto-scored — verify against CBO")
            else:
                st_module.caption("Calc. Estimate: not scored")

        with col_btn:
            if st_module.button("Details", key=f"bt_detail_{bill_id}"):
                st_module.session_state[f"bt_show_detail_{bill_id}"] = True

        # Detail view (shown when "Details" button clicked)
        if st_module.session_state.get(f"bt_show_detail_{bill_id}", False):
            _render_bill_detail(st_module, bill, cbo_score, auto_score, db)

        if freshness.warning:
            st_module.caption(f"⚠ {freshness.warning}")


def _render_bill_detail(
    st_module: Any,
    bill: dict,
    cbo_score: dict | None,
    auto_score: dict | None,
    db: Any,
) -> None:
    """Expanded detail view for a bill."""
    bill_id = bill.get("bill_id", "")
    summary = bill.get("summary") or "_No CRS summary available._"

    st_module.markdown("---")
    st_module.markdown("**Bill Summary (CRS)**")
    st_module.markdown(summary[:1500] + ("…" if len(summary or "") > 1500 else ""))

    # Provisions
    if auto_score and auto_score.get("policies_json"):
        st_module.markdown("**Provisions Identified**")
        try:
            policies = json.loads(auto_score["policies_json"])
            for p in policies:
                policy_type = p.get("policy_type", "unknown")
                provision_text = p.get("provision_text", "")
                confidence = p.get("confidence", "")
                conf_icon = {"high": "✓", "medium": "~", "low": "⚠"}.get(confidence, "?")
                st_module.markdown(
                    f"- {conf_icon} **{policy_type}** — {provision_text[:120]}  "
                    f"*(confidence: {confidence})*"
                )
        except Exception:
            st_module.caption("Could not parse provisions.")

    # Official score
    st_module.markdown("**Official Score**")
    if cbo_score:
        cost = cbo_score.get("ten_year_cost_billions", 0)
        date = (cbo_score.get("estimate_date") or "")[:10]
        cbo_url = cbo_score.get("cbo_url", "")
        st_module.markdown(
            f"CBO Estimate: **{_format_cost(cost)}** over 10 years (published {date})"
        )
        if cbo_url:
            st_module.markdown(f"[View CBO estimate →]({cbo_url})")
    else:
        st_module.caption("No CBO score published yet.")

    # Calculator estimate
    st_module.markdown("**Calculator Estimate**")
    if auto_score:
        static = auto_score.get("static_cost", 0)
        behavioral = auto_score.get("behavioral_offset", 0)
        total = auto_score.get("ten_year_cost_billions", 0)
        conf = auto_score.get("confidence", "low")
        scored_at = (auto_score.get("scored_at") or "")[:10]
        st_module.markdown(
            f"Static: **{_format_cost(static / 1e9 if abs(static) > 1e6 else static)}** · "
            f"Behavioral offset: {_format_cost(behavioral / 1e9 if abs(behavioral) > 1e6 else behavioral)} · "
            f"Total: **{_format_cost(total)}**"
        )
        st_module.caption(
            f"Confidence: {conf} · Scored {scored_at} · "
            "Auto-scored — verify against official CBO/JCT estimates"
        )

        # CBO vs calculator comparison
        if cbo_score:
            cbo_cost = cbo_score.get("ten_year_cost_billions", 0)
            calc_cost = total
            if cbo_cost and calc_cost:
                diff_pct = abs(calc_cost - cbo_cost) / max(abs(cbo_cost), 0.01) * 100
                st_module.caption(
                    f"Model vs CBO: {diff_pct:.1f}% difference "
                    f"({'within' if diff_pct <= 15 else 'outside'} expected ±15% range)"
                )
    else:
        st_module.caption("Not yet scored by calculator.")

    if st_module.button("Hide details", key=f"bt_hide_{bill_id}"):
        st_module.session_state[f"bt_show_detail_{bill_id}"] = False
        st_module.rerun()


def _render_freshness_badge(st_module: Any, freshness: FreshnessStatus) -> None:  # type: ignore[name-defined]
    color_map = {
        "green": "🟢",
        "yellow": "🟡",
        "red": "🔴",
        "blue": "🔵",
    }
    icon = color_map.get(freshness.badge_color, "⚪")
    st_module.caption(f"{icon} {freshness.badge_label}")


def _status_label(status: str) -> str:
    return {
        "introduced": "Introduced",
        "committee": "In Committee",
        "passed_chamber": "Passed Chamber",
        "enacted": "Enacted",
    }.get(status, status.title())


def _format_cost(cost: float) -> str:
    """Format a cost in billions to a readable string."""
    if cost == 0:
        return "$0"
    sign = "+" if cost > 0 else "-"
    abs_cost = abs(cost)
    if abs_cost >= 1000:
        return f"{sign}${abs_cost / 1000:.1f}T"
    if abs_cost >= 1:
        return f"{sign}${abs_cost:.1f}B"
    return f"{sign}${abs_cost * 1000:.0f}M"


def _get_database(db_path: str | None) -> Any | None:
    """Load the bill database, returning None if not available."""
    try:
        from bill_tracker.database import BillDatabase
        path = db_path or str(DEFAULT_DB_PATH)
        db = BillDatabase(path)
        return db
    except Exception:
        return None
