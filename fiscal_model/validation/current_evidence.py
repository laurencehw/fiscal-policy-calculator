"""The one versioned report of current validation evidence.

**Why this file exists.** ``planning/ROUTE_TO_9.md`` priority 2: *generate
headline metrics and data-vintage summaries from one versioned report*, so the
README, the pages, the API and the validation reports cannot disagree. They
did. When PR #173 moved the out-of-sample tier 18.0% -> 15.2% on the same 44
rows, the About page, the Methodology page and two strings the Ask assistant
hands the model kept printing 18.0% and "35/44", because each had typed the
figure. A typed figure is a claim nothing checks.

So the figures are generated: ``scripts/build_current_evidence.py`` runs the
same computations the validation reports run — ``cold_holdout.build_report()``,
the dashboard's calibrated tiers, the leave-one-out suite and the health
snapshot — and writes ``data_files/validation/current_evidence.json``. The
surfaces read that file; ``tests/test_current_evidence.py`` recomputes it and
fails if it has drifted, and pins the live headline sentences in the README,
``CLAUDE.md`` and ``docs/`` to it.

**How this differs from** ``fiscal_model/ui/validation_headline.py``. That
artifact holds *counts* only, by rule, so it moves when a benchmark is added or
retired and never when a model number moves. This one holds exactly the
figures that move when a model number moves. The two are separate so each
keeps its own contract; a lane that moves a tier regenerates this one.

**Reading it is cheap and must stay cheap**: stdlib ``json`` over one small
file, once per process. Nothing here imports the scorer, the scorecard or a
script — the builder is a pure function of the dicts the generator passes in.
No timestamp is recorded, so regenerating an unchanged tree is a no-op diff.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

#: The committed artifact, beside the other generated validation data.
EVIDENCE_PATH: Path = (
    Path(__file__).resolve().parents[1]
    / "data_files"
    / "validation"
    / "current_evidence.json"
)

#: Written into the file so whoever opens it knows what regenerates it.
GENERATOR = "scripts/build_current_evidence.py"

_NOTE = (
    "Generated file - do not hand-edit. These are the validation figures the "
    "app, the Ask assistant and the docs quote; they move whenever a model "
    "number that moves a tier moves. Regenerate with: python " + GENERATOR
)

#: Scorecard rows a surface quotes by id (the Methodology page's tables). The
#: report carries exactly these, and a test fails if a surface quotes a row
#: that is not listed here.
QUOTED_ROW_IDS: tuple[str, ...] = (
    # Out-of-sample sample rows.
    "cbo_opt45_all_rates_1pp",
    "cbo_opt46_agi_surtax_2pp_100k",
    "biden_high_income_tax",
    "cbo_opt64_corporate_rate_1pp",
    # Calibrated (fitted) sample rows.
    "tcja_full_extension",
    "biden_corporate_28",
    "biden_ctc_2021",
    "biden_estate_reform",
    "repeal_corporate_amt",
    "cap_employer_health",
    # The reconstruction row the Methodology page explains.
    "ss_donut_250k",
)

#: The summary fields every tier block carries, in the report's own names.
_SUMMARY_FIELDS: tuple[str, ...] = (
    "n",
    "mean_abs_error",
    "median_abs_error",
    "within_15pct",
    "within_25pct",
)

#: Health fields that are properties of the tree rather than of the machine
#: or the moment (a cache age or a timestamp would churn the file).
_VINTAGE_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("baseline", "vintage", "cbo_baseline_vintage"),
    ("baseline", "vintage_key", "cbo_baseline_vintage_key"),
    ("irs_soi", "available_years", "irs_soi_tax_years"),
    ("irs_soi", "latest_year", "irs_soi_latest_tax_year"),
    ("microdata", "calibration_year", "microdata_calibration_year"),
    ("microdata", "returns_coverage_pct", "microdata_returns_coverage_pct"),
    ("microdata", "agi_coverage_pct", "microdata_agi_coverage_pct"),
)


def _summary(block: Mapping[str, Any]) -> dict[str, Any]:
    return {field: block[field] for field in _SUMMARY_FIELDS}


def _round1(value: float) -> float:
    return round(float(value), 1)


def build_payload(
    *,
    holdout_report: Mapping[str, Any],
    calibrated_tiers: Mapping[str, Any],
    loo_suite: Mapping[str, Any],
    health: Mapping[str, Any],
) -> dict[str, Any]:
    """Assemble the report from the computations the generator ran.

    ``holdout_report`` is ``scripts/cold_holdout.build_report()``,
    ``calibrated_tiers`` the dashboard's ``collect_calibrated_tiers()``,
    ``loo_suite`` ``run_leave_one_out().to_dict()`` and ``health``
    ``fiscal_model.health.check_health()``. Every figure is copied, never
    recomputed, so this file cannot disagree with the report it came from.
    """
    oos = holdout_report["out_of_sample"]
    oos_entries = oos["entries"]
    out_of_sample = _summary(oos["summary"])
    # The pooled mass, on each row's error as reported (one decimal), which is
    # what the per-class masses below sum and what every lane doc quotes.
    out_of_sample["error_mass"] = _round1(
        sum(float(entry["abs_percent_error"]) for entry in oos_entries)
    )

    classes = {
        slug: {
            "label": block["label"],
            "n": block["n"],
            "mean_abs_error": block["mean_abs_error"],
            "median_abs_error": block["median_abs_error"],
            "within_15pct": block["within_15pct"],
            "within_25pct": block["within_25pct"],
            "error_mass": block["error_mass"],
        }
        for slug, block in sorted(oos["classes"].items())
    }

    rows_by_id: dict[str, tuple[str, Mapping[str, Any]]] = {}
    for tier_key, tier_name in (
        ("out_of_sample", "out_of_sample"),
        ("calibrated_reference", "fitted"),
        ("uncalibrated_reconstruction", "reconstruction"),
    ):
        for entry in holdout_report[tier_key]["entries"]:
            rows_by_id[entry["policy_id"]] = (tier_name, entry)
    missing = [pid for pid in QUOTED_ROW_IDS if pid not in rows_by_id]
    if missing:
        raise KeyError(
            f"quoted row(s) not in any scored tier: {missing}. A surface quotes "
            "a row the scorecard no longer carries; update QUOTED_ROW_IDS and "
            "the surface together."
        )
    quoted_rows = {}
    for pid in QUOTED_ROW_IDS:
        tier_name, entry = rows_by_id[pid]
        quoted_rows[pid] = {
            "tier": tier_name,
            "official_10yr_billions": entry["official_10yr_billions"],
            "model_10yr_billions": entry["model_10yr_billions"],
            "abs_percent_error": entry["abs_percent_error"],
        }

    retired = holdout_report["retired_targets"]
    components = health.get("components", health)
    data_vintages = {}
    for component, field, key in _VINTAGE_FIELDS:
        block = components.get(component) or {}
        value = block.get(field)
        data_vintages[key] = list(value) if isinstance(value, (list, tuple)) else value

    return {
        "_note": _NOTE,
        "generated_by": GENERATOR,
        "out_of_sample": out_of_sample,
        "out_of_sample_classes": classes,
        "calibrated": {
            "fitted": _summary(calibrated_tiers["fitted"]),
            "fitted_held_in_place": _summary(calibrated_tiers["fitted_held_in_place"]),
            "reconstruction": _summary(calibrated_tiers["reconstruction"]),
            "reconstruction_retired_held_in_place": _summary(
                calibrated_tiers["reconstruction_retired_held_in_place"]
            ),
            "retired_targets": {
                "n": retired["summary"]["n"],
                "policy_ids": sorted(entry["policy_id"] for entry in retired["entries"]),
            },
        },
        "leave_one_out": {
            "n": int(loo_suite["n_included"]),
            "not_cross_validatable": int(loo_suite["n_not_cross_validatable"]),
            "mean_abs_error": _round1(loo_suite["mean_abs_percent_error"]),
            "median_abs_error": _round1(loo_suite["median_abs_percent_error"]),
            "within_15pct": int(loo_suite["within_15pct"]),
        },
        "quoted_rows": quoted_rows,
        "data_vintages": data_vintages,
    }


def write_payload(payload: Mapping[str, Any], path: Path | None = None) -> Path:
    """Write the report, stably formatted, and drop the read cache."""
    target = path or EVIDENCE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    reset_cache()
    return target


@lru_cache(maxsize=1)
def load_evidence() -> dict[str, Any] | None:
    """The committed report, read once per process, or ``None`` if unreadable.

    ``None`` rather than an empty dict: "the report is missing" is a state a
    surface must handle by saying less, never by printing a zero.
    """
    try:
        data = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def reset_cache() -> None:
    """Clear the memoized read. For tests and for the generator script."""
    cache_clear = getattr(load_evidence, "cache_clear", None)
    if cache_clear is not None:
        cache_clear()


def _section(*path: str) -> dict[str, Any] | None:
    node: Any = load_evidence()
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node if isinstance(node, dict) else None


def out_of_sample() -> dict[str, Any] | None:
    """The pre-registered out-of-sample tier: n, mean, median, within-15/25, mass."""
    return _section("out_of_sample")


def policy_class(slug: str | None) -> dict[str, Any] | None:
    """One out-of-sample class (``cold_holdout.py``'s eight), or ``None``."""
    if not slug:
        return None
    return _section("out_of_sample_classes", slug)


def class_mean_range() -> tuple[dict[str, Any], dict[str, Any]] | None:
    """The classes with the lowest and the highest mean error, in that order."""
    classes = _section("out_of_sample_classes")
    if not classes:
        return None
    ordered = sorted(classes.values(), key=lambda block: block["mean_abs_error"])
    return ordered[0], ordered[-1]


def calibrated(tier: str) -> dict[str, Any] | None:
    """``fitted``, ``fitted_held_in_place``, ``reconstruction`` or
    ``reconstruction_retired_held_in_place``."""
    return _section("calibrated", tier)


def leave_one_out() -> dict[str, Any] | None:
    return _section("leave_one_out")


def quoted_row(policy_id: str) -> dict[str, Any] | None:
    """A row a surface quotes by id; see :data:`QUOTED_ROW_IDS`."""
    return _section("quoted_rows", policy_id)


def data_vintages() -> dict[str, Any] | None:
    return _section("data_vintages")


__all__ = [
    "EVIDENCE_PATH",
    "GENERATOR",
    "QUOTED_ROW_IDS",
    "build_payload",
    "calibrated",
    "class_mean_range",
    "data_vintages",
    "leave_one_out",
    "load_evidence",
    "out_of_sample",
    "policy_class",
    "quoted_row",
    "reset_cache",
    "write_payload",
]
