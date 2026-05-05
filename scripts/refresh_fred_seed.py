"""Refresh the bundled FRED seed snapshot from the live FRED API.

This script is intentionally stricter than the runtime data path: it requires
live FRED data and fails rather than falling back to cache, bundled seed, or
hardcoded estimates. The committed seed is used only for deterministic offline
smoke/readiness checks, so refreshing it should preserve clear provenance.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fiscal_model.data.fred_data import FREDData  # noqa: E402
from fiscal_model.exceptions import FREDUnavailableError  # noqa: E402
from fiscal_model.time_utils import utc_isoformat, utc_now  # noqa: E402

DEFAULT_SEED_PATH = REPO_ROOT / "fiscal_model" / "data_files" / "fred_seed.json"
DEFAULT_OBSERVATION_COUNT = 8


@dataclass(frozen=True)
class FredSeedSeries:
    """Metadata stored alongside each bundled FRED series."""

    series_id: str
    label: str
    units: str

    @property
    def source_url(self) -> str:
        return f"https://fred.stlouisfed.org/series/{self.series_id}"


FRED_SEED_SERIES: tuple[FredSeedSeries, ...] = (
    FredSeedSeries(
        series_id="GDP",
        label="Gross Domestic Product",
        units="Billions of dollars, seasonally adjusted annual rate",
    ),
    FredSeedSeries(
        series_id="GDPC1",
        label="Real Gross Domestic Product",
        units="Billions of chained 2017 dollars, seasonally adjusted annual rate",
    ),
    FredSeedSeries(
        series_id="UNRATE",
        label="Unemployment Rate",
        units="Percent",
    ),
    FredSeedSeries(
        series_id="DGS10",
        label="10-Year Treasury Constant Maturity Rate",
        units="Percent",
    ),
)


def _format_observation_date(index_value: object) -> str:
    """Return the same timestamp-key shape used by the FRED runtime cache."""
    timestamp = pd.Timestamp(index_value)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_convert("UTC").tz_localize(None)
    return str(timestamp.to_pydatetime())


def _tail_values(series: pd.Series, observation_count: int) -> dict[str, float]:
    if observation_count < 1:
        raise ValueError("--observations must be at least 1")

    clean = series.dropna().sort_index().tail(observation_count)
    if clean.empty:
        raise FREDUnavailableError(f"FRED returned no usable observations for {series.name}")

    return {
        _format_observation_date(index_value): float(value)
        for index_value, value in clean.items()
    }


def build_seed_payload(
    fred: FREDData,
    *,
    observation_count: int = DEFAULT_OBSERVATION_COUNT,
    fetched_at: datetime | None = None,
) -> dict[str, Any]:
    """Build a bundled seed payload from live FRED series."""
    timestamp = utc_isoformat(fetched_at or utc_now())
    series_payloads: dict[str, dict[str, Any]] = {}

    for config in FRED_SEED_SERIES:
        try:
            series = fred.require_live(config.series_id)
            values = _tail_values(series, observation_count)
        except Exception as exc:
            raise FREDUnavailableError(
                f"Failed to refresh live FRED series {config.series_id}: {exc}"
            ) from exc

        series_payloads[config.series_id] = {
            "label": config.label,
            "latest_observation": next(reversed(values)),
            "observations": len(values),
            "series_id": config.series_id,
            "source_url": config.source_url,
            "units": config.units,
            "updated_at": timestamp,
            "values": values,
        }

    return {
        "generated_at": timestamp,
        "max_age_days": getattr(fred, "bundled_seed_max_age_days", 120),
        "refresh_command": "python scripts/refresh_fred_seed.py",
        "series": series_payloads,
        "source": "Bundled FRED seed snapshot for deterministic offline smoke/readiness checks.",
        "updated_at": timestamp,
    }


def write_seed_payload(path: Path, payload: dict[str, Any]) -> None:
    """Write seed JSON atomically enough for local and CI refresh jobs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f"{path.name}.tmp")
    temporary_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def refresh_seed(
    output_path: Path = DEFAULT_SEED_PATH,
    *,
    observation_count: int = DEFAULT_OBSERVATION_COUNT,
    timeout_seconds: int = 10,
    dry_run: bool = False,
    fred_client: FREDData | None = None,
    fetched_at: datetime | None = None,
) -> dict[str, Any]:
    """Refresh the bundled seed and return the payload that was generated."""
    fred = fred_client or FREDData(timeout_seconds=timeout_seconds)
    if not fred.is_available():
        raise FREDUnavailableError(
            "FRED API is not configured. Set FRED_API_KEY and ensure fredapi is installed."
        )

    payload = build_seed_payload(
        fred,
        observation_count=observation_count,
        fetched_at=fetched_at,
    )

    if not dry_run:
        write_seed_payload(output_path, payload)

    return payload


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_SEED_PATH,
        help=f"Seed JSON path to write (default: {DEFAULT_SEED_PATH})",
    )
    parser.add_argument(
        "--observations",
        type=int,
        default=DEFAULT_OBSERVATION_COUNT,
        help="Number of most recent observations to store per series.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=10,
        help="Timeout passed through to live FRED requests.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the refreshed seed payload without writing it.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        payload = refresh_seed(
            args.output,
            observation_count=args.observations,
            timeout_seconds=args.timeout_seconds,
            dry_run=args.dry_run,
        )
    except (FREDUnavailableError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Wrote {args.output} with {len(payload['series'])} FRED series.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
