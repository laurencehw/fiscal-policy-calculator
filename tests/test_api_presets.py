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


def test_every_listed_preset_has_a_unique_stable_id():
    presets = _client().get("/presets").json()["presets"]
    ids = [p["id"] for p in presets]
    assert len(ids) == len(set(ids)) == len(presets)
    assert all(i and i == i.lower() and " " not in i for i in ids)
    assert "tcja-full-extension" in ids


def test_a_preset_scores_the_same_by_id_and_by_name():
    client = _client()
    preset = next(p for p in client.get("/presets").json()["presets"] if p["id"] == "tcja-full-extension")
    by_id = client.post("/score/preset", json={"preset_name": preset["id"]})
    by_name = client.post("/score/preset", json={"preset_name": preset["name"]})
    assert by_id.status_code == by_name.status_code == 200, by_id.text
    assert by_id.json()["policy_name"] == by_name.json()["policy_name"] == preset["name"]
    assert by_id.json()["ten_year_deficit_impact"] == by_name.json()["ten_year_deficit_impact"]


def test_an_old_share_link_spelling_still_scores():
    # A URL-encoded emoji label, as pasted from a link made before ids existed.
    from urllib.parse import quote_plus

    name = next(p for p in PRESET_POLICIES if p.startswith("🏛️ TCJA Full Extension"))
    response = _client().post("/score/preset", json={"preset_name": quote_plus(name)})
    assert response.status_code == 200, response.text
    assert response.json()["policy_name"] == name


def test_the_placeholder_id_is_refused_too():
    response = _client().post("/score/preset", json={"preset_name": "custom-policy"})
    assert response.status_code == 422
