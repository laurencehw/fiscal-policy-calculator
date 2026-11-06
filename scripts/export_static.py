#!/usr/bin/env python3
"""Write the static export the new site reads (tools plan FPC-5 and FPC-6).

Everything a visitor can see without scoring something new is computed here,
once a night, and written as JSON under ``site_data/``:

- ``manifest.json``: schema version, baseline vintage, budget window, counts.
- ``schema/score-result.v1.json``: the JSON Schema of one score, the API's own
  ``ScorePolicyResponse``. The site generates its TypeScript types from it.
- ``presets/index.json``: the API's ``/presets`` answer, plus ``cbo_published``
  per preset: whether its ``cbo_score`` is a published figure. It is false when
  the scorecard row behind it is this repository's own estimate
  (``model_estimate`` provenance) or a retired target, so the site never labels
  either one "published".
- ``presets/<id>.json``: one preset, ``{"conventional": …, "dynamic": …}``,
  each the API's ``/score/preset`` answer for that id.
- ``build-catalog.json``: the Build page's checkable rows, in catalog order.
- ``validation/scorecard.json``: the API's ``/validation/scorecard`` answer.
- ``validation/evidence.json``: the generated validation figures the app's About
  and Methodology pages quote (``current_evidence.json``), copied as is.
- ``tracker/index.json``: every bill the nightly job has ingested, one line each,
  with its latest CBO estimate and calculator auto-score where it has them, so
  the site can list all bills or only those with a fiscal estimate (decision F4).
- ``tracker/scored.json``: the detail for bills with an estimate: summary,
  annual path, and the provisions the auto-scorer mapped.
- ``values.json``: Build's five starting philosophies and the package the
  deterministic composer picks for each, with the "why" line for every pick.
- ``classroom/index.json`` and ``classroom/<id>.json``: the Classroom
  assignments as a student sees them, without instructor notes or the numbers
  an answer is checked against; the engine's ``/classroom/check`` holds those.
- ``ranges.json``: where a corporate-rate or published-range preset sits among
  the houses that scored it (``estimator_ranges.house_strip``).
- ``baseline.json``: CBO's February 2026 deficit, debt held by the public and
  nominal GDP by fiscal year, so a proposal page can draw the policy on the
  baseline. Deficit keeps CBO's sign.
- ``changes.json``: what moved since the previous export, kept for a year:
  preset scores that moved by more than 0.5% (old and new figures), new CBO
  estimates in the tracker, and a baseline vintage change. Each item says
  whether it is a score change or a data refresh. It is built only from
  exported files, so no visitor's scenario can ever appear in it.
- ``social-security.json``: the Social Security page's inputs (Trustees
  baseline rates, OCACT options and their annual paths, the CRFB comparison)
  plus the ledger's own answers for current law and each option alone, which
  the site's TypeScript ledger is tested against.

The script calls the API's own endpoint functions, so an exported preset is the
API's answer by construction; ``tests/test_export_static.py`` checks it anyway.
The output carries no timestamps, so a night with no model change writes
identical files and the nightly job has nothing to commit. The one date in it,
``manifest.json``'s ``scores_date``, is the day the scored figures last changed:
it moves only when ``scores_fingerprint`` does, and share links carry it as
``v=`` so a page can say when the numbers behind an old link were recomputed.

Usage:
    python scripts/export_static.py                 # writes site_data/
    python scripts/export_static.py --out /tmp/x    # writes elsewhere
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

#: Bump when a field is removed or changes meaning; adding a field does not.
SCHEMA_VERSION = 1
DEFAULT_OUT = ROOT / "site_data"
BILLS_DB = ROOT / "fiscal_model" / "data_files" / "bills.db"


def _write(path: Path, payload: Any, *, compact: bool = False) -> None:
    """Indented JSON, or for large files one top-level entry per line.

    The compact layout keeps the file small and still gives git a line per bill,
    so a nightly diff shows which bills changed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if not compact:
        text = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False)
    else:

        def line(value: Any) -> str:
            return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))

        if isinstance(payload, list):
            text = "[\n" + ",\n".join(line(v) for v in payload) + "\n]"
        else:
            items = []
            for key, value in payload.items():
                if isinstance(value, list):
                    inner = ",\n".join(line(v) for v in value)
                    items.append(f"{line(key)}:[\n{inner}\n]")
                else:
                    items.append(f"{line(key)}:{line(value)}")
            text = "{\n" + ",\n".join(items) + "\n}"
    path.write_text(text + "\n", encoding="utf-8")


