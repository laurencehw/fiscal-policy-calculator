"""
Tests for the Package Studio tab.

The composer and translator live behind the two lazy bridges
``_compose_and_score`` / ``_translate_goal_text``; every test here swaps in a
lightweight fake so the tab is exercised without the scoring engine (or an API
key). Streamlit is replaced by the dummy-module stub pattern used across the
UI tests.
"""

from __future__ import annotations

import sys
import types

import pytest

from fiscal_model.composer.contracts import MixComponent, PolicyMix, ScoredMix
from fiscal_model.composer.goal_spec import CANNED_GOAL_SPECS, GoalSpec
from fiscal_model.policy_status import PolicyStatus
from fiscal_model.ui.tabs import package_studio as ps

# ------------------------------------------------------------------
# Streamlit stub
# ------------------------------------------------------------------


class _DummyContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        del exc_type, exc, tb
        return False


class _DummySessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class _DummyStreamlit:
    """Records every rendered element so assertions can inspect the output."""

    def __init__(
        self,
        *,
        text_area_value: str = "",
        selectbox_value: str | None = None,
        button_returns: bool = False,
    ) -> None:
        self.session_state = _DummySessionState()
        self._text_area_value = text_area_value
        self._selectbox_value = selectbox_value
        self._button_returns = button_returns

        self.headers: list[str] = []
        self.subheaders: list[str] = []
        self.markdowns: list[str] = []
        self.captions: list[str] = []
        self.infos: list[str] = []
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self.metrics: list[tuple] = []
        self.dataframes: list = []
        self.charts: list = []
        self.spinners: list[str] = []

    # --- text output -------------------------------------------------
    def header(self, text, *args, **kwargs):
        del args, kwargs
        self.headers.append(text)

    def subheader(self, text, *args, **kwargs):
        del args, kwargs
        self.subheaders.append(text)

    def markdown(self, text="", *args, **kwargs):
        del args, kwargs
        self.markdowns.append(text)

    def caption(self, text="", *args, **kwargs):
        del args, kwargs
        self.captions.append(text)

    def info(self, text="", *args, **kwargs):
        del args, kwargs
        self.infos.append(text)

    def warning(self, text="", *args, **kwargs):
        del args, kwargs
        self.warnings.append(text)

    def error(self, text="", *args, **kwargs):
        del args, kwargs
        self.errors.append(text)

    # --- widgets -----------------------------------------------------
    def text_area(self, label, *args, **kwargs):
        del label, args, kwargs
        return self._text_area_value

    def selectbox(self, label, options, *args, **kwargs):
        del label, args, kwargs
        if self._selectbox_value is not None:
            return self._selectbox_value
        return next(iter(options))

    def button(self, *args, **kwargs):
        del args, kwargs
        return self._button_returns

    def metric(self, label, value, *args, **kwargs):
        del args
        self.metrics.append((label, value, kwargs.get("delta")))

    def dataframe(self, data, *args, **kwargs):
        del args, kwargs
        self.dataframes.append(data)

    def plotly_chart(self, figure, *args, **kwargs):
        del args, kwargs
        self.charts.append(figure)

    # --- layout ------------------------------------------------------
    def columns(self, spec, *args, **kwargs):
        del args, kwargs
        n = spec if isinstance(spec, int) else len(spec)
        return [_DummyContext() for _ in range(n)]

    def expander(self, *args, **kwargs):
        del args, kwargs
        return _DummyContext()

    def spinner(self, text="", *args, **kwargs):
        del args, kwargs
        self.spinners.append(text)
        return _DummyContext()

    # --- convenience for assertions ----------------------------------
    @property
    def all_text(self) -> list[str]:
        return (
            self.headers
            + self.subheaders
            + self.markdowns
            + self.captions
            + self.infos
            + self.warnings
            + self.errors
        )


# ------------------------------------------------------------------
# Fixtures / builders
# ------------------------------------------------------------------


