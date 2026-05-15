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
* ``st.secrets["ANTHROPIC_API_KEY"]`` is promoted to ``os.environ`` so
  Streamlit Cloud deployments (which surface secrets via ``st.secrets``,
  not env vars) just work out of the box.
"""

from __future__ import annotations

import os
import time
from typing import Any

from fiscal_model.assistant.citations import render_provenance_footer
from fiscal_model.assistant.rate_limit import RateLimiter, new_session_id


_HISTORY_KEY = "ask_history"
_PENDING_PROMPT_KEY = "_ask_pending_prompt"
_SESSION_ID_KEY = "_ask_session_id"
_LAST_TS_KEY = "_ask_last_message_ts"
_LIMITER_CACHE_KEY = "_ask_limiter"


def _promote_secret_to_env(st_module: Any) -> dict[str, Any]:
    """Promote ``st.secrets["ANTHROPIC_API_KEY"]`` to ``os.environ`` if set.

    Streamlit Cloud surfaces deployment secrets via ``st.secrets``, not
    env vars. The Anthropic SDK and the rest of this codebase read from
    ``os.environ``, so we bridge the gap on first render. Idempotent.

    Returns a small diagnostic dict (env_var_set, secrets_object_present,
    secrets_keys_seen, attempted_keys) so the unavailable-message UI can
    explain exactly what was checked.
    """
    diag: dict[str, Any] = {
        "env_var_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "secrets_object_present": False,
        "secrets_keys_seen": [],
        "promoted_from": None,
    }
    if diag["env_var_set"]:
        return diag

    secrets = getattr(st_module, "secrets", None)
    if secrets is None:
        return diag
    diag["secrets_object_present"] = True

    # Try several access patterns — `st.secrets` behavior varies across
    # Streamlit versions and across (no-secrets-file / has-file) states.
    candidates = ("ANTHROPIC_API_KEY", "anthropic_api_key", "anthropic", "ANTHROPIC")
    value = None
    matched_key = None
    try:
        # Enumerate visible top-level keys (helps the diagnostic message).
        if hasattr(secrets, "keys"):
            try:
                diag["secrets_keys_seen"] = [str(k) for k in secrets.keys()]
            except Exception:  # noqa: BLE001
                diag["secrets_keys_seen"] = ["(error enumerating keys)"]
    except Exception:  # noqa: BLE001
        pass

    for key in candidates:
        try:
            # __getitem__ raises on missing keys for Streamlit Secrets.
            v = secrets[key]
        except Exception:  # noqa: BLE001
            try:
                v = getattr(secrets, key, None)
            except Exception:  # noqa: BLE001
                v = None
        if v:
            value = v
            matched_key = key
            break

    if value:
        # If the matched object is itself a nested dict (e.g. a [anthropic]
        # TOML section), look one level deeper.
        if hasattr(value, "get") and not isinstance(value, str):
            for nested in ("api_key", "API_KEY", "key"):
                try:
                    nv = value.get(nested)
                except Exception:  # noqa: BLE001
                    nv = None
                if nv:
                    value = nv
                    matched_key = f"{matched_key}.{nested}"
                    break

    if value and isinstance(value, str):
        os.environ["ANTHROPIC_API_KEY"] = value
        diag["env_var_set"] = True
        diag["promoted_from"] = f"st.secrets[{matched_key!r}]"
    return diag


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

    # Promote st.secrets → os.environ before checking availability so
    # Streamlit Cloud deployments work without an env var.
    diag = _promote_secret_to_env(st_module)

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
        _render_unavailable(st_module, diag)
        return

    # --- ensure session state -------------------------------------------
    # initialize_session_state pre-seeds ask_history to None per the
    # session_state.py schema; ``setdefault`` won't replace a stored None,
    # so we have to explicitly coerce it to a list here.
    if state.get(_HISTORY_KEY) is None:
        state[_HISTORY_KEY] = []
    state.setdefault(_SESSION_ID_KEY, new_session_id())
    state.setdefault(_LAST_TS_KEY, None)

    limiter = _get_rate_limiter(state)

    # --- options bar ----------------------------------------------------
    cols = st_module.columns([4, 1])
    with cols[0]:
        scoring_label = (
            f"📊 Using current scored policy as context: **{_scoring_summary(scoring_result)}**"
            if scoring_result is not None
            else "_No policy scored yet — score one on the Calculator tab to "
            "ground the conversation in your own numbers._"
        )
        st_module.caption(scoring_label)
    with cols[1]:
        if st_module.button("🗑 Clear", use_container_width=True):
            state[_HISTORY_KEY] = []
            fiscal_assistant.cost.turns = []
            st_module.rerun()

    # Model is fixed to Sonnet 4.6 for cost predictability. To experiment
    # with Opus locally, set ASSISTANT_MODEL=claude-opus-4-7 in your env.
    fiscal_assistant._model = (  # noqa: SLF001
        os.environ.get("ASSISTANT_MODEL", "").strip() or "claude-sonnet-4-6"
    )

    # --- daily budget readout ------------------------------------------
    _render_budget_status(st_module, limiter)

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

    # Rate-limit / budget check before spending any tokens.
    user_turns = sum(1 for t in state[_HISTORY_KEY] if t["role"] == "user")
    decision = limiter.check(
        session_id=state[_SESSION_ID_KEY],
        session_message_count=user_turns,
        last_message_ts=state.get(_LAST_TS_KEY),
    )
    if not decision.allowed:
        st_module.warning(decision.reason)
        return

    # --- render the user turn --------------------------------------------
    with st_module.chat_message("user"):
        st_module.markdown(user_message)

    # --- stream the assistant turn ---------------------------------------
    history_for_api = _history_for_api(state[_HISTORY_KEY])
    scoring_context = _scoring_context(scoring_result)
    turn_start = time.time()
    error_msg: str | None = None
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
            error_msg = f"{type(exc).__name__}: {exc}"
            # Still record so a runaway error doesn't go unbilled in budget terms.
            _record_turn(
                limiter,
                state,
                fiscal_assistant,
                question=user_message,
                answer="",
                elapsed_s=time.time() - turn_start,
                error=error_msg,
            )
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
    state[_LAST_TS_KEY] = time.time()

    # Persist the turn to sqlite (telemetry + daily-cap accounting).
    _record_turn(
        limiter,
        state,
        fiscal_assistant,
        question=user_message,
        answer=final_text,
        elapsed_s=time.time() - turn_start,
        error=None,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _detect_typo(keys: list[str], expected: str, max_distance: int = 2) -> str | None:
    """Find a key in ``keys`` that is within edit distance of ``expected``.

    Catches common deployer mistakes like ``ANTHROPHIC_API_KEY`` (extra H)
    or ``ANTROPIC_API_KEY`` (missing H).
    """
    expected_lower = expected.lower()
    best: tuple[int, str] | None = None
    for key in keys:
        if key == expected:
            continue
        d = _edit_distance(key.lower(), expected_lower)
        if d <= max_distance and (best is None or d < best[0]):
            best = (d, key)
    return best[1] if best else None


def _edit_distance(a: str, b: str) -> int:
    """Levenshtein distance (small implementation; inputs are short keys)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i] + [0] * len(b)
        for j, cb in enumerate(b, start=1):
            curr[j] = min(
                curr[j - 1] + 1,           # insertion
                prev[j] + 1,               # deletion
                prev[j - 1] + (ca != cb),  # substitution
            )
        prev = curr
    return prev[-1]


