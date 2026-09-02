"""
Tests for Package Studio — now Build's "Start from your values" panel.

``DECISIONS.md`` #3 folded Studio into Build and retired its page and its tab
module (``fiscal_model/ui/tabs/package_studio.py``, ``app_pages/studio.py``).
The *pipeline* survived the move intact and is still covered by
``tests/test_composer.py`` + ``tests/test_composer_translate.py``; this file
follows the surface, which now lives in :mod:`app_pages.build`.

The two lazy bridges came with it. Studio carried ``_translate_goal_text`` /
``_compose_and_score``; the panel carries ``_translate_values_text`` /
``_select_package``, speaking the values-vector contract instead of the
GoalSpec one. Every test here swaps in a lightweight fake through those two
names, so the panel is exercised without the scoring engine or an API key.

The deterministic selector itself is tested in ``tests/test_values_selector.py``.
"""

from __future__ import annotations

import pytest

from app_pages import build
from fiscal_model.composer.composer import CatalogPolicy, ValuesPackage, ValuesPick
from fiscal_model.composer.values_schema import ValuesVector
from fiscal_model.ui.session_state import (
    KEY_BUILD_MODE,
    KEY_BUILD_TARGET_PCT,
    KEY_VALUES_ARCHETYPE,
    KEY_VALUES_PENDING_LOAD,
    KEY_VALUES_PROTECTED,
    KEY_VALUES_READING,
    KEY_VALUES_TARGET_PCT,
    KEY_VALUES_TEXT,
    VALUES_DIMENSION_KEYS,
)

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
    """Records every rendered element so assertions can inspect the output.

    Widgets read their value straight out of ``session_state``, which is how
    the real panel behaves: the dials *are* the vector, so a test that seeds a
    key is seeding the reader's position exactly as a drag would.
    """

    def __init__(self, *, clicked: set[str] | None = None, secrets=None) -> None:
        self.session_state = _DummySessionState()
        self.clicked = set(clicked or ())
        self.secrets = secrets

        self.markdowns: list[str] = []
        self.captions: list[str] = []
        self.infos: list[str] = []
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self.codes: list[str] = []
        self.sliders: list[str] = []
        self.text_areas: list[str] = []
        self.multiselects: list[str] = []
        self.buttons: list[str] = []
        self.expanders: list[str] = []
        self.reruns = 0

    # --- text output -------------------------------------------------
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

    def code(self, text="", *args, **kwargs):
        del args, kwargs
        self.codes.append(text)

    # --- widgets -----------------------------------------------------
    def slider(self, label, *args, **kwargs):
        self.sliders.append(label)
        del args
        key = kwargs.get("key")
        return self.session_state.get(key)

    def multiselect(self, label, *args, **kwargs):
        self.multiselects.append(label)
        del args
        return self.session_state.get(kwargs.get("key")) or []

    def text_area(self, label, *args, **kwargs):
        self.text_areas.append(label)
        del args
        return self.session_state.get(kwargs.get("key"), "")

    def button(self, label="", *args, **kwargs):
        del args
        self.buttons.append(label)
        return kwargs.get("key") in self.clicked

    # --- layout ------------------------------------------------------
    def columns(self, spec, *args, **kwargs):
        del args, kwargs
        n = spec if isinstance(spec, int) else len(spec)
        return [_DummyContext() for _ in range(n)]

    def container(self, *args, **kwargs):
        del args, kwargs
        return _DummyContext()

    def expander(self, label="", *args, **kwargs):
        del args, kwargs
        self.expanders.append(label)
        return _DummyContext()

    def popover(self, *args, **kwargs):
        del args, kwargs
        return _DummyContext()

    def spinner(self, text="", *args, **kwargs):
        del text, args, kwargs
        return _DummyContext()

    def rerun(self):
        self.reruns += 1

    # --- convenience for assertions ----------------------------------
    @property
    def all_text(self) -> list[str]:
        return (
            self.markdowns + self.captions + self.infos + self.warnings + self.errors
        )


class _Deps:
    """The two attributes the panel path touches on ``AppDependencies``."""

    def __init__(self):
        from fiscal_model.app_data import CBO_SCORE_MAP

        self.CBO_SCORE_MAP = CBO_SCORE_MAP


# ------------------------------------------------------------------
# Fixtures / builders
# ------------------------------------------------------------------


@pytest.fixture
def no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture
def with_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")


