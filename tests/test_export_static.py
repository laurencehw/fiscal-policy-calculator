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
    index = _read(exported / "presets" / "index.json")["presets"]
    assert [{k: v for k, v in p.items() if k != "cbo_published"} for p in index] == presets
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


def test_only_published_scores_are_flagged_published(exported: Path):
    """The site prints a ``cbo_score`` as "published" only when the flag is set.

    The four below carry a figure in ``CBO_SCORE_MAP`` that is not a published
    score: this repository's own decomposition, two retired targets, and a
    "CBO-style" estimate. Every other figure has a document behind it.
    """
    index = _read(exported / "presets" / "index.json")["presets"]
    unpublished = {p["id"] for p in index if p["cbo_score"] is not None and not p["cbo_published"]}
    assert unpublished == {
        "tcja-extension-no-salt-cap",
        "drug-negotiation-expand",
        "drug-reference-pricing",
        "carbon-tax-50",
    }
    assert all(not p["cbo_published"] for p in index if p["cbo_score"] is None)


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


def test_the_evidence_export_is_the_generated_report(exported: Path):
    from fiscal_model.validation import current_evidence

    assert _read(exported / "validation" / "evidence.json") == json.loads(
        current_evidence.EVIDENCE_PATH.read_text(encoding="utf-8")
    )


def test_the_values_export_is_the_composer(exported: Path):
    from fiscal_model.composer.archetypes import load_archetypes, rationale_template_for
    from fiscal_model.composer.composer import compose_values_package

    written = _read(exported / "values.json")["archetypes"]
    archetypes = load_archetypes()
    assert [a["id"] for a in written] == list(archetypes)
    assert _read(exported / "manifest.json")["values_archetypes"] == len(written)
    catalog = {row["build_id"] for row in _read(exported / "build-catalog.json")}
    for entry in written:
        package = compose_values_package(
            archetypes[entry["id"]].vector, rationale_template=rationale_template_for(entry["id"])
        )
        assert [p["policy_id"] for p in entry["picks"]] == [p.policy_id for p in package.picks]
        assert entry["total_billions"] == pytest.approx(package.total_billions)
        assert {p["policy_id"] for p in entry["picks"]} <= catalog


def test_the_social_security_export_is_the_ledger(exported: Path):
    from fiscal_model.social_security import trust_fund as tf

    data = _read(exported / "social-security.json")
    assert _read(exported / "manifest.json")["social_security_options"] == len(tf.load_catalog())
    assert [p["provision_id"] for p in data["provisions"]] == [p.provision_id for p in tf.load_catalog()]
    span = tf.LAST_YEAR + 2 - tf.FIRST_YEAR
    assert all(len(p["change_cost_rate"]) == span for p in data["provisions"])
    law = data["checks"][0]
    assert law["provision_ids"] == []
    assert law["depletion_year"] == tf.TRUSTEES_OASDI_DEPLETION_YEAR
    for check in data["checks"]:
        expected = tf.project(check["provision_ids"])
        assert check["depletion_year"] == expected.depletion_year
        assert check["change_in_actuarial_balance"] == expected.change_in_actuarial_balance


def test_the_views_export_agrees_with_the_scores(exported: Path):
    """Economic effects reproduce the dynamic score; every preset has a views file."""
    presets = _read(exported / "presets" / "index.json")["presets"]
    assert {p.name for p in (exported / "views").glob("*.json")} == {
        f"{p['id']}.json" for p in presets
    }
    shown = 0
    for preset in presets:
        views = _read(exported / "views" / f"{preset['id']}.json")
        dynamic = _read(exported / "presets" / f"{preset['id']}.json")["dynamic"]
        econ = views["economic"]
        if econ["available"]:
            assert econ["dynamic_total_billions"] == pytest.approx(dynamic["dynamic_adjusted_impact"])
            assert econ["gdp_percent_years"] == pytest.approx(dynamic["gdp_effect"])
            assert len(econ["years"]) == len(econ["gdp_level_pct"]) == len(econ["employment_millions"])
        dist = views["distribution"]
        if dist["available"]:
            shown += 1
            for grouping in dist["groupings"].values():
                total = sum(g["share_of_total"] for g in grouping["groups"])
                assert (grouping["groups"] and abs(total - 1.0) < 0.02) or grouping["total_tax_change_billions"] == 0
        else:
            assert dist["groupings"] == {} and dist["reason"]
    assert shown > 0


def test_the_models_view_leads_with_the_headline(exported: Path):
    """CBO-Style in the comparison is the same scorer as the headline; other pilots may differ."""
    paired = 0
    for preset in _read(exported / "presets" / "index.json")["presets"]:
        models = _read(exported / "views" / f"{preset['id']}.json")["models"]
        headline = _read(exported / "presets" / f"{preset['id']}.json")["conventional"]
        cbo = [r for r in models["results"] if r["model"] == "CBO-Style"]
        assert cbo and cbo[0]["ten_year_billions"] == pytest.approx(headline["ten_year_deficit_impact"])
        assert all(s["reason"] for s in models["skipped"])
        paired += len(models["results"]) > 1
    assert paired > 0


def test_the_states_export_is_the_state_module(exported: Path):
    from fiscal_model.models.state.database import SUPPORTED_STATES

    states = _read(exported / "states.json")
    assert [s["code"] for s in states["states"]] == list(SUPPORTED_STATES)
    assert _read(exported / "manifest.json")["states"] == len(SUPPORTED_STATES)
    for s in states["states"]:
        assert s["rate_curve"] and all(
            r["combined_rate"] == pytest.approx(r["federal_rate"] + r["state_rate"]) for r in s["rate_curve"]
        )


def test_the_classroom_export_is_the_assignments_without_answers(exported: Path):
    from classroom.engine import AssignmentLoader

    ids = AssignmentLoader().list_assignments()
    index = _read(exported / "classroom" / "index.json")
    assert [row["id"] for row in index] == ids
    assert _read(exported / "manifest.json")["classroom_assignments"] == len(ids)
    for assignment_id in ids:
        text = (exported / "classroom" / f"{assignment_id}.json").read_text(encoding="utf-8")
        assert "min_acceptable" not in text and "policy_params" not in text
