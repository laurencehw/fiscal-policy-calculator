"""
Streamlit tab: Real-Time Bill Tracker.

Displays active legislation with CBO scores, calculator estimates,
and freshness indicators. Connects to SQLite bill database.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bill_tracker.freshness import FreshnessStatus

DEFAULT_DB_PATH = Path(__file__).parent.parent.parent.parent / "fiscal_model" / "data_files" / "bills.db"
POPULATED_DB_PATH = Path(__file__).parent.parent.parent.parent / "fiscal_model" / "data_files" / "bills_populated.db"
DEMO_DATA_PATH = Path(__file__).parent.parent.parent.parent / "fiscal_model" / "data_files" / "bill_tracker_demo.json"


def render_bill_tracker_tab(st_module: Any, db_path: str | None = None) -> None:
    """
    Main entry point for the Bill Tracker tab.

    Args:
        st_module: Streamlit module (injected for testability).
        db_path: Path to bills.db. Defaults to fiscal_model/data_files/bills.db.
    """
    st_module.header("Active Legislation Tracker")
    st_module.caption("119th Congress (2025–2027) · Fiscal bills from congress.gov")
    st_module.caption(
        "🔵 *Experimental feature.* Fiscal provisions are extracted from bill text by an LLM "
        "and are not validated scores — treat them as a research starting point, not estimates."
    )

    # Load database
    db, using_demo = _get_database(db_path)

    if db is None:
        _render_no_db_state(st_module)
        return

    if using_demo:
        st_module.info(
            "Showing sample bills for demonstration. Live congress.gov data "
            "has not been loaded on this deployment."
        )
    elif POPULATED_DB_PATH.exists():
        try:
            bill_count = db.count_bills()
            cbo_count = db.count_bills_with_cbo()
            st_module.success(f"✅ Loaded database with {bill_count:,} bills and {cbo_count:,} CBO scores")
        except Exception:
            logging.getLogger(__name__).exception("Failed to query bill/CBO counts")
            st_module.warning("Loaded bill database (could not retrieve counts)")

    # Pipeline status bar
    _render_status_bar(st_module, db)

    # One honest freshness banner instead of a repeated per-card warning.
    data_is_stale = _render_global_freshness_banner(st_module, db)

    # Filters (pass db so policy area options can be populated)
    filters = _render_filters(st_module, db)

    # Bill list
    bills = _get_filtered_bills(db, filters)

    if not bills:
        st_module.info(
            "No bills match the current filters — try widening the criteria."
        )
        return

    # Render each bill card
    for bill in bills[:100]:  # cap at 100 for performance
        _render_bill_card(
            st_module, bill, db, suppress_freshness_warning=data_is_stale
        )

    if len(bills) > 100:
        st_module.caption(f"Showing 100 of {len(bills)} matching bills.")


# ------------------------------------------------------------------
# Sub-renderers
# ------------------------------------------------------------------

def _is_operator_view(st_module: Any) -> bool:
    """Whether this request carries the ``?admin=<token>`` operator gate.

    Reuses the assistant's admin check so the tracker's runbook is visible on
    exactly the same terms as the admin dashboard.
    """
    try:
        from fiscal_model.assistant.admin import is_admin_request
    except Exception:  # pragma: no cover — defensive
        return False

    try:
        query_params = st_module.query_params
    except AttributeError:  # older Streamlit / test fakes
        try:
            query_params = st_module.experimental_get_query_params()
        except Exception:
            return False
    except Exception:  # pragma: no cover — defensive
        return False

    try:
        return bool(is_admin_request(query_params))
    except Exception:  # pragma: no cover — defensive
        return False


def _render_no_db_state(st_module: Any) -> None:
    """Shown when the database hasn't been populated yet.

    User-facing copy states the *condition*, not the fix: "run
    ``python scripts/update_bills.py``" is an instruction only the deployment
    operator can act on, so it lives in the log line and the operator runbook
    below (see :func:`_render_update_instructions`).
    """
    st_module.warning(
        "Live legislation data is not available on this deployment — "
        "data refresh pending."
    )
    logging.getLogger(__name__).info(
        "Bill database not found; populate it with `python scripts/update_bills.py` "
        "(see the operator runbook in the Tracker page)."
    )
    _render_update_instructions(st_module)


def _render_update_instructions(st_module: Any) -> None:
    """Operator runbook for the update pipeline — gated on ``?admin=<token>``.

    This is developer documentation (API keys, shell commands, a cron line).
    Showing it to a visitor who cannot run any of it is noise; showing it to
    the operator is the whole point. Everyone else sees the "data refresh
    pending" notice above.
    """
    if not _is_operator_view(st_module):
        return

    with st_module.expander("Operator runbook — populate the bill database"):
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

If CBO endpoints are blocked in your environment, use fallback scores:
```bash
python scripts/validate_cbo_fallback_scores.py --file bill_tracker/cbo_manual_scores.json
python scripts/update_bills.py --skip-cbo-fetch --cbo-fallback-file bill_tracker/cbo_manual_scores.json
python scripts/import_cbo_fallback_scores.py --file bill_tracker/cbo_manual_scores.json
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


def _render_global_freshness_banner(st_module: Any, db: Any) -> bool:
    """Render one dataset-level staleness banner; True when data is stale.

    When the whole database is old, every card used to repeat the same
    (doubled-glyph) warning 100 times. One dated banner carries the message;
    per-card warnings are suppressed while it is shown.
    """
    try:
        last_update = db.get_last_update()
    except Exception:
        return False
    if not last_update:
        return False

    # timezone.utc, not datetime.UTC: the latter is 3.11+ and this repo
    # supports 3.10.
    now = datetime.now(timezone.utc) if last_update.tzinfo else datetime.now()
    age_days = max(0, (now - last_update).days)
    if age_days <= 7:
        return False

    st_module.warning(
        f"⚠ Data as of {last_update.strftime('%b %d, %Y')} ({age_days} days "
        "old) — data refresh pending. Bill statuses and scores may have "
        "changed on congress.gov since this snapshot was taken."
    )
    return True


def _render_status_bar(st_module: Any, db: Any) -> None:
    """Show pipeline status: last updated, total bills tracked."""
    col1, col2, col3 = st_module.columns([2, 1, 1])
    with col1:
        try:
            last_update = db.get_last_update()
            if last_update:
                st_module.caption(f"Last updated: {last_update.strftime('%b %d, %Y %I:%M %p UTC')}")
            else:
                st_module.caption("Last updated: never")
        except Exception:
            st_module.caption("Last updated: unavailable")
    with col2:
        try:
            total = db.count_bills()
            st_module.caption(f"{total} bills tracked")
        except Exception:
            st_module.caption("Bill count unavailable")
    with col3:
        if st_module.button("🔄 Refresh", key="bt_refresh"):
            st_module.cache_data.clear()
            st_module.rerun()


def _render_filters(st_module: Any, db: Any) -> dict:
    """Render filter controls and return current filter state."""
    subjects = _get_unique_subjects(db)

    with st_module.expander("Search & Filters", expanded=True):
        search_query = st_module.text_input(
            "Search bills",
            key="bt_search",
            placeholder="e.g. 'tax relief', 'HR 1234', or 'Smith'",
        )

        col1, col2, col3 = st_module.columns(3)
        with col1:
            status_options = [
                "All", "introduced", "committee", "passed_chamber", "enacted",
            ]
            status_filter = st_module.selectbox(
                "Status",
                status_options,
                key="bt_status_filter",
            )
        with col2:
            chamber_filter = st_module.selectbox(
                "Chamber",
                ["All", "house", "senate"],
                key="bt_chamber_filter",
            )
        with col3:
            # Fiscal impact leads: sorting by recency surfaced $2M veterans
            # and lands bills while the major fiscal legislation of the
            # Congress sat below the fold.
            sort_options = [
                "Fiscal impact: Largest First",
                "Date: Newest First",
                "Date: Oldest First",
                "Relevance",
            ]
            sort_order = st_module.selectbox(
                "Sort by",
                sort_options,
                key="bt_sort_order",
            )

        col4, col5 = st_module.columns([3, 1])
        with col4:
            policy_areas: list[str] = []
            if subjects:
                policy_areas = st_module.multiselect(
                    "Policy Area",
                    options=subjects,
                    key="bt_policy_areas",
                    placeholder="All policy areas",
                )
        with col5:
            cbo_filter = st_module.checkbox("Has CBO score", key="bt_cbo_filter")
            major_fiscal = st_module.checkbox(
                "Major fiscal (≥ \\$1B)",
                key="bt_major_fiscal",
                help="Only bills whose CBO or calculator 10-year score is at least $1B in either direction.",
            )

    return {
        "status": status_filter if status_filter != "All" else None,
        "has_cbo_score": cbo_filter if cbo_filter else None,
        "chamber": chamber_filter if chamber_filter != "All" else None,
        "search": search_query.strip().lower() if search_query else None,
        "policy_areas": list(policy_areas) if policy_areas else None,
        "sort": sort_order,
        "major_fiscal": bool(major_fiscal),
    }


def _get_filtered_bills(db: Any, filters: dict) -> list[dict]:
    """Retrieve bills from database applying filters."""
    bills = db.get_all_bills(
        status=filters.get("status"),
        has_cbo_score=filters.get("has_cbo_score"),
        limit=500,
    )

    query = filters.get("search")
    policy_areas = filters.get("policy_areas")
    sort_order = filters.get("sort", "Fiscal impact: Largest First")

    impact_map: dict[str, float] = {}
    if filters.get("major_fiscal") or sort_order == "Fiscal impact: Largest First":
        try:
            impact_map = db.get_fiscal_impact_map()
        except Exception:
            impact_map = {}

    result = []
    relevance_scores: dict[str, int] = {}

    for bill in bills:
        if filters.get("major_fiscal"):
            impact = impact_map.get(bill.get("bill_id", ""))
            if impact is None or abs(impact) < 1.0:
                continue
        # Chamber filter
        if filters.get("chamber") and bill.get("chamber") != filters["chamber"]:
            continue

        # Policy area filter (crs_subjects stored as JSON string)
        if policy_areas:
            raw_subjects = bill.get("crs_subjects") or "[]"
            try:
                bill_subjects = json.loads(raw_subjects) if isinstance(raw_subjects, str) else raw_subjects
            except (json.JSONDecodeError, TypeError):
                bill_subjects = []
            if not any(s in bill_subjects for s in policy_areas):
                continue

        # Keyword search across title, sponsor, bill number, and summary
        if query:
            score = 0
            title = (bill.get("title") or "").lower()
            sponsor = (bill.get("sponsor") or "").lower()
            number = (bill.get("number") or "").lower()
            bill_type = (bill.get("bill_type") or "").lower()
            summary = (bill.get("summary") or "").lower()
            bill_id = (bill.get("bill_id") or "").lower()

            if query in title:
                score += 3
            if query in sponsor:
                score += 2
            if query in number or query in bill_id:
                score += 2
            # Also match "hr 1234" style queries against combined type+number
            combined = f"{bill_type} {number}"
            if query in combined or query.replace(" ", "") in combined.replace(" ", ""):
                score += 2
            if query in summary:
                score += 1

            if score == 0:
                continue
            relevance_scores[bill.get("bill_id", "")] = score

        result.append(bill)

    # Sort
    if sort_order == "Fiscal impact: Largest First":
        # Unscored bills keep their recency order below every scored bill.
        result.sort(
            key=lambda b: abs(impact_map.get(b.get("bill_id", ""), 0.0)),
            reverse=True,
        )
    elif sort_order == "Date: Oldest First":
        result.sort(key=lambda b: (b.get("introduced_date") or ""), reverse=False)
    elif sort_order == "Relevance" and query:
        result.sort(
            key=lambda b: relevance_scores.get(b.get("bill_id", ""), 0),
            reverse=True,
        )
    # "Date: Newest First" uses DB ordering (introduced_date DESC)

    return result


def _get_unique_subjects(db: Any) -> list[str]:
    """Extract unique CRS subject areas from all bills for the policy area filter."""
    try:
        bills = db.get_all_bills(limit=500)
    except Exception:
        return []

    subjects: set[str] = set()
    for bill in bills:
        raw = bill.get("crs_subjects") or "[]"
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(parsed, list):
                subjects.update(s for s in parsed if isinstance(s, str) and s)
        except (json.JSONDecodeError, TypeError):
            pass

    return sorted(subjects)


def _render_bill_card(
    st_module: Any,
    bill: dict,
    db: Any,
    suppress_freshness_warning: bool = False,
) -> None:
    """Render a single bill card with key metadata and scores."""
    from bill_tracker.freshness import freshness_from_db_row

    bill_id = bill.get("bill_id", "")
    title = bill.get("title", "Unknown Title")
    sponsor = bill.get("sponsor", "Unknown")
    status = bill.get("status", "introduced")
    url = bill.get("url", "")
    bill_type = (bill.get("bill_type") or "").upper()
    number = bill.get("number", "")
    introduced = _format_date(bill.get("introduced_date", ""))

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
            # When the dataset-level staleness banner is up, a per-card
            # "Expired (Nd)" chip on all 100 cards just repeats it — keep
            # only bill-specific badges (e.g. Enacted) in that case.
            if not suppress_freshness_warning or freshness.status in (
                "enacted",
                "fresh",
            ):
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

        if freshness.warning and not suppress_freshness_warning:
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

        # Category-level model accuracy band, pulled from the live
        # validation scorecard via the dominant provision's policy_type.
        # Tells readers "TCJA-style provisions average ±5.5% across 3
        # calibrated runs" so the calculator estimate isn't disembodied.
        _render_bill_calibration_band(st_module, auto_score, total)

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


def _dominant_provision_policy_type(auto_score: dict) -> str | None:
    """Pick the most-confident provision's policy_type from a bill's
    auto-score. Used to look up a category-level calibration band when
    a bill spans multiple provisions."""
    raw_policies = auto_score.get("policies_json")
    if not raw_policies:
        return None
    try:
        policies = json.loads(raw_policies)
    except Exception:
        return None
    if not isinstance(policies, list) or not policies:
        return None

    confidence_rank = {"high": 3, "medium": 2, "low": 1}
    best = max(
        policies,
        key=lambda p: confidence_rank.get(p.get("confidence", ""), 0),
        default=None,
    )
    if not isinstance(best, dict):
        return None
    return best.get("policy_type")


def _render_bill_calibration_band(
    st_module: Any,
    auto_score: dict,
    total_billions: float,
) -> None:
    """Surface the validation-scorecard accuracy for a bill's dominant
    provision type. Falls back silently when the scorecard fails or no
    provisions are available — never breaks the bill card."""
    try:
        from fiscal_model.ui.confidence_band import (
            estimate_uncertainty_dollars,
            get_band_for_policy_type,
        )
    except Exception:
        return

    policy_type = _dominant_provision_policy_type(auto_score)
    if policy_type is None:
        # Without a parsed provision, defaulting to "Generic" would
        # surface a misleading ±29% band. Skip silently.
        return
    band = get_band_for_policy_type(policy_type)
    if band is None:
        return

    half = estimate_uncertainty_dollars(total_billions, band)
    st_module.caption(
        f"Calibration band: ±{band.mean_abs_pct_error:.1f}% mean error in "
        f"{band.category} category ({band.n_calibrated} calibrated run"
        f"{'s' if band.n_calibrated != 1 else ''}, {band.rating_label}) "
        f"— implies ±{_format_cost(half)} on this $-amount."
    )


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


def _format_date(date_str: str | None) -> str:
    """Return YYYY-MM-DD portion of an ISO date string, or 'Date unknown'."""
    if not date_str:
        return "Date unknown"
    date_part = date_str[:10]
    # Treat Unix epoch as missing (legacy DB rows written before the None fix)
    if date_part == "1970-01-01":
        return "Date unknown"
    return date_part


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


class _DemoBillDatabase:
    """In-memory adapter that mirrors BillDatabase methods for hosted demo mode."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._generated_at = payload.get("generated_at")
        self._bills: list[dict[str, Any]] = payload.get("bills", [])
        self._cbo_by_bill = {}
        self._auto_by_bill = {}

        for bill in self._bills:
            bill_id = bill.get("bill_id")
            if not bill_id:
                continue
            cbo_score = bill.get("cbo_score")
            auto_score = bill.get("auto_score")
            if cbo_score:
                self._cbo_by_bill[bill_id] = cbo_score
            if auto_score:
                auto_copy = dict(auto_score)
                policies = auto_copy.pop("policies", None)
                if policies is not None:
                    auto_copy["policies_json"] = json.dumps(policies)
                self._auto_by_bill[bill_id] = auto_copy

    def get_last_update(self) -> datetime | None:
        if not self._generated_at:
            return None
        try:
            return datetime.fromisoformat(self._generated_at.replace("Z", "+00:00"))
        except ValueError:
            return None

    def count_bills(self) -> int:
        return len(self._bills)

    def get_all_bills(
        self,
        status: str | None = None,
        has_cbo_score: bool | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        filtered: list[dict[str, Any]] = []
        for bill in self._bills:
            if status and bill.get("status") != status:
                continue
            if has_cbo_score is True and not bill.get("cbo_score"):
                continue
            filtered.append(bill)
            if len(filtered) >= limit:
                break
        return filtered

    def get_cbo_score(self, bill_id: str) -> dict[str, Any] | None:
        return self._cbo_by_bill.get(bill_id)

    def get_auto_score(self, bill_id: str) -> dict[str, Any] | None:
        return self._auto_by_bill.get(bill_id)

    def get_fiscal_impact_map(self) -> dict[str, float]:
        """Mirror BillDatabase: latest 10-year cost per bill, CBO first.

        Without this, demo mode silently lost fiscal-impact sorting and the
        major-fiscal filter hid every bill.
        """
        impacts: dict[str, float] = {}
        for source in (self._auto_by_bill, self._cbo_by_bill):
            for bill_id, score in source.items():
                cost = score.get("ten_year_cost_billions")
                if cost is not None:
                    impacts[bill_id] = float(cost)
        return impacts


def _get_database(db_path: str | None) -> tuple[Any | None, bool]:
    """Load live database; fall back to demo data when unavailable or corrupt."""
    try:
        from bill_tracker.database import BillDatabase
        # Prefer populated DB if it exists and is healthy; fall back to default
        path = db_path or str(POPULATED_DB_PATH if POPULATED_DB_PATH.exists() else DEFAULT_DB_PATH)
        db = BillDatabase(path)
        # Smoke-test: if DB is corrupt, this raises sqlite3.DatabaseError
        db.count_bills()
        return db, False
    except Exception:
        try:
            demo_payload = json.loads(DEMO_DATA_PATH.read_text(encoding="utf-8"))
            return _DemoBillDatabase(demo_payload), True
        except Exception:
            return None, False