def _fake_package(vector: ValuesVector | None = None) -> ValuesPackage:
    vector = vector or ValuesVector()
    return ValuesPackage(
        vector=vector,
        picks=(
            ValuesPick(
                policy_id="ss-cap-eliminate",
                label="Eliminate SS Cap",
                score=-3_200.0,
                area="Payroll / Social Security",
                why="Eliminate SS Cap closes 18% of the gap on its own.",
                alignment=1.5,
                tags={"direction": "raise_revenue", "progressivity": "strong_progressive"},
            ),
            ValuesPick(
                policy_id="corporate-28pct",
                label="Biden Corporate 28%",
                score=-1_347.0,
                area="Corporate",
                why="Biden Corporate 28% closes 8% of the gap on its own.",
                alignment=0.7,
            ),
        ),
        gap_billions=17_896.0,
        total_billions=-4_547.0,
    )


def _stub_selector(monkeypatch, package: ValuesPackage | None = None) -> list:
    """Swap the selector bridge for a fake, recording every call."""
    calls: list = []
    result = package or _fake_package()

    def _fake(vector, *, rationale_template=None):
        calls.append((vector, rationale_template))
        return _fake_package(vector) if package is None else result

    monkeypatch.setattr(build, "_select_package", _fake)
    return calls


def _forbid_translation(monkeypatch) -> None:
    """Any LLM call from this point is a test failure, not a slow test."""

    def _boom(*args, **kwargs):
        raise AssertionError("the selector must never call the translator")

    monkeypatch.setattr(build, "_translate_values_text", _boom)


# ------------------------------------------------------------------
# Offline archetype path
# ------------------------------------------------------------------


def test_panel_renders_offline_with_cards_and_a_package(no_api_key, monkeypatch):
    """No API key: five cards, a package, and no free-text box."""
    _forbid_translation(monkeypatch)
    st = _DummyStreamlit()

    build.render_values_panel(_Deps(), lambda ids: None, st_module=st)

    from fiscal_model.composer.archetypes import load_archetypes

    for archetype in load_archetypes().values():
        assert any(archetype.name in text for text in st.all_text)
        assert any(archetype.one_line in text for text in st.all_text)
    assert st.text_areas == [], "the free-text box must be hidden without a key"
    assert any("needs an" in text and "ANTHROPIC_API_KEY" in text for text in st.captions)
    # A real package, with a why sentence on every row.
    assert any("of target" in text for text in st.all_text)
    assert any("closes" in text or "of the gap" in text for text in st.captions)


def test_panel_states_the_starting_point_notice(no_api_key, monkeypatch):
    _forbid_translation(monkeypatch)
    st = _DummyStreamlit()

    build.render_values_panel(_Deps(), lambda ids: None, st_module=st)

    assert any("starting point, not a verdict" in text for text in st.all_text)
    assert any("deterministic from tags" in text for text in st.captions)


def test_clicking_a_card_writes_that_archetypes_vector(no_api_key, monkeypatch):
    _forbid_translation(monkeypatch)
    _stub_selector(monkeypatch)
    st = _DummyStreamlit(clicked={"values_card_egalitarian"})

    build.render_values_panel(_Deps(), lambda ids: None, st_module=st)

    from fiscal_model.composer.archetypes import get_archetype

    expected = get_archetype("egalitarian").vector
    assert st.session_state[KEY_VALUES_ARCHETYPE] == "egalitarian"
    assert st.session_state[VALUES_DIMENSION_KEYS["redistribution"]] == pytest.approx(
        expected.redistribution
    )
    assert set(st.session_state[KEY_VALUES_PROTECTED]) == set(expected.protected)
    # The panel's target is pushed onto the checklist's own slider key.
    assert st.session_state[KEY_BUILD_TARGET_PCT] == pytest.approx(
        expected.target_pct_gdp
    )
    assert st.session_state[KEY_VALUES_READING] == get_archetype("egalitarian").one_line


def test_every_dial_and_the_protected_control_are_editable(no_api_key, monkeypatch):
    _forbid_translation(monkeypatch)
    _stub_selector(monkeypatch)
    st = _DummyStreamlit()

    build.render_values_panel(_Deps(), lambda ids: None, st_module=st)

    from fiscal_model.composer.values_schema import DIMENSION_LABELS

    for label in DIMENSION_LABELS.values():
        assert any(text.startswith(label) for text in st.sliders), label
    assert any("Protected" in text for text in st.multiselects)
    assert any("Deficit target" in text for text in st.sliders)