#: Presets the house strip can draw. A statutory-rate change with no direct
#: multi-house score uses the converted per-point record. A policy whose own
#: target is a published range uses that range, not a scaled rate.
STRIP_POLICY_IDS: dict[str, str] = {
    "corporate-28pct": "biden_corporate_28",
    "corporate-15pct": "trump_corporate_15",
    "pillar-two-adoption": "pillar_two_adoption",
    "tariff-reciprocal": "reciprocal_tariffs",
}


def estimator_strips_payload(model_billions_by_preset: dict[str, float]) -> dict[str, Any]:
    """House strips for the presets that have one. Keyed by preset id."""
    import api
    from fiscal_model.preset_ids import resolve_preset
    from fiscal_model.ui.estimator_ranges import house_strip
    from fiscal_model.ui.preset_validation import TIER_FITTED, get_validation_badge

    strips: dict[str, Any] = {}
    for preset_id, policy_id in STRIP_POLICY_IDS.items():
        label = resolve_preset(preset_id) or preset_id
        policy, _use_real_data = api._build_preset_policy(label)
        badge = get_validation_badge(preset_id)
        fitted = None
        if badge is not None and badge.get("tier") == TIER_FITTED:
            fitted = float(badge["official"])
        strip = house_strip(
            policy_id=policy_id,
            policy=policy,
            model_billions=model_billions_by_preset[preset_id],
            fitted_target_billions=fitted,
        )
        if strip is not None:
            strips[preset_id] = strip
    return strips


def _commented_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        body = (line for line in handle if not line.startswith("#"))
        return list(csv.DictReader(body))


def baseline_payload() -> dict[str, Any]:
    """February 2026 deficit, debt and nominal GDP, FY2026-2035.

    Read from the transcribed CBO tables. ``deficit_billions`` keeps CBO's
    sign: negative is a deficit. The site flips it for display.
    """
    data = ROOT / "fiscal_model" / "data_files" / "cbo_baseline"
    vintage = "cbo_feb_2026"
    budget: dict[tuple[str, int], float] = {}
    for row in _commented_csv(data / "cbo_budget_baseline.csv"):
        if row["vintage"] != vintage:
            continue
        if row["variable"] not in {"deficit_total", "debt_held_by_public"}:
            continue
        budget[(row["variable"], int(row["fiscal_year"]))] = float(row["value"])
    gdp: dict[int, float] = {}
    for row in _commented_csv(data / "cbo_economic_baseline.csv"):
        if row["vintage"] == vintage and row["variable"] == "nominal_gdp":
            gdp[int(row["fiscal_year"])] = float(row["value"])
    years = []
    for year in range(2026, 2036):
        years.append(
            {
                "fiscal_year": year,
                "deficit_billions": budget[("deficit_total", year)],
                "debt_held_by_public_billions": budget[("debt_held_by_public", year)],
                "nominal_gdp_billions": gdp[year],
            }
        )
    return {
        "vintage": vintage,
        "vintage_label": "February 2026",
        "window": "FY2026-2035",
        "years": years,
    }


def score_preset_payload(preset_id: str, *, dynamic: bool) -> dict[str, Any]:
    """The API's ``/score/preset`` answer for ``preset_id``, as JSON-ready data."""
    import api

    response = api.score_preset(
        api.ScorePresetRequest(preset_name=preset_id, dynamic=dynamic),
        _api_key_label="static-export",
    )
    return response.model_dump(mode="json")


