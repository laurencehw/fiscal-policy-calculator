"""Guard: ``app.py`` paints before it imports the model.

On Streamlit Cloud nothing reaches the browser until the script emits its first
element, and Streamlit executes ``app.py`` top to bottom before ``main()``
reaches a line. So every module-level import in ``app.py`` is time the visitor
spends looking at a blank page — and naming *any* ``fiscal_model`` submodule
costs the whole package, because Python must execute ``fiscal_model/__init__``
(which re-exports every policy module, and through them ``scipy.stats`` and
``matplotlib.pyplot``) to reach a submodule of it.

Measured on ``perf/cold-start-measurement``: one such import, of three
stdlib-only logging helpers, cost **1.59s before the first paint**, and removing
it took ``import app`` from 1,901 modules to 586. See
``planning/memos/COLD_START.md``.

Nothing about that is self-evident from reading ``app.py``, and the regression
is silent — a future `from fiscal_model.x import y` at the top of the file
re-introduces the whole cost with no test failing and no visible symptom on a
warm developer machine. Hence this file.

Every check runs in a **subprocess**: the assertions are about what is in
``sys.modules``, and by the time pytest reaches this file the whole model is
loaded in-process.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _probe(source: str) -> dict:
    """Run ``source`` in a cold interpreter and read back its ``@@JSON@@`` line."""
    proc = subprocess.run(
        [sys.executable, "-c", source],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=300,
    )
    for line in proc.stdout.splitlines():
        if line.startswith("@@JSON@@"):
            return json.loads(line[len("@@JSON@@") :])
    raise AssertionError(
        f"probe produced no result\n--- stdout ---\n{proc.stdout[-3000:]}\n"
        f"--- stderr ---\n{proc.stderr[-3000:]}"
    )


def _loaded_after(import_line: str) -> set[str]:
    result = _probe(
        f'import json, sys\n{import_line}\nprint("@@JSON@@" + json.dumps(sorted(sys.modules)))\n'
    )
    return set(result)


def test_importing_app_does_not_import_the_model() -> None:
    """``import app`` must not reach ``fiscal_model``.

    This is the whole point: the package costs ~1.0s to execute and the router
    does not need any of it until after the boot placeholder is on screen.
    """
    loaded = _loaded_after("import app")
    offenders = sorted(name for name in loaded if name.split(".")[0] == "fiscal_model")
    assert not offenders, (
        "app.py pulls fiscal_model in at module scope, which is paid before the "
        "first pixel of the first script run. Move the import into the function "
        "that needs it — after _render_head_metadata and _boot_placeholder. "
        f"Modules loaded: {offenders[:10]}"
    )


def test_app_adds_no_heavy_third_party_import_over_streamlit() -> None:
    """``app.py`` must add nothing heavy of its own on top of ``streamlit``.

    Phrased as a *difference* against ``import streamlit`` rather than as an
    absolute list, so the test tracks what the app is responsible for and does
    not break the day Streamlit itself starts importing one of these.
    """
    baseline = _loaded_after("import streamlit")
    with_app = _loaded_after("import app")
    added_roots = {name.split(".")[0] for name in with_app - baseline}
    heavy = added_roots & {"pandas", "numpy", "scipy", "matplotlib", "plotly", "sklearn"}
    assert not heavy, (
        "app.py imports a heavy third-party package at module scope that "
        f"streamlit does not already load: {sorted(heavy)}. Defer it to the "
        "point of use — see planning/memos/COLD_START.md."
    )


def test_page_config_fires_before_the_model_is_imported() -> None:
    """The ordering inside ``main()``, not just the module scope.

    Module-level cleanliness is not enough: ``main()`` could still import the
    model on its first line and paint on its second. This drives the real
    ``main()`` with a fake ``st`` that records, at the moment
    ``set_page_config`` is called, whether ``fiscal_model`` had been imported
    yet — which is exactly the question "was anything on screen first?".
    """
    result = _probe(
        """
import json, sys

import app

seen = {}


class _Slot:
    def caption(self, *a, **k):
        seen.setdefault("caption_before_model", not _model_loaded())

    def empty(self, *a, **k):
        pass


class _FakeSt:
    def __init__(self):
        self.query_params = {}
        self.session_state = {}

    def set_page_config(self, **kwargs):
        seen["page_config_before_model"] = not _model_loaded()

    def markdown(self, *a, **k):
        pass

    def empty(self):
        return _Slot()

    def error(self, message):
        seen.setdefault("errors", []).append(message)

    def Page(self, page, **kwargs):
        return None

    def navigation(self, pages, **kwargs):
        class _Nav:
            def run(self_inner):
                pass

        return _Nav()


def _model_loaded():
    return any(name.split(".")[0] == "fiscal_model" for name in sys.modules)


def _deps_builder(*, pd_module):
    # Stand in for the real bundle, but import the model the way the real
    # builder does, so "after the paint" is a real claim and not an artifact
    # of a stub that never touches fiscal_model at all.
    import fiscal_model.ui.dependencies  # noqa: F401

    class _Deps:
        def apply_app_styles(self, st_module):
            pass

    return _Deps()


app.main(st_module=_FakeSt(), pd_module=object(), deps_builder=_deps_builder)
seen["model_loaded_at_end"] = _model_loaded()
print("@@JSON@@" + json.dumps(seen))
"""
    )

    assert result.get("page_config_before_model") is True, (
        "st.set_page_config fired after fiscal_model was already imported, so "
        "the visitor waited for the model before anything could paint. "
        f"probe: {result}"
    )
    assert result.get("caption_before_model") is True, (
        "the boot placeholder's caption was claimed after fiscal_model was "
        "imported. PR #82 added that caption precisely so something is on "
        f"screen during the model load. probe: {result}"
    )
    # Guards the guard: if the builder never imported the model, the two
    # assertions above would pass vacuously.
    assert result.get("model_loaded_at_end") is True, (
        "the probe's dependency builder did not import fiscal_model, so the "
        "ordering assertions above proved nothing."
    )


@pytest.mark.parametrize("symbol", ["build_runtime_metadata", "configure_runtime_logger"])
def test_runtime_logging_helpers_are_still_reachable(symbol: str) -> None:
    """The deferral must not have dropped a helper ``main()`` relies on."""
    import app

    helpers = app._runtime_logging()
    assert len(helpers) == 3
    names = {fn.__name__ for fn in helpers}
    assert symbol in names, f"{symbol} missing from _runtime_logging(): {names}"
