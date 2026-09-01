"""
Tests for preset share-link generation and restoration.

Phase 5 changed two things these tests pin, deliberately:

* emitted links carry the **stable preset id** (``preset=top-rate-39-6``), not
  the emoji display label, plus ``baseline`` / ``spec`` / ``mode`` provenance;
* the link points at the page that owns the flow (``/explore``, ``/tailor``)
  instead of ``/``.

Decoding still accepts every legacy spelling — that half must never change.
"""

from __future__ import annotations

from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

from fiscal_model.ui.share_links import (
    apply_share_query_params,
    baseline_vintage_token,
    build_share_url,
    decode_tailor_query,
    encode_tailor_share,
    parse_tailor_who,
    rewrite_legacy_query,
)


class _DummySessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class _DummyStreamlit:
    def __init__(self, query_params):
        self.query_params = query_params
        self.session_state = _DummySessionState()


def test_apply_share_query_params_for_spending_preset_primes_sidebar_once():
    st_module = _DummyStreamlit(
        {
            "analysis": "spending",
            "spending_preset": "Infrastructure Investment ($100B/yr)",
            "dynamic": "1",
            "run": "1",
        }
    )

    apply_share_query_params(st_module=st_module)

    assert st_module.session_state["sidebar_analysis_mode"] == "💰 Spending program"
    assert st_module.session_state["sidebar_spending_preset"] == "Infrastructure Investment ($100B/yr)"
    assert st_module.session_state["sidebar_setting_dynamic_scoring"] is True
    assert st_module.session_state["qs_calculate"] is True

    del st_module.session_state["qs_calculate"]
    apply_share_query_params(st_module=st_module)

    assert "qs_calculate" not in st_module.session_state


def test_apply_share_query_params_for_tax_preset_sets_preset_choice():
    st_module = _DummyStreamlit(
        {
            "analysis": "preset",
            "preset": "TCJA Full Extension",
            "dynamic": "0",
            "run": "1",
        }
    )

    apply_share_query_params(st_module=st_module)

    assert st_module.session_state["sidebar_analysis_mode"] == "📋 Tax proposal (preset)"
    assert st_module.session_state["sidebar_policy_area"] == "TCJA / Individual"
    assert st_module.session_state["sidebar_preset_choice"] == "TCJA Full Extension"
    assert st_module.session_state["sidebar_setting_dynamic_scoring"] is False


def test_apply_share_query_params_accepts_legacy_policy_key_and_list_values():
    st_module = _DummyStreamlit(
        {
            "policy": ["Biden 2025 Proposal"],
            "dynamic": ["yes"],
            "run": ["true"],
        }
    )

    apply_share_query_params(st_module=st_module)

    assert st_module.session_state["sidebar_analysis_mode"] == "📋 Tax proposal (preset)"
    assert st_module.session_state["sidebar_policy_area"] == "TCJA / Individual"
    assert st_module.session_state["sidebar_preset_choice"] == "Biden 2025 Proposal"
    assert st_module.session_state["sidebar_setting_dynamic_scoring"] is True
    assert st_module.session_state["qs_calculate"] is True


def test_apply_share_query_params_overrides_stale_sidebar_state():
    st_module = _DummyStreamlit(
        {
            "analysis": "preset",
            "preset": "TCJA Full Extension",
        }
    )
    st_module.session_state["sidebar_policy_area"] = "Climate / Energy"
    st_module.session_state["sidebar_spending_preset"] = "Infrastructure Investment ($100B/yr)"

    apply_share_query_params(st_module=st_module)

    assert st_module.session_state["sidebar_policy_area"] == "TCJA / Individual"
    assert st_module.session_state["sidebar_preset_choice"] == "TCJA Full Extension"
    assert "sidebar_spending_preset" not in st_module.session_state


def test_apply_share_query_params_for_spending_clears_tax_state():
    st_module = _DummyStreamlit(
        {
            "analysis": "spending",
            "spending_preset": "Infrastructure Investment ($100B/yr)",
        }
    )
    st_module.session_state["sidebar_policy_area"] = "Income Tax"
    st_module.session_state["sidebar_preset_choice"] = "Biden 2025 Proposal"

    apply_share_query_params(st_module=st_module)

    assert st_module.session_state["sidebar_analysis_mode"] == "💰 Spending program"
    assert st_module.session_state["sidebar_spending_preset"] == "Infrastructure Investment ($100B/yr)"
    assert "sidebar_policy_area" not in st_module.session_state
    assert "sidebar_preset_choice" not in st_module.session_state


