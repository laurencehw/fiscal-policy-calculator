"""Build the reciprocal-tariff partner schedule from Census 2024 bilateral trade.

Lane H8 of ``planning/HIGH_STAKES_ACCURACY.md``. Replaces
``TRADE_BASELINE["reciprocal_coverage_rate"] = 0.50`` — "a flat 20pp on half of
goods imports", which is not a policy anyone proposed — with the schedule
Executive Order 14257 (2 April 2025) actually set.

The EO's own formula, as published by USTR in *Reciprocal Tariff
Calculations*: for each trading partner, take the 2024 U.S. bilateral goods
deficit over 2024 U.S. goods imports from that partner, halve it, and floor the
result at 10 percent. Annex II then exempts the sectors already under, or
announced for, Section 232 investigation. Canada and Mexico are not in Annex I
at all; they were covered by a separate IEEPA order.

Nothing here is fitted. Every level is a Census measurement and the rate is the
EO's arithmetic applied to it. The sixteen published Annex I rates the script
prints alongside its reconstruction are an **out-of-sample check** written into
the CSV as ``external_check`` rows; they are never inputs.

Usage::

    CENSUS_API_KEY=... python scripts/build_reciprocal_schedule.py
    python scripts/build_reciprocal_schedule.py --check   # re-derive, compare

Writes ``fiscal_model/data_files/trade/reciprocal_schedule.csv``.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = REPO_ROOT / "fiscal_model" / "data_files" / "trade" / "reciprocal_schedule.csv"

IMPORTS_URL = "https://api.census.gov/data/timeseries/intltrade/imports/hs"
EXPORTS_URL = "https://api.census.gov/data/timeseries/intltrade/exports/hs"
PERIOD = "2024-12"  # year-to-date through December 2024 = calendar 2024

#: Annex II sectors, mapped to the HS2 chapters that carry them. Steel,
#: aluminium and their derivative articles; autos and parts; copper;
#: pharmaceuticals; lumber articles; energy and energy products.
EXEMPT_CHAPTERS: dict[str, str] = {
    "27": "energy and energy products",
    "30": "pharmaceuticals",
    "44": "lumber articles",
    "72": "iron and steel (Section 232)",
    "73": "articles of iron or steel (Section 232 derivatives)",
    "74": "copper",
    "76": "aluminium (Section 232)",
    "87": "vehicles and parts (Section 232)",
}

#: The two Annex II sectors that are not whole chapters. Semiconductors sit in
#: HS 8541-8542; bullion in HS 7106, 7108 and 7118.
EXEMPT_HS4: dict[str, str] = {
    "8541": "semiconductors",
    "8542": "semiconductors",
    "7106": "bullion",
    "7108": "bullion",
    "7118": "bullion",
}

#: Covered by a separate IEEPA order, not by Annex I.
USMCA_PARTNERS = {"1220": "Canada", "2010": "Mexico"}

#: Partners below this much covered trade are folded into one remainder row;
#: 134 partners share $5.5B, 0.33% of the covered base.
MIN_COVERED_BILLIONS = 0.25

#: Published Annex I rates, transcribed from the Federal Register notice of
#: Executive Order 14257 (90 FR 15041, 7 April 2025), Annex I. Check only.
ANNEX_I_PUBLISHED: dict[str, tuple[str, float]] = {
    "5700": ("China", 0.34),
    "5520": ("Vietnam", 0.46),
    "5830": ("Taiwan", 0.32),
    "5880": ("Japan", 0.24),
    "5800": ("Korea, South", 0.25),
    "5330": ("India", 0.26),
    "5490": ("Thailand", 0.36),
    "4419": ("Switzerland", 0.31),
    "5570": ("Malaysia", 0.24),
    "5600": ("Indonesia", 0.32),
    "5550": ("Cambodia", 0.49),
    "5380": ("Bangladesh", 0.37),
    "5650": ("Philippines", 0.17),
    "4120": ("United Kingdom", 0.10),
    "3510": ("Brazil", 0.10),
    "6021": ("Australia", 0.10),
}

CENSUS_SOURCE = (
    "U.S. Census Bureau, general imports at customs value (GEN_VAL_YR) and "
    "total exports (ALL_VAL_YR), all HS2 chapters, YTD through December 2024"
)
CENSUS_URL = "https://api.census.gov/data/timeseries/intltrade/imports/hs"
EO_URL = "https://www.federalregister.gov/d/2025-06063"


def _get(url: str, tries: int = 3):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=180) as response:
                raw = response.read()
            return json.loads(raw) if raw else None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if attempt == tries - 1:
                raise
            time.sleep(3)
    return None


def _is_country(code: str) -> bool:
    """Census mixes real partners with region aggregates in ``CTY_CODE``.

    Aggregates are ``-`` (world), zero-padded bloc codes (``0003`` EU, ``0026``
    APEC) and continent codes carrying an ``X`` (``5XXX`` Asia). Summing them
    with the countries gives $19.7T of imports against an actual $3.26T.
    """
    return code.isdigit() and len(code) == 4 and not code.startswith("0")


def fetch_bilateral(key: str) -> dict:
    """One request per HS2 chapter; the API refuses an unfiltered country pull."""
    imports: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    exports: dict[str, float] = defaultdict(float)
    names: dict[str, str] = {}

    for chapter in (f"{c:02d}" for c in range(1, 100)):
        url = (
            f"{IMPORTS_URL}?get=CTY_CODE,CTY_NAME,GEN_VAL_YR&time={PERIOD}"
            f"&COMM_LVL=HS2&I_COMMODITY={chapter}&CTY_CODE=*&key={key}"
        )
        payload = _get(url)
        if payload:
            header = payload[0]
            for row in payload[1:]:
                record = dict(zip(header, row, strict=False))
                code = record["CTY_CODE"]
                names[code] = record["CTY_NAME"]
                imports[code][chapter] += float(record["GEN_VAL_YR"])

        url = (
            f"{EXPORTS_URL}?get=CTY_CODE,CTY_NAME,ALL_VAL_YR&time={PERIOD}"
            f"&COMM_LVL=HS2&E_COMMODITY={chapter}&CTY_CODE=*&key={key}"
        )
        payload = _get(url)
        if payload:
            header = payload[0]
            for row in payload[1:]:
                record = dict(zip(header, row, strict=False))
                code = record["CTY_CODE"]
                names.setdefault(code, record["CTY_NAME"])
                exports[code] += float(record["ALL_VAL_YR"])
        print(f"  chapter {chapter}", file=sys.stderr)

    hs4: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for code in EXEMPT_HS4:
        url = (
            f"{IMPORTS_URL}?get=CTY_CODE,CTY_NAME,GEN_VAL_YR&time={PERIOD}"
            f"&COMM_LVL=HS4&I_COMMODITY={code}&CTY_CODE=*&key={key}"
        )
        payload = _get(url)
        if payload:
            header = payload[0]
            for row in payload[1:]:
                record = dict(zip(header, row, strict=False))
                hs4[record["CTY_CODE"]][code] += float(record["GEN_VAL_YR"])
        print(f"  hs4 {code}", file=sys.stderr)

    return {
        "names": names,
        "imports": {k: dict(v) for k, v in imports.items()},
        "exports": dict(exports),
        "hs4": {k: dict(v) for k, v in hs4.items()},
    }


def eo_rate(imports_b: float, exports_b: float) -> float:
    """EO 14257's own formula: deficit over imports, halved, floored at 10%."""
    if imports_b <= 0:
        return 0.10
    return max(0.10, (imports_b - exports_b) / imports_b / 2.0)


