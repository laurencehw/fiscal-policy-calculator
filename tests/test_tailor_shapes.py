"""Tailor's "Adjust in Tailor" shapes reproduce their presets through the live route.

``web/lib/adjust.ts`` lists the presets Tailor can score as a rate and a
threshold, with each one's ten-year figure. The web test checks that figure
against the preset file, which catches a preset that drifts but not a Tailor
path that drifts. This test sends each shape through ``POST /score``, the
engine route the site's ``/api/score`` forwards to, built the way
``engineRequest`` in ``web/lib/tailor.ts`` builds it, and asserts the
conventional ten-year figure matches the exported preset to the cent.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api as api_module
from fiscal_model import api_security

ROOT = Path(__file__).resolve().parents[1]
ADJUST_TS = ROOT / "web" / "lib" / "adjust.ts"
TAILOR_TS = ROOT / "web" / "lib" / "tailor.ts"

_SHAPE = re.compile(
    r'"(?P<id>[a-z0-9-]+)":\s*\{\s*kind:\s*"(?P<kind>income|corporate)",\s*'
    r"rate:\s*(?P<rate>-?[\d.]+),\s*who:\s*(?P<who>[\d_]+),\s*"
    r"duration:\s*(?P<duration>\d+),\s*dynamic:\s*(?:true|false),\s*"
    r"tenYear:\s*(?P<ten>-?[\d.]+)\s*\}"
)


def _shapes() -> list[dict]:
    text = ADJUST_TS.read_text(encoding="utf-8")
    block = text[text.index("TAILOR_SHAPES") :]
    block = block[: block.index("};")]
    shapes = [m.groupdict() for m in _SHAPE.finditer(block)]
    # Every entry in the block must parse, or a shape would silently go unchecked.
    assert len(shapes) == block.count("kind:"), "a TAILOR_SHAPES entry did not parse"
    return shapes


def _engine_request(shape: dict) -> dict:
    """The body ``engineRequest`` sends for this shape."""
    rate = float(shape["rate"])
    corporate = shape["kind"] == "corporate"
    return {
        "name": f"Tailor {shape['id']}",
        "description": "Tailor shape check.",
        "rate_change": round(rate * 1e6) / 1e8,
        "income_threshold": 0 if corporate else int(shape["who"].replace("_", "")),
        "duration_years": int(shape["duration"]),
        "dynamic": True,
        "policy_type": "corporate_tax" if corporate else "income_tax",
    }


def test_the_request_shape_here_is_the_one_tailor_sends():
    # If engineRequest changes how it builds the body, this copy must follow.
    text = TAILOR_TS.read_text(encoding="utf-8")
    for fragment in (
        "rate_change: Math.round(input.rate * 1e6) / 1e8",
        'income_threshold: input.kind === "corporate" ? 0 : input.who',
        "duration_years: input.duration",
        "dynamic: true",
        'policy_type: input.kind === "corporate" ? "corporate_tax" : "income_tax"',
    ):
        assert fragment in text, fragment


@pytest.fixture(scope="module")
def client():
    api_security.configure(per_minute=100_000, burst=100_000)
    yield TestClient(api_module.app)
    api_security.configure()


@pytest.mark.parametrize("shape", _shapes(), ids=lambda s: s["id"])
def test_each_tailor_shape_scores_its_preset_to_the_cent(shape: dict, client: TestClient):
    response = client.post("/score", json=_engine_request(shape))
    assert response.status_code == 200, response.text
    live = response.json()["ten_year_deficit_impact"]
    preset = json.loads((ROOT / "site_data" / "presets" / f"{shape['id']}.json").read_text(encoding="utf-8"))
    exported = preset["conventional"]["ten_year_deficit_impact"]
    assert round(live, 2) == round(exported, 2), (shape["id"], live, exported)
    assert round(live, 2) == float(shape["ten"]), (shape["id"], live, shape["ten"])
