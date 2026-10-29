"""The static export the new site reads equals the API's answers (tools plan FPC-6).

The export calls the API's endpoint functions directly; these tests ask the API
over HTTP, the way the site's live routes will, and compare every preset in both
modes. The committed ``site_data/`` is refreshed nightly, so its *values* may lag
a model change by a day; its *shape* (the preset ids, the schema) may not.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api as api_module
from fiscal_model import api_security
from scripts import export_static

ROOT = Path(__file__).resolve().parents[1]
COMMITTED = ROOT / "site_data"


@pytest.fixture(scope="module")
def exported(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("site_data")
    export_static.export(out)
    return out


@pytest.fixture(scope="module")
def client():
    # ~110 requests in a few seconds: lift the per-caller limit for this module only.
    api_security.configure(per_minute=100_000, burst=100_000)
    yield TestClient(api_module.app)
    api_security.configure()


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_every_preset_equals_the_api_in_both_modes(exported: Path, client: TestClient):
    presets = client.get("/presets").json()["presets"]
    assert _read(exported / "presets" / "index.json")["presets"] == presets
    for preset in presets:
        data = _read(exported / "presets" / f"{preset['id']}.json")
        for mode, dynamic in (("conventional", False), ("dynamic", True)):
            response = client.post(
                "/score/preset", json={"preset_name": preset["id"], "dynamic": dynamic}
            )
            assert response.status_code == 200, (preset["id"], response.text)
            assert data[mode] == response.json(), (preset["id"], mode)


def test_the_scorecard_and_schema_equal_the_api(exported: Path, client: TestClient):
    assert _read(exported / "validation" / "scorecard.json") == client.get(
        "/validation/scorecard"
    ).json()
    schema = _read(exported / "schema" / "score-result.v1.json")
    assert schema == api_module.ScorePolicyResponse.model_json_schema()


def test_the_manifest_counts_what_was_written(exported: Path):
    manifest = _read(exported / "manifest.json")
    assert manifest["schema_version"] == export_static.SCHEMA_VERSION
    assert manifest["presets"] == len(list((exported / "presets").glob("*.json"))) - 1
    assert manifest["build_catalog_rows"] == len(_read(exported / "build-catalog.json"))
    assert manifest["baseline_vintages"] and manifest["budget_windows"]


def test_the_export_is_deterministic(exported: Path, tmp_path: Path):
    """No timestamps: a night with no model change has nothing to commit."""
    export_static.export(tmp_path)
    first = {p.relative_to(exported): p.read_bytes() for p in exported.rglob("*.json")}
    second = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*.json")}
    assert first == second


def test_the_committed_export_has_the_current_shape(exported: Path):
    def names(root: Path) -> set[Path]:
        return {p.relative_to(root) for p in root.rglob("*.json")}

    assert names(COMMITTED) == names(exported), (
        "site_data/ is out of date: run python scripts/export_static.py"
    )
    for path in (Path("schema") / "score-result.v1.json", Path("presets") / "index.json"):
        assert _read(COMMITTED / path) == _read(exported / path), (
            f"site_data/{path} is out of date: run python scripts/export_static.py"
        )


def test_the_tracker_export_matches_the_nightly_database(exported: Path):
    import sqlite3

    index = _read(exported / "tracker" / "index.json")
    scored = _read(exported / "tracker" / "scored.json")
    conn = sqlite3.connect(f"file:{export_static.BILLS_DB}?mode=ro", uri=True)
    try:
        bills = conn.execute("SELECT COUNT(*) FROM bills").fetchone()[0]
        with_cbo = conn.execute(
            "SELECT COUNT(DISTINCT bill_id) FROM cbo_estimates WHERE bill_id IN "
            "(SELECT bill_id FROM bills)"
        ).fetchone()[0]
        last = conn.execute(
            "SELECT value FROM pipeline_state WHERE key = 'last_update'"
        ).fetchone()
    finally:
        conn.close()
    assert index["bills"] == len(index["rows"]) == bills
    assert index["with_cbo_estimate"] == with_cbo
    assert index["last_update"] == (last[0] if last else None)
    has_estimate = {
        r["id"]
        for r in index["rows"]
        if r["cbo_ten_year_billions"] is not None or r["auto_ten_year_billions"] is not None
    }
    assert set(scored) == has_estimate
