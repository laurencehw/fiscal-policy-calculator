"""``/presets`` and ``/score/preset`` and the UI's "Custom Policy" placeholder.

``POST /score/preset {"preset_name": "Custom Policy"}`` used to score the
placeholder (-2pp at $500K) as though it were a proposal.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

import api as api_module
from fiscal_model.app_data import PRESET_POLICIES
from fiscal_model.preset_ids import CUSTOM_POLICY_LABEL


def _client() -> TestClient:
    return TestClient(api_module.app)


def test_the_placeholder_is_not_listed():
    payload = _client().get("/presets").json()
    names = [p["name"] for p in payload["presets"]]
    assert CUSTOM_POLICY_LABEL not in names
    assert payload["count"] == len(names) == len(PRESET_POLICIES) - 1


def test_the_placeholder_is_refused_with_a_pointer_to_score():
    response = _client().post("/score/preset", json={"preset_name": CUSTOM_POLICY_LABEL})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "placeholder" in detail
    assert "/score" in detail


def test_a_real_preset_still_scores():
    name = next(n for n in PRESET_POLICIES if n != CUSTOM_POLICY_LABEL)
    response = _client().post("/score/preset", json={"preset_name": name})
    assert response.status_code == 200, response.text
    assert response.json()["policy_name"] == name
