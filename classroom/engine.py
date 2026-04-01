"""
Classroom Mode Engine

Handles assignment loading (YAML), exercise progression, and answer
validation.  The key validation path is ``relative_to_model``: at
check-time the student's parameters are fed into the live scorer,
and the answer is accepted when it falls within ±tolerance of the
model's output.  This means assignments stay correct automatically
when the CBO baseline is updated.

Assignment lifecycle
--------------------
1. ``AssignmentLoader.load(assignment_id)``  →  ``Assignment``
2. Student selects complexity level and works through ``Exercise`` list
3. ``ExerciseRunner.check_answer()``  →  ``ValidationResult``
4. ``ExerciseRunner.get_hint()``  →  hint text
5. ``ProgressTracker`` persists completed exercises in Streamlit session state
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

ASSIGNMENTS_DIR = Path(__file__).parent / "assignments"


class ComplexityLevel(str, Enum):
    UNDERGRADUATE = "undergraduate"
    GRADUATE = "graduate"
    ADVANCED = "advanced"


class ExerciseType(str, Enum):
    PARAMETER_EXPLORATION = "parameter_exploration"
    TARGET_FINDING = "target_finding"
    COMPARISON = "comparison"
    OPEN_ANALYSIS = "open_analysis"


class ValidationMethod(str, Enum):
    RELATIVE_TO_MODEL = "relative_to_model"
    QUALITATIVE = "qualitative"
    RANGE_CHECK = "range_check"
    NONE = "none"


@dataclass
class Hint:
    level: int        # 1 = gentle, 2 = stronger, 3 = near-answer
    text: str


@dataclass
class ExerciseParameter:
    name: str
    label: str
    min: float
    max: float
    step: float
    default: float
    unit: str = ""
    description: str = ""


@dataclass
class ValidationSpec:
    method: ValidationMethod
    # For relative_to_model
    policy_type: str = ""          # "income_tax", "trade", "olg", etc.
    policy_params: dict = field(default_factory=dict)
    target_field: str = ""         # attribute on ScoringResult / OLGResult
    tolerance: float = 0.02        # ±2% of model output
    # For qualitative
    expected_sign: str = ""        # "positive", "negative", or ""
    # For range_check
    min_acceptable: float = float("-inf")
    max_acceptable: float = float("inf")


@dataclass
class ValidationResult:
    correct: bool
    student_answer: float
    model_answer: Optional[float]
    tolerance: float
    message: str
    pct_error: Optional[float] = None  # |student - model| / |model|


@dataclass
class Exercise:
    id: str
    title: str
    type: ExerciseType
    complexity: ComplexityLevel
    prompt: str
    parameters: list[ExerciseParameter]
    hints: list[Hint]
    validation: Optional[ValidationSpec]
    expected_insight: str = ""
    solution_notes: str = ""       # instructor-only


@dataclass
class Assignment:
    id: str
    title: str
    description: str
    complexity_levels: list[ComplexityLevel]
    learning_objectives: list[str]
    exercises: list[Exercise]
    estimated_minutes: int = 45
    tags: list[str] = field(default_factory=list)

    def exercises_for_level(self, level: ComplexityLevel) -> list[Exercise]:
        """Return exercises appropriate for the given complexity level."""
        return [e for e in self.exercises if e.complexity == level]


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------

class AssignmentLoader:
    """
    Loads Assignment objects from YAML files in the assignments directory.

    YAML schema (condensed)::

        id: laffer_curve
        title: "Laffer Curve Exploration"
        complexity_levels: [undergraduate, graduate]
        description: "..."
        learning_objectives: [...]
        estimated_minutes: 45
        exercises:
          - id: ex1
            title: "..."
            type: parameter_exploration
            complexity: undergraduate
            prompt: "..."
            parameters:
              - name: rate_change
                label: "Rate change (pp)"
                min: -0.20
                max: 0.20
                step: 0.01
                default: 0.02
                unit: "pp"
            hints:
              - level: 1
                text: "Think about what happens to revenue when the rate changes..."
            validation:
              method: relative_to_model
              policy_type: income_tax
              policy_params:
                name: "Student Policy"
                description: "Student-defined policy"
                rate_change: "{rate_change}"
                affected_income_threshold: 400000
              target_field: total_10_year_cost
              tolerance: 0.02
            expected_insight: "..."
    """

    def __init__(self, assignments_dir: Path = ASSIGNMENTS_DIR):
        self.assignments_dir = assignments_dir

    def list_assignments(self) -> list[str]:
        """Return IDs of all available assignments."""
        if not self.assignments_dir.exists():
            return []
        return sorted(
            p.stem for p in self.assignments_dir.glob("*.yaml")
        )

    def load(self, assignment_id: str) -> Assignment:
        """Load and parse an assignment from its YAML file."""
        path = self.assignments_dir / f"{assignment_id}.yaml"
        if not path.exists():
            raise FileNotFoundError(
                f"Assignment '{assignment_id}' not found at {path}"
            )
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return self._parse(data)

    def _parse(self, data: dict) -> Assignment:
        exercises = [self._parse_exercise(e) for e in data.get("exercises", [])]
        return Assignment(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            complexity_levels=[
                ComplexityLevel(c) for c in data.get("complexity_levels", ["undergraduate"])
            ],
            learning_objectives=data.get("learning_objectives", []),
            exercises=exercises,
            estimated_minutes=data.get("estimated_minutes", 45),
            tags=data.get("tags", []),
        )

    def _parse_exercise(self, data: dict) -> Exercise:
        params = [self._parse_param(p) for p in data.get("parameters", [])]
        hints = [Hint(level=h["level"], text=h["text"]) for h in data.get("hints", [])]
        validation = self._parse_validation(data.get("validation"))
        return Exercise(
            id=data["id"],
            title=data["title"],
            type=ExerciseType(data.get("type", "parameter_exploration")),
            complexity=ComplexityLevel(data.get("complexity", "undergraduate")),
            prompt=data["prompt"],
            parameters=params,
            hints=hints,
            validation=validation,
            expected_insight=data.get("expected_insight", ""),
            solution_notes=data.get("solution_notes", ""),
        )

    def _parse_param(self, data: dict) -> ExerciseParameter:
        return ExerciseParameter(
            name=data["name"],
            label=data["label"],
            min=float(data["min"]),
            max=float(data["max"]),
            step=float(data["step"]),
            default=float(data["default"]),
            unit=data.get("unit", ""),
            description=data.get("description", ""),
        )

    def _parse_validation(self, data: Optional[dict]) -> Optional[ValidationSpec]:
        if data is None:
            return None
        return ValidationSpec(
            method=ValidationMethod(data.get("method", "none")),
            policy_type=data.get("policy_type", ""),
            policy_params=data.get("policy_params", {}),
            target_field=data.get("target_field", ""),
            tolerance=float(data.get("tolerance", 0.02)),
            expected_sign=data.get("expected_sign", ""),
            min_acceptable=float(data.get("min_acceptable", float("-inf"))),
            max_acceptable=float(data.get("max_acceptable", float("inf"))),
        )


# ---------------------------------------------------------------------------
# Relative-to-model validator
# ---------------------------------------------------------------------------

class RelativeValidator:
    """
    Validates student answers by comparing against live model output.

    For ``relative_to_model`` validation, the student's parameter values
    are substituted into the spec's ``policy_params`` template (using
    ``{param_name}`` placeholders), the model is run, and the answer
    is accepted when::

        |student_answer - model_answer| / |model_answer| <= tolerance

    This ensures assignments remain correct after CBO baseline updates.
    """

    def validate(
        self,
        student_answer: float,
        spec: ValidationSpec,
        student_params: dict[str, float],
    ) -> ValidationResult:
        """
        Validate a student answer against the given spec.

        Parameters
        ----------
        student_answer
            The numeric answer the student submitted.
        spec
            Validation specification from the YAML.
        student_params
            The parameter values the student set (name → value).
        """
        if spec.method == ValidationMethod.RELATIVE_TO_MODEL:
            return self._validate_relative(student_answer, spec, student_params)
        elif spec.method == ValidationMethod.QUALITATIVE:
            return self._validate_qualitative(student_answer, spec)
        elif spec.method == ValidationMethod.RANGE_CHECK:
            return self._validate_range(student_answer, spec)
        else:
            # No validation — always correct (open analysis)
            return ValidationResult(
                correct=True,
                student_answer=student_answer,
                model_answer=None,
                tolerance=0,
                message="Open-ended exercise — no automated validation.",
            )

    def _validate_relative(
        self,
        student_answer: float,
        spec: ValidationSpec,
        student_params: dict[str, float],
    ) -> ValidationResult:
        try:
            model_answer = self._compute_model_answer(spec, student_params)
        except Exception as exc:
            return ValidationResult(
                correct=False,
                student_answer=student_answer,
                model_answer=None,
                tolerance=spec.tolerance,
                message=f"Could not compute model answer: {exc}",
            )

        if model_answer is None or model_answer == 0:
            # Fall back to range check when model returns zero
            abs_diff = abs(student_answer - (model_answer or 0))
            correct = abs_diff < 1.0
            return ValidationResult(
                correct=correct,
                student_answer=student_answer,
                model_answer=model_answer,
                tolerance=spec.tolerance,
                message=(
                    "Your answer is within $1B of the model estimate."
                    if correct else
                    f"Model estimate: ${model_answer:.1f}B. "
                    f"Your answer: ${student_answer:.1f}B."
                ),
                pct_error=None,
            )

        pct_error = abs(student_answer - model_answer) / abs(model_answer)
        correct = pct_error <= spec.tolerance

        if correct:
            msg = (
                f"Correct! Your answer (${student_answer:.1f}B) is within "
                f"{spec.tolerance*100:.0f}% of the model estimate "
                f"(${model_answer:.1f}B)."
            )
        else:
            msg = (
                f"Not quite. Model estimate: ${model_answer:.1f}B. "
                f"Your answer: ${student_answer:.1f}B "
                f"({pct_error*100:.1f}% off, tolerance {spec.tolerance*100:.0f}%)."
            )
        return ValidationResult(
            correct=correct,
            student_answer=student_answer,
            model_answer=model_answer,
            tolerance=spec.tolerance,
            message=msg,
            pct_error=pct_error,
        )

    def _validate_qualitative(
        self, student_answer: float, spec: ValidationSpec
    ) -> ValidationResult:
        if spec.expected_sign == "positive":
            correct = student_answer > 0
            msg = (
                "Correct — the effect is positive (revenue-raising)."
                if correct else
                "The effect should be positive (revenue-raising). Check your sign."
            )
        elif spec.expected_sign == "negative":
            correct = student_answer < 0
            msg = (
                "Correct — the effect is negative (revenue-losing)."
                if correct else
                "The effect should be negative (revenue-losing). Check your sign."
            )
        else:
            correct = True
            msg = "Qualitative check passed."
        return ValidationResult(
            correct=correct,
            student_answer=student_answer,
            model_answer=None,
            tolerance=0,
            message=msg,
        )

    def _validate_range(
        self, student_answer: float, spec: ValidationSpec
    ) -> ValidationResult:
        correct = spec.min_acceptable <= student_answer <= spec.max_acceptable
        if correct:
            msg = f"Answer ${student_answer:.1f}B is in the expected range."
        else:
            msg = (
                f"Answer ${student_answer:.1f}B is outside expected range "
                f"[${spec.min_acceptable:.0f}B, ${spec.max_acceptable:.0f}B]."
            )
        return ValidationResult(
            correct=correct,
            student_answer=student_answer,
            model_answer=None,
            tolerance=0,
            message=msg,
        )

    # ------------------------------------------------------------------
    # Model dispatch
    # ------------------------------------------------------------------

    def _compute_model_answer(
        self, spec: ValidationSpec, student_params: dict[str, float]
    ) -> Optional[float]:
        """Resolve template params, run scorer, return target_field value."""
        resolved = self._resolve_params(spec.policy_params, student_params)

        pt = spec.policy_type
        if pt == "income_tax":
            return self._run_income_tax(resolved, spec.target_field)
        elif pt == "capital_gains":
            return self._run_capital_gains(resolved, spec.target_field)
        elif pt == "corporate":
            return self._run_corporate(resolved, spec.target_field)
        elif pt == "trade":
            return self._run_trade(resolved, spec.target_field)
        elif pt == "spending":
            return self._run_spending(resolved, spec.target_field)
        elif pt == "olg":
            return self._run_olg(resolved, spec.target_field)
        else:
            raise ValueError(f"Unknown policy_type: '{pt}'")

    def _resolve_params(
        self, template: dict, student_params: dict[str, float]
    ) -> dict:
        """Replace ``{param_name}`` placeholders with student values."""
        resolved = {}
        for k, v in template.items():
            if isinstance(v, str):
                # Replace all {placeholder} occurrences
                for pname, pval in student_params.items():
                    v = v.replace(f"{{{pname}}}", str(pval))
                # Try to cast back to number
                try:
                    resolved[k] = float(v)
                except (ValueError, TypeError):
                    resolved[k] = v
            else:
                resolved[k] = v
        return resolved

    def _run_income_tax(self, params: dict, target_field: str) -> float:
        from fiscal_model.policies import TaxPolicy, PolicyType
        from fiscal_model.scoring import FiscalPolicyScorer

        policy = TaxPolicy(
            name=str(params.get("name", "Student Policy")),
            description=str(params.get("description", "")),
            policy_type=PolicyType.INCOME_TAX,
            rate_change=float(params["rate_change"]),
            affected_income_threshold=float(params.get("affected_income_threshold", 0)),
            taxable_income_elasticity=float(params.get("taxable_income_elasticity", 0.25)),
        )
        scorer = FiscalPolicyScorer(use_real_data=True)
        result = scorer.score_policy(policy, dynamic=False)
        return float(getattr(result, target_field))

    def _run_capital_gains(self, params: dict, target_field: str) -> float:
        from fiscal_model.data.capital_gains import CapitalGainsTaxPolicy
        from fiscal_model.scoring import FiscalPolicyScorer

        policy = CapitalGainsTaxPolicy(
            name=str(params.get("name", "Capital Gains Policy")),
            description=str(params.get("description", "")),
            rate_change=float(params["rate_change"]),
        )
        scorer = FiscalPolicyScorer(use_real_data=True)
        result = scorer.score_policy(policy, dynamic=False)
        return float(getattr(result, target_field))

    def _run_corporate(self, params: dict, target_field: str) -> float:
        from fiscal_model.corporate import CorporateTaxPolicy
        from fiscal_model.scoring import FiscalPolicyScorer

        policy = CorporateTaxPolicy(
            name=str(params.get("name", "Corporate Policy")),
            description=str(params.get("description", "")),
            rate_change=float(params["rate_change"]),
        )
        scorer = FiscalPolicyScorer(use_real_data=True)
        result = scorer.score_policy(policy, dynamic=False)
        return float(getattr(result, target_field))

    def _run_spending(self, params: dict, target_field: str) -> float:
        from fiscal_model.policies import SpendingPolicy, PolicyType
        from fiscal_model.scoring import FiscalPolicyScorer

        policy = SpendingPolicy(
            name=str(params.get("name", "Spending Policy")),
            description=str(params.get("description", "")),
            policy_type=PolicyType.DISCRETIONARY_NONDEFENSE,
            annual_change_billions=float(params["annual_change_billions"]),
        )
        scorer = FiscalPolicyScorer(use_real_data=True)
        result = scorer.score_policy(policy, dynamic=False)
        return float(getattr(result, target_field))

    def _run_trade(self, params: dict, target_field: str) -> float:
        from fiscal_model.trade import TariffPolicy
        from fiscal_model.scoring import FiscalPolicyScorer

        policy = TariffPolicy(
            name=str(params.get("name", "Tariff Policy")),
            description=str(params.get("description", "")),
            tariff_rate=float(params["tariff_rate"]),
            import_base_billions=float(params.get("import_base_billions", 3200.0)),
        )
        scorer = FiscalPolicyScorer(use_real_data=True)
        result = scorer.score_policy(policy, dynamic=False)
        return float(getattr(result, target_field))

    def _run_olg(self, params: dict, target_field: str) -> float:
        from fiscal_model.models.olg import OLGModel, OLGParams

        olg_params = OLGParams(
            baseline_deficit_gdp=float(params.get("baseline_deficit_gdp", 0.06)),
        )
        model = OLGModel(params=olg_params)
        result = model.run(
            debt_shock_pct_gdp=float(params.get("debt_shock_pct_gdp", 0.0)),
            ss_replacement_change=float(params.get("ss_replacement_change", 0.0)),
            labor_tax_change=float(params.get("labor_tax_change", 0.0)),
        )
        # OLG target fields
        if target_field == "mean_net_tax_rate_current":
            # Mean net tax rate for cohorts born 1980-2010
            mask = (result.birth_years >= 1980) & (result.birth_years <= 2010)
            valid = result.net_tax_rate[mask]
            valid = valid[~(valid != valid)]  # remove NaN
            return float(valid.mean()) if len(valid) > 0 else 0.0
        elif target_field == "mean_net_tax_rate_future":
            mask = (result.birth_years >= 2025) & (result.birth_years <= 2060)
            valid = result.net_tax_rate[mask]
            valid = valid[~(valid != valid)]
            return float(valid.mean()) if len(valid) > 0 else 0.0
        elif target_field == "debt_pct_gdp_final":
            final_gdp = result.gdp_path[-1]
            final_debt = result.debt_path[-1]
            return float(final_debt / final_gdp * 100) if final_gdp > 0 else 0.0
        else:
            raise ValueError(f"Unknown OLG target_field: '{target_field}'")


# ---------------------------------------------------------------------------
# Exercise runner
# ---------------------------------------------------------------------------

class ExerciseRunner:
    """
    Orchestrates a single exercise: parameter rendering, answer checking,
    hint delivery, and state tracking.

    Designed to be instantiated once per Streamlit session; state is
    stored externally in the progress tracker.
    """

    def __init__(self):
        self.validator = RelativeValidator()

    def check_answer(
        self,
        exercise: Exercise,
        student_params: dict[str, float],
        student_answer: float,
    ) -> ValidationResult:
        """Check the student's answer against the exercise validation spec."""
        if exercise.validation is None:
            return ValidationResult(
                correct=True,
                student_answer=student_answer,
                model_answer=None,
                tolerance=0,
                message="No automated validation for this exercise.",
            )
        return self.validator.validate(student_answer, exercise.validation, student_params)

    def get_hint(self, exercise: Exercise, hint_level: int) -> str:
        """Return the hint at the given level (1-indexed). Returns '' if not available."""
        for h in exercise.hints:
            if h.level == hint_level:
                return h.text
        return ""

    def get_all_hints(self, exercise: Exercise) -> list[Hint]:
        return sorted(exercise.hints, key=lambda h: h.level)