def _make_scored_mix(
    name: str = "Top-heavy",
    total: float = -1_250.0,
    *,
    with_badge: bool = True,
    with_status: bool = True,
    caveats: tuple[str, ...] = (
        "Sized to a $400K threshold; the composer did not re-optimize it.",
    ),
) -> ScoredMix:
    badge = (
        {
            "rating": "Excellent",
            "signed_pct": -1.2,
            "official": -1_347.0,
            "model": -1_397.0,
            "source": "CBO",
            "url": "https://example.gov/score",
            "icon": "🟢",
        }
        if with_badge
        else None
    )
    components = (
        MixComponent(
            label="🏢 Biden Corporate 28%",
            kind="revenue",
            preset_name="🏢 Biden Corporate 28% (CBO: -$1.35T)",
            ten_year_billions=-1_347.0,
            annual_billions=-134.7,
            validation_badge=badge,
            policy_status=(
                PolicyStatus("proposed", "Green Book proposal; not enacted.")
                if with_status
                else None
            ),
            tier="calibrated",
        ),
        MixComponent(
            label="Infrastructure investment",
            kind="spending",
            preset_name=None,
            ten_year_billions=600.0,
            annual_billions=60.0,
            tier="spending",
        ),
    )
    years = tuple(range(2026, 2036))
    path = tuple(total / len(years) for _ in years)
    return ScoredMix(
        mix=PolicyMix(
            name=name,
            rationale="Raises on the corporate side to fund public investment.",
            components=components,
        ),
        years=years,
        deficit_path_billions=path,
        ten_year_deficit_billions=total,
        revenue_10yr_billions=-1_347.0,
        spending_10yr_billions=600.0,
        revenue_distribution_rows=(
            {"Income Group": "Bottom quintile", "Avg Tax Change ($)": -5.0},
            {"Income Group": "Top 1%", "Avg Tax Change ($)": -18_642.0},
        ),
        caveats=caveats,
    )


@pytest.fixture
def no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture
def with_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")


def _fake_compose(mixes):
    def _compose(spec, n_mixes=3):
        del spec, n_mixes
        return list(mixes)

    return _compose


# ------------------------------------------------------------------
# Rendering smoke
# ------------------------------------------------------------------


def test_renders_without_crashing_and_shows_maturity_framing(no_api_key):
    st = _DummyStreamlit()

    ps.render_package_studio_tab(st)

    assert any("Package Studio" in h for h in st.headers)
    assert ps.MATURITY_CAPTION in st.captions
    # Nothing composed yet — the tab prompts instead of rendering results.
    assert st.metrics == []


def test_missing_api_key_shows_canned_fallback(no_api_key):
    st = _DummyStreamlit()

    ps.render_package_studio_tab(st)

    key_notice = [m for m in st.infos if "ANTHROPIC_API_KEY" in m]
    assert key_notice, "expected a plain statement that free text needs a key"
    assert "canned" in key_notice[0].lower()


def test_canned_philosophies_are_offered_as_selectbox_options(no_api_key):
    seen: dict[str, list] = {}

    class _CapturingStreamlit(_DummyStreamlit):
        def selectbox(self, label, options, *args, **kwargs):
            seen["options"] = list(options)
            return super().selectbox(label, options, *args, **kwargs)

    st = _CapturingStreamlit()
    ps.render_package_studio_tab(st)

    assert seen["options"] == list(CANNED_GOAL_SPECS)


# ------------------------------------------------------------------
# Composition
# ------------------------------------------------------------------


def test_compose_from_canned_choice_renders_one_metric_per_mix(
    no_api_key, monkeypatch
):
    mixes = [
        _make_scored_mix("Top-heavy", -1_250.0),
        _make_scored_mix("Broader base", 320.0),
    ]
    monkeypatch.setattr(ps, "_compose_and_score", _fake_compose(mixes))

    st = _DummyStreamlit(selectbox_value="Deficit hawk", button_returns=True)
    ps.render_package_studio_tab(st)

    labels = [label for label, _value, _delta in st.metrics]
    assert labels == ["10-Year Deficit Impact"] * len(mixes)
    values = [value for _label, value, _delta in st.metrics]
    assert values == ["$-1,250B", "$+320B"]
    # Sign framing is explicit, not left to the reader.
    deltas = [delta for _l, _v, delta in st.metrics]
    assert deltas == ["Reduces the deficit", "Increases the deficit"]
    assert any("increase the deficit" in c for c in st.captions)
    # Per mix: components table, the chart's accessible data table, and the
    # revenue-side distribution table.
    assert len(st.dataframes) == 3 * len(mixes)
    assert len(st.charts) == len(mixes)
    assert st.spinners, "compose should run behind a spinner"