def test_build_share_url_for_tax_preset_emits_the_stable_id_on_explore():
    result_data = {
        "policy_name": "Biden 2025 Proposal",
        "result": SimpleNamespace(dynamic_effects=object()),
        "is_spending": False,
    }

    share_url = build_share_url(result_data=result_data, public_app_url="https://example.com")
    parsed = urlparse(share_url)
    params = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "example.com"
    assert parsed.path == "/explore"
    assert params["analysis"] == ["preset"]
    # The emoji label must never reach a URL: it moves whenever a score is
    # refreshed, the id is frozen.
    assert params["preset"] == ["top-rate-39-6"]
    assert params["dynamic"] == ["1"]
    assert params["run"] == ["1"]


def test_build_share_url_carries_baseline_spec_and_mode_from_the_result():
    scored = SimpleNamespace(
        baseline_vintage="CBO Feb 2026",
        policy_spec_hash="abc123def456",
        mode="dynamic",
    )
    share_url = build_share_url(
        result_data={
            "policy_name": "🏛️ TCJA Full Extension (CBO: $4.6T)",
            "result": SimpleNamespace(dynamic_effects=object()),
            "is_spending": False,
        },
        public_app_url="https://example.com",
        scored=scored,
    )
    params = parse_qs(urlparse(share_url).query)

    assert params["preset"] == ["tcja-full-extension"]
    assert params["baseline"] == ["feb2026"]
    assert params["spec"] == ["abc123def456"]
    assert params["mode"] == ["dynamic"]


def test_share_url_baseline_token_and_export_vintage_share_one_source():
    """§9.10: the URL cannot claim a vintage the CSV beside it disagrees with."""
    from components.results import resolve_baseline_vintage

    assert baseline_vintage_token(resolve_baseline_vintage()) == baseline_vintage_token()
    assert baseline_vintage_token("CBO Feb 2026") == "feb2026"
    assert baseline_vintage_token("Jan 2025") == "jan2025"


def test_share_url_round_trips_back_onto_the_preset():
    label = "🏛️ TCJA Full Extension (CBO: $4.6T)"
    share_url = build_share_url(
        result_data={
            "policy_name": label,
            "result": SimpleNamespace(dynamic_effects=None),
            "is_spending": False,
        },
        public_app_url="https://example.com",
    )
    params = {k: v[0] for k, v in parse_qs(urlparse(share_url).query).items()}

    st_module = _DummyStreamlit(params)
    assert apply_share_query_params(st_module=st_module) is None
    assert st_module.session_state["sidebar_policy_area"] == "TCJA / Individual"
    assert st_module.session_state["sidebar_preset_choice"] == "TCJA Full Extension"
    assert st_module.session_state["qs_calculate"] is True


def test_build_share_url_for_spending_preset_points_at_tailor():
    result_data = {
        "selected_spending_preset": "Infrastructure Investment ($100B/yr)",
        "result": SimpleNamespace(dynamic_effects=None),
        "is_spending": True,
    }

    share_url = build_share_url(result_data=result_data, public_app_url="https://example.com")
    parsed = urlparse(share_url)
    params = parse_qs(parsed.query)

    assert parsed.path == "/tailor"
    assert params["analysis"] == ["spending"]
    assert params["type"] == ["spending"]
    assert params["spending_preset"] == ["Infrastructure Investment ($100B/yr)"]
    assert params["dynamic"] == ["0"]


def test_build_share_url_returns_none_for_custom_or_microsim_results():
    assert build_share_url(
        result_data={"policy_name": "Custom Policy", "result": SimpleNamespace(dynamic_effects=None)},
        public_app_url="https://example.com",
    ) is None
    assert build_share_url(
        result_data={"is_spending": True, "selected_spending_preset": "Custom program"},
        public_app_url="https://example.com",
    ) is None
    assert build_share_url(
        result_data={"is_microsim": True},
        public_app_url="https://example.com",
    ) is None
    # A user-named generic run with no scored policy object attached carries
    # nothing to describe, so it still has no link.
    assert build_share_url(
        result_data={
            "policy_name": "My own 3pp surtax",
            "result": SimpleNamespace(dynamic_effects=None),
        },
        public_app_url="https://example.com",
    ) is None
    # Nor does a policy type Tailor has no form for (payroll, estate, …).
    assert build_share_url(
        result_data={
            "policy_name": "My own payroll change",
            "result": SimpleNamespace(dynamic_effects=None),
            "policy": _generic_policy(policy_type="payroll_tax"),
        },
        public_app_url="https://example.com",
    ) is None


