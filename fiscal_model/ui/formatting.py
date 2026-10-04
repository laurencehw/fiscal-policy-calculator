"""The one money formatter for user-facing UI strings.

**Sign rule.** The sign goes *before* the dollar sign: ``+$4,581.9B`` and
``-$302.2B``, never ``$+4,581.9B`` / ``$-302.2B`` (which is what
``f"${x:+,.1f}B"`` prints, and what about ninety UI sites printed until
2026-10-04). The minus is the ASCII hyphen-minus ``-``, not U+2212 ``−``:

* it is what the app already used for negatives in the places that had the
  sign in the right position (Build's package total, the side-by-side and
  policy-comparison tables, the preset badge, the Methodology tables);
* screen readers pronounce ``-`` as "minus" reliably, while several engines
  skip U+2212 or read it as "dash", which flips the meaning of a deficit
  figure in the accessible text (``fiscal_model.ui.a11y``);
* tests, CSV exports and copy-paste into spreadsheets parse it.

**Numbers do not change.** The digits and the sign are exactly what Python's
own format spec produces for the same value and precision — this function
formats with ``{value:+,.Nf}`` (or ``{value:,.Nf}`` unsigned) and only *moves*
the leading sign in front of the ``$``. So ``-0.04`` at one decimal is
``-$0.0B``, as ``f"{-0.04:+.1f}"`` is ``-0.0``, and a positive value carries
``+`` when ``signed=True``. That makes the sweep that introduced this module a
pure display change, which ``tests/test_money_sign_position.py`` pins.

**Markdown.** Streamlit renders markdown through KaTeX, so two bare ``$`` in a
markdown string can open a math span (``tests/test_dollar_rendering.py``).
``escape=True`` emits ``\\$`` for a markdown sink; leave it ``False`` for raw
HTML blocks, ``st.metric`` values, dataframe cells, chart labels, ``st.code``
and plain-text downloads, where a backslash would show literally. With the sign
in front, a bare ``$`` is now followed by a digit, so
:func:`fiscal_model.ui.helpers.escape_markdown_dollars` also catches it.
"""

from __future__ import annotations

__all__ = ["format_dollars", "format_money"]


def format_money(
    value: float,
    *,
    decimals: int = 1,
    unit: str = "B",
    signed: bool = True,
    escape: bool = False,
    thousands: bool = True,
) -> str:
    """Format ``value`` as money with the sign in front of the ``$``.

    Args:
        value: The amount, already in ``unit`` (billions for ``"B"``,
            trillions for ``"T"``, dollars for ``""``).
        decimals: Digits after the decimal point.
        unit: Suffix after the number — ``"B"``, ``"T"``, ``""`` (dollars) …
            Anything further (``"/yr"``) is the caller's to append.
        signed: ``True`` prints ``+`` on non-negative values (``{:+}``);
            ``False`` prints a sign only on negatives (``{:}``).
        escape: ``True`` writes ``\\$`` for a markdown sink.
        thousands: ``True`` groups digits with commas (``{:,}``).

    >>> format_money(4581.94)
    '+$4,581.9B'
    >>> format_money(-302.2, decimals=0)
    '-$302B'
    >>> format_money(-460.0, signed=False)
    '-$460.0B'
    >>> format_money(12.5, escape=True)
    '+\\\\$12.5B'
    """
    spec = f"{'+' if signed else ''}{',' if thousands else ''}.{int(decimals)}f"
    text = format(float(value), spec)
    sign = ""
    if text and text[0] in "+-":
        sign, text = text[0], text[1:]
    dollar = "\\$" if escape else "$"
    return f"{sign}{dollar}{text}{unit}"


def format_dollars(
    value: float,
    *,
    decimals: int = 0,
    signed: bool = True,
    escape: bool = False,
    thousands: bool = True,
) -> str:
    """:func:`format_money` in plain dollars: ``-1234`` -> ``'-$1,234'``."""
    return format_money(
        value,
        decimals=decimals,
        unit="",
        signed=signed,
        escape=escape,
        thousands=thousands,
    )