def preset_views_payload(preset_id: str, comparison_models: dict[bool, Any] | None = None) -> dict[str, Any]:
    """Who pays, economic effects and other models for ``preset_id``, scored as ``/score/preset`` scores it."""
    import api
    from fiscal_model.models.comparison import build_default_comparison_models
    from fiscal_model.preset_ids import resolve_preset
    from fiscal_model.result_views import distribution_view, economic_view, models_view

    label = resolve_preset(preset_id) or preset_id
    policy, use_real_data = api._build_preset_policy(label)
    scorer = api.FiscalPolicyScorer(
        start_year=max(int(getattr(policy, "start_year", api.APP_DEFAULT_START_YEAR)), api.APP_DEFAULT_START_YEAR),
        use_real_data=use_real_data,
    )
    result = scorer.score_policy(policy, dynamic=False)
    cache = comparison_models if comparison_models is not None else {}
    if use_real_data not in cache:
        cache[use_real_data] = build_default_comparison_models(api.FiscalPolicyScorer, use_real_data=use_real_data)
    return {
        "id": preset_id,
        "distribution": distribution_view(policy),
        "economic": economic_view(policy, result),
        "models": models_view(policy, cache[use_real_data]),
    }


def preset_index_payload() -> dict[str, Any]:
    import api
    from fiscal_model.ui.preset_validation import (
        PRESET_ID_TO_SCORECARD_ID,
        get_validation_badge,
    )
    from fiscal_model.validation.provenance import MODEL_ESTIMATE
    from fiscal_model.validation.target_revisions import RETIRED_POLICY_IDS

    payload = api.list_presets().model_dump(mode="json")
    for info in payload["presets"]:
        published = info["cbo_score"] is not None
        if published and PRESET_ID_TO_SCORECARD_ID.get(info["id"]) in RETIRED_POLICY_IDS:
            published = False
        if published:
            badge = get_validation_badge(info["id"])
            if badge is not None and badge.get("provenance") == MODEL_ESTIMATE:
                published = False
        info["cbo_published"] = published
    return payload


def build_catalog_payload() -> list[dict[str, Any]]:
    from fiscal_model.app_data import CBO_SCORE_MAP
    from fiscal_model.ui.tabs.deficit_target import build_catalog

    rows = []
    for option in build_catalog(CBO_SCORE_MAP).values():
        row = asdict(option)
        row["exclusive_groups"] = list(option.exclusive_groups)
        row["subsumes"] = list(option.subsumes)
        row["tags"] = dict(option.tags)
        rows.append(row)
    return rows


def evidence_payload() -> dict[str, Any]:
    """The generated validation figures, as ``current_evidence`` reads them."""
    from fiscal_model.validation import current_evidence

    return json.loads(current_evidence.EVIDENCE_PATH.read_text(encoding="utf-8"))


def scorecard_payload() -> dict[str, Any]:
    import api

    return api.validation_scorecard().model_dump(mode="json")


def _json_or(text: str | None, default: Any) -> Any:
    try:
        return json.loads(text) if text else default
    except ValueError:
        return default


