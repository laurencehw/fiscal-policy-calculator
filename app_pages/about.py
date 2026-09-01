"""About — what this is, who made it, how to read it (``/about``).

A static page: standard chrome, five Markdown sections, standard footer. The
only interactive element is the ``st.page_link`` to Methodology, which the
"How to read the numbers" section points at.

Two repo-wide Markdown guards apply to every string below
(``tests/test_tilde_rendering.py``, ``tests/test_dollar_rendering.py``): a
``~`` before a number must reach Streamlit as ``\\~`` or it opens a
strikethrough span, and two unescaped ``$`` in one string can be parsed as
inline math. The accuracy figures here are written ``\\~5%`` / ``\\~8%`` for
that reason; the page carries no currency at all.
"""

from __future__ import annotations

from typing import Any

from components.chrome import page_link, render_chrome, render_page_footer
from fiscal_model.ui.helpers import TEXTBOOK_HOME

PAGE_TITLE = "About"
URL_PATH = "about"

APP_URL = "https://fiscal-policy-calculator.streamlit.app"
REPO_URL = "https://github.com/laurencehw/fiscal-policy-calculator"
SA_POLICY_SPACE_URL = "https://sa-policy-space.vercel.app"
LINKEDIN_URL = "https://www.linkedin.com/in/laurence-w-764b562"
CONTACT_EMAIL = "lw3387@nyu.edu"

_ABOUT_THIS_CALCULATOR = """### About this calculator

This calculator estimates the ten-year budgetary and economic effects of U.S.
tax and spending proposals — what a policy costs, who bears it, and how
confident anyone should be in that number. It grew out of teaching public
economics: the official scores from CBO, JCT and Treasury are the gold
standard, but they arrive as finished verdicts, and the machinery behind them
stays out of view. This tool opens the machinery. Every number links back to
the data vintage, the method and the nearest official benchmark, and every
result says plainly which tier it belongs to — a calibrated reconstruction of
a published score, or a genuine out-of-sample prediction. It is also a
companion to the *Public Economics* textbook, and, through
**Build → Start from your values**, an attempt at a bridge between public
finance as practised and everyone who arrives thinking in commitments rather
than instruments."""

_WHO_MADE_IT = f"""### Who made it

Laurence Wilse-Samson. I am an economist (PhD, Columbia) at NYU's Wagner
School of Public Service, based in New York. This is a personal research
project; the views and the modelling choices are my own and do not represent
the positions of any employer. Also by me: [SA Policy Space]({SA_POLICY_SPACE_URL}),
a tracker of policy ideas in the South African parliament, and the
[Public Economics]({TEXTBOOK_HOME}) textbook this app accompanies."""

# ``\~5%`` / ``\~8%``: see the module docstring — an unescaped tilde before a
# number pairs with the next one and strikes the paragraph through.
_HOW_TO_READ = r"""### How to read the numbers

Two tiers, never collapsed into one accuracy claim: *calibrated reference
models* reproduce official decompositions (\~5% mean error, low by
construction) and *out-of-sample predictions* are the honest test (\~8% mean
error). The **Methodology** page documents parameters, elasticities and
validation; the data-status pill at the top of every page shows the CBO and
IRS vintages behind the current session. Treat every figure as an estimate
with a stated source, not a score."""

_CONTACT_AND_LINKS = f"""### Contact and links

Email [{CONTACT_EMAIL}](mailto:{CONTACT_EMAIL}) ·
[GitHub — source code]({REPO_URL}) ·
[Public Economics textbook]({TEXTBOOK_HOME}) ·
[SA Policy Space]({SA_POLICY_SPACE_URL}) ·
[LinkedIn]({LINKEDIN_URL})"""

_LICENSE = f"""### License

Code is released under the MIT License; written content under CC BY 4.0.
Please cite the app as *Wilse-Samson, L. (2026). Fiscal Policy Impact
Calculator.* with the URL: <{APP_URL}>"""

#: The five sections, in render order. Exported so the page test can assert
#: the set of headings without re-deriving them from the rendered output.
SECTIONS: tuple[str, ...] = (
    _ABOUT_THIS_CALCULATOR,
    _WHO_MADE_IT,
    _HOW_TO_READ,
    _CONTACT_AND_LINKS,
    _LICENSE,
)


def render(st_module: Any, deps: Any, app_root: Any = None) -> None:
    """Render the About surface."""
    del app_root
    render_chrome(st_module=st_module, deps=deps)

    st_module.markdown(_ABOUT_THIS_CALCULATOR)
    st_module.markdown(_WHO_MADE_IT)
    st_module.markdown(_HOW_TO_READ)
    page_link(st_module, "methodology", label="Methodology")
    st_module.markdown(_CONTACT_AND_LINKS)
    st_module.markdown(_LICENSE)

    render_page_footer(st_module)