def test_honesty_captions_always_render_for_each_mix(no_api_key, monkeypatch):
    mixes = [_make_scored_mix("Top-heavy", -1_250.0)]
    monkeypatch.setattr(ps, "_compose_and_score", _fake_compose(mixes))

    st = _DummyStreamlit(button_returns=True)
    ps.render_package_studio_tab(st)

    assert ps.CAVEAT_INTERACTIONS in st.captions
    assert ps.CAVEAT_REVENUE_ONLY in st.captions
    # The mix's own caveats are rendered too, never swallowed.
    assert any("did not re-optimize" in m for m in st.markdowns)


def test_caveat_captions_render_even_when_mix_has_no_caveats(
    no_api_key, monkeypatch
):
    mixes = [_make_scored_mix("Top-heavy", -1_250.0, caveats=())]
    monkeypatch.setattr(ps, "_compose_and_score", _fake_compose(mixes))

    st = _DummyStreamlit(button_returns=True)
    ps.render_package_studio_tab(st)

    assert ps.CAVEAT_INTERACTIONS in st.captions
    assert ps.CAVEAT_REVENUE_ONLY in st.captions


def test_components_table_carries_tier_status_and_benchmark(
    no_api_key, monkeypatch
):
    mixes = [_make_scored_mix("Top-heavy", -1_250.0)]
    monkeypatch.setattr(ps, "_compose_and_score", _fake_compose(mixes))

    st = _DummyStreamlit(button_returns=True)
    ps.render_package_studio_tab(st)

    components = st.dataframes[0].to_dict("records")
    assert components[0]["Tier"] == "🎯 Calibrated preset"
    assert components[0]["Status"].startswith("🔵")
    assert "Calibrated vs CBO" in components[0]["Benchmark"]
    assert components[1]["Tier"] == "🧾 Uncalibrated spending build"
    # Untracked components render blank chips rather than invented ones.
    assert components[1]["Status"] == ""
    assert components[1]["Benchmark"] == ""


def test_chart_ships_accessible_description_and_data_table(
    no_api_key, monkeypatch
):
    mixes = [_make_scored_mix("Top-heavy", -1_250.0)]
    monkeypatch.setattr(ps, "_compose_and_score", _fake_compose(mixes))

    st = _DummyStreamlit(button_returns=True)
    ps.render_package_studio_tab(st)

    assert len(st.charts) == 1
    # render_accessible_chart emits an sr-only description block…
    assert any('class="sr-only"' in m for m in st.markdowns)
    # …and a caption describing the chart in words.
    assert any("Bar chart" in c for c in st.captions)


# ------------------------------------------------------------------
# Translation path
# ------------------------------------------------------------------


def test_free_text_is_translated_when_a_key_is_present(with_api_key, monkeypatch):
    seen: dict[str, object] = {}
    spec = GoalSpec(revenue_philosophy="progressive", deficit_stance="neutral")

    def _fake_translate(text):
        seen["text"] = text
        return spec, ""

    def _fake_compose(spec_in, n_mixes=3):
        seen["spec"] = spec_in
        del n_mixes
        return [_make_scored_mix()]

    monkeypatch.setattr(ps, "_translate_goal_text", _fake_translate)
    monkeypatch.setattr(ps, "_compose_and_score", _fake_compose)

    st = _DummyStreamlit(
        text_area_value="Tax the top, build transit.", button_returns=True
    )
    ps.render_package_studio_tab(st)

    assert seen["text"] == "Tax the top, build transit."
    assert seen["spec"] is spec
    assert len(st.metrics) == 1