def tracker_payloads(db_path: Path = BILLS_DB) -> tuple[dict[str, Any], dict[str, Any]]:
    """``(index, scored)`` for the tracker, read from the nightly database."""
    import sqlite3

    from bill_tracker.ingestor import congress_gov_url

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        # Newest row per bill wins, as in BillDatabase.get_fiscal_impact_map.
        cbo = {
            r["bill_id"]: dict(r)
            for r in conn.execute("SELECT * FROM cbo_estimates ORDER BY estimate_date, id")
        }
        auto = {
            r["bill_id"]: dict(r)
            for r in conn.execute("SELECT * FROM auto_scores ORDER BY scored_at, id")
        }
        state = conn.execute(
            "SELECT value FROM pipeline_state WHERE key = 'last_update'"
        ).fetchone()
        bills = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM bills ORDER BY introduced_date DESC, bill_id"
            )
        ]
    finally:
        conn.close()

    rows = []
    scored = {}
    for bill in bills:
        bill_id = bill["bill_id"]
        estimate = cbo.get(bill_id)
        score = auto.get(bill_id)
        rows.append(
            {
                "id": bill_id,
                "congress": bill["congress"],
                "chamber": bill["chamber"],
                "type": bill["bill_type"],
                "number": bill["number"],
                "title": bill["title"],
                "sponsor": bill["sponsor"],
                "introduced": bill["introduced_date"],
                "latest_action": bill["latest_action"],
                "latest_action_date": bill["latest_action_date"],
                "status": bill["status"],
                # Rebuilt from type and number: rows ingested before Nov 2026
                # carry a chamber-bill path for every resolution.
                "url": congress_gov_url(bill["congress"], bill["bill_type"], bill["number"]) or bill["url"],
                "cbo_ten_year_billions": estimate["ten_year_cost_billions"] if estimate else None,
                "auto_ten_year_billions": score["ten_year_cost_billions"] if score else None,
                "auto_confidence": score["confidence"] if score else None,
            }
        )
        if estimate or score:
            scored[bill_id] = {
                "summary": bill["summary"],
                "subjects": _json_or(bill["crs_subjects"], []),
                "cbo": None
                if not estimate
                else {
                    "date": estimate["estimate_date"],
                    "ten_year_billions": estimate["ten_year_cost_billions"],
                    "annual_billions": _json_or(estimate["annual_costs"], []),
                    "dynamic_billions": estimate["dynamic_estimate"],
                    "url": estimate["cbo_url"] or estimate["pdf_url"],
                },
                "auto": None
                if not score
                else {
                    "scored_at": score["scored_at"],
                    "ten_year_billions": score["ten_year_cost_billions"],
                    "annual_billions": _json_or(score["annual_effects"], []),
                    "confidence": score["confidence"],
                    "provisions": _json_or(score["policies_json"], []),
                },
            }
    index = {
        "last_update": state["value"] if state else None,
        "bills": len(rows),
        "with_cbo_estimate": sum(r["cbo_ten_year_billions"] is not None for r in rows),
        "with_auto_score": sum(r["auto_ten_year_billions"] is not None for r in rows),
        "sign_convention": "Billions over ten years; positive increases the deficit.",
        "rows": rows,
    }
    return index, scored


def values_payload() -> dict[str, Any]:
    """Build's "Start from your values": each archetype and its composed package."""
    from fiscal_model.composer.archetypes import load_archetypes, rationale_template_for
    from fiscal_model.composer.composer import compose_values_package
    from fiscal_model.composer.values_schema import PROTECTED_LABELS

    archetypes = []
    for archetype in load_archetypes().values():
        package = compose_values_package(
            archetype.vector, rationale_template=rationale_template_for(archetype.id)
        )
        vector = package.vector
        archetypes.append(
            {
                "id": archetype.id,
                "name": archetype.name,
                "one_line": archetype.one_line,
                "chips": list(archetype.chips),
                "target_pct_gdp": float(vector.target_pct_gdp),
                "protected": [PROTECTED_LABELS[key] for key in vector.protected],
                "summary": package.summary(),
                "gap_billions": package.gap_billions,
                "total_billions": package.total_billions,
                "picks": [
                    {
                        "policy_id": pick.policy_id,
                        "label": pick.label,
                        "score": pick.score,
                        "why": pick.why,
                        "tags": dict(pick.tags),
                    }
                    for pick in package.picks
                ],
            }
        )
    return {"archetypes": archetypes}


