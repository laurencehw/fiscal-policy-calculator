"""Tests for accessibility helpers."""

from __future__ import annotations

import plotly.graph_objects as go

from fiscal_model.ui.a11y import (
    A11Y_STYLES,
    SKIP_NAV_HTML,
    ChartDescription,
    format_currency_rows,
    inject_a11y_styles,
    render_accessible_chart,
)


class _FakeExpander:
    def __init__(self, owner, label):
        self.owner = owner
        self.label = label

    def __enter__(self):
        self.owner.expander_opened.append(self.label)
        return self.owner

    def __exit__(self, *args):
        return False


class _FakeStreamlit:
    """Minimal Streamlit stand-in that records every call."""

    def __init__(self):
        self.markdowns: list[tuple[str, bool]] = []
        self.captions: list[str] = []
        self.plotly_charts: list = []
        self.dataframes: list = []
        self.expander_opened: list[str] = []

    def markdown(self, text, unsafe_allow_html=False):
        self.markdowns.append((text, bool(unsafe_allow_html)))

    def caption(self, text):
        self.captions.append(text)

    def plotly_chart(self, figure, **_):
        self.plotly_charts.append(figure)

    def dataframe(self, df, **_):
        self.dataframes.append(df)

    def expander(self, label, expanded=False):
        del expanded
        return _FakeExpander(self, label)


def _simple_figure() -> go.Figure:
    return go.Figure(data=[go.Bar(x=["A", "B"], y=[1.0, -2.0])])


def test_inject_a11y_styles_writes_styles_and_skip_link():
    st = _FakeStreamlit()
    inject_a11y_styles(st)
    joined = "\n".join(text for text, _ in st.markdowns)
    assert ".sr-only" in joined
    assert 'class="skip-nav"' in joined
    assert 'id="main-content"' in joined
    # All injected blocks must be marked unsafe_allow_html.
    assert all(unsafe for _, unsafe in st.markdowns)


def test_a11y_styles_and_skip_html_are_self_contained():
    """The styles/skip-link HTML should be trivially renderable strings."""
    assert "<style>" in A11Y_STYLES and "</style>" in A11Y_STYLES
    assert "skip-nav" in SKIP_NAV_HTML
    assert "main-content" in SKIP_NAV_HTML


def test_render_accessible_chart_adds_caption_and_sr_only():
    st = _FakeStreamlit()
    fig = _simple_figure()
    desc = ChartDescription(
        title="Sample",
        summary="A short summary.",
        data_rows=[("A", "$1B"), ("B", "-$2B")],
    )
    render_accessible_chart(st, fig, desc)

    # Visible caption rendered once.
    assert st.captions == ["A short summary."]
    # Plotly figure rendered once.
    assert len(st.plotly_charts) == 1
    # Hidden sr-only description emitted.
    assert any(
        'class="sr-only"' in text and "Sample" in text and "A short summary." in text
        for text, unsafe in st.markdowns
        if unsafe
    )
    # Expandable data fallback opened.
    assert st.expander_opened == ["Show chart data as a table"]
    assert st.dataframes, "should render a dataframe fallback"


def test_render_accessible_chart_sets_figure_title_when_missing():
    st = _FakeStreamlit()
    fig = _simple_figure()
    assert not getattr(fig.layout.title, "text", None)
    render_accessible_chart(
        st,
        fig,
        ChartDescription(title="Auto Title", summary="..."),
    )
    assert fig.layout.title.text == "Auto Title"
    assert fig.layout.meta["description"] == "..."
    assert fig.layout.meta["accessible_title"] == "Auto Title"


def test_render_accessible_chart_preserves_existing_title():
    st = _FakeStreamlit()
    fig = _simple_figure()
    fig.update_layout(title="Pre-existing")
    render_accessible_chart(
        st,
        fig,
        ChartDescription(title="Should-not-override", summary="."),
    )
    assert fig.layout.title.text == "Pre-existing"


def test_render_accessible_chart_without_data_rows_skips_expander():
    st = _FakeStreamlit()
    fig = _simple_figure()
    render_accessible_chart(
        st,
        fig,
        ChartDescription(title="No data", summary="No table."),
    )
    assert st.expander_opened == []
    assert not st.dataframes


def test_chart_description_hidden_description_includes_data():
    desc = ChartDescription(
        title="T",
        summary="S",
        data_rows=[("a", "1"), ("b", "2")],
    )
    text = desc.hidden_description()
    assert "T" in text
    assert "S" in text
    assert "a: 1" in text
    assert "b: 2" in text


def test_format_currency_rows_produces_signed_billions():
    rows = format_currency_rows([("2026", 12.5), ("2027", -3.25)])
    assert rows == [("2026", "$+12.5B"), ("2027", "$-3.2B")]


def test_render_accessible_chart_escapes_html_in_description():
    """ChartDescription can carry user-supplied text (policy names, etc.);
    the sr-only block must escape HTML so it can't inject markup."""
    st = _FakeStreamlit()
    fig = _simple_figure()
    desc = ChartDescription(
        title='Scary <script>alert("xss")</script>',
        summary='<img src=x onerror=alert(1)>',
        data_rows=[("<b>row</b>", "<i>val</i>")],
    )
    render_accessible_chart(st, fig, desc)

    sr_blocks = [
        text for text, unsafe in st.markdowns
        if unsafe and 'class="sr-only"' in text
    ]
    assert sr_blocks, "should emit sr-only block"
    for block in sr_blocks:
        # Raw HTML must be escaped inside the sr-only div.
        assert "<script>" not in block
        assert "&lt;script&gt;" in block
        assert "onerror=" not in block or "&lt;img" in block
        assert "&lt;b&gt;row&lt;/b&gt;" in block


def test_render_accessible_chart_survives_figure_without_update_layout():
    """If a non-Plotly object sneaks in, the helper must still render the
    sr-only fallback instead of crashing."""

    class _FakeFigure:
        pass

    st = _FakeStreamlit()
    render_accessible_chart(
        st,
        _FakeFigure(),
        ChartDescription(title="X", summary="Y"),
    )
    assert st.captions == ["Y"]
    assert any('class="sr-only"' in text for text, _ in st.markdowns)


def test_run_main_app_invokes_inject_a11y_styles(monkeypatch):
    """``run_main_app`` must call ``inject_a11y_styles`` before rendering.

    Uses a spy to record the first call, then short-circuits the rest of
    bootstrap by raising so we don't have to build a full fake deps/tab
    tree. The assertion is on the call log, not on successful completion
    of the whole pipeline.
    """
    import fiscal_model.ui.app_controller as app_controller

    calls: list[tuple] = []
    sentinel = RuntimeError("stop-after-a11y-injection")

    def _spy(st_module):
        calls.append((st_module,))
        raise sentinel

    monkeypatch.setattr(app_controller, "inject_a11y_styles", _spy)

    class _Session(dict):
        def __getattr__(self, name):
            try:
                return self[name]
            except KeyError as exc:
                raise AttributeError(name) from exc

        def __setattr__(self, name, value):
            self[name] = value

    class _FakeSt:
        def __init__(self):
            self.session_state = _Session()

        def title(self, _text):  # pragma: no cover — never reached
            raise AssertionError("title should not render — spy raised first")

        def markdown(self, *args, **kwargs):
            pass

    fake_st = _FakeSt()
    try:
        app_controller.run_main_app(
            st_module=fake_st,
            deps=None,
            model_available=True,
            app_root=None,
        )
    except RuntimeError as exc:
        assert exc is sentinel

    assert len(calls) == 1
    assert calls[0][0] is fake_st
