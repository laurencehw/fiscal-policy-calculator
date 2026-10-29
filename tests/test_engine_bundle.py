"""The engine-only API (``engine/``, tools plan FPC-4) runs without the UI stack.

The Vercel function installs ``engine/pyproject.toml``, which leaves out
streamlit, plotly, matplotlib and pyarrow. These tests import the API with those
packages blocked, score a preset, and check that every third-party package the
API imported is declared there.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "engine"
UI_ONLY = ("streamlit", "plotly", "matplotlib", "pyarrow")
#: Import name -> distribution name, where they differ.
DISTRIBUTIONS = {"yaml": "pyyaml", "bs4": "beautifulsoup4"}

_PROBE = """
import importlib.abc, json, sys
BLOCKED = {blocked!r}

class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in BLOCKED:
            raise ImportError(f"{{name}} is not in the engine bundle")
        return None

sys.meta_path.insert(0, Block())
sys.path.insert(0, {engine!r})
import index
from fastapi.testclient import TestClient

client = TestClient(index.app)
response = client.post("/score/preset", json={{"preset_name": "tcja-full-extension"}})
classroom = client.post(
    "/classroom/check",
    json={{"assignment_id": "laffer_curve", "exercise_id": "laffer_ug_ex1", "answer": -266}},
)
stdlib = set(sys.stdlib_module_names)
third_party = sorted(
    {{m.split(".")[0] for m in sys.modules}}
    - stdlib
    - {{"api", "index", "fiscal_model", "classroom", "__main__"}}
)
print(json.dumps({{"status": response.status_code, "classroom": classroom.status_code, "modules": third_party}}))
"""


def _declared() -> set[str]:
    # tomllib is 3.11+ and CI still runs 3.10, so read the list by hand.
    text = (ENGINE / "pyproject.toml").read_text(encoding="utf-8")
    block = re.search(r"^dependencies = \[(.*?)^\]", text, re.S | re.M)
    assert block, "engine/pyproject.toml has no dependencies list"
    names = set()
    for spec in re.findall(r'"([^"]+)"', block.group(1)):
        name = spec.split(">")[0].split("<")[0].split("=")[0].split("[")[0].strip()
        names.add(name.lower().replace("_", "-"))
    return names


def test_the_engine_declares_no_ui_package():
    assert not _declared() & set(UI_ONLY)


def test_the_api_scores_with_the_ui_stack_blocked():
    probe = _PROBE.format(blocked=UI_ONLY, engine=str(ENGINE))
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={"PATH": "", "ANTHROPIC_API_KEY": ""},
        timeout=300,
    )
    assert result.returncode == 0, result.stderr[-3000:]
    report = json.loads(result.stdout.strip().splitlines()[-1])
    assert report["status"] == 200
    assert report["classroom"] == 200
    # Every top-level package the API pulled in is either declared or a
    # dependency of a declared one (pydantic, starlette, etc. come with fastapi).
    imported = {DISTRIBUTIONS.get(m, m).lower().replace("_", "-") for m in report["modules"]}
    for package in ("numpy", "pandas", "scipy", "pydantic", "fastapi", "pyyaml"):
        assert package in _declared()
    assert not imported & set(UI_ONLY)


def test_the_build_step_copies_the_engine(tmp_path: Path):
    sys.path.insert(0, str(ENGINE))
    try:
        import build
    finally:
        sys.path.remove(str(ENGINE))
    build.main(tmp_path)
    assert (tmp_path / "api.py").read_bytes() == (ROOT / "api.py").read_bytes()
    assert (tmp_path / "fiscal_model" / "scoring.py").exists()
    assert (tmp_path / "classroom" / "assignments" / "laffer_curve.yaml").exists()
    assert not list((tmp_path / "fiscal_model").rglob("bills*.db"))
    assert not list((tmp_path / "fiscal_model").rglob("__pycache__"))