def social_security_payload() -> dict[str, Any]:
    """Everything the Social Security page needs; the site runs the ledger itself."""
    from fiscal_model.social_security import trust_fund as tf
    from fiscal_model.social_security.crfb_benchmark import METRIC_LABELS, crfb_comparison

    years = list(range(tf.FIRST_YEAR, tf.LAST_YEAR + 2))
    paths = tf.load_provision_paths()

    def checked(projection: tf.Projection) -> dict[str, Any]:
        return {
            "provision_ids": list(projection.provision_ids),
            "depletion_year": projection.depletion_year,
            "payable_at_depletion": projection.payable_at_depletion,
            "change_in_actuarial_balance": projection.change_in_actuarial_balance,
            "computed_actuarial_balance": projection.computed_actuarial_balance,
            "trust_fund_ratio": list(projection.trust_fund_ratio),
        }

    catalog = tf.load_catalog()
    return {
        "first_year": tf.FIRST_YEAR,
        "last_year": tf.LAST_YEAR,
        "reserves_end_2025": tf.RESERVES_END_2025,
        "baseline_cost_rate_2101": tf.BASELINE_COST_RATE_2101,
        "trustees": {
            "actuarial_balance": tf.TRUSTEES_ACTUARIAL_BALANCE,
            "oasdi_depletion_year": tf.TRUSTEES_OASDI_DEPLETION_YEAR,
            "oasdi_payable_pct": tf.TRUSTEES_OASDI_PAYABLE_PCT,
            "oasi_depletion": tf.TRUSTEES_OASI_DEPLETION,
            "oasi_payable_pct": tf.TRUSTEES_OASI_PAYABLE_PCT,
        },
        "baseline": [asdict(row) for row in tf.load_baseline() if row.year >= tf.FIRST_YEAR - 1],
        "categories": tf.CATEGORY_LABELS,
        "provisions": [
            {**asdict(p), "source_url": p.source_url,
             "change_cost_rate": [paths[p.provision_id].change_cost_rate[y] for y in years],
             "change_income_rate": [paths[p.provision_id].change_income_rate[y] for y in years]}
            for p in catalog
        ],
        "crfb": [
            {
                "crfb_item": r.crfb_item,
                "measure": METRIC_LABELS[r.metric] + (" (OASI)" if r.framing == "oasi" else ""),
                "crfb": r.display(r.crfb_value, ours=False),
                "ours": r.display(r.our_value, ours=True),
                "our_basis": r.our_basis,
                "note": r.note,
                "source_url": r.source_url,
            }
            for r in crfb_comparison()
        ],
        "checks": [checked(tf.project(()))]
        + [checked(tf.project((p.provision_id,))) for p in catalog],
    }


def classroom_payloads() -> dict[str, Any]:
    """Classroom assignments as students see them: no instructor notes, no answers."""
    from classroom.engine import AssignmentLoader
    from classroom.web import assignment_payload, index_payload

    loader = AssignmentLoader()
    return {
        "index": index_payload(loader),
        "assignments": [assignment_payload(loader.load(i)) for i in loader.list_assignments()],
    }