# ---------------------------------------------------------------------------
# Progress tracking (Streamlit session-state backed)
# ---------------------------------------------------------------------------

class ProgressTracker:
    """
    Tracks exercise completion in Streamlit session state.

    Keys in ``st.session_state``:
    - ``classroom_assignment_id``     current assignment
    - ``classroom_complexity``        selected complexity level
    - ``classroom_current_exercise``  index of current exercise
    - ``classroom_completed``         set of completed exercise IDs
    - ``classroom_hints_used``        dict[exercise_id → int] hint level used
    - ``classroom_answers``           dict[exercise_id → ValidationResult]
    """

    def __init__(self, session_state: dict):
        self._s = session_state
        self._s.setdefault("classroom_completed", set())
        self._s.setdefault("classroom_hints_used", {})
        self._s.setdefault("classroom_answers", {})
        self._s.setdefault("classroom_current_exercise", 0)

    @property
    def assignment_id(self) -> Optional[str]:
        return self._s.get("classroom_assignment_id")

    @assignment_id.setter
    def assignment_id(self, value: str) -> None:
        self._s["classroom_assignment_id"] = value

    @property
    def complexity(self) -> ComplexityLevel:
        raw = self._s.get("classroom_complexity", ComplexityLevel.UNDERGRADUATE)
        return ComplexityLevel(raw)

    @complexity.setter
    def complexity(self, value: ComplexityLevel) -> None:
        self._s["classroom_complexity"] = value

    @property
    def current_exercise_index(self) -> int:
        return self._s.get("classroom_current_exercise", 0)

    def mark_complete(self, exercise_id: str, result: ValidationResult) -> None:
        self._s["classroom_completed"].add(exercise_id)
        self._s["classroom_answers"][exercise_id] = result
        self._s["classroom_current_exercise"] = (
            self._s.get("classroom_current_exercise", 0) + 1
        )

    def use_hint(self, exercise_id: str, level: int) -> None:
        self._s["classroom_hints_used"][exercise_id] = max(
            self._s["classroom_hints_used"].get(exercise_id, 0), level
        )

    def hints_used(self, exercise_id: str) -> int:
        return self._s["classroom_hints_used"].get(exercise_id, 0)

    def is_complete(self, exercise_id: str) -> bool:
        return exercise_id in self._s["classroom_completed"]

    def completion_fraction(self, exercises: list[Exercise]) -> tuple[int, int]:
        completed = sum(1 for e in exercises if self.is_complete(e.id))
        return completed, len(exercises)

    def get_answer(self, exercise_id: str) -> Optional[ValidationResult]:
        return self._s["classroom_answers"].get(exercise_id)

    def reset(self) -> None:
        self._s["classroom_completed"] = set()
        self._s["classroom_hints_used"] = {}
        self._s["classroom_answers"] = {}
        self._s["classroom_current_exercise"] = 0