def test_translation_refusal_falls_back_to_canned_selection(
    with_api_key, monkeypatch
):
    monkeypatch.setattr(
        ps,
        "_translate_goal_text",
        lambda text: (None, "that description doesn't name a revenue side"),
    )
    composed: dict[str, object] = {}

    def _fake_compose(spec_in, n_mixes=3):
        composed["spec"] = spec_in
        del n_mixes
        return [_make_scored_mix()]

    monkeypatch.setattr(ps, "_compose_and_score", _fake_compose)

    st = _DummyStreamlit(
        text_area_value="do something good",
        selectbox_value="Progressive investment",
        button_returns=True,
    )
    ps.render_package_studio_tab(st)

    # Calm info message carrying the reason, not an error.
    assert st.errors == []
    assert any("doesn't name a revenue side" in m for m in st.infos)
    # And it actually composed the canned spec.
    assert composed["spec"] is CANNED_GOAL_SPECS["Progressive investment"]
    assert len(st.metrics) == 1


def test_translation_exception_is_contained(with_api_key, monkeypatch):
    def _boom(text):
        del text
        raise RuntimeError("translator offline")

    monkeypatch.setattr(ps, "_translate_goal_text", _boom)
    monkeypatch.setattr(ps, "_compose_and_score", _fake_compose([_make_scored_mix()]))

    st = _DummyStreamlit(text_area_value="anything", button_returns=True)
    ps.render_package_studio_tab(st)

    assert any("translator offline" in m for m in st.infos)
    assert len(st.metrics) == 1


def test_free_text_ignored_without_a_key(no_api_key, monkeypatch):
    def _should_not_run(text):
        raise AssertionError("translation must not run without an API key")

    monkeypatch.setattr(ps, "_translate_goal_text", _should_not_run)
    monkeypatch.setattr(ps, "_compose_and_score", _fake_compose([_make_scored_mix()]))

    st = _DummyStreamlit(text_area_value="tax the rich", button_returns=True)
    ps.render_package_studio_tab(st)

    assert len(st.metrics) == 1


def test_compose_failure_reports_without_crashing(no_api_key, monkeypatch):
    def _boom(spec, n_mixes=3):
        del spec, n_mixes
        raise ValueError("no preset covers that goal")

    monkeypatch.setattr(ps, "_compose_and_score", _boom)

    st = _DummyStreamlit(button_returns=True)
    ps.render_package_studio_tab(st)

    assert any("no preset covers that goal" in e for e in st.errors)
    assert st.metrics == []


def test_missing_composer_module_is_reported_calmly(no_api_key, monkeypatch):
    def _missing(spec, n_mixes=3):
        del spec, n_mixes
        raise ModuleNotFoundError("No module named 'fiscal_model.composer.composer'")

    monkeypatch.setattr(ps, "_compose_and_score", _missing)

    st = _DummyStreamlit(button_returns=True)
    ps.render_package_studio_tab(st)

    assert any("composer isn't available" in e for e in st.errors)
    assert st.metrics == []


# ------------------------------------------------------------------
# Caching
# ------------------------------------------------------------------


def test_result_is_cached_by_input_hash_across_reruns(no_api_key, monkeypatch):
    calls: list[int] = []

    def _counting_compose(spec, n_mixes=3):
        del spec, n_mixes
        calls.append(1)
        return [_make_scored_mix()]

    monkeypatch.setattr(ps, "_compose_and_score", _counting_compose)

    st = _DummyStreamlit(selectbox_value="Deficit hawk", button_returns=True)
    ps.render_package_studio_tab(st)
    assert len(calls) == 1
    assert ps._RESULT_KEY in st.session_state

    # Second run: same session state, same input, button pressed again.
    ps.render_package_studio_tab(st)
    assert len(calls) == 1, "same input should reuse the cached mixes"

    # A rerun with no button press still renders the cached result.
    st_rerun = _DummyStreamlit(selectbox_value="Deficit hawk")
    st_rerun.session_state = st.session_state
    ps.render_package_studio_tab(st_rerun)
    assert len(calls) == 1
    assert len(st_rerun.metrics) == 1


