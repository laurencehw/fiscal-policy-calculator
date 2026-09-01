"""Ask — the citation-grounded assistant, and the home page of the app (``/``).

Layout (wireframes ``01-ask-home-desktop`` / ``04-ask-mobile``):

    shared chrome
    ────────────────────────────────────
    centered hero: H1 + one-line subtitle
    st.chat_input
    suggestion chips (st.pills)
    context chip · answer transcript          } inside @st.fragment
    ────────────────────────────────────
    doorway cards -> /build, /tailor
    worked-example cards (prefill the question box)
    footer

The chat lives inside the fragment so asking a question does not rerun the
whole page; the doorways and example cards sit outside it, because clicking
one is a navigation or a prefill, not a chat interaction.

URL contract: ``/?q=…`` (and ``/ask?q=…``) prefills and auto-asks once per
session — see :func:`_query_prefill`.
"""

from __future__ import annotations

from typing import Any

from components.cards import render_doorway_cards, render_example_cards
from components.chrome import render_chrome, render_page_footer
from fiscal_model.ui.tabs.ask_assistant import queue_question

PAGE_TITLE = "Ask"
URL_PATH = "ask"

# Bounded so a hostile link cannot push an essay into the model. The chat
# input applies the same ceiling.
_MAX_PREFILL_CHARS = 2000


def _query_prefill(st_module: Any) -> str | None:
    """Read ``?q=`` from the URL, if present.

    Auto-submission happens exactly once per session: the Ask renderer keeps
    a flag keyed on the question text, so a refresh of the same link does not
    re-spend a turn and a rerun mid-conversation does not re-ask.
    """
    try:
        query_params = st_module.query_params
    except AttributeError:  # pragma: no cover — older Streamlit / test doubles
        try:
            query_params = st_module.experimental_get_query_params()
        except Exception:
            return None

    raw = query_params.get("q") if hasattr(query_params, "get") else None
    if isinstance(raw, list):
        raw = raw[0] if raw else None
    if not isinstance(raw, str):
        return None
    question = raw.strip()[:_MAX_PREFILL_CHARS]
    return question or None


def render(st_module: Any, deps: Any, app_root: Any = None) -> None:
    """Render the Ask home page."""
    del app_root
    render_chrome(st_module=st_module, deps=deps)

    deps.render_ask_tab(
        st_module=st_module,
        fiscal_assistant=deps.fiscal_assistant,
        scoring_result=st_module.session_state.get("results"),
        prefill=_query_prefill(st_module),
    )

    st_module.markdown("---")
    render_doorway_cards(st_module)

    picked = render_example_cards(st_module)
    if picked:
        # Queue the question for the chat fragment and rerun so the answer
        # streams in above, exactly as if it had been typed.
        queue_question(st_module, picked)
        st_module.rerun()

    render_page_footer(st_module)
