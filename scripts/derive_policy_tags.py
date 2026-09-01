#!/usr/bin/env python
"""Derive the Build-catalog values tags and regenerate ``policy_tags_generated``.

REDESIGN_PLAN.md §5b.1 asks for five tags per catalog policy
(``direction`` / ``progressivity`` / ``govt_size`` / ``base`` /
``generational``) and specifies that ``progressivity`` be *derived from the
app's own distribution engine*, with a manual-override file for the policies
the engine cannot represent.

That derivation already exists: ``fiscal_model/composer/progressivity.py``
runs ``DistributionalEngine`` per preset and falls back to nine documented
incidence families when the engine is silent. This script reuses it verbatim
rather than adding a second, divergent estimate of the same quantity. The
other four tags are read off the catalog's own ``is_*`` flags and the sign of
the model's 10-year deficit path — the same routing the scorer uses.

Usage
-----
    python scripts/derive_policy_tags.py            # rewrite the generated module
    python scripts/derive_policy_tags.py --check    # exit 1 if it is stale
    python scripts/derive_policy_tags.py --report   # print the derivation table

Runtime is ~10s (52 presets × score + distribution run).

How ``progressivity`` is computed
---------------------------------
``measure_incidence`` returns ``top_quintile_share`` — the share of the
policy's |burden| landing in the top quintile. That is a *burden* measure, so
it has to be signed by whether the policy imposes the burden or confers the
benefit:

    score = direction_sign x (top_quintile_share - PROPORTIONAL_TOP_QUINTILE_SHARE)

with ``direction_sign = +1`` when the policy reduces the deficit (it takes)
and ``-1`` when it increases it (it gives). ``PROPORTIONAL_TOP_QUINTILE_SHARE``
(0.45) is progressivity.py's own line for "roughly proportional". Bands are
stated in percentage points off proportional, not fitted:

    score >= +0.25  strong_progressive
    score >= +0.05  progressive
    |score| < 0.05  neutral            (within 5pp of proportional)
    score <= -0.05  regressive

There is no ``strong_regressive`` in the plan's enum, so the negative tail
collapses into ``regressive``.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import logging
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import yaml  # noqa: E402

from fiscal_model.app_data import PRESET_POLICIES  # noqa: E402
from fiscal_model.composer.composer import (  # noqa: E402
    _build_preset_policy,
    _scorer_for,
)
from fiscal_model.composer.progressivity import (  # noqa: E402
    PROPORTIONAL_TOP_QUINTILE_SHARE,
    measure_incidence,
)
from fiscal_model.distribution import DistributionalEngine, IncomeGroupType  # noqa: E402
from fiscal_model.preset_ids import (  # noqa: E402
    ALLOWED_TAG_VALUES,
    CUSTOM_POLICY_LABEL,
    PRESET_ID_BY_LABEL,
    TAG_KEYS,
)

logger = logging.getLogger("derive_policy_tags")

GENERATED_PATH = REPO_ROOT / "fiscal_model" / "policy_tags_generated.py"
OVERRIDES_PATH = (
    REPO_ROOT / "fiscal_model" / "data_files" / "policy_tags_overrides.yaml"
)

STRONG_BAND = 0.25
NEUTRAL_BAND = 0.05

#: Whose lifetime the policy's *programme* incidence lands on, by module.
#: Deliberately not the debt channel — every deficit-financed policy shifts
#: cost forward, so tagging on that would just restate ``direction``.
GENERATIONAL_BY_MODULE: dict[str, str] = {
    "payroll": "future",       # the SS/Medicare trust funds
    "estate": "mixed",         # taxes a transfer between two generations
    "corporate": "mixed",      # capital stock -> future wages
    "international": "mixed",
    "climate": "future",
    "trade": "current",
    "enforcement": "current",
    "pharma": "current",
    "ptc": "current",
    "credit": "current",
    "tcja": "current",
    "amt": "current",
    "expenditure": "current",
    "generic": "current",
}


def _module_of(preset: dict[str, Any]) -> str:
    """Which policy module scores this preset (mirrors ``_preset_category``)."""
    for flag in (
        "tcja",
        "corporate",
        "international",
        "credit",
        "estate",
        "payroll",
        "amt",
        "ptc",
        "expenditure",
        "enforcement",
        "pharma",
        "trade",
        "climate",
    ):
        if preset.get(f"is_{flag}"):
            return flag
    return "generic"


def derive_base(preset: dict[str, Any]) -> str:
    """Which tax/spending base the policy moves."""
    module = _module_of(preset)
    if module in {"corporate", "international"}:
        return "corporate"
    if module == "amt":
        return "corporate" if preset.get("amt_type") == "repeal_corporate" else "individual"
    if module == "payroll":
        return "payroll"
    if module == "estate":
        return "estate"
    if module == "enforcement":
        return "enforcement"
    if module == "trade":
        return "consumption"
    if module == "climate":
        # A carbon tax is paid at the pump; a credit repeal is not.
        carbon = str(preset.get("climate_type", "")).startswith("carbon")
        return "consumption" if carbon else "corporate"
    if module in {"credit", "ptc", "pharma"}:
        # Refundable credits, ACA premium credits and Medicare drug pricing
        # are transfer programmes that happen to run through the tax code or
        # the outlay side.
        return "transfer"
    return "individual"


def derive_direction(base: str, ten_year_deficit: float) -> str:
    """Revenue vs spending side, signed by the model's own 10-year path.

    Deficit convention: negative = reduces the deficit.
    """
    reduces_deficit = ten_year_deficit < 0
    if base == "transfer":
        return "cut_spending" if reduces_deficit else "add_spending"
    return "raise_revenue" if reduces_deficit else "cut_revenue"


def derive_govt_size(direction: str) -> str:
    """Bigger or smaller public sector. Overridden where the sign misleads."""
    return "grow" if direction in {"raise_revenue", "add_spending"} else "shrink"


def derive_generational(preset: dict[str, Any]) -> str:
    return GENERATIONAL_BY_MODULE[_module_of(preset)]


def derive_progressivity(
    incidence: Any, ten_year_deficit: float
) -> tuple[str, str]:
    """``(tag, source)`` for one preset's progressivity.

    ``source`` is ``engine:<path>`` when the distribution engine produced a
    real quintile table, ``fallback:<family>`` when progressivity.py's
    documented incidence family stood in, and ``not_modeled`` when neither is
    defensible (no household tax base, or no documented family at all).
    """
    if not incidence.is_household_tax:
        return "not_modeled", "not_modeled:no_household_base"
    if not incidence.representable and incidence.family == "unclassified":
        return "not_modeled", "not_modeled:no_incidence_family"

    sign = 1.0 if ten_year_deficit < 0 else -1.0
    # Rounded before banding: several documented fallback shares sit exactly
    # on a band edge (consumption = 0.40 against a 0.45 proportional line),
    # where binary float noise would otherwise decide the tag.
    score = round(
        sign * (incidence.top_quintile_share - PROPORTIONAL_TOP_QUINTILE_SHARE), 6
    )

    if score >= STRONG_BAND:
        tag = "strong_progressive"
    elif score >= NEUTRAL_BAND:
        tag = "progressive"
    elif score <= -NEUTRAL_BAND:
        tag = "regressive"
    else:
        tag = "neutral"

    source = (
        f"engine:{incidence.source}"
        if incidence.representable
        else incidence.source  # already "fallback:<family>"
    )
    return tag, source


def load_overrides() -> dict[str, dict[str, Any]]:
    """Read and validate the manual-override file."""
    if not OVERRIDES_PATH.exists():
        return {}
    raw = yaml.safe_load(OVERRIDES_PATH.read_text(encoding="utf-8")) or {}
    overrides = raw.get("overrides") or {}

    known_ids = set(PRESET_ID_BY_LABEL.values())
    for preset_id, entry in overrides.items():
        if preset_id not in known_ids:
            raise SystemExit(
                f"{OVERRIDES_PATH.name}: unknown preset id {preset_id!r}. "
                "Overrides are keyed by stable id, not display label."
            )
        if not str(entry.get("note", "")).strip():
            raise SystemExit(
                f"{OVERRIDES_PATH.name}: override {preset_id!r} has no note. "
                "Every hand-set tag must say why."
            )
        for key, value in entry.items():
            if key == "note":
                continue
            if key not in TAG_KEYS:
                raise SystemExit(
                    f"{OVERRIDES_PATH.name}: {preset_id!r} sets unknown tag {key!r}."
                )
            if value not in ALLOWED_TAG_VALUES[key]:
                raise SystemExit(
                    f"{OVERRIDES_PATH.name}: {preset_id!r} sets "
                    f"{key}={value!r}, which is not in the allowed enum."
                )
    return overrides


def _committed_tag_sources() -> dict[str, dict[str, str]]:
    """Provenance recorded in the checked-in module, if it is importable."""
    try:
        from fiscal_model.policy_tags_generated import TAG_SOURCES
    except Exception:
        return {}
    return dict(TAG_SOURCES)


def derive_all(allow_degraded: bool = False) -> tuple[
    dict[str, dict[str, str]], dict[str, dict[str, str]], list[dict[str, Any]]
]:
    """Return ``(tags, sources, report_rows)`` for every catalog preset.

    ``DistributionalEngine`` falls back from its return-level microsim path
    to synthetic brackets when the microsim cannot run — including on a
    transient ``MemoryError``, which it logs and swallows. That changes
    ``top_quintile_share`` and therefore the emitted tag, so a regeneration
    on a loaded machine would silently rewrite tags that nothing about the
    catalog had changed. Any preset that *was* measured on the microsim path
    and now is not aborts the run instead. ``--allow-degraded`` is the escape
    hatch for a deliberate re-baseline.
    """
    committed_sources = _committed_tag_sources()
    degraded: list[tuple[str, str, str]] = []
    overrides = load_overrides()
    engine = DistributionalEngine()

    tags: dict[str, dict[str, str]] = {}
    sources: dict[str, dict[str, str]] = {}
    rows: list[dict[str, Any]] = []

    for label, preset in PRESET_POLICIES.items():
        if label == CUSTOM_POLICY_LABEL:
            continue
        preset_id = PRESET_ID_BY_LABEL.get(label)
        if preset_id is None:
            raise SystemExit(
                f"Preset {label!r} has no stable id. Add it to "
                "fiscal_model/preset_ids.py:PRESET_ID_BY_LABEL first."
            )

        policy, use_real_data = _build_preset_policy(label, preset)
        result = _scorer_for(policy, use_real_data).score_policy(policy, dynamic=False)
        ten_year = float(sum(result.final_deficit_effect))
        incidence = measure_incidence(
            label, preset, policy, engine, IncomeGroupType.QUINTILE
        )

        base = derive_base(preset)
        direction = derive_direction(base, ten_year)
        progressivity, prog_source = derive_progressivity(incidence, ten_year)
        derived = {
            "direction": direction,
            "progressivity": progressivity,
            "govt_size": derive_govt_size(direction),
            "base": base,
            "generational": derive_generational(preset),
        }
        derived_sources = {
            "direction": "derived:deficit_sign",
            "progressivity": prog_source,
            "govt_size": "derived:direction",
            "base": "derived:policy_module",
            "generational": "derived:policy_module",
        }

        was = committed_sources.get(preset_id, {}).get("progressivity", "")
        if was == "engine:microsim" and prog_source != "engine:microsim":
            degraded.append((preset_id, was, prog_source))

        override = overrides.get(preset_id, {})
        for key, value in override.items():
            if key == "note":
                continue
            derived[key] = value
            derived_sources[key] = "override"

        for key in TAG_KEYS:
            if derived[key] not in ALLOWED_TAG_VALUES[key]:
                raise SystemExit(
                    f"{preset_id}: derived {key}={derived[key]!r} is not in the enum."
                )

        tags[preset_id] = derived
        sources[preset_id] = derived_sources
        rows.append(
            {
                "preset_id": preset_id,
                "label": label,
                "ten_year": ten_year,
                "top_quintile_share": incidence.top_quintile_share,
                "incidence_source": incidence.source,
                "family": incidence.family,
                "tags": derived,
            }
        )

    if degraded and not allow_degraded:
        detail = "\n".join(
            f"  {preset_id}: {was} -> {now}" for preset_id, was, now in degraded
        )
        raise SystemExit(
            "Refusing to write: the distribution engine's microsim path "
            f"degraded for {len(degraded)} preset(s) on this run.\n{detail}\n"
            "This is usually memory pressure, not a catalog change — the "
            "engine logs the failure and falls back to synthetic brackets. "
            "Re-run on an idle machine, or pass --allow-degraded to "
            "deliberately re-baseline."
        )

    return tags, sources, rows


def _render_module(
    tags: dict[str, dict[str, str]], sources: dict[str, dict[str, str]]
) -> str:
    """Render the generated module (deterministic: catalog order, no timestamp)."""
    lines: list[str] = [
        '"""Values tags for the Build catalog — GENERATED, do not edit by hand.',
        "",
        "Regenerate with::",
        "",
        "    python scripts/derive_policy_tags.py",
        "",
        "Schema and enums live in ``fiscal_model/preset_ids.py``; the derivation",
        "and its bands are documented in ``scripts/derive_policy_tags.py``;",
        "hand-set values live in ``fiscal_model/data_files/policy_tags_overrides.yaml``.",
        "",
        "``TAG_SOURCES`` records where each tag came from, so the UI can",
        "distinguish a measured tag from an asserted one:",
        "",
        "* ``engine:<path>``  - the distribution engine produced a quintile table",
        "* ``fallback:<fam>`` - progressivity.py's documented incidence family",
        "* ``not_modeled:*``  - the app declines to assert a progressivity",
        "* ``derived:*``      - read off the catalog flags / the model's deficit sign",
        "* ``override``       - set by hand in the overrides file, with a note",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "POLICY_TAGS: dict[str, dict[str, str]] = {",
    ]
    for preset_id, tag_map in tags.items():
        lines.append(f"    {preset_id!r}: {{")
        for key in TAG_KEYS:
            lines.append(f"        {key!r}: {tag_map[key]!r},")
        lines.append("    },")
    lines.append("}")
    lines.append("")
    lines.append("TAG_SOURCES: dict[str, dict[str, str]] = {")
    for preset_id, source_map in sources.items():
        lines.append(f"    {preset_id!r}: {{")
        for key in TAG_KEYS:
            lines.append(f"        {key!r}: {source_map[key]!r},")
        lines.append("    },")
    lines.append("}")
    lines.append("")
    lines.append('__all__ = ["POLICY_TAGS", "TAG_SOURCES"]')
    lines.append("")
    return "\n".join(lines)