def build_rows(raw: dict) -> list[dict]:
    rows: list[dict] = []
    for code, chapters in raw["imports"].items():
        if not _is_country(code) or code in USMCA_PARTNERS:
            continue
        imports_b = sum(chapters.values()) / 1e9
        if imports_b <= 0:
            continue
        exports_b = raw["exports"].get(code, 0.0) / 1e9
        exempt_b = sum(chapters.get(ch, 0.0) for ch in EXEMPT_CHAPTERS) / 1e9
        exempt_b += sum(raw["hs4"].get(code, {}).get(c, 0.0) for c in EXEMPT_HS4) / 1e9
        rows.append(
            {
                "cty_code": code,
                "partner": raw["names"][code].title(),
                "imports_2024_billions": round(imports_b, 4),
                "exports_2024_billions": round(exports_b, 4),
                "annex2_exempt_imports_billions": round(exempt_b, 4),
                "covered_imports_billions": round(max(0.0, imports_b - exempt_b), 4),
                "reciprocal_rate": round(eo_rate(imports_b, exports_b), 6),
            }
        )
    rows.sort(key=lambda r: -r["covered_imports_billions"])

    kept = [r for r in rows if r["covered_imports_billions"] >= MIN_COVERED_BILLIONS]
    tail = [r for r in rows if r["covered_imports_billions"] < MIN_COVERED_BILLIONS]
    if tail:
        covered = sum(r["covered_imports_billions"] for r in tail)
        weighted = (
            sum(r["covered_imports_billions"] * r["reciprocal_rate"] for r in tail)
            / covered
            if covered
            else 0.10
        )
        kept.append(
            {
                "cty_code": "REMAINDER",
                "partner": f"Other partners ({len(tail)})",
                "imports_2024_billions": round(
                    sum(r["imports_2024_billions"] for r in tail), 4
                ),
                "exports_2024_billions": round(
                    sum(r["exports_2024_billions"] for r in tail), 4
                ),
                "annex2_exempt_imports_billions": round(
                    sum(r["annex2_exempt_imports_billions"] for r in tail), 4
                ),
                "covered_imports_billions": round(covered, 4),
                "reciprocal_rate": round(weighted, 6),
            }
        )
    return kept