def _generic_policy(
    *,
    policy_type: str = "income_tax",
    rate_change: float = 0.03,
    threshold: float = 400_000,
    phase_in_years: int = 2,
    duration_years: int = 10,
):
    """Stand-in for the scored ``TaxPolicy`` a generic Tailor run produces."""
    return SimpleNamespace(
        policy_type=SimpleNamespace(value=policy_type),
        rate_change=rate_change,
        affected_income_threshold=threshold,
        phase_in_years=phase_in_years,
        duration_years=duration_years,
    )


def test_generic_tailor_run_emits_a_tailor_share_link():
    """Phase 5 leftover: a custom run had no share link at all."""
    url = build_share_url(
        result_data={
            "policy_name": "My own 3pp surtax",
            "result": SimpleNamespace(dynamic_effects=None),
            "policy": _generic_policy(),
        },
        public_app_url="https://example.com",
        scored=SimpleNamespace(
            baseline_vintage="CBO February 2026",
            policy_spec_hash="abc123",
            mode="conventional",
        ),
    )
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    assert parsed.path == "/tailor"
    assert params["type"] == ["income"]
    assert params["rate"] == ["3"]
    assert params["who"] == ["top400k"]
    assert params["phase"] == ["2"]
    assert params["duration"] == ["10"]
    assert params["run"] == ["1"]
    # Same provenance stamps a preset link carries.
    assert params["baseline"] == [baseline_vintage_token("CBO February 2026")]
    assert params["spec"] == ["abc123"]
    assert params["mode"] == ["conventional"]


def test_generic_tailor_share_link_round_trips():
    """The link the result panel emits re-creates the run it came from."""
    url = build_share_url(
        result_data={
            "policy_name": "Corporate rate to 28%",
            "result": SimpleNamespace(dynamic_effects=object()),
            "policy": _generic_policy(
                policy_type="corporate_tax",
                rate_change=0.07,
                threshold=0,
                phase_in_years=1,
                duration_years=8,
            ),
        },
        public_app_url="https://example.com",
    )
    decoded = decode_tailor_query(parse_qs(urlparse(url).query))
    assert decoded["kind"] == "Corporate"
    assert decoded["rate"] == 7
    assert decoded["threshold"] == 0
    assert decoded["phase"] == 1
    assert decoded["duration"] == 8
    assert decoded["dynamic"] is True
    assert decoded["run"] is True
    assert decoded["has_params"] is True


# ---------------------------------------------------------------------------
# Decoding accepts every legacy spelling (this half must never change)
# ---------------------------------------------------------------------------


def test_apply_share_query_params_accepts_a_stable_id():
    st_module = _DummyStreamlit({"preset": "tcja-full-extension", "run": "1"})

    assert apply_share_query_params(st_module=st_module) is None
    assert st_module.session_state["sidebar_policy_area"] == "TCJA / Individual"
    assert st_module.session_state["sidebar_preset_choice"] == "TCJA Full Extension"


def test_apply_share_query_params_accepts_the_url_encoded_emoji_label():
    encoded = "%F0%9F%8F%9B%EF%B8%8F+TCJA+Full+Extension+%28CBO%3A+%244.6T%29"
    st_module = _DummyStreamlit({"analysis": "preset", "preset": encoded})

    apply_share_query_params(st_module=st_module)
    assert st_module.session_state["sidebar_preset_choice"] == "TCJA Full Extension"


def test_unknown_preset_token_is_reported_not_crashed():
    st_module = _DummyStreamlit({"preset": "policy-that-was-renamed", "run": "1"})

    unresolved = apply_share_query_params(st_module=st_module)

    assert unresolved == "policy-that-was-renamed"
    # Nothing was silently substituted for it...
    assert "sidebar_preset_choice" not in st_module.session_state
    # ...but the rest of the link still applied.
    assert st_module.session_state["qs_calculate"] is True
    # A rerun re-reports it without re-arming the auto-run.
    del st_module.session_state["qs_calculate"]
    assert apply_share_query_params(st_module=st_module) == "policy-that-was-renamed"
    assert "qs_calculate" not in st_module.session_state