def scores_fingerprint(figures: dict[str, Any]) -> str:
    """A short hash of the scored figures, rounded to $0.1B so float noise is not a change."""

    def rounded(value: Any) -> Any:
        if isinstance(value, float):
            return round(value, 1) + 0.0  # -0.0 and 0.0 hash alike
        if isinstance(value, dict):
            return {k: rounded(v) for k, v in sorted(value.items())}
        if isinstance(value, list):
            return [rounded(v) for v in value]
        return value

    text = json.dumps(rounded(figures), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def scores_date(fingerprint: str, previous: dict[str, Any] | None, today: str) -> str:
    """Keep the previous date while the figures are unchanged; otherwise today."""
    if previous and previous.get("scores_fingerprint") == fingerprint and previous.get("scores_date"):
        return str(previous["scores_date"])
    return today


#: A preset figure must move by more than this share (or $0.1B near zero) to be listed.
CHANGE_THRESHOLD = 0.005
CHANGE_FLOOR_BILLIONS = 0.1
#: How long changes.json keeps an item, and the most it keeps.
CHANGES_KEEP_DAYS = 400
CHANGES_KEEP_MAX = 500


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def export_snapshot(out: Path) -> dict[str, Any] | None:
    """The figures an export published, read back from its files; None if there is no export."""
    index = _read_json(out / "presets" / "index.json")
    if not isinstance(index, dict):
        return None
    presets: dict[str, Any] = {}
    vintages: set[str] = set()
    for info in index.get("presets", []):
        data = _read_json(out / "presets" / f"{info['id']}.json")
        if not isinstance(data, dict):
            continue
        conventional = data.get("conventional") or {}
        dynamic = data.get("dynamic") or {}
        presets[info["id"]] = {
            "name": info.get("name") or conventional.get("policy_name") or info["id"],
            "conventional": conventional.get("ten_year_deficit_impact"),
            "dynamic": dynamic.get("dynamic_adjusted_impact"),
        }
        if conventional.get("baseline_vintage"):
            vintages.add(conventional["baseline_vintage"])
    cbo: dict[str, Any] = {}
    tracker = _read_json(out / "tracker" / "index.json")
    if isinstance(tracker, dict):
        for row in tracker.get("rows", []):
            if row.get("cbo_ten_year_billions") is not None:
                cbo[row["id"]] = {
                    "title": row.get("title", ""),
                    "ten_year": row["cbo_ten_year_billions"],
                    "url": row.get("url") or "",
                }
    return {"presets": presets, "cbo": cbo, "vintages": sorted(vintages)}


def _moved(old: Any, new: Any) -> bool:
    if old is None or new is None:
        return (old is None) != (new is None)
    diff = abs(float(new) - float(old))
    return diff > max(CHANGE_FLOOR_BILLIONS, CHANGE_THRESHOLD * abs(float(old)))


def _rounded(value: Any) -> Any:
    return None if value is None else round(float(value), 1)


def changes_between(
    before: dict[str, Any] | None, after: dict[str, Any], today: str
) -> list[dict[str, Any]]:
    """What moved from one export to the next. Nothing when there is no earlier export."""
    if not before:
        return []
    items: list[dict[str, Any]] = []
    if before["vintages"] != after["vintages"]:
        items.append(
            {
                "date": today,
                "category": "data",
                "kind": "baseline",
                "id": "baseline",
                "title": "Baseline vintage",
                "old": ", ".join(before["vintages"]),
                "new": ", ".join(after["vintages"]),
                "href": "/methods",
            }
        )
    for preset_id, now in sorted(after["presets"].items()):
        then = before["presets"].get(preset_id)
        if then is None:
            continue
        if _moved(then["conventional"], now["conventional"]) or _moved(then["dynamic"], now["dynamic"]):
            items.append(
                {
                    "date": today,
                    "category": "score",
                    "kind": "preset",
                    "id": preset_id,
                    "title": now["name"],
                    "old": _rounded(then["conventional"]),
                    "new": _rounded(now["conventional"]),
                    "old_dynamic": _rounded(then["dynamic"]),
                    "new_dynamic": _rounded(now["dynamic"]),
                    "href": f"/explore/{preset_id}",
                }
            )
    for bill_id, estimate in sorted(after["cbo"].items()):
        if bill_id in before["cbo"]:
            continue
        items.append(
            {
                "date": today,
                "category": "data",
                "kind": "cbo_estimate",
                "id": bill_id,
                "title": estimate["title"],
                "old": None,
                "new": _rounded(estimate["ten_year"]),
                "href": estimate.get("url") or "/tracker",
            }
        )
    return items


def merged_changes(
    previous: list[dict[str, Any]], new: list[dict[str, Any]], today: str
) -> list[dict[str, Any]]:
    """New items first, then the kept ones, newest first, trimmed by age and count."""
    cutoff = (dt.date.fromisoformat(today) - dt.timedelta(days=CHANGES_KEEP_DAYS)).isoformat()
    kept = [item for item in previous if str(item.get("date", "")) >= cutoff]
    items = sorted(new + kept, key=lambda item: str(item.get("date", "")), reverse=True)
    return items[:CHANGES_KEEP_MAX]


def _previous_manifest(out: Path) -> dict[str, Any] | None:
    for path in (out / "manifest.json", DEFAULT_OUT / "manifest.json"):
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None
    return None


def export(out: Path, *, today: str | None = None) -> dict[str, Any]:
    """Write the whole export to ``out`` (replacing it) and return the manifest."""
    import api

    previous = _previous_manifest(out)
    before = export_snapshot(out)
    previous_changes = _read_json(out / "changes.json")
    if not isinstance(previous_changes, dict):
        previous_changes = {"items": []}
    day = today or dt.datetime.now(dt.timezone.utc).date().isoformat()
    if out.exists():
        shutil.rmtree(out)

    index = preset_index_payload()
    _write(out / "presets" / "index.json", index)

    vintages: set[str] = set()
    comparison_models: dict[bool, Any] = {}
    windows: set[str] = set()
    headlines: dict[str, float] = {}
    figures: dict[str, Any] = {"presets": {}, "build": {}}
    for preset in index["presets"]:
        conventional = score_preset_payload(preset["id"], dynamic=False)
        dynamic = score_preset_payload(preset["id"], dynamic=True)
        if preset["id"] in STRIP_POLICY_IDS:
            headlines[preset["id"]] = float(conventional["ten_year_deficit_impact"])
        figures["presets"][preset["id"]] = [
            conventional.get("ten_year_deficit_impact"),
            dynamic.get("dynamic_adjusted_impact"),
        ]
        vintages.add(conventional["baseline_vintage"])
        windows.add(conventional["budget_window"])
        _write(
            out / "presets" / f"{preset['id']}.json",
            {"id": preset["id"], "conventional": conventional, "dynamic": dynamic},
        )
        _write(out / "views" / f"{preset['id']}.json", preset_views_payload(preset["id"], comparison_models))

    catalog = build_catalog_payload()
    _write(out / "build-catalog.json", catalog)
    figures["build"] = {row["build_id"]: row["score"] for row in catalog}
    scorecard = scorecard_payload()
    _write(out / "validation" / "scorecard.json", scorecard)
    _write(out / "validation" / "evidence.json", evidence_payload())
    tracker_index, tracker_scored = tracker_payloads()
    # 11,000 bills: indentation alone would double the size.
    _write(out / "tracker" / "index.json", tracker_index, compact=True)
    _write(out / "tracker" / "scored.json", tracker_scored, compact=True)
    values = values_payload()
    _write(out / "values.json", values)
    from fiscal_model.result_views import states_view

    states = states_view()
    _write(out / "states.json", states)
    _write(out / "ranges.json", estimator_strips_payload(headlines))
    _write(out / "baseline.json", baseline_payload())
    social_security = social_security_payload()
    _write(out / "social-security.json", social_security, compact=True)
    classroom = classroom_payloads()
    _write(out / "classroom" / "index.json", classroom["index"])
    for assignment in classroom["assignments"]:
        _write(out / "classroom" / f"{assignment['id']}.json", assignment)
    _write(
        out / "schema" / f"score-result.v{SCHEMA_VERSION}.json",
        api.ScorePolicyResponse.model_json_schema(),
    )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        # Presets that start later than the app window score their own window,
        # so these are lists; the site shows each result's own fields.
        "baseline_vintages": sorted(vintages),
        "budget_windows": sorted(windows),
        "presets": index["count"],
        "build_catalog_rows": len(catalog),
        "scorecard_entries": scorecard["total_entries"],
        "tracker_bills": tracker_index["bills"],
        "tracker_last_update": tracker_index["last_update"],
        "values_archetypes": len(values["archetypes"]),
        "social_security_options": len(social_security["provisions"]),
        "states": len(states["states"]),
        "classroom_assignments": len(classroom["index"]),
        "sign_convention": (
            "Billions of dollars over the budget window; positive increases "
            "the deficit, negative reduces it."
        ),
    }
    fingerprint = scores_fingerprint({**figures, "vintages": sorted(vintages)})
    manifest["scores_fingerprint"] = fingerprint
    manifest["scores_date"] = scores_date(fingerprint, previous, day)
    _write(out / "manifest.json", manifest)
    after = export_snapshot(out)
    new_items = changes_between(before, after, day) if after else []
    _write(
        out / "changes.json",
        {
            "threshold": CHANGE_THRESHOLD,
            "items": merged_changes(list(previous_changes.get("items", [])), new_items, day),
        },
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    manifest = export(args.out)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
