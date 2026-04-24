"""
Tests for the Data-details augmentation preview in the sidebar.

The preview is a diagnostic toggle: when the checkbox is off, no
augmentation work runs; when on, the sidebar shows the before/after
coverage numbers. Tests exercise both paths with a Streamlit stub so
they don't need a real session.
"""

from __future__ import annotations

from fiscal_model.ui.app_controller import _render_augmentation_preview


class _StubCheckbox:
    def __init__(self, value: bool):
        self.value = value

    def __call__(self, *args, **kwargs):  # Streamlit-compatible call
        return self.value


class _StubStreamlit:
    def __init__(self, checkbox_value: bool):
        self._checkbox_value = checkbox_value
        self.markdowns: list[str] = []
        self.captions: list[str] = []

    def checkbox(self, label, value=False, **kwargs):
        return self._checkbox_value

    def markdown(self, text, **kwargs):
        self.markdowns.append(text)

    def caption(self, text):
        self.captions.append(text)


def test_preview_is_silent_when_toggle_is_off():
    st = _StubStreamlit(checkbox_value=False)
    microdata = {"status": "ok", "calibration_year": 2023}
    _render_augmentation_preview(st, microdata)
    # When off, only the divider markdown was emitted.
    assert len(st.markdowns) == 1
    assert "---" in st.markdowns[0]
    assert st.captions == []


def test_preview_shows_coverage_change_when_toggle_is_on():
    st = _StubStreamlit(checkbox_value=True)
    microdata = {"status": "ok", "calibration_year": 2023}
    _render_augmentation_preview(st, microdata)
    rendered = "\n".join(st.markdowns)
    # The preview should name the calibration year, show returns/AGI
    # coverage lines, and mention synthetic-record counts.
    assert "2023" in rendered
    assert "Returns coverage" in rendered
    assert "AGI coverage" in rendered
    assert "Synthetic top-tail AGI added" in rendered
    # Caption explains the coverage-vs-representation caveat.
    assert any("coverage" in c.lower() for c in st.captions)


def test_preview_survives_unexpected_year():
    """An odd calibration year shouldn't crash the preview."""
    st = _StubStreamlit(checkbox_value=True)
    microdata = {"status": "ok", "calibration_year": 9999}
    _render_augmentation_preview(st, microdata)
    # Either the preview renders a fallback caption or silently exits;
    # both are acceptable, but it must not raise.