def _render_unavailable(st_module: Any, diag: dict[str, Any] | None = None) -> None:
    """Show a friendly admin-facing message when no API key is configured.

    Includes a "What we looked for" diagnostic so the deployer can tell
    exactly what failed: env var? secrets file? wrong key name?
    """
    st_module.info(
        "💬 The Ask assistant is not configured for this deployment.\n\n"
        "*If you're the deployer:* set `ANTHROPIC_API_KEY` either as a "
        "Streamlit secret or an environment variable. See the expander "
        "below for what was checked."
    )

    with st_module.expander("How to set the key", expanded=False):
        st_module.markdown(
            "**Streamlit Cloud** — Settings → Secrets, add:\n\n"
            "```toml\n"
            'ANTHROPIC_API_KEY = "sk-ant-..."\n'
            "```\n\n"
            "Save and the app reboots automatically.\n\n"
            "**Local** — set an env var before launching:\n\n"
            "```bash\n"
            "export ANTHROPIC_API_KEY=sk-ant-...\n"
            "streamlit run app.py\n"
            "```\n\n"
            "Or create `.streamlit/secrets.toml` in the repo with the "
            "same TOML block above.\n\n"
            "**Local on Windows (PowerShell)**:\n\n"
            "```powershell\n"
            '$env:ANTHROPIC_API_KEY = "sk-ant-..."\n'
            "streamlit run app.py\n"
            "```"
        )

    if diag:
        with st_module.expander("Diagnostic — what was checked", expanded=True):
            st_module.markdown(
                f"- `os.environ['ANTHROPIC_API_KEY']` present: "
                f"**{diag.get('env_var_set', False)}**"
            )
            st_module.markdown(
                f"- `st.secrets` accessible: "
                f"**{diag.get('secrets_object_present', False)}**"
            )
            keys = diag.get("secrets_keys_seen") or []
            if keys:
                st_module.markdown(
                    "- Top-level keys visible in `st.secrets`: "
                    + ", ".join(f"`{k}`" for k in keys)
                )
                near = _detect_typo(keys, "ANTHROPIC_API_KEY")
                if near:
                    st_module.error(
                        f"🪲 **Likely typo**: your secret is named `{near}`, "
                        "but the assistant looks for `ANTHROPIC_API_KEY` "
                        "(no extra 'H'). Rename the secret in Streamlit "
                        "Cloud → Settings → Secrets to fix this."
                    )
            else:
                st_module.markdown(
                    "- Top-level keys visible in `st.secrets`: _none_ "
                    "(either no secrets file is loaded, or it is empty)"
                )
            if diag.get("promoted_from"):
                st_module.markdown(
                    f"- ✅ Promoted from `{diag['promoted_from']}` "
                    "(but `is_available()` still returned False — that's a bug; please report)"
                )
            st_module.caption(
                "The key name must be exactly `ANTHROPIC_API_KEY` "
                "(case-sensitive). Common mistakes: extra whitespace, "
                "quotes left in the value field, or pasting into the "
                "wrong app's secrets."
            )


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
    """Render a small per-turn caption.

    Tool internals are intentionally hidden from the reader by default —
    sources are already cited in the answer via [^N] footnotes. Deployers
    who want to inspect tool calls can set ASSISTANT_SHOW_TOOLS=1 in the
    environment to surface a collapsed expander.
    """
    provenance = turn.get("provenance") or []
    usage = turn.get("usage")
    stripped = turn.get("stripped_markers") or []

    if provenance and os.environ.get("ASSISTANT_SHOW_TOOLS", "").strip() in {
        "1",
        "true",
        "TRUE",
    }:
        with st_module.expander(
            f"🔧 Tool calls (dev mode) — {len(provenance)}", expanded=False
        ):
            st_module.markdown(render_provenance_footer(provenance))

    caption_bits: list[str] = []
    if provenance:
        # Count distinct tools used (more reader-friendly than the raw list).
        distinct = len({p.get("tool") for p in provenance})
        caption_bits.append(
            f"Drew on {distinct} source{'s' if distinct != 1 else ''}"
        )
    if stripped:
        caption_bits.append(
            f"⚠️ {len(stripped)} unsupported claim{'s' if len(stripped) != 1 else ''} stripped"
        )
    if caption_bits:
        st_module.caption(" · ".join(caption_bits))


