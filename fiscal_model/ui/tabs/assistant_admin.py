"""
Admin dashboard for the Ask assistant.

**Token-gated.** Only renders when ``ASSISTANT_ADMIN_TOKEN`` is set in the
environment (or Streamlit secrets) and the URL has a matching
``?admin=<token>`` query parameter. If either condition fails, the tab
is hidden entirely from the top-level tab list — non-admins don't even
see the tab title.

Shows:

* Today's spend vs. daily cap, with a "near-exhaustion" warning band.
* Headline KPIs (total turns, all-time cost, avg cost/turn,
  cache-hit ratio, error rate, avg elapsed, 30-day unique sessions).
* Daily cost + turn-count chart for the last 30 days.
* Tool usage frequency bar chart (last 30 days).
* Recent 20 turns table.

All values are read live from the same ``assistant_events`` sqlite the
rate limiter uses, so the dashboard is always in sync with reality.
"""

from __future__ import annotations

from typing import Any

from fiscal_model.assistant.admin import (
    daily_spend_series,
    estimate_runway_days,
    recent_turns,
    snapshot,
    tool_usage_counts,
)
from fiscal_model.assistant.rate_limit import RateLimiter


def render_assistant_admin_tab(st_module: Any) -> None:
    """Render the admin dashboard. Caller has already cleared the token gate."""
    st_module.subheader("💼 Ask — Admin")
    st_module.caption(
        "Read-only view of `assistant_events`. Live from the same sqlite "
        "ledger the rate limiter writes to."
    )

    try:
        limiter = RateLimiter()
        snap = snapshot(limiter)
    except Exception as exc:  # noqa: BLE001
        st_module.error(f"Failed to read usage db: {exc}")
        return

    # --- daily budget readout -----------------------------------------------
    today_pct = (
        100.0 * snap.today_cost_usd / snap.daily_cap_usd
        if snap.daily_cap_usd > 0
        else 0.0
    )
    if today_pct >= 95:
        st_module.error(
            f"🚨 Daily budget **near exhausted**: ${snap.today_cost_usd:.2f} "
            f"of ${snap.daily_cap_usd:.2f} used ({today_pct:.0f}%). "
            "Further requests will be rate-limited until UTC midnight."
        )
    elif today_pct >= 70:
        st_module.warning(
            f"⚠️ Daily budget: ${snap.today_cost_usd:.2f} of "
            f"${snap.daily_cap_usd:.2f} ({today_pct:.0f}%)."
        )
    else:
        st_module.info(
            f"💰 Daily budget: ${snap.today_cost_usd:.2f} of "
            f"${snap.daily_cap_usd:.2f} ({today_pct:.0f}%)."
        )
    st_module.progress(min(1.0, today_pct / 100.0))

    # --- headline metrics ---------------------------------------------------
    cols = st_module.columns(4)
    cols[0].metric("Today's turns", snap.today_turns)
    cols[1].metric("Today's cost", f"${snap.today_cost_usd:.4f}")
    cols[2].metric("Cache-hit ratio", f"{snap.cache_hit_ratio:.0%}")
    cols[3].metric("Error rate", f"{snap.error_rate_pct:.1f}%")

    cols = st_module.columns(4)
    cols[0].metric("All-time turns", f"{snap.total_turns:,}")
    cols[1].metric("All-time cost", f"${snap.total_cost_usd:.2f}")
    cols[2].metric("Avg cost / turn", f"${snap.avg_cost_per_turn_usd:.5f}")
    cols[3].metric("Avg elapsed (s)", f"{snap.avg_elapsed_s:.1f}")

    # 30-day unique sessions
    st_module.caption(
        f"📈 {snap.n_unique_sessions_30d:,} unique sessions in the last 30 days "
        f"· daily cap configurable via `ASSISTANT_DAILY_COST_CAP_USD`"
    )
    runway = estimate_runway_days(snap)
    if runway.get("projected_30d_burn"):
        st_module.caption(
            f"📐 If today's pace held: ~${runway['projected_30d_burn']:.2f} over 30 days."
        )

    st_module.divider()

    # --- daily spend + turn chart -------------------------------------------
    st_module.markdown("### Daily activity — last 30 days")
    try:
        daily = daily_spend_series(limiter, days=30)
    except Exception as exc:  # noqa: BLE001
        st_module.error(f"Failed to load daily series: {exc}")
        daily = None
    if daily is not None and not daily.empty:
        chart_col, table_col = st_module.columns([3, 1])
        with chart_col:
            st_module.line_chart(
                daily.set_index("day")[["cost_usd"]],
                height=240,
                use_container_width=True,
            )
            st_module.bar_chart(
                daily.set_index("day")[["turns"]],
                height=180,
                use_container_width=True,
            )
        with table_col:
            non_zero = daily[daily["turns"] > 0].tail(7)
            st_module.dataframe(
                non_zero,
                hide_index=True,
                use_container_width=True,
            )

    st_module.divider()

    # --- tool usage ---------------------------------------------------------
    st_module.markdown("### Tool usage — last 30 days")
    try:
        tools_df = tool_usage_counts(limiter, days=30)
    except Exception as exc:  # noqa: BLE001
        st_module.error(f"Failed to load tool stats: {exc}")
        tools_df = None
    if tools_df is not None and not tools_df.empty:
        st_module.bar_chart(
            tools_df.set_index("tool"),
            height=260,
            use_container_width=True,
        )
    else:
        st_module.caption("_No tool-call activity yet._")

    st_module.divider()

    # --- recent turns table -------------------------------------------------
    st_module.markdown("### Recent turns")
    try:
        recent = recent_turns(limiter, limit=20)
    except Exception as exc:  # noqa: BLE001
        st_module.error(f"Failed to load recent turns: {exc}")
        recent = None
    if recent is not None and not recent.empty:
        st_module.dataframe(recent, hide_index=True, use_container_width=True)
    else:
        st_module.caption("_No turns recorded yet._")

    st_module.divider()
    st_module.caption(
        "ℹ️ Configuration: daily cap, session cap, cool-down, and kill switch "
        "are read from `ASSISTANT_DAILY_COST_CAP_USD`, "
        "`ASSISTANT_SESSION_MESSAGE_CAP`, `ASSISTANT_COOLDOWN_SECONDS`, "
        "`ASSISTANT_DISABLED`. To rotate the admin token, change "
        "`ASSISTANT_ADMIN_TOKEN` and redeploy."
    )


__all__ = ["render_assistant_admin_tab"]
