"""Guard: Streamlit renders a single ``~...~`` pair as strikethrough, so an
unescaped ``~8%`` ... ``~±15%`` inside one Markdown block struck a whole
paragraph on the live Methodology page (2026-09-01). Every ``~`` that precedes
a number in rendered UI text must reach Streamlit as a backslash-tilde:
two backslashes + tilde in a normal Python string, one in a raw string.
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCAN = [ROOT / "fiscal_model" / "ui", ROOT / "app_pages", ROOT / "components"]

# A tilde directly before a digit, a dollar sign, or a plus-minus sign that is
# NOT itself preceded by a backslash. (Two backslashes in source, e.g.
# ``\\~8%`` inside a normal string, still leave a backslash right before the
# tilde, so the lookbehind is satisfied either way.)
UNESCAPED = re.compile(r"(?<!\\)~(?=[0-9$±])")


def _offenders() -> list[str]:
    found: list[str] = []
    for base in SCAN:
        for path in base.rglob("*.py"):
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                stripped = line.lstrip()
                # Comments and bare docstring prose never reach Streamlit; only
                # lines that carry a string literal can.
                if stripped.startswith("#") or ('"' not in line and "'" not in line):
                    continue
                if "http" in line or "tilde-ok" in line:
                    continue
                if UNESCAPED.search(line):
                    found.append(f"{path.relative_to(ROOT)}:{lineno}: {stripped[:90]}")
    return found


def test_no_unescaped_tilde_before_numbers_in_ui_source():
    offenders = _offenders()
    assert not offenders, "escape as \\\\~ (Streamlit strikethrough):\n" + "\n".join(offenders)


def test_guard_pattern_semantics():
    assert UNESCAPED.search("about ~8% error")
    assert UNESCAPED.search("(~±15%)")
    assert UNESCAPED.search("~$900B")
    assert not UNESCAPED.search(r"about \~8% error")
    assert not UNESCAPED.search("about \\\\~8% error")
    assert not UNESCAPED.search("home ~/.config")