def _render_cost_meter(st_module: Any, fiscal_assistant: Any) -> None:
    """Footer-style cost meter for the session."""
    summary = fiscal_assistant.cost.summary()
    if "No usage" in summary:
        return
    st_module.markdown("---")
    st_module.caption(f"Session usage — {summary}")


def _get_rate_limiter(state: Any) -> RateLimiter:
    """Cache the limiter on session_state so we don't rebuild every rerun.

    The limiter itself is stateless except for the sqlite handle; the daily
    cap is read from sqlite live each turn so concurrent sessions correctly
    share the same budget.
    """
    limiter = state.get(_LIMITER_CACHE_KEY)
    if limiter is None:
        limiter = RateLimiter()
        state[_LIMITER_CACHE_KEY] = limiter
    return limiter


def _render_budget_status(st_module: Any, limiter: RateLimiter) -> None:
    """Show today's spend and the remaining daily budget as a progress bar."""
    spent = limiter.today_spend_usd()
    cap = limiter.config.daily_cost_cap_usd
    pct = min(1.0, spent / cap) if cap > 0 else 0.0
    if pct >= 0.95:
        st_module.warning(
            f"Today's free-tier budget is nearly exhausted: "
            f"${spent:.2f} of ${cap:.2f} used. Resets at UTC midnight."
        )
    elif pct >= 0.7:
        st_module.caption(
            f"📊 Today's usage: ${spent:.2f} of ${cap:.2f} daily budget."
        )
    # Below 70%, keep the chat clean.


def _record_turn(
    limiter: RateLimiter,
    state: Any,
    fiscal_assistant: Any,
    *,
    question: str,
    answer: str,
    elapsed_s: float,
    error: str | None,
) -> None:
    """Persist a turn to the usage db (rate-limit + telemetry)."""
    usage_dict = (
        fiscal_assistant.last_usage.to_dict()
        if fiscal_assistant.last_usage
        else None
    )
    tools_used = [p["tool"] for p in (fiscal_assistant.last_provenance or [])]
    limiter.record_turn(
        session_id=state.get(_SESSION_ID_KEY, "unknown"),
        role="assistant",
        model=getattr(fiscal_assistant, "_model", None),
        usage_dict=usage_dict,
        elapsed_s=elapsed_s,
        tools_used=tools_used,
        stripped_markers=len(fiscal_assistant.last_stripped_markers or []),
        error=error,
        question_chars=len(question or ""),
        answer_chars=len(answer or ""),
    )


__all__ = ["render_ask_tab"]