def test_tags_are_available_on_request_per_policy(no_api_key, monkeypatch):
    _forbid_translation(monkeypatch)
    _stub_selector(monkeypatch)
    st = _DummyStreamlit()

    build.render_values_panel(_Deps(), lambda ids: None, st_module=st)

    assert any("Tags behind Eliminate SS Cap" in label for label in st.expanders)
    assert any("strong_progressive" in text for text in st.markdowns)


# ------------------------------------------------------------------
# Editing the reflection re-runs the selector, with no LLM
# ------------------------------------------------------------------


def test_editing_a_dial_changes_the_package_without_any_llm_call(no_api_key, monkeypatch):
    """The plan's §5b.8 criterion, asserted the only way that means anything:
    the translator raises if it is called at all."""
    _forbid_translation(monkeypatch)

    def _run(**overrides):
        st = _DummyStreamlit()
        st.session_state.update(overrides)
        build.render_values_panel(_Deps(), lambda ids: None, st_module=st)
        return build._select_package(build._vector_from_session(st)).policy_ids

    baseline = _run()
    shifted = _run(
        **{
            VALUES_DIMENSION_KEYS["govt_size"]: -0.9,
            VALUES_DIMENSION_KEYS["redistribution"]: -0.2,
            KEY_VALUES_PROTECTED: [],
            KEY_VALUES_TARGET_PCT: 3.0,
        }
    )
    assert baseline != shifted, "moving the dials must change the package"


def test_protections_are_honoured_through_the_panel(no_api_key, monkeypatch):
    _forbid_translation(monkeypatch)
    st = _DummyStreamlit()
    st.session_state.update(
        {
            KEY_VALUES_PROTECTED: ["middle_class_rates"],
            KEY_VALUES_TARGET_PCT: 3.0,
            **dict.fromkeys(VALUES_DIMENSION_KEYS.values(), 0.5),
        }
    )

    build.render_values_panel(_Deps(), lambda ids: None, st_module=st)
    ids = build._select_package(build._vector_from_session(st)).policy_ids

    assert not any(pid.startswith("tariff-") for pid in ids)
    assert "carbon-tax-50" not in ids


# ------------------------------------------------------------------
# Free text (chip 13)
# ------------------------------------------------------------------


def test_free_text_box_appears_only_with_a_key(with_api_key, monkeypatch):
    _stub_selector(monkeypatch)
    st = _DummyStreamlit()

    build.render_values_panel(_Deps(), lambda ids: None, st_module=st)

    assert st.text_areas, "the box must be offered when a key is configured"
    assert any("Translate to a package" in label for label in st.buttons)


def test_translation_writes_the_vector_and_the_reading(with_api_key, monkeypatch):
    _stub_selector(monkeypatch)
    translated = ValuesVector(
        redistribution=0.8,
        deficit_concern=0.7,
        govt_size=0.0,
        growth_priority=0.3,
        generational_weight=0.5,
        protected=("middle_class_rates", "ss_benefits"),
        target_pct_gdp=3.0,
    )
    seen: list[str] = []

    def _fake_translate(text, *, default_target_pct_gdp=3.0):
        seen.append(text)
        return translated, "You want the debt down, not on the middle class.", ""

    monkeypatch.setattr(build, "_translate_values_text", _fake_translate)

    st = _DummyStreamlit(clicked={"values_translate"})
    st.session_state[KEY_VALUES_TEXT] = "debt down, middle class alone"
    build.render_values_panel(_Deps(), lambda ids: None, st_module=st)

    assert seen == ["debt down, middle class alone"]
    assert st.session_state[VALUES_DIMENSION_KEYS["redistribution"]] == pytest.approx(0.8)
    assert set(st.session_state[KEY_VALUES_PROTECTED]) == {
        "middle_class_rates",
        "ss_benefits",
    }
    assert "middle class" in st.session_state[KEY_VALUES_READING]
    # Free text never names an archetype.
    assert st.session_state[KEY_VALUES_ARCHETYPE] is None
    assert st.reruns == 1


