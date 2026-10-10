"""The default microsimulation population: CPS tax units calibrated to IRS SOI.

Every surface that runs the microsim on the bundled file reads it through
:func:`load_default_population`, so they all see one population:

1. :func:`fiscal_model.data.cps_asec.load_tax_microdata` (the raw CPS file);
2. :func:`fiscal_model.microsim.top_tail.augment_top_tail` with
   ``by_status=True`` (SOI-cell top tail, states drawn from the CPS's own
   high-income rows);
3. :func:`fiscal_model.microsim.soi_calibration.calibrate_cells_to_soi`
   (weights raked to SOI returns and AGI by AGI class and filing status).

This became the default in R6c
(``planning/lanes/R6c_salt_mechanism_and_calibration_default.md``) on the owner's
decision, together with the statutory AMT and the SOI SALT imputation that keep
the SALT distributional benchmark under its gate on it. Before, the
distributional engine, Build's interaction measurement and the credits
module each read the raw file their own way (Build with a different, default
augmentation), and the raw file covers 119% of SOI returns and 81% of SOI AGI.

A synthetic or fixture file (``MicrodataSource.is_synthetic``) is returned
uncalibrated: the cell targets are national SOI totals and would rescale a
toy frame into nonsense. :func:`fiscal_model.data.cps_asec.load_tax_microdata`
remains the raw loader for callers that need the uncalibrated file, such as
the dashboard's before/after coverage line.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

#: IRS SOI tax year the top tail and the cell targets are read from (the
#: latest year ``IRSSOIData`` loads, and the year R6/R6b/R6c measured on).
DEFAULT_CALIBRATION_YEAR = 2023


@lru_cache(maxsize=4)
def _calibrated(path: str | None, mtime_ns: int) -> pd.DataFrame:
    from fiscal_model.data.cps_asec import load_tax_microdata
    from fiscal_model.microsim.soi_calibration import calibrate_cells_to_soi
    from fiscal_model.microsim.top_tail import augment_top_tail

    raw, source = load_tax_microdata(path)
    if source.is_synthetic:
        return raw
    augmented, _ = augment_top_tail(raw, year=DEFAULT_CALIBRATION_YEAR, by_status=True)
    calibrated, _ = calibrate_cells_to_soi(augmented, year=DEFAULT_CALIBRATION_YEAR)
    return calibrated


def load_default_population(path: str | Path | None = None) -> pd.DataFrame:
    """The SOI-calibrated tax-unit population (a fresh copy on every call).

    Cached per process on the file's path and modification time, so a rebuilt
    file is picked up without a restart.

    Raises:
        FileNotFoundError / ValueError: as
            :func:`fiscal_model.data.cps_asec.load_tax_microdata`.
    """
    from fiscal_model.data.cps_asec import _default_microdata_path

    resolved = Path(path).resolve() if path else _default_microdata_path()
    mtime_ns = resolved.stat().st_mtime_ns if resolved.exists() else -1
    key = str(resolved) if path else None
    return _calibrated(key, mtime_ns).copy()


__all__ = ["DEFAULT_CALIBRATION_YEAR", "load_default_population"]
