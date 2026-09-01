"""
Static guard: every Streamlit widget in the redesign-relocated modules is keyed.

The custom tax form, the spending form and the model settings are moving out of
the sidebar (onto ``/tailor`` and a settings popover). An *unkeyed* Streamlit
widget has no session-state identity — its value is derived from its position
in the render tree — so relocating it silently resets it. These tests fail if a
new unkeyed widget is added to any of the three modules, and if a widget key is
not registered in the ``ui/session_state.py`` schema.

See ``planning/redesign/NOTES.md`` §2, §7 and §11 item 3.
"""

from __future__ import annotations

import ast
import inspect
import pathlib

import pytest

from fiscal_model.ui import (
    policy_input_spending,
    policy_input_tax,
    settings_controller,
)
from fiscal_model.ui.session_state import ALL_KEYS

# Streamlit callables that create a stateful widget.
WIDGET_FUNCS = frozenset(
    {
        "slider",
        "number_input",
        "selectbox",
        "radio",
        "checkbox",
        "toggle",
        "text_input",
        "text_area",
        "multiselect",
        "select_slider",
        "segmented_control",
        "pills",
        "button",
    }
)

# The object the module calls Streamlit through.
ST_NAMES = frozenset({"st", "st_module"})

MODULES = [policy_input_tax, policy_input_spending, settings_controller]

# Widgets that already had a key before this commit. They pass both ``key=``
# and ``index=``/``value=``; that combination is left untouched on purpose,
# because renaming or resequencing them breaks share links (NOTES §3.3).
GRANDFATHERED_KEYS = frozenset(
    {
        "sidebar_policy_area",
        "sidebar_preset_choice",
        "sidebar_spending_preset",
        "sidebar_setting_dynamic_scoring",
    }
)


def _widget_calls(module):
    """Yield ``(node, module)`` for every Streamlit widget call in *module*."""
    source = pathlib.Path(inspect.getfile(module)).read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr not in WIDGET_FUNCS:
            continue
        if not isinstance(func.value, ast.Name) or func.value.id not in ST_NAMES:
            continue
        yield node


def _keyword(node, name):
    for kw in node.keywords:
        if kw.arg == name:
            return kw
    return None


def _string_aliases(module):
    """Map ``name -> "literal"`` for every simple string assignment in *module*.

    Covers both module-level constants and the local aliases the preset
    pickers use (``area_key = _POLICY_AREA_KEY``). Repeated passes resolve
    chained aliases.
    """
    source = pathlib.Path(inspect.getfile(module)).read_text(encoding="utf-8")
    tree = ast.parse(source)
    aliases: dict[str, str] = {}
    for _ in range(3):
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            value = node.value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                aliases[target.id] = value.value
            elif isinstance(value, ast.Name) and value.id in aliases:
                aliases[target.id] = aliases[value.id]
    return aliases


def _resolve_key(module, node, aliases=None):
    """Return the literal key string for a widget call, or ``None``."""
    kw = _keyword(node, "key")
    if kw is None:
        return None
    if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
        return kw.value.value
    if isinstance(kw.value, ast.Name):
        # Imported KEY_* constant, module-level constant, or local alias.
        resolved = getattr(module, kw.value.id, None)
        if isinstance(resolved, str):
            return resolved
        if aliases is None:
            aliases = _string_aliases(module)
        return aliases.get(kw.value.id)
    return None


def _label(node):
    if node.args and isinstance(node.args[0], ast.Constant):
        return str(node.args[0].value)
    return f"line {node.lineno}"


@pytest.mark.parametrize("module", MODULES, ids=lambda m: m.__name__)
def test_every_widget_has_an_explicit_key(module):
    """No unkeyed widgets: relocating the form must not reset its values."""
    unkeyed = [
        f"{_label(node)} (line {node.lineno})"
        for node in _widget_calls(module)
        if _keyword(node, "key") is None
    ]
    assert not unkeyed, (
        f"{module.__name__} has unkeyed Streamlit widgets: {unkeyed}. "
        "Add an explicit key= (tailor_tax_*, tailor_spend_*, setting_*) and "
        "register it in fiscal_model/ui/session_state.py."
    )


@pytest.mark.parametrize("module", MODULES, ids=lambda m: m.__name__)
def test_widget_keys_are_registered_in_the_schema(module):
    """Every widget key must be known to SafeSessionState."""
    aliases = _string_aliases(module)
    unregistered = []
    for node in _widget_calls(module):
        key = _resolve_key(module, node, aliases)
        assert key is not None, (
            f"{module.__name__}:{node.lineno} — key= must be a string literal or "
            "a module-level constant so the schema can be checked statically."
        )
        # ``sidebar_setting_dynamic_scoring`` is schema-registered under a
        # separate dead-literal fix; the grandfathered keys are exempt here so
        # this guard stays scoped to the keys added with the widgets.
        if key not in ALL_KEYS and key not in GRANDFATHERED_KEYS:
            unregistered.append(f"{key} (line {node.lineno})")
    assert not unregistered, (
        f"{module.__name__} uses widget keys missing from session_state.ALL_KEYS: "
        f"{unregistered}"
    )


@pytest.mark.parametrize("module", MODULES, ids=lambda m: m.__name__)
def test_widget_keys_are_unique_within_a_module(module):
    """Duplicate keys raise Streamlit's DuplicateWidgetID at runtime."""
    aliases = _string_aliases(module)
    seen: dict[str, int] = {}
    duplicates = []
    for node in _widget_calls(module):
        key = _resolve_key(module, node, aliases)
        if key in seen:
            duplicates.append(f"{key} (lines {seen[key]}, {node.lineno})")
        else:
            seen[key] = node.lineno
    assert not duplicates, f"{module.__name__} reuses widget keys: {duplicates}"


@pytest.mark.parametrize("module", MODULES, ids=lambda m: m.__name__)
def test_newly_keyed_widgets_do_not_also_pass_a_default(module):
    """Guard against Streamlit's "default value + Session State" warning.

    Once a key is pre-seeded, passing ``value=``/``index=`` as well makes
    Streamlit warn. The pattern used here is: seed the key, omit the default.
    """
    # Widgets whose second positional argument is the default value (for
    # selectbox/radio/multiselect it is the *options* list, which is fine).
    positional_default = {"text_input", "text_area", "number_input", "checkbox", "toggle"}
    aliases = _string_aliases(module)
    offenders = []
    for node in _widget_calls(module):
        key = _resolve_key(module, node, aliases)
        if key in GRANDFATHERED_KEYS:
            continue
        has_default = (
            _keyword(node, "value") is not None
            or _keyword(node, "index") is not None
            or (node.func.attr in positional_default and len(node.args) > 1)
        )
        if has_default:
            offenders.append(f"{key} (line {node.lineno})")
    assert not offenders, (
        f"{module.__name__}: keyed widgets also pass a default: {offenders}. "
        "Seed st.session_state[key] before the widget and drop value=/index=."
    )