HEADER_NOTE = f"""\
# Reciprocal-tariff partner schedule, read by fiscal_model/trade.py's
# create_reciprocal_tariffs(). Lane H8 of planning/HIGH_STAKES_ACCURACY.md.
#
# This file replaces TRADE_BASELINE["reciprocal_coverage_rate"] = 0.50 - "a
# flat 20pp on half of goods imports", the one number left in TRADE_BASELINE
# that was a shape assumption rather than a measurement, and a policy nobody
# proposed. Executive Order 14257 (2 April 2025; 90 FR 15041) set a rate per
# partner by a stated formula, and this is that formula applied to the Census
# series the rest of the trade module already reads.
#
#   rate_i = max(10%, (goods imports from i - goods exports to i) / imports_i / 2)
#
# Annex II exempts the sectors already under, or announced for, Section 232:
# steel, aluminium and their derivative articles (HS 72, 73, 76), autos and
# parts (HS 87), copper (HS 74), pharmaceuticals (HS 30), lumber (HS 44),
# energy (HS 27), semiconductors (HS 8541-8542) and bullion (HS 7106, 7108,
# 7118). Those are removed partner by partner, because the exemptions are
# sectoral and the sectors are not evenly spread across partners - Ireland's
# pharmaceutical share and Japan's vehicle share carve out half of each of
# those partners' trade and almost none of Cambodia's.
#
# Canada and Mexico are absent: they were never in Annex I, having been
# covered by a separate IEEPA order.
#
# Nothing here is fitted. The rows marked role=external_check are the
# published Annex I rates, transcribed from the Federal Register notice; the
# module never reads them, and they exist so that a reconstruction that drifts
# from the document is visible. The reconstruction reproduces all sixteen
# within about a point, the residual being that Annex I rounds up.
#
# Rebuild with: CENSUS_API_KEY=... python scripts/build_reciprocal_schedule.py
#
# Columns
#   cty_code    Census CTY_CODE; REMAINDER aggregates partners below
#               ${MIN_COVERED_BILLIONS}B of covered trade
#   role        model_input    = read by trade.py
#               external_check = a published quantity the reconstruction is
#                                compared against, never an input to it
"""


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "cty_code",
        "partner",
        "imports_2024_billions",
        "exports_2024_billions",
        "annex2_exempt_imports_billions",
        "covered_imports_billions",
        "reciprocal_rate",
        "role",
        "source",
        "page",
        "url",
        "published",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(HEADER_NOTE)
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "role": "model_input",
                    "source": CENSUS_SOURCE,
                    "page": "API timeseries/intltrade/{imports,exports}/hs",
                    "url": CENSUS_URL,
                    "published": "2025-02",
                }
            )
        for code, (name, rate) in ANNEX_I_PUBLISHED.items():
            writer.writerow(
                {
                    "cty_code": code,
                    "partner": name,
                    "imports_2024_billions": "",
                    "exports_2024_billions": "",
                    "annex2_exempt_imports_billions": "",
                    "covered_imports_billions": "",
                    "reciprocal_rate": rate,
                    "role": "external_check",
                    "source": (
                        "Executive Order 14257, Annex I, as published in the "
                        "Federal Register - the rate the document states for "
                        "this partner, against which the formula above is checked"
                    ),
                    "page": "Annex I",
                    "url": EO_URL,
                    "published": "2025-04",
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="re-derive and report the Annex I comparison without writing",
    )
    args = parser.parse_args()

    key = os.environ.get("CENSUS_API_KEY")
    if not key:
        print("CENSUS_API_KEY is not set.", file=sys.stderr)
        return 2

    print("Fetching Census bilateral trade...", file=sys.stderr)
    raw = fetch_bilateral(key)
    rows = build_rows(raw)

    covered = sum(r["covered_imports_billions"] for r in rows)
    weighted = sum(
        r["covered_imports_billions"] * r["reciprocal_rate"] for r in rows
    ) / covered
    print(f"\npartners written: {len(rows)}")
    print(f"covered base:     ${covered:,.1f}B")
    print(f"weighted rate:    {weighted:.4f}")

    by_code = {r["cty_code"]: r for r in rows}
    print("\nAnnex I check (published vs reconstructed):")
    for code, (name, published) in ANNEX_I_PUBLISHED.items():
        row = by_code.get(code)
        if row is None:
            print(f"  {name:20s} published {published:.2f}  (not in schedule)")
            continue
        print(
            f"  {name:20s} published {published:.2f}  "
            f"reconstructed {row['reciprocal_rate']:.4f}  "
            f"diff {row['reciprocal_rate'] - published:+.4f}"
        )

    if not args.check:
        write_csv(rows, OUT_PATH)
        print(f"\nwrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
