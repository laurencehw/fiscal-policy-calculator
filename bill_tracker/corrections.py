"""Pinned bill-tracker corrections the nightly job cannot overwrite.

``apply_pinned_corrections`` runs at the end of every ``update_bills`` pass,
including when the bill was not in that night's congress.gov fetch window.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from bill_tracker.cbo_fetcher import CBOCostEstimate, _parse_date
from bill_tracker.citations import is_concurrent_resolution
from bill_tracker.confidence import unmapped_policy_dicts

logger = logging.getLogger(__name__)

PINNED_PATH = Path(__file__).parent / "pinned_corrections.json"
MANUAL_MAPPINGS_PATH = Path(__file__).parent / "manual_mappings.json"


def load_pinned(path: Path | str | None = None) -> dict[str, Any]:
    file_path = Path(path) if path else PINNED_PATH
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to parse pinned corrections %s: %s", file_path, exc)
        return {}
    return payload if isinstance(payload, dict) else {}


def pinned_cbo_ids(pinned: dict[str, Any] | None = None) -> set[str]:
    data = pinned if pinned is not None else load_pinned()
    scores = data.get("cbo_scores") or {}
    return {str(k) for k in scores} if isinstance(scores, dict) else set()


def no_cbo_ids(pinned: dict[str, Any] | None = None) -> set[str]:
    data = pinned if pinned is not None else load_pinned()
    raw = data.get("no_cbo_score") or {}
    if isinstance(raw, dict):
        return {str(k) for k in raw}
    if isinstance(raw, list):
        return {str(k) for k in raw}
    return set()


def skip_live_cbo_match(bill_id: str, pinned: dict[str, Any] | None = None) -> bool:
    """True when live/fallback CBO matching must not write this bill."""
    data = pinned if pinned is not None else load_pinned()
    if bill_id in pinned_cbo_ids(data) or bill_id in no_cbo_ids(data):
        return True
    return is_concurrent_resolution(bill_id)


def _estimate_from_pin(bill_id: str, raw: dict[str, Any]) -> CBOCostEstimate:
    estimate_date = _parse_date(str(raw.get("estimate_date", "")))
    if estimate_date.year == 1970:
        estimate_date = datetime(2025, 7, 21)
    annual_raw = raw.get("annual_costs") or []
    annual: list[float] = []
    if isinstance(annual_raw, list):
        for value in annual_raw:
            try:
                annual.append(float(value))
            except (TypeError, ValueError):
                continue
    dynamic = raw.get("dynamic_estimate")
    return CBOCostEstimate(
        bill_id=bill_id,
        title=str(raw.get("title", "")),
        estimate_date=estimate_date,
        ten_year_cost_billions=float(raw["ten_year_cost_billions"]),
        annual_costs=annual,
        budget_function=str(raw.get("budget_function", "")),
        dynamic_estimate=float(dynamic) if dynamic is not None else None,
        pdf_url=str(raw.get("pdf_url", "")),
        cbo_url=str(raw.get("cbo_url", "")),
    )


def apply_pinned_corrections(
    db: Any,
    *,
    scorer: Any | None = None,
    mapper: Any | None = None,
    pinned: dict[str, Any] | None = None,
    rescore: bool = True,
) -> dict[str, int]:
    """Write pinned CBO scores, clear forbidden scores, pin status, rescore overrides.

    Returns counts of rows touched, for tests and logs.
    """
    data = pinned if pinned is not None else load_pinned()
    counts = {"cbo_replaced": 0, "cbo_cleared": 0, "status": 0, "rescored": 0}

    for bill_id, raw in (data.get("cbo_scores") or {}).items():
        if not isinstance(raw, dict) or db.get_bill(bill_id) is None:
            continue
        db.replace_cbo_score(_estimate_from_pin(bill_id, raw))
        counts["cbo_replaced"] += 1

    for bill_id in no_cbo_ids(data):
        if db.get_bill(bill_id) is None:
            continue
        db.clear_cbo_score(bill_id)
        counts["cbo_cleared"] += 1

    for bill_id, raw in (data.get("status") or {}).items():
        if not isinstance(raw, dict) or db.get_bill(bill_id) is None:
            continue
        db.update_bill_status(
            bill_id,
            status=str(raw["status"]),
            latest_action=raw.get("latest_action"),
            latest_action_date=raw.get("latest_action_date"),
        )
        counts["status"] += 1

    if rescore:
        counts["rescored"] = _rescore_manual_overrides(db, scorer=scorer, mapper=mapper)

    logger.info(
        "Pinned corrections: cbo_replaced=%d cbo_cleared=%d status=%d rescored=%d",
        counts["cbo_replaced"],
        counts["cbo_cleared"],
        counts["status"],
        counts["rescored"],
    )
    return counts


def _rescore_manual_overrides(
    db: Any,
    *,
    scorer: Any | None,
    mapper: Any | None,
) -> int:
    if scorer is None:
        return 0
    if mapper is None:
        from bill_tracker.provision_mapper import ProvisionMapper

        mapper = ProvisionMapper()

    if not MANUAL_MAPPINGS_PATH.exists():
        return 0
    try:
        payload = json.loads(MANUAL_MAPPINGS_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to read manual mappings: %s", exc)
        return 0

    rescored = 0
    for bill_id, entry in payload.items():
        if bill_id.startswith("_") or not isinstance(entry, dict):
            continue
        if db.get_bill(bill_id) is None:
            continue
        bill = db.get_bill(bill_id)
        mapping = mapper.map_bill(bill_id, bill.get("summary") if bill else None)
        db.upsert_manual_override(
            bill_id,
            mapping.policies + unmapped_policy_dicts(mapping.unmapped_provisions),
            override_reason=mapping.mapping_notes or entry.get("override_reason", ""),
            mapped_by=str(entry.get("mapped_by") or "pinned"),
        )
        score = scorer.score(mapping)
        if score is not None:
            db.replace_auto_score(score)
            rescored += 1
    return rescored
