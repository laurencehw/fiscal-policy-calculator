"""
Ask-assistant tab: chat UI for the Fiscal Policy Calculator.

Renders a conversational interface that lets the reader pose public-
finance questions. The assistant is grounded in the app's scoring engine
and a curated corpus of authoritative sources (CBO, JCT, PWBM, Yale
Budget Lab, TPC, SSA Trustees, FRED, etc.).

Streamlit pitfalls handled here:

* The tab body is wrapped in ``@st.fragment`` so a mid-stream user
  interaction does not rerun the entire app and kill the in-progress
  response.
* The Anthropic client is cached with ``@st.cache_resource`` so it is
  built once per session rather than per rerun.
"""

from __future__ import annotations

from typing import Any

from fiscal_model.assistant.citations import render_provenance_footer


_HISTORY_KEY = "ask_history"
_PENDING_PROMPT_KEY = "_ask_pending_prompt"
_USE_OPUS_KEY = "_ask_use_opus"
_MAX_TURNS = 30


_STARTER_PROMPTS: list[str] = [
    "What does CBO project for the 10-year deficit, and what's driving it?",
    "How does the TCJA full extension affect each income decile?",
    "Compare PWBM and CBO on a corporate-rate increase.",
    "Explain dynamic scoring as this app applies it.",
    "When is the Social Security trust fund projected to be depleted?",
    "Score a 25% corporate rate and tell me what it costs.",
]


def render_ask_tab(
    st_module: Any,
    fiscal_assistant: Any,
    scoring_result: Any = None,
) -> None:
    """Top-level renderer; wraps the body in ``st.fragment`` if available.

    Streamlit ≥1.33 has ``st.fragment``; on older versions we fall back
    to a plain render (the user will see occasional stream interruption
    when they click sidebar widgets — known limitation).
    """
    fragment = getattr(st_module, "fragment", None)
    if callable(fragment):
        @fragment
        def _body() -> None:
            _render_body(st_module, fiscal_assistant, scoring_result)

        _body()
    else:
        _render_body(st_module, fiscal_assistant, scoring_result)


def _render_body(
    st_module: Any,
    fiscal_assistant: Any,
    scoring_result: Any,
) -> None:
    state = st_module.session_state

    st_module.subheader("💬 Ask")
    st_module.markdown(
        "Pose public-finance questions about this app's scoring or the broader "
        "fiscal picture. Answers draw on the app's calibrated engine and a "
        "curated set of authoritative sources — CBO, JCT, Penn Wharton Budget "
        "Model, Yale Budget Lab, Tax Policy Center, Peterson Foundation, "
        "BEA, BLS, SSA Trustees, and FRED. Every substantive claim is "
        "cited — markers with no source are stripped automatically."
    )

    # --- API key check --------------------------------------------------
    if not fiscal_assistant.is_available():
        _render_no_api_key(st_module)
        return

    # --- ensure session state -------------------------------------------
    state.setdefault(_HISTORY_KEY, [])
    state.setdefault(_USE_OPUS_KEY, False)

    # --- options bar ----------------------------------------------------
    cols = st_module.columns([3, 2, 2])
    with cols[0]:
        scoring_label = (
            f"📊 Using current scored policy as context: **{_scoring_summary(scoring_result)}**"
            if scoring_result is not None
            else "_No policy scored yet — score one on the Calculator tab to "
            "ground the conversation in your own numbers._"
        )
        st_module.caption(scoring_label)
    with cols[1]:
        state[_USE_OPUS_KEY] = st_module.toggle(
            "Use Opus 4.7 for harder questions",
            value=state.get(_USE_OPUS_KEY, False),
            help="More careful reasoning, ~5× more expensive than Sonnet.",
            key="_ask_opus_toggle",
        )
    with cols[2]:
        if st_module.button("🗑 Clear conversation", use_container_width=True):
            state[_HISTORY_KEY] = []
            fiscal_assistant.cost.turns = []
            st_module.rerun()

    # Apply the model toggle.
    fiscal_assistant._model = (  # noqa: SLF001 — small intentional internal access
        "claude-opus-4-7" if state.get(_USE_OPUS_KEY) else "claude-sonnet-4-6"
    )

    # --- starter prompts (only visible when history is empty) -----------
    if not state[_HISTORY_KEY]:
        st_module.markdown("**Try one of these to start:**")
        prompt_cols = st_module.columns(2)
        for i, prompt in enumerate(_STARTER_PROMPTS):
            col = prompt_cols[i % 2]
            if col.button(prompt, key=f"_ask_starter_{i}", use_container_width=True):
                state[_PENDING_PROMPT_KEY] = prompt
                st_module.rerun()
        st_module.markdown("---")

    # --- render history --------------------------------------------------
    for turn in state[_HISTORY_KEY]:
        with st_module.chat_message(turn["role"]):
            st_module.markdown(turn["content"])
            if turn["role"] == "assistant":
                _render_assistant_extras(st_module, turn)

    # --- handle pending starter-prompt click -----------------------------
    pending = state.pop(_PENDING_PROMPT_KEY, None)

    # --- chat input ------------------------------------------------------
    user_message = pending or st_module.chat_input(
        "Ask a public-finance question…",
        max_chars=2000,
    )

    if not user_message:
        # No input this rerun.
        _render_cost_meter(st_module, fiscal_assistant)
        return

    # Cap conversation length.
    if len([t for t in state[_HISTORY_KEY] if t["role"] == "user"]) >= _MAX_TURNS:
        st_module.warning(
            f"This conversation has reached {_MAX_TURNS} turns. Please clear it "
            "to continue."
        )
        return

    # --- render the user turn --------------------------------------------
    with st_module.chat_message("user"):
        st_module.markdown(user_message)

    # --- stream the assistant turn ---------------------------------------
    history_for_api = _history_for_api(state[_HISTORY_KEY])
    scoring_context = _scoring_context(scoring_result)
    with st_module.chat_message("assistant"):
        placeholder = st_module.empty()
        accumulated: list[str] = []
        try:
            for chunk in fiscal_assistant.stream_response(
                user_message=user_message,
                history=history_for_api,
                scoring_context=scoring_context,
            ):
                accumulated.append(chunk)
                placeholder.markdown("".join(accumulated))
        except Exception as exc:  # noqa: BLE001
            placeholder.error(f"Assistant error: {exc}")
            return

        final_text = fiscal_assistant.last_full_text or "".join(accumulated)
        placeholder.markdown(final_text)

        turn_entry = {
            "role": "assistant",
            "content": final_text,
            "provenance": list(fiscal_assistant.last_provenance),
            "usage": (
                fiscal_assistant.last_usage.to_dict()
                if fiscal_assistant.last_usage
                else None
            ),
            "stripped_markers": list(fiscal_assistant.last_stripped_markers),
        }
        _render_assistant_extras(st_module, turn_entry)

    # Append both turns to history (atomic; only after streaming completes).
    state[_HISTORY_KEY].append({"role": "user", "content": user_message})
    state[_HISTORY_KEY].append(turn_entry)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _render_no_api_key(st_module: Any) -> None:
    st_module.info(
        "The Ask assistant requires an Anthropic API key. Set the "
        "`ANTHROPIC_API_KEY` environment variable before launching "
        "Streamlit (or paste a key below). The key is **not** stored "
        "anywhere — it lives only in this session."
    )
    state = st_module.session_state
    key = st_module.text_input(
        "Anthropic API key",
        type="password",
        value=state.get("_ask_byo_key", ""),
        key="_ask_byo_key_input",
        help="Get one at https://console.anthropic.com/",
    )
    if st_module.button("Use this key for this session", disabled=not key):
        import os

        os.environ["ANTHROPIC_API_KEY"] = key
        state["_ask_byo_key"] = key
        st_module.rerun()


