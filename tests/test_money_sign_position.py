"""Money prints its sign before the dollar sign: ``+$4,581.9B``, ``-$302.2B``.

Until 2026-10-04 about ninety user-facing sites wrote ``f"${x:+,.1f}B"``,
which renders ``$+4,581.9B`` / ``$-302.2B`` — the headline number on every
result panel among them. They now go through
:func:`fiscal_model.ui.formatting.format_money`, and this file is what keeps
the pattern from coming back:

* the formatter's own contract — the sign moves, the digits do not;
* a source grep over every UI tree for the three spellings of the old shape.

The rendered-page half (a real ``/explore`` run read back through
``AppTest``) lives in ``tests/test_dollar_rendering.py`` beside the other
rendered-currency guards, so it shares that file's offline fixture.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import pytest

from fiscal_model.ui.formatting import format_dollars, format_money

ROOT = Path(__file__).resolve().parents[1]

#: The trees whose strings reach a user. ``fiscal_model/validation`` prints CLI
#: reports, not UI, and is deliberately out of scope.
UI_TREES = ("fiscal_model/ui", "app_pages", "components")

#: ``${value:+,.1f}`` — a ``+`` format spec on a field that follows a ``$``.
SIGNED_FIELD_AFTER_DOLLAR = re.compile(r"\$\{[^{}\n]*?:\+[^{}\n]*\}")
#: ``"$-3.2B"`` / ``"$+12B"`` — a literal signed amount after the ``$``.
LITERAL_SIGN_AFTER_DOLLAR = re.compile(r"\$[+\-−]\d")
#: ``f"$-{abs(x)}"`` — a hand-placed sign after the ``$``.
HAND_SIGN_AFTER_DOLLAR = re.compile(r"\$[+\-−]\{")

PATTERNS = (SIGNED_FIELD_AFTER_DOLLAR, LITERAL_SIGN_AFTER_DOLLAR, HAND_SIGN_AFTER_DOLLAR)

#: ``(path, reason)``. Anything listed here is a string that *names* the old
#: shape rather than rendering it. Keep it short; every entry needs a reason.
ALLOWLIST: dict[str, str] = {
    "fiscal_model/ui/formatting.py": (
        "the formatter's docstring quotes the forbidden f-string to explain "
        "what it replaces"
    ),
}


def _ui_sources() -> list[Path]:
    files: list[Path] = []
    for tree in UI_TREES:
        files.extend(sorted((ROOT / tree).rglob("*.py")))
    return files


def test_the_scan_actually_covers_the_ui():
    """Guards the guard: a moved tree would make the grep pass vacuously."""
    names = {p.relative_to(ROOT).as_posix() for p in _ui_sources()}
    for expected in (
        "fiscal_model/ui/tabs/results_summary.py",
        "fiscal_model/ui/a11y.py",
        "app_pages/build.py",
        "components/results.py",
    ):
        assert expected in names


def test_no_ui_source_puts_the_sign_after_the_dollar():
    offenders: list[str] = []
    for path in _ui_sources():
        rel = path.relative_to(ROOT).as_posix()
        if rel in ALLOWLIST:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            # A ``#`` comment never renders; it may quote the old shape as history.
            if line.lstrip().startswith("#"):
                continue
            if any(p.search(line) for p in PATTERNS):
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
    assert not offenders, (
        "Money must print its sign before the $ (+$4,581.9B, -$302.2B). Use "
        "fiscal_model.ui.formatting.format_money instead of f\"${x:+,.1f}B\". "
        "Offenders:\n" + "\n".join(offenders)
    )


def test_allowlisted_files_still_exist_and_still_need_it():
    for rel, reason in ALLOWLIST.items():
        assert reason
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert any(p.search(text) for p in PATTERNS), (
            f"{rel} no longer contains the old shape; drop it from ALLOWLIST"
        )


@pytest.mark.parametrize(
    ("source", "caught"),
    [
        ('f"${headline:+,.1f}B"', True),
        ('rf"\\${previous:+,.1f}B"', True),
        ('f"\\\\${band[0]:+,.1f}B"', True),
        ('"$-3.2B"', True),
        ('f"$-{abs(x):,.0f}B"', True),
        ("format_money(headline)", False),
        ('f"{sign}${abs(x):,.0f}B"', False),
        ('f"${value:,.0f}B"', False),
        ('f"{x:+.1f}pp above ${threshold:,.0f}"', False),
    ],
)
def test_detector(source, caught):
    assert any(p.search(source) for p in PATTERNS) is caught


# ── The formatter's contract ─────────────────────────────────────────────


def test_sign_goes_before_the_dollar():
    assert format_money(4581.94) == "+$4,581.9B"
    assert format_money(-302.2) == "-$302.2B"
    assert format_money(-302.2, decimals=0) == "-$302B"
    assert format_money(12.5, unit="T") == "+$12.5T"
    assert format_dollars(-18642) == "-$18,642"
    assert format_dollars(1234.567, decimals=2) == "+$1,234.57"


def test_minus_is_ascii_hyphen_minus():
    """U+2212 reads poorly in some screen readers; the rule is ASCII ``-``."""
    assert format_money(-1.0).startswith("-$")
    assert "−" not in format_money(-1.0)


def test_unsigned_prints_a_sign_only_on_negatives():
    assert format_money(460.0, signed=False) == "$460.0B"
    assert format_money(-460.0, signed=False) == "-$460.0B"


def test_escape_is_for_markdown_sinks_only():
    assert format_money(-1040, decimals=0, escape=True) == "-\\$1,040B"
    assert format_money(1040, decimals=0) == "+$1,040B"


def test_thousands_grouping_is_optional():
    assert format_money(4581.94, thousands=False) == "+$4581.9B"


_VALUES = (0.0, -0.0, 0.04, -0.04, 0.5, -0.5, 1.0, -1.0, 999.95, -999.95, 4581.94, -1_427.3,
           1e6 + 0.123, -1e6 - 0.123, 12.345678)


@pytest.mark.parametrize("value", _VALUES)
@pytest.mark.parametrize("decimals", [0, 1, 2])
@pytest.mark.parametrize("signed", [True, False])
@pytest.mark.parametrize("thousands", [True, False])
def test_digits_are_exactly_pythons_only_the_sign_moves(value, decimals, signed, thousands):
    """The sweep that introduced the formatter changed no number.

    Each output is Python's own ``{value:+,.Nf}`` (or unsigned) with the
    leading sign lifted in front of the ``$`` — so ``-0.04`` at one decimal is
    still ``-0.0``, exactly as ``f"${-0.04:+.1f}B"`` printed it.
    """
    spec = f"{'+' if signed else ''}{',' if thousands else ''}.{decimals}f"
    old = "$" + format(value, spec) + "B"
    new = format_money(value, decimals=decimals, signed=signed, thousands=thousands)
    if old[1] in "+-":
        assert new == old[1] + "$" + old[2:]
    else:
        assert new == old


def test_non_finite_values_do_not_raise():
    assert format_money(math.nan, signed=False) == "$nanB"
    assert format_money(-math.inf) == "-$infB"
