#!/usr/bin/env python3
"""Write the static export the new site reads (tools plan FPC-5 and FPC-6).

Everything a visitor can see without scoring something new is computed here,
once a night, and written as JSON under ``site_data/``:

- ``manifest.json``: schema version, baseline vintage, budget window, counts.
- ``schema/score-result.v1.json``: the JSON Schema of one score, the API's own
  ``ScorePolicyResponse``. The site generates its TypeScript types from it.
- ``presets/index.json``: the API's ``/presets`` answer.
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
- ``social-security.json``: the Social Security page's inputs (Trustees
  baseline rates, OCACT options and their annual paths, the CRFB comparison)
  plus the ledger's own answers for current law and each option alone, which
  the site's TypeScript ledger is tested against.

The script calls the API's own endpoint functions, so an exported preset is the
API's answer by construction; ``tests/test_export_static.py`` checks it anyway.
The output carries no timestamps, so a night with no model change writes
identical files and the nightly job has nothing to commit.

Usage:
    python scripts/export_static.py                 # writes site_data/
    python scripts/export_static.py --out /tmp/x    # writes elsewhere
"""

from __future__ import annotations

import argparse
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


def score_preset_payload(preset_id: str, *, dynamic: bool) -> dict[str, Any]:
    """The API's ``/score/preset`` answer for ``preset_id``, as JSON-ready data."""
    import api

    response = api.score_preset(
        api.ScorePresetRequest(preset_name=preset_id, dynamic=dynamic),
        _api_key_label="static-export",
    )
    return response.model_dump(mode="json")


def preset_views_payload(preset_id: str) -> dict[str, Any]:
    """Who pays and economic effects for ``preset_id``, scored as ``/score/preset`` scores it."""
    import api
    from fiscal_model.preset_ids import resolve_preset
    from fiscal_model.result_views import distribution_view, economic_view

    label = resolve_preset(preset_id) or preset_id
    policy, use_real_data = api._build_preset_policy(label)
    scorer = api.FiscalPolicyScorer(
        start_year=max(int(getattr(policy, "start_year", api.APP_DEFAULT_START_YEAR)), api.APP_DEFAULT_START_YEAR),
        use_real_data=use_real_data,
    )
    result = scorer.score_policy(policy, dynamic=False)
    return {
        "id": preset_id,
        "distribution": distribution_view(policy),
        "economic": economic_view(policy, result),
    }


def preset_index_payload() -> dict[str, Any]:
    import api

    return api.list_presets().model_dump(mode="json")


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
                "url": bill["url"],
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


def export(out: Path) -> dict[str, Any]:
    """Write the whole export to ``out`` (replacing it) and return the manifest."""
    import api

    if out.exists():
        shutil.rmtree(out)

    index = preset_index_payload()
    _write(out / "presets" / "index.json", index)

    vintages: set[str] = set()
    windows: set[str] = set()
    for preset in index["presets"]:
        conventional = score_preset_payload(preset["id"], dynamic=False)
        dynamic = score_preset_payload(preset["id"], dynamic=True)
        vintages.add(conventional["baseline_vintage"])
        windows.add(conventional["budget_window"])
        _write(
            out / "presets" / f"{preset['id']}.json",
            {"id": preset["id"], "conventional": conventional, "dynamic": dynamic},
        )
        _write(out / "views" / f"{preset['id']}.json", preset_views_payload(preset["id"]))

    catalog = build_catalog_payload()
    _write(out / "build-catalog.json", catalog)
    scorecard = scorecard_payload()
    _write(out / "validation" / "scorecard.json", scorecard)
    _write(out / "validation" / "evidence.json", evidence_payload())
    tracker_index, tracker_scored = tracker_payloads()
    # 11,000 bills: indentation alone would double the size.
    _write(out / "tracker" / "index.json", tracker_index, compact=True)
    _write(out / "tracker" / "scored.json", tracker_scored, compact=True)
    values = values_payload()
    _write(out / "values.json", values)
    social_security = social_security_payload()
    _write(out / "social-security.json", social_security, compact=True)
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
        "sign_convention": (
            "Billions of dollars over the budget window; positive increases "
            "the deficit, negative reduces it."
        ),
    }
    _write(out / "manifest.json", manifest)
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