def _scoring_context(scoring_result: Any) -> dict[str, Any] | None:
    """Distill a ScoringResult into a small dict for prompt injection."""
    if scoring_result is None:
        return None
    try:
        policy = getattr(scoring_result, "policy", None)
        cred = getattr(scoring_result, "credibility", None)
        return {
            "policy_name": getattr(policy, "name", None) if policy else None,
            "policy_type": (
                getattr(getattr(policy, "policy_type", None), "value", None)
                if policy
                else None
            ),
            "ten_year_deficit_impact_billions": float(
                getattr(scoring_result, "total_10_year_cost", 0.0)
            ),
            "static_total_billions": float(
                getattr(scoring_result, "total_static_cost", 0.0)
            ),
            "revenue_feedback_10yr_billions": float(
                getattr(scoring_result, "revenue_feedback_10yr", 0.0)
            ),
            "is_dynamic": bool(getattr(scoring_result, "is_dynamic", False)),
            "credibility": {
                "evidence_type": getattr(cred, "evidence_type", None),
                "n_benchmarks": getattr(cred, "n_benchmarks", None),
                "mean_abs_pct_error": getattr(cred, "mean_abs_pct_error", None),
            }
            if cred
            else None,
        }
    except Exception:  # noqa: BLE001
        return None


def _scoring_summary(scoring_result: Any) -> str:
    policy = getattr(scoring_result, "policy", None)
    name = getattr(policy, "name", None) or "current policy"
    impact = getattr(scoring_result, "total_10_year_cost", None)
    if impact is None:
        return name
    sign = "+" if impact >= 0 else "−"
    return f"{name} ({sign}\\${abs(float(impact)):,.0f}B / 10y)"


def _history_for_api(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip per-turn metadata before passing history to the API."""
    out: list[dict[str, Any]] = []
    for turn in history:
        out.append({"role": turn["role"], "content": turn["content"]})
    return out


def _render_assistant_extras(st_module: Any, turn: dict[str, Any]) -> None:
    """Render the tool-call expander and per-turn usage caption."""
    provenance = turn.get("provenance") or []
    usage = turn.get("usage")
    stripped = turn.get("stripped_markers") or []

    if provenance:
        with st_module.expander(
            f"🔧 Tool calls used ({len(provenance)})", expanded=False
        ):
            st_module.markdown(render_provenance_footer(provenance))

    caption_bits: list[str] = []
    if usage:
        caption_bits.append(
            f"{usage['input_tokens'] + usage['output_tokens']:,} tok · "
            f"${usage['cost_usd']:.4f}"
        )
        if usage["cache_read_tokens"]:
            caption_bits.append(f"cache-hit {usage['cache_read_tokens']:,}")
    if stripped:
        caption_bits.append(f"⚠️ {len(stripped)} unsupported marker(s) stripped")
    if caption_bits:
        st_module.caption(" · ".join(caption_bits))


def _render_cost_meter(st_module: Any, fiscal_assistant: Any) -> None:
    """Footer-style cost meter for the session."""
    summary = fiscal_assistant.cost.summary()
    if "No usage" in summary:
        return
    st_module.markdown("---")
    st_module.caption(f"Session usage — {summary}")


__all__ = ["render_ask_tab"]