def test_schema_invalid_translation_degrades_to_the_cards(with_api_key, monkeypatch):
    """A refused translation must leave a usable surface, not an error screen."""
    _stub_selector(monkeypatch)
    monkeypatch.setattr(
        build,
        "_translate_values_text",
        lambda text, **kw: (None, "", "redistribution must be between -1 and 1"),
    )

    st = _DummyStreamlit(clicked={"values_translate"})
    st.session_state[KEY_VALUES_TEXT] = "something the model mangled"
    build.render_values_panel(_Deps(), lambda ids: None, st_module=st)

    assert any("Couldn't read that as a set of values" in text for text in st.infos)
    assert any("redistribution must be between" in text for text in st.infos)
    # The offline path is still fully rendered underneath the notice.
    from fiscal_model.composer.archetypes import load_archetypes

    for archetype in load_archetypes().values():
        assert any(archetype.name in text for text in st.all_text)
    assert st.reruns == 0


def test_translation_exception_is_contained(with_api_key, monkeypatch):
    _stub_selector(monkeypatch)

    def _boom(text, **kwargs):
        raise RuntimeError("provider exploded")

    monkeypatch.setattr(build, "_translate_values_text", _boom)

    st = _DummyStreamlit(clicked={"values_translate"})
    st.session_state[KEY_VALUES_TEXT] = "anything"
    build.render_values_panel(_Deps(), lambda ids: None, st_module=st)

    assert any("provider exploded" in text for text in st.infos)
    assert st.errors == []


def test_free_text_is_not_offered_without_a_key_even_with_text_in_state(
    no_api_key, monkeypatch
):
    _forbid_translation(monkeypatch)
    _stub_selector(monkeypatch)
    st = _DummyStreamlit(clicked={"values_translate"})
    st.session_state[KEY_VALUES_TEXT] = "left over from a keyed session"

    build.render_values_panel(_Deps(), lambda ids: None, st_module=st)

    assert st.text_areas == []


# ------------------------------------------------------------------
# Load into the checklist
# ------------------------------------------------------------------


def test_load_button_queues_the_package_for_the_next_run(no_api_key, monkeypatch):
    _forbid_translation(monkeypatch)
    _stub_selector(monkeypatch)
    st = _DummyStreamlit(clicked={"values_load"})

    build.render_values_panel(_Deps(), lambda ids: None, st_module=st)

    assert st.session_state[KEY_VALUES_PENDING_LOAD] == [
        "ss-cap-eliminate",
        "corporate-28pct",
    ]
    assert st.reruns == 1


def test_pending_load_applies_the_preselection_and_flips_the_mode():
    st = _DummyStreamlit()
    st.session_state[KEY_VALUES_PENDING_LOAD] = ["ss-donut-250k", "corporate-28pct"]

    assert build._apply_pending_load(st, _Deps()) is True

    assert st.session_state["build_selection"] == ["ss-donut-250k", "corporate-28pct"]
    assert st.session_state["dt_ss-donut-250k"] is True
    assert st.session_state[KEY_BUILD_MODE] == build.MODE_SCRATCH
    assert st.session_state[KEY_VALUES_PENDING_LOAD] is None


def test_pending_load_applies_the_checklists_own_overlap_guardrails():
    """A composed package can never load a double-counted mix."""
    st = _DummyStreamlit()
    st.session_state[KEY_VALUES_PENDING_LOAD] = [
        "ss-cap-90pct",
        "ss-donut-250k",
        "ss-cap-eliminate",
    ]

    build._apply_pending_load(st, _Deps())

    assert st.session_state["build_selection"] == ["ss-cap-90pct"]


def test_pending_load_is_a_no_op_when_nothing_is_queued():
    st = _DummyStreamlit()
    assert build._apply_pending_load(st, _Deps()) is False


# ------------------------------------------------------------------
# Share links (chip 15)
# ------------------------------------------------------------------


def test_values_link_restores_the_panel(no_api_key, monkeypatch):
    _forbid_translation(monkeypatch)
    st = _DummyStreamlit()

    request = build.restore_values_from_query(st, {"values": "egalitarian"})

    from fiscal_model.composer.archetypes import get_archetype

    expected = get_archetype("egalitarian").vector
    assert request["archetype_id"] == "egalitarian"
    assert st.session_state[KEY_VALUES_ARCHETYPE] == "egalitarian"
    assert build._vector_from_session(st) == expected
    assert not st.session_state.get(KEY_VALUES_PENDING_LOAD)


