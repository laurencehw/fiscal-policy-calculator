"""
Executable feasibility audits for the manuscript-grade roadmap items.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_MICRODATA_RELATIVE_PATH = Path("fiscal_model") / "microsim" / "tax_microdata_2024.csv"
DEFAULT_RAW_CPS_RELATIVE_DIR = Path("data") / "asecpub24csv"
DEFAULT_RAW_CPS_ARCHIVE = Path("data") / "asecpub24csv.zip"

MICROSIM_REQUIRED_COLUMNS = (
    "agi",
    "wages",
    "married",
    "children",
    "weight",
    "age_head",
)

MICROSIM_OPTIONAL_COLUMNS = (
    "interest_income",
    "dividend_income",
    "capital_gains",
    "social_security",
    "unemployment",
    "itemized_deductions",
    "state_and_local_taxes",
    "investment_income",
)

DEFAULT_MODEL_PILOT_MIN_MODELS = 2
DEFAULT_MODEL_PILOT_MAX_GAP_BILLIONS = 10_000.0
DEFAULT_MODEL_PILOT_MAX_ABS_COST_BILLIONS = 10_000.0


@dataclass
class AggregateCheck:
    """One sanity check over the built microsim file."""

    name: str
    actual: float
    lower_bound: float | None = None
    upper_bound: float | None = None
    unit: str = ""
    passed: bool = False

    def __post_init__(self) -> None:
        self.passed = True
        if self.lower_bound is not None and self.actual < self.lower_bound:
            self.passed = False
        if self.upper_bound is not None and self.actual > self.upper_bound:
            self.passed = False


@dataclass
class CPSMicrosimAudit:
    """Structured readiness report for the CPS-backed microsim track."""

    microdata_path: str
    raw_data_dir: str
    archive_path: str
    microdata_exists: bool
    raw_person_exists: bool
    raw_household_exists: bool
    archive_exists: bool
    row_count: int = 0
    required_columns: list[str] = field(default_factory=list)
    missing_required_columns: list[str] = field(default_factory=list)
    optional_columns_present: list[str] = field(default_factory=list)
    optional_columns_missing: list[str] = field(default_factory=list)
    checks: list[AggregateCheck] = field(default_factory=list)
    rebuild_command: str = "python fiscal_model/microsim/data_builder.py"
    reproducible_from_repo_inputs: bool = False
    warnings: list[str] = field(default_factory=list)

    @property
    def ready_for_spike(self) -> bool:
        return (
            self.microdata_exists
            and self.raw_person_exists
            and self.raw_household_exists
            and not self.missing_required_columns
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ready_for_spike"] = self.ready_for_spike
        return payload


@dataclass
class ModelPilotAssessment:
    """Structured go/no-go assessment for the pilot multi-model comparison."""

    result_count: int
    error_count: int
    max_gap: float | None = None
    max_abs_ten_year_cost: float | None = None
    min_required_models: int = DEFAULT_MODEL_PILOT_MIN_MODELS
    max_gap_limit_billions: float = DEFAULT_MODEL_PILOT_MAX_GAP_BILLIONS
    max_abs_cost_limit_billions: float = DEFAULT_MODEL_PILOT_MAX_ABS_COST_BILLIONS
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ready_for_spike(self) -> bool:
        return not self.blockers

    @property
    def status(self) -> str:
        return "ready" if self.ready_for_spike else "blocked"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ready_for_spike"] = self.ready_for_spike
        payload["status"] = self.status
        return payload


def _project_root_from(value: str | Path | None) -> Path:
    if value is not None:
        return Path(value).resolve()
    return Path(__file__).resolve().parents[1]


def _build_check(name: str, actual: float, lower: float, upper: float, unit: str) -> AggregateCheck:
    return AggregateCheck(
        name=name,
        actual=float(actual),
        lower_bound=float(lower),
        upper_bound=float(upper),
        unit=unit,
    )


def audit_cps_microsim_readiness(
    *,
    project_root: str | Path | None = None,
    microdata_path: str | Path | None = None,
    raw_data_dir: str | Path | None = None,
    archive_path: str | Path | None = None,
) -> CPSMicrosimAudit:
    """
    Audit whether the repo is ready for a CPS microsim hardening sprint.

    The audit stays lightweight: it checks source availability, expected schema,
    and a handful of weighted aggregate sanity bounds on the built microdata file.
    """

    root = _project_root_from(project_root)
    microdata = Path(microdata_path).resolve() if microdata_path else root / DEFAULT_MICRODATA_RELATIVE_PATH
    raw_dir = Path(raw_data_dir).resolve() if raw_data_dir else root / DEFAULT_RAW_CPS_RELATIVE_DIR
    archive = Path(archive_path).resolve() if archive_path else root / DEFAULT_RAW_CPS_ARCHIVE

    person_file = raw_dir / "pppub24.csv"
    household_file = raw_dir / "hhpub24.csv"

    audit = CPSMicrosimAudit(
        microdata_path=str(microdata),
        raw_data_dir=str(raw_dir),
        archive_path=str(archive),
        microdata_exists=microdata.exists(),
        raw_person_exists=person_file.exists(),
        raw_household_exists=household_file.exists(),
        archive_exists=archive.exists(),
    )
    audit.required_columns = list(MICROSIM_REQUIRED_COLUMNS)
    audit.reproducible_from_repo_inputs = (
        audit.raw_person_exists and audit.raw_household_exists and audit.microdata_exists
    )

    if not audit.raw_person_exists or not audit.raw_household_exists:
        audit.warnings.append("Raw CPS ASEC person/household files are incomplete.")
    if not audit.archive_exists:
        audit.warnings.append("The CPS archive zip is not present alongside the extracted files.")
    if not audit.microdata_exists:
        audit.warnings.append("Built microsim file is missing; run the data builder before scoring.")
        return audit

    header = pd.read_csv(microdata, nrows=0)
    available_columns = header.columns.tolist()
    audit.missing_required_columns = [
        column for column in MICROSIM_REQUIRED_COLUMNS if column not in available_columns
    ]
    audit.optional_columns_present = [
        column for column in MICROSIM_OPTIONAL_COLUMNS if column in available_columns
    ]
    audit.optional_columns_missing = [
        column for column in MICROSIM_OPTIONAL_COLUMNS if column not in available_columns
    ]

    if audit.missing_required_columns:
        audit.warnings.append(
            "Built microsim file is missing required columns: "
            + ", ".join(audit.missing_required_columns)
        )
        return audit

    usecols = list(dict.fromkeys((*MICROSIM_REQUIRED_COLUMNS, *audit.optional_columns_present)))
    df = pd.read_csv(microdata, usecols=usecols)
    audit.row_count = int(len(df))

    weighted_tax_units = float(df["weight"].sum())
    weighted_wages = float((df["wages"] * df["weight"]).sum() / 1e9)
    weighted_agi = float((df["agi"] * df["weight"]).sum() / 1e9)
    weighted_children = float((df["children"] * df["weight"]).sum() / 1e6)

    audit.checks = [
        _build_check("weighted_tax_units", weighted_tax_units, 100_000_000, 200_000_000, "tax_units"),
        _build_check("weighted_wages", weighted_wages, 8_000, 20_000, "billions_usd"),
        _build_check("weighted_agi", weighted_agi, 10_000, 25_000, "billions_usd"),
        _build_check("weighted_children", weighted_children, 40, 90, "millions"),
    ]

    if not all(check.passed for check in audit.checks):
        audit.warnings.append(
            "One or more weighted aggregate sanity checks fell outside the current expected bounds."
        )
    if audit.optional_columns_missing:
        audit.warnings.append(
            "Optional microsim fields are still absent: " + ", ".join(audit.optional_columns_missing)
        )

    return audit


def assess_model_pilot_comparison(
    comparison_bundle: Any,
    *,
    min_required_models: int = DEFAULT_MODEL_PILOT_MIN_MODELS,
    max_gap_limit_billions: float = DEFAULT_MODEL_PILOT_MAX_GAP_BILLIONS,
    max_abs_cost_limit_billions: float = DEFAULT_MODEL_PILOT_MAX_ABS_COST_BILLIONS,
) -> ModelPilotAssessment:
    """Assess whether the pilot model comparison is credible enough to expand.

    The pilot comparison intentionally runs heterogeneous engines. Large
    disagreement can be expected, but order-of-magnitude or sign/pathology gaps
    should block further UI/productization until the adapter assumptions are
    narrowed or the unstable engine is removed from the default pilot.
    """

    results = list(getattr(comparison_bundle, "results", []) or [])
    errors = dict(getattr(comparison_bundle, "errors", {}) or {})
    max_gap = getattr(comparison_bundle, "max_gap", None)
    costs: list[tuple[str, float]] = []

    for result in results:
        model_name = str(getattr(result, "model_name", type(result).__name__))
        ten_year_cost = float(getattr(result, "ten_year_cost", 0.0))
        costs.append((model_name, ten_year_cost))

    max_abs_cost = max((abs(cost) for _, cost in costs), default=None)
    assessment = ModelPilotAssessment(
        result_count=len(results),
        error_count=len(errors),
        max_gap=float(max_gap) if max_gap is not None else None,
        max_abs_ten_year_cost=max_abs_cost,
        min_required_models=min_required_models,
        max_gap_limit_billions=float(max_gap_limit_billions),
        max_abs_cost_limit_billions=float(max_abs_cost_limit_billions),
    )

    if len(results) < min_required_models:
        assessment.blockers.append(
            f"Only {len(results)} model result(s) returned; need at least "
            f"{min_required_models} comparable engines."
        )

    for model_name, error in errors.items():
        message = f"{model_name} did not run: {error}"
        if len(results) < min_required_models:
            assessment.blockers.append(message)
        else:
            assessment.warnings.append(message)

    for model_name, cost in costs:
        if abs(cost) > max_abs_cost_limit_billions:
            assessment.blockers.append(
                f"{model_name} 10-year estimate is {cost:,.1f}B, outside the "
                f"+/-{max_abs_cost_limit_billions:,.0f}B pilot sanity bound."
            )

    if max_gap is not None and abs(float(max_gap)) > max_gap_limit_billions:
        assessment.blockers.append(
            f"Max model gap is {float(max_gap):,.1f}B, above the "
            f"{max_gap_limit_billions:,.0f}B pilot sanity bound."
        )

    if not any(getattr(result, "distributional", None) is not None for result in results):
        assessment.warnings.append(
            "No pilot model returned distributional output; the comparison is aggregate-only."
        )

    return assessment
