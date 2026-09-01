"""Guard: Streamlit renders a single ``~...~`` pair as strikethrough, so an
unescaped ``~8%`` ... ``~±15%`` inside one Markdown block struck a whole
paragraph on the live Methodology page (2026-09-01). Every ``~`` that precedes
a number (or a dollar sign, escaped or not) in rendered UI text must reach
Streamlit as a backslash-tilde: two backslashes + tilde in a normal Python
string, one in a raw string.

The scan walks the AST so multi-line literals (``st.markdown(r\"\"\"...\"\"\")``
tables) are covered and docstrings are excluded. A source line carrying the
marker ``tilde-ok`` is exempt (used for a catalog label key that must not be
renamed).
"""
from __future__ import annotations

import ast
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCAN = [ROOT / "fiscal_model" / "ui", ROOT / "app_pages", ROOT / "components"]

# A tilde that is not preceded by a backslash and is followed by a digit, a
# plus-minus sign, or a dollar sign (optionally itself backslash-escaped —
# ``~\$950,000`` still renders as ``~$950,000`` and still pairs).
UNESCAPED = re.compile(r"(?<!\\)~(?=\\?\$|[0-9±])")


def _docstring_nodes(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                if isinstance(body[0].value.value, str):
                    ids.add(id(body[0].value))
    return ids


def _string_constants(path: pathlib.Path):
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(path))
    skip = _docstring_nodes(tree)
    # Literal fragments of f-strings are reported through their JoinedStr.
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            skip.update(id(part) for part in node.values if isinstance(part, ast.Constant))
    lines = src.splitlines()
    for node in ast.walk(tree):
        # f-strings: a tilde at the end of a literal fragment followed by a
        # formatted number (``f"~{rel:.0f}%"``) is invisible to the Constant
        # scan below, so reconstruct the runtime text with a digit standing
        # in for each formatted value.
        if isinstance(node, ast.JoinedStr):
            text = "".join(
                part.value if isinstance(part, ast.Constant) and isinstance(part.value, str) else "0"
                for part in node.values
            )
            if "<style" in text or text.lstrip().startswith("<"):
                continue  # pass-through CSS / block HTML, as below
            line = lines[node.lineno - 1] if node.lineno - 1 < len(lines) else ""
            yield node.lineno, text, line
            continue
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip:
            # CSS and block-level HTML are passed through verbatim by
            # Streamlit (block HTML is opaque to the Markdown parser), so
            # a tilde there can neither strike nor be escaped.
            if "<style" in node.value or node.value.lstrip().startswith("<"):
                continue
            line = lines[node.lineno - 1] if node.lineno - 1 < len(lines) else ""
            yield node.lineno, node.value, line


def _offenders() -> list[str]:
    found: list[str] = []
    for base in SCAN:
        for path in sorted(base.rglob("*.py")):
            for lineno, value, line in _string_constants(path):
                if "tilde-ok" in line:
                    continue
                for m in UNESCAPED.finditer(value):
                    snippet = value[max(0, m.start() - 30) : m.end() + 30].replace("\n", " ")
                    found.append(f"{path.relative_to(ROOT)}:{lineno}: ...{snippet}...")
    return found


def test_no_unescaped_tilde_before_numbers_in_ui_strings():
    offenders = _offenders()
    assert not offenders, "escape the tilde (Streamlit strikethrough):\n" + "\n".join(offenders)


def test_guard_pattern_semantics():
    assert UNESCAPED.search("about ~8% error")
    assert UNESCAPED.search("(~±15%)")
    assert UNESCAPED.search("~$900B")
    assert UNESCAPED.search(r"~\$950,000")
    assert not UNESCAPED.search(r"about \~8% error")
    assert not UNESCAPED.search(r"\~\$950,000")
    assert not UNESCAPED.search("home ~/.config")
    assert not UNESCAPED.search("https://eml.berkeley.edu/~saez/paper.pdf")


def test_guard_sees_inside_multiline_raw_blocks(tmp_path, monkeypatch):
    sample = tmp_path / "ui"
    sample.mkdir()
    (sample / "page.py").write_text(
        'import streamlit as st\n\n\ndef render():\n    """~1-2s docstring is fine."""\n'
        '    st.markdown(r"""\n| a | b |\n|---|---|\n| ~8% | ~\\$5B |\n""")\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("tests.test_tilde_rendering.SCAN", [sample])
    monkeypatch.setattr("tests.test_tilde_rendering.ROOT", tmp_path)
    hits = _offenders()
    assert len(hits) == 2, hits