def _print_report(rows: list[dict[str, Any]]) -> None:
    header = (
        f"{'preset_id':32s} {'10yr $B':>9s} {'top20%':>6s} "
        f"{'direction':13s} {'progressivity':18s} {'govt':7s} {'base':12s} gen"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        tags = row["tags"]
        print(
            f"{row['preset_id']:32s} {row['ten_year']:9.0f} "
            f"{row['top_quintile_share']:6.3f} "
            f"{tags['direction']:13s} {tags['progressivity']:18s} "
            f"{tags['govt_size']:7s} {tags['base']:12s} {tags['generational']}"
        )
    not_modeled = [
        row["preset_id"]
        for row in rows
        if row["tags"]["progressivity"] == "not_modeled"
    ]
    print(
        f"\n{len(rows)} catalog policies; "
        f"{len(not_modeled)} not_modeled: {', '.join(not_modeled) or '-'}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if the generated module is stale (for CI).",
    )
    parser.add_argument(
        "--report", action="store_true", help="Print the derivation table."
    )
    parser.add_argument(
        "--allow-degraded",
        action="store_true",
        help=(
            "Write even if the distribution engine's microsim path degraded "
            "to synthetic brackets on this run (deliberate re-baseline only)."
        ),
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.ERROR, format="%(message)s")

    tags, sources, rows = derive_all(allow_degraded=args.allow_degraded)
    rendered = _render_module(tags, sources)

    if args.report:
        _print_report(rows)

    if args.check:
        current = (
            GENERATED_PATH.read_text(encoding="utf-8")
            if GENERATED_PATH.exists()
            else ""
        )
        if current != rendered:
            print(
                f"STALE: {GENERATED_PATH.relative_to(REPO_ROOT)} does not match "
                "the current derivation. Run: python scripts/derive_policy_tags.py",
                file=sys.stderr,
            )
            return 1
        print(f"OK: {GENERATED_PATH.relative_to(REPO_ROOT)} is up to date.")
        return 0

    # Written with the platform's native line ending (the repo has
    # core.autocrlf=true and no .gitattributes) but compared above via
    # read_text()'s universal-newline decoding, so --check is stable on both
    # Windows and Linux CI.
    GENERATED_PATH.write_text(rendered, encoding="utf-8")
    stamp = _dt.date.today().isoformat()
    print(
        f"Wrote {GENERATED_PATH.relative_to(REPO_ROOT)} "
        f"({len(tags)} policies, {stamp})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