def test_changing_the_canned_choice_recomposes(no_api_key, monkeypatch):
    calls: list[str] = []

    def _counting_compose(spec, n_mixes=3):
        del n_mixes
        calls.append(spec.revenue_philosophy)
        return [_make_scored_mix()]

    monkeypatch.setattr(ps, "_compose_and_score", _counting_compose)

    st = _DummyStreamlit(selectbox_value="Deficit hawk", button_returns=True)
    ps.render_package_studio_tab(st)

    st_next = _DummyStreamlit(
        selectbox_value="Progressive investment", button_returns=True
    )
    st_next.session_state = st.session_state
    ps.render_package_studio_tab(st_next)

    assert calls == ["mixed", "progressive"]


def test_input_hash_distinguishes_text_from_canned():
    assert ps._input_hash("text", "Deficit hawk") != ps._input_hash(
        "canned", "Deficit hawk"
    )
    assert ps._input_hash("canned", "Deficit hawk") == ps._input_hash(
        "canned", "Deficit hawk"
    )


# ------------------------------------------------------------------
# Dollar escaping
# ------------------------------------------------------------------


def test_dollar_amounts_in_markdown_are_escaped(no_api_key, monkeypatch):
    mixes = [
        _make_scored_mix(
            "Top-heavy",
            -1_250.0,
            caveats=("Sized against a $400K threshold; not re-optimized.",),
        )
    ]
    monkeypatch.setattr(ps, "_compose_and_score", _fake_compose(mixes))

    st = _DummyStreamlit(button_returns=True)
    ps.render_package_studio_tab(st)

    # The sr-only block is raw HTML (already html-escaped by the a11y helper),
    # not markdown prose — everything else must carry escaped currency.
    dollar_markdowns = [
        m for m in st.markdowns if "$" in m and "sr-only" not in m
    ]
    assert dollar_markdowns, "expected currency text in the rendered markdown"
    for text in dollar_markdowns:
        # Every `$` must be backslash-escaped: two bare ones on a line make
        # Streamlit render the span between them as LaTeX math.
        for idx, char in enumerate(text):
            if char == "$":
                assert idx > 0 and text[idx - 1] == "\\", (
                    f"unescaped currency in markdown: {text!r}"
                )


def test_dataframe_currency_is_left_unescaped(no_api_key, monkeypatch):
    """``st.dataframe`` renders raw text — backslashes there would be visible."""
    mixes = [_make_scored_mix("Top-heavy", -1_250.0)]
    monkeypatch.setattr(ps, "_compose_and_score", _fake_compose(mixes))

    st = _DummyStreamlit(button_returns=True)
    ps.render_package_studio_tab(st)

    components = st.dataframes[0].to_dict("records")
    assert components[0]["10-yr $B"] == "$-1,347B"


# ------------------------------------------------------------------
# Contract wiring with the sibling modules
# ------------------------------------------------------------------


def test_lazy_bridges_call_the_agreed_composer_api(monkeypatch):
    """The bridges must import the exact names the composer agents ship."""
    seen: dict[str, object] = {}

    composer_mod = types.ModuleType("fiscal_model.composer.composer")

    def compose_and_score(spec, *, n_mixes=3):
        seen["spec"] = spec
        seen["n_mixes"] = n_mixes
        return ["mix"]

    composer_mod.compose_and_score = compose_and_score

    translate_mod = types.ModuleType("fiscal_model.composer.translate")

    def translate_goal_text(text):
        seen["text"] = text
        return None, "stub"

    translate_mod.translate_goal_text = translate_goal_text

    monkeypatch.setitem(sys.modules, "fiscal_model.composer.composer", composer_mod)
    monkeypatch.setitem(sys.modules, "fiscal_model.composer.translate", translate_mod)

    spec = CANNED_GOAL_SPECS["Deficit hawk"]
    assert ps._compose_and_score(spec, n_mixes=2) == ["mix"]
    assert seen["spec"] is spec
    assert seen["n_mixes"] == 2
    assert ps._translate_goal_text("hello") == (None, "stub")
    assert seen["text"] == "hello"