def test_values_link_with_load_queues_the_package(no_api_key, monkeypatch):
    _forbid_translation(monkeypatch)
    st = _DummyStreamlit()

    build.restore_values_from_query(st, {"values": "egalitarian", "load": "1"})

    queued = st.session_state[KEY_VALUES_PENDING_LOAD]
    assert queued and all(isinstance(item, str) for item in queued)


def test_values_link_applies_once_per_distinct_link(no_api_key, monkeypatch):
    _forbid_translation(monkeypatch)
    st = _DummyStreamlit()
    query = {"values": "egalitarian"}

    assert build.restore_values_from_query(st, query) is not None
    st.session_state[VALUES_DIMENSION_KEYS["redistribution"]] = -1.0
    assert build.restore_values_from_query(st, query) is None
    assert st.session_state[VALUES_DIMENSION_KEYS["redistribution"]] == -1.0


def test_unknown_values_slug_is_ignored(no_api_key, monkeypatch):
    _forbid_translation(monkeypatch)
    st = _DummyStreamlit()
    assert build.restore_values_from_query(st, {"values": "not-a-philosophy"}) is None


def test_vector_link_beats_the_slug(no_api_key, monkeypatch):
    _forbid_translation(monkeypatch)
    edited = ValuesVector(
        redistribution=-0.4,
        deficit_concern=0.9,
        govt_size=-0.8,
        growth_priority=0.5,
        generational_weight=0.5,
        protected=(),
        target_pct_gdp=3.0,
    )
    st = _DummyStreamlit()

    build.restore_values_from_query(
        st, {"values": "egalitarian", "vector": edited.to_base64()}
    )

    assert build._vector_from_session(st) == edited
    # The slug survives as the label for the reading, not as the vector.
    assert st.session_state[KEY_VALUES_ARCHETYPE] == "egalitarian"


# ------------------------------------------------------------------
# Markdown safety and the lazy bridges
# ------------------------------------------------------------------


def test_dollar_amounts_in_markdown_are_escaped(no_api_key, monkeypatch):
    """Two unescaped ``$`` in one line render as a KaTeX span in Streamlit.

    …but *inside* a code span the escape is the bug: markdown processes no
    escapes there, so ``` `-\\$3,200B` ``` puts a literal backslash on screen
    (external UI review, 2026-09-01). Each pick line is a bold label plus a
    code span, so the rule is: escaped outside the backticks, raw inside.
    """
    import re

    _forbid_translation(monkeypatch)
    _stub_selector(monkeypatch)
    st = _DummyStreamlit()

    build.render_values_panel(_Deps(), lambda ids: None, st_module=st)

    money_lines = [text for text in st.markdowns if "B`" in text and "$" in text]
    assert money_lines
    for line in money_lines:
        spans = re.findall(r"`[^`]+`", line)
        assert spans, line
        for span in spans:
            assert "\\$" not in span, f"escaped inside a code span: {span!r}"
        outside = re.sub(r"`[^`]+`", "", line)
        assert not re.search(r"(?<!\\)\$\d", outside), (
            f"unescaped currency outside the code span: {outside!r}"
        )

    # The coverage line is plain markdown throughout, so it must be escaped.
    coverage = [text for text in st.markdowns if "of target" in text]
    assert coverage
    assert "\\$" in coverage[0], coverage[0]


def test_lazy_bridges_call_the_agreed_composer_api(monkeypatch):
    """The seams point at the real functions, with the real signatures."""
    import fiscal_model.composer.composer as composer_module
    import fiscal_model.composer.translate as translate_module

    seen: dict[str, object] = {}

    def _fake_compose(vector, catalog, *, rationale_template=None):
        seen["compose"] = (vector, catalog, rationale_template)
        return "package"

    def _fake_translate(text, *, default_target_pct_gdp=3.0):
        seen["translate"] = (text, default_target_pct_gdp)
        return None, "", "stubbed"

    monkeypatch.setattr(composer_module, "compose_values_package", _fake_compose)
    monkeypatch.setattr(translate_module, "translate_values_text", _fake_translate)

    assert build._select_package(ValuesVector(), rationale_template="{policy}") == "package"
    vector, catalog, template = seen["compose"]
    assert isinstance(vector, ValuesVector)
    assert isinstance(catalog, dict)
    assert all(isinstance(entry, CatalogPolicy) for entry in catalog.values())
    assert template == "{policy}"

    assert build._translate_values_text("hi", default_target_pct_gdp=4.0)[2] == "stubbed"
    assert seen["translate"] == ("hi", 4.0)