# ---------------------------------------------------------------------------
# /tailor query contract
# ---------------------------------------------------------------------------


def test_tailor_who_enum_and_shorthands():
    assert parse_tailor_who("top400k") == 400_000
    assert parse_tailor_who("all") == 0
    assert parse_tailor_who("top1m") == 1_000_000
    assert parse_tailor_who("400000") == 400_000
    assert parse_tailor_who("$400,000") == 400_000
    assert parse_tailor_who("1M") == 1_000_000
    assert parse_tailor_who("not-a-threshold") is None
    assert parse_tailor_who(None) is None


def test_decode_tailor_query_reads_the_documented_contract():
    request = decode_tailor_query(
        {"type": "income", "rate": "2", "who": "top400k", "phase": "1", "duration": "10", "run": "1"}
    )

    assert request["kind"] == "Income"
    assert request["rate"] == 2.0
    assert request["threshold"] == 400_000
    assert request["phase"] == 1
    assert request["duration"] == 10
    assert request["run"] is True
    assert request["has_params"] is True


def test_decode_tailor_query_clamps_phase_in_to_the_engine_contract():
    """Chip ⑨: ``phase_in_years >= 1``; a link may not smuggle 0 past it."""
    assert decode_tailor_query({"phase": "0"})["phase"] == 1
    assert decode_tailor_query({"phase": "99"})["phase"] == 5


def test_decode_tailor_query_is_empty_for_a_bare_url():
    request = decode_tailor_query({})
    assert request["has_params"] is False
    assert request["kind"] is None and request["rate"] is None


def test_tailor_share_url_round_trips():
    url = encode_tailor_share(
        kind="Capital gains",
        rate=-1.5,
        threshold=1_000_000,
        phase=2,
        duration=8,
        public_app_url="https://example.com",
    )
    parsed = urlparse(url)
    assert parsed.path == "/tailor"

    request = decode_tailor_query({k: v[0] for k, v in parse_qs(parsed.query).items()})
    assert request["kind"] == "Capital gains"
    assert request["rate"] == -1.5
    assert request["threshold"] == 1_000_000
    assert request["phase"] == 2
    assert request["duration"] == 8


# ---------------------------------------------------------------------------
# Legacy URL rewriting (the pure half of app._apply_legacy_url_shim)
# ---------------------------------------------------------------------------


def test_rewrite_legacy_preset_link_to_the_explore_contract():
    url_path, params = rewrite_legacy_query(
        {
            "analysis": "preset",
            "preset": "🏛️ TCJA Full Extension (CBO: $4.6T)",
            "dynamic": "0",
            "run": "1",
        }
    )

    assert url_path == "explore"
    assert params == {"dynamic": "0", "run": "1", "preset": "tcja-full-extension"}


def test_rewrite_legacy_policy_and_spending_links():
    assert rewrite_legacy_query({"policy": "Biden 2025 Proposal", "run": "yes"}) == (
        "explore",
        {"dynamic": "0", "run": "1", "preset": "top-rate-39-6"},
    )
    assert rewrite_legacy_query(
        {"analysis": "spending", "spending_preset": "Infrastructure Investment ($100B/yr)"}
    ) == (
        "tailor",
        {
            "dynamic": "0",
            "type": "spending",
            "spending_preset": "Infrastructure Investment ($100B/yr)",
        },
    )
    assert rewrite_legacy_query({"analysis": "custom", "dynamic": "1"}) == (
        "tailor",
        {"dynamic": "1", "type": "income"},
    )


def test_rewrite_legacy_preserves_the_admin_gate_and_unknown_presets():
    url_path, params = rewrite_legacy_query(
        {"analysis": "preset", "preset": "renamed-policy", "admin": "s3cret"}
    )
    assert url_path == "explore"
    assert params["admin"] == "s3cret"
    assert params["preset"] == "renamed-policy"


def test_rewrite_legacy_leaves_new_contract_and_ask_urls_alone():
    assert rewrite_legacy_query({"preset": "tcja-full-extension", "run": "1"}) is None
    assert rewrite_legacy_query({"q": "what is the deficit?"}) is None
    assert rewrite_legacy_query({"mode": "classroom"}) is None
    assert rewrite_legacy_query({}) is None
