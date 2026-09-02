"""
Public-facing CPS ASEC microdata loader.

The heavy lifting — parsing raw CPS person/household files and constructing
tax units via spouse and parent pointers — lives in
``fiscal_model.microsim.data_builder``. This module is the thin public
entry point: it decides which file to load, validates the result, and
documents the two supported paths.

Supported paths
---------------
1. **Bundled CPS-derived microdata** (default). The repository ships
   ``fiscal_model/microsim/tax_microdata_2024.csv``, a tax-unit file
   produced from CPS ASEC 2024 microdata by the builder below. It
   covers ~191M weighted tax units / ~$12T weighted AGI — the real US
   population, not a synthetic sample.

2. **CPS ASEC rebuild**. Under owner Decision 4 the raw extract is
   *fetched by script and never vendored*:

       python -m fiscal_model.microsim.data_builder --fetch

   downloads the Census archive to a cache outside the repository
   (``scripts/fetch_cps_asec.py``, SHA-256 verified), extracts
   ``pppub24.csv`` / ``hhpub24.csv`` and overwrites
   ``fiscal_model/microsim/tax_microdata_2024.csv`` plus its
   ``.provenance.json`` sidecar. Pass ``--data-dir DIR`` instead to build
   from an extract you already have.

:func:`load_tax_microdata` also returns a :class:`MicrodataSource`
descriptor with an ``is_synthetic`` flag. The bundled file is *not*
flagged synthetic; the flag flips when the file is replaced by a small
demonstration sample (e.g. in CI fixtures), so downstream reports can
warn that distributional output should not be taken literally.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


# Column contract returned to callers. Must be a subset of
# ``fiscal_model.microsim.data_builder.OUTPUT_COLUMNS``.
REQUIRED_COLUMNS = (
    "id",
    "weight",
    "wages",
    "interest_income",
    "dividend_income",
    "capital_gains",
    "social_security",
    "unemployment",
    "children",
    "married",
    "age_head",
    "agi",
)

#: Dependent detail the credit rules need: the dependent headcount and the
#: five statutory age bands (:mod:`fiscal_model.microsim.data_builder`).
#: Deliberately **not** in :data:`REQUIRED_COLUMNS` — a small demonstration or
#: CI-fixture file can legitimately lack them, and the microsim engine falls
#: back to ``children`` when they are absent. Callers that need real dependent
#: ages should check :attr:`MicrodataSource.has_dependent_ages` rather than
#: assume a zero-filled column means "no dependents".
DEPENDENT_COLUMNS = (
    "dependent_count",
    "dependents_under_6",
    "dependents_6_to_16",
    "dependents_age_17",
    "dependents_age_18",
    "dependents_19_to_23_student",
)

DEFAULT_MICRODATA_FILENAME = "tax_microdata_2024.csv"


def _default_microdata_path() -> Path:
    """Path to the bundled microdata inside the installed package."""
    return (
        Path(__file__).resolve().parents[1]
        / "microsim"
        / DEFAULT_MICRODATA_FILENAME
    )


@dataclass(frozen=True)
class MicrodataSource:
    """Describes which microdata file a caller is actually using."""

    path: Path
    is_synthetic: bool
    weighted_tax_units: float
    weighted_agi_billions: float
    notes: str = ""
    #: Whether every column in :data:`DEPENDENT_COLUMNS` is present, i.e.
    #: whether dependent ages survived the build. False for pre-2026-09
    #: files and for small fixtures.
    has_dependent_ages: bool = False


def load_tax_microdata(
    path: str | Path | None = None,
) -> tuple[pd.DataFrame, MicrodataSource]:
    """
    Load tax-unit microdata, returning the DataFrame and a source descriptor.

    Args:
        path: Optional override. When omitted, the default bundled file is
            used.

    Returns:
        Tuple of ``(dataframe, MicrodataSource)``. The DataFrame is
        guaranteed to contain every column in :data:`REQUIRED_COLUMNS`.

    Raises:
        FileNotFoundError: No microdata file exists at the given (or
            default) path.
        ValueError: The file exists but is missing required columns.
    """
    resolved = Path(path).resolve() if path else _default_microdata_path()
    if not resolved.exists():
        raise FileNotFoundError(
            f"No tax microdata file at {resolved}. "
            "Either point at a built tax_microdata_*.csv file, or run "
            "`python -m fiscal_model.microsim.data_builder` with raw "
            "CPS ASEC files in data/asecpub24csv/ to produce one."
        )

    df = pd.read_csv(resolved)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"{resolved} is missing required columns: {missing}. "
            "Rebuild the microdata file from CPS ASEC sources."
        )

    weighted_units = float(df["weight"].sum())
    weighted_agi = float((df["agi"] * df["weight"]).sum() / 1e9)
    has_dependent_ages = all(column in df.columns for column in DEPENDENT_COLUMNS)

    # Heuristic: the bundled synthetic file has far fewer rows (~50-150)
    # and a very small weighted-population total. The real CPS-derived
    # file has tens of thousands of rows and weights summing into the
    # ~120-160M range.
    is_synthetic = len(df) < 5_000 or weighted_units < 50_000_000
    notes = (
        "Bundled demonstration microdata (synthetic). Replace with a "
        "CPS-built file for realistic distributional output. "
        "See fiscal_model/data/cps_asec.py for instructions."
        if is_synthetic
        else "CPS ASEC-derived tax-unit file."
    )

    return df, MicrodataSource(
        path=resolved,
        is_synthetic=is_synthetic,
        weighted_tax_units=weighted_units,
        weighted_agi_billions=weighted_agi,
        notes=notes,
        has_dependent_ages=has_dependent_ages,
    )


def describe_microdata(
    path: str | Path | None = None,
) -> dict[str, object]:
    """
    One-shot summary suitable for an app sidebar, the /health endpoint,
    or a CLI status command.
    """
    try:
        _, source = load_tax_microdata(path)
    except FileNotFoundError as exc:
        return {"status": "missing", "message": str(exc)}
    except ValueError as exc:
        return {"status": "malformed", "message": str(exc)}
    return {
        "status": "synthetic" if source.is_synthetic else "real",
        "path": str(source.path),
        "weighted_tax_units": source.weighted_tax_units,
        "weighted_agi_billions": source.weighted_agi_billions,
        "has_dependent_ages": source.has_dependent_ages,
        "notes": source.notes,
    }


__all__ = [
    "DEFAULT_MICRODATA_FILENAME",
    "DEPENDENT_COLUMNS",
    "REQUIRED_COLUMNS",
    "MicrodataSource",
    "describe_microdata",
    "load_tax_microdata",
]
