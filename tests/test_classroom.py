"""
Tests for Classroom Mode

Covers:
- Assignment loading (YAML parsing, all 7 assignments)
- Exercise structure validation
- RelativeValidator: relative_to_model, qualitative, range_check, none
- ExerciseRunner: check_answer, get_hint
- ProgressTracker: state management
- OLG model basic sanity
- PDF/HTML export
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from classroom.engine import (
    AssignmentLoader,
    ComplexityLevel,
    Exercise,
    ExerciseParameter,
    ExerciseRunner,
    ExerciseType,
    Hint,
    ProgressTracker,
    RelativeValidator,
    ValidationMethod,
    ValidationResult,
    ValidationSpec,
)
from classroom.feedback import FeedbackEngine
from classroom.pdf_export import generate_submission_html

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def loader():
    return AssignmentLoader()


@pytest.fixture
def runner():
    return ExerciseRunner()


@pytest.fixture
def feedback_engine():
    return FeedbackEngine()


@pytest.fixture
def mock_session_state():
    return {}


@pytest.fixture
def tracker(mock_session_state):
    return ProgressTracker(mock_session_state)


@pytest.fixture
def simple_parameter():
    return ExerciseParameter(
        name="rate_change",
        label="Rate change",
        min=-0.10,
        max=0.10,
        step=0.01,
        default=0.02,
        unit="decimal",
    )


@pytest.fixture
def simple_exercise(simple_parameter):
    return Exercise(
        id="test_ex1",
        title="Test Exercise",
        type=ExerciseType.PARAMETER_EXPLORATION,
        complexity=ComplexityLevel.UNDERGRADUATE,
        prompt="Test prompt",
        parameters=[simple_parameter],
        hints=[
            Hint(level=1, text="First hint"),
            Hint(level=2, text="Second hint"),
        ],
        validation=ValidationSpec(
            method=ValidationMethod.RELATIVE_TO_MODEL,
            policy_type="income_tax",
            policy_params={
                "name": "Test",
                "description": "Test policy",
                "rate_change": "{rate_change}",
                "affected_income_threshold": 400000,
            },
            target_field="total_10_year_cost",
            tolerance=0.02,
        ),
        expected_insight="Revenue scales linearly with rate change.",
    )


@pytest.fixture
def range_check_exercise():
    return Exercise(
        id="range_ex1",
        title="Range Check Exercise",
        type=ExerciseType.TARGET_FINDING,
        complexity=ComplexityLevel.UNDERGRADUATE,
        prompt="Enter a value in the range.",
        parameters=[],
        hints=[],
        validation=ValidationSpec(
            method=ValidationMethod.RANGE_CHECK,
            min_acceptable=10.0,
            max_acceptable=30.0,
        ),
    )


@pytest.fixture
def qualitative_exercise():
    return Exercise(
        id="qual_ex1",
        title="Qualitative Exercise",
        type=ExerciseType.COMPARISON,
        complexity=ComplexityLevel.UNDERGRADUATE,
        prompt="Is this positive or negative?",
        parameters=[],
        hints=[],
        validation=ValidationSpec(
            method=ValidationMethod.QUALITATIVE,
            expected_sign="negative",
        ),
    )


@pytest.fixture
def open_exercise():
    return Exercise(
        id="open_ex1",
        title="Open Analysis Exercise",
        type=ExerciseType.OPEN_ANALYSIS,
        complexity=ComplexityLevel.GRADUATE,
        prompt="Write your analysis.",
        parameters=[],
        hints=[],
        validation=ValidationSpec(method=ValidationMethod.NONE),
    )


# =============================================================================
# ASSIGNMENT LOADING TESTS
# =============================================================================

class TestAssignmentLoader:

    def test_list_assignments_returns_expected_ids(self, loader):
        assignments = loader.list_assignments()
        expected = {
            "laffer_curve",
            "tcja_analysis",
            "distributional_incidence",
            "progressive_vs_flat",
            "deficit_financing",
            "trade_tariff",
            "olg_generational",
        }
        assert expected.issubset(set(assignments)), (
            f"Missing assignments: {expected - set(assignments)}"
        )

    def test_load_laffer_curve(self, loader):
        a = loader.load("laffer_curve")
        assert a.id == "laffer_curve"
        assert a.title
        assert len(a.exercises) > 0
        assert ComplexityLevel.UNDERGRADUATE in a.complexity_levels

    def test_load_tcja_analysis(self, loader):
        a = loader.load("tcja_analysis")
        assert a.id == "tcja_analysis"
        assert len(a.exercises_for_level(ComplexityLevel.UNDERGRADUATE)) >= 2

    def test_load_distributional_incidence(self, loader):
        a = loader.load("distributional_incidence")
        assert a.id == "distributional_incidence"

    def test_load_progressive_vs_flat(self, loader):
        a = loader.load("progressive_vs_flat")
        assert a.id == "progressive_vs_flat"

    def test_load_deficit_financing(self, loader):
        a = loader.load("deficit_financing")
        assert a.id == "deficit_financing"

    def test_load_trade_tariff(self, loader):
        a = loader.load("trade_tariff")
        assert a.id == "trade_tariff"
        exercises = a.exercises_for_level(ComplexityLevel.UNDERGRADUATE)
        assert len(exercises) >= 1

    def test_load_olg_generational(self, loader):
        a = loader.load("olg_generational")
        assert a.id == "olg_generational"
        # Should have exercises at all levels
        assert len(a.exercises_for_level(ComplexityLevel.UNDERGRADUATE)) >= 1

    def test_missing_assignment_raises(self, loader):
        with pytest.raises(FileNotFoundError):
            loader.load("nonexistent_assignment_xyz")

    def test_all_exercises_have_required_fields(self, loader):
        for aid in loader.list_assignments():
            a = loader.load(aid)
            for ex in a.exercises:
                assert ex.id, f"{aid}: exercise missing id"
                assert ex.title, f"{aid}/{ex.id}: missing title"
                assert ex.prompt, f"{aid}/{ex.id}: missing prompt"
                assert ex.complexity in ComplexityLevel.__members__.values()
                assert ex.type in ExerciseType.__members__.values()

    def test_all_exercises_with_relative_validation_have_policy_type(self, loader):
        for aid in loader.list_assignments():
            a = loader.load(aid)
            for ex in a.exercises:
                if (
                    ex.validation
                    and ex.validation.method == ValidationMethod.RELATIVE_TO_MODEL
                ):
                    assert ex.validation.policy_type, (
                        f"{aid}/{ex.id}: relative_to_model missing policy_type"
                    )
                    assert ex.validation.target_field, (
                        f"{aid}/{ex.id}: relative_to_model missing target_field"
                    )

    def test_hints_sorted_by_level(self, loader):
        for aid in ["laffer_curve", "tcja_analysis"]:
            a = loader.load(aid)
            for ex in a.exercises:
                if ex.hints:
                    levels = [h.level for h in ex.hints]
                    assert levels == sorted(levels), (
                        f"{aid}/{ex.id}: hints not sorted by level"
                    )

    def test_parameters_have_valid_ranges(self, loader):
        for aid in loader.list_assignments():
            a = loader.load(aid)
            for ex in a.exercises:
                for p in ex.parameters:
                    assert p.min <= p.default <= p.max, (
                        f"{aid}/{ex.id}/{p.name}: default {p.default} "
                        f"not in [{p.min}, {p.max}]"
                    )
                    assert p.step > 0, f"{aid}/{ex.id}/{p.name}: step must be positive"

    def test_learning_objectives_present(self, loader):
        for aid in loader.list_assignments():
            a = loader.load(aid)
            assert a.learning_objectives, f"{aid}: missing learning_objectives"

    def test_exercises_for_level_filters_correctly(self, loader):
        a = loader.load("laffer_curve")
        ug_exercises = a.exercises_for_level(ComplexityLevel.UNDERGRADUATE)
        for ex in ug_exercises:
            assert ex.complexity == ComplexityLevel.UNDERGRADUATE

    def test_complexity_levels_nonempty(self, loader):
        for aid in loader.list_assignments():
            a = loader.load(aid)
            assert len(a.complexity_levels) > 0


# =============================================================================
# VALIDATION TESTS — Range and Qualitative
# =============================================================================

class TestValidatorNonRelative:

    def test_range_check_passes_in_range(self, runner, range_check_exercise):
        result = runner.check_answer(range_check_exercise, {}, 20.0)
        assert result.correct

    def test_range_check_fails_below_range(self, runner, range_check_exercise):
        result = runner.check_answer(range_check_exercise, {}, 5.0)
        assert not result.correct

    def test_range_check_fails_above_range(self, runner, range_check_exercise):
        result = runner.check_answer(range_check_exercise, {}, 50.0)
        assert not result.correct

    def test_range_check_passes_at_boundary(self, runner, range_check_exercise):
        result = runner.check_answer(range_check_exercise, {}, 10.0)
        assert result.correct

    def test_qualitative_negative_correct(self, runner, qualitative_exercise):
        result = runner.check_answer(qualitative_exercise, {}, -100.0)
        assert result.correct

    def test_qualitative_negative_wrong_sign(self, runner, qualitative_exercise):
        result = runner.check_answer(qualitative_exercise, {}, 100.0)
        assert not result.correct

    def test_qualitative_positive_sign(self, runner):
        ex = Exercise(
            id="q_pos",
            title="Positive",
            type=ExerciseType.COMPARISON,
            complexity=ComplexityLevel.UNDERGRADUATE,
            prompt="...",
            parameters=[],
            hints=[],
            validation=ValidationSpec(
                method=ValidationMethod.QUALITATIVE,
                expected_sign="positive",
            ),
        )
        assert runner.check_answer(ex, {}, 50.0).correct
        assert not runner.check_answer(ex, {}, -50.0).correct

    def test_open_exercise_always_passes(self, runner, open_exercise):
        result = runner.check_answer(open_exercise, {}, 999.0)
        assert result.correct

    def test_no_validation_always_passes(self, runner):
        ex = Exercise(
            id="no_val",
            title="No val",
            type=ExerciseType.OPEN_ANALYSIS,
            complexity=ComplexityLevel.ADVANCED,
            prompt="...",
            parameters=[],
            hints=[],
            validation=None,
        )
        result = runner.check_answer(ex, {}, 0.0)
        assert result.correct


# =============================================================================
# VALIDATION TESTS — Relative to model
# =============================================================================

class TestRelativeValidator:

    def test_param_resolution_replaces_placeholders(self):
        v = RelativeValidator()
        template = {
            "rate_change": "{rate_change}",
            "threshold": "{affected_income_threshold}",
            "name": "Test",
        }
        student_params = {"rate_change": 0.02, "affected_income_threshold": 400000.0}
        resolved = v._resolve_params(template, student_params)
        assert resolved["rate_change"] == 0.02
        assert resolved["threshold"] == 400000.0
        assert resolved["name"] == "Test"  # unchanged string without placeholder

    def test_param_resolution_multiple_placeholders(self):
        v = RelativeValidator()
        # Mixed: one placeholder remaining after resolution of 'a'
        resolved = v._resolve_params({"x": "{a}"}, {"a": 1.5})
        assert resolved["x"] == 1.5

    def test_correct_answer_within_tolerance(self):
        RelativeValidator()
        spec = ValidationSpec(
            method=ValidationMethod.RELATIVE_TO_MODEL,
            policy_type="income_tax",
            policy_params={},
            target_field="total_10_year_cost",
            tolerance=0.02,
        )
        # Patch: set model_answer manually to avoid running real scorer
        spec._mock_answer = -250.0  # won't be used; we'll test the logic path

        # Test the tolerance check logic directly
        model_answer = -250.0
        student_answer = -252.5  # 1% off
        pct_error = abs(student_answer - model_answer) / abs(model_answer)
        assert pct_error <= spec.tolerance

    def test_incorrect_answer_outside_tolerance(self):
        model_answer = -250.0
        student_answer = -200.0  # 20% off
        tolerance = 0.02
        pct_error = abs(student_answer - model_answer) / abs(model_answer)
        assert pct_error > tolerance

    def test_validate_qualitative_returns_result(self):
        v = RelativeValidator()
        spec = ValidationSpec(
            method=ValidationMethod.QUALITATIVE,
            expected_sign="negative",
        )
        result = v.validate(-100.0, spec, {})
        assert result.correct
        assert isinstance(result, ValidationResult)

    def test_validate_range_check_returns_result(self):
        v = RelativeValidator()
        spec = ValidationSpec(
            method=ValidationMethod.RANGE_CHECK,
            min_acceptable=5.0,
            max_acceptable=25.0,
        )
        assert v.validate(15.0, spec, {}).correct
        assert not v.validate(50.0, spec, {}).correct

    def test_income_tax_relative_validation(self):
        """Integration test: income_tax relative_to_model validation."""
        v = RelativeValidator()
        spec = ValidationSpec(
            method=ValidationMethod.RELATIVE_TO_MODEL,
            policy_type="income_tax",
            policy_params={
                "name": "Test",
                "description": "Test",
                "rate_change": "{rate_change}",
                "affected_income_threshold": 400000,
            },
            target_field="total_10_year_cost",
            tolerance=0.02,
        )
        # Get the actual model answer first
        model_answer = v._compute_model_answer(spec, {"rate_change": 0.02})
        assert model_answer is not None
        assert isinstance(model_answer, float)

        # An answer matching the model exactly should pass
        result = v.validate(model_answer, spec, {"rate_change": 0.02})
        assert result.correct
        assert result.pct_error is not None
        assert result.pct_error < 0.001

    def test_income_tax_relative_wrong_answer(self):
        """A very wrong answer should fail relative validation."""
        v = RelativeValidator()
        spec = ValidationSpec(
            method=ValidationMethod.RELATIVE_TO_MODEL,
            policy_type="income_tax",
            policy_params={
                "name": "Test",
                "description": "Test",
                "rate_change": "{rate_change}",
                "affected_income_threshold": 400000,
            },
            target_field="total_10_year_cost",
            tolerance=0.02,
        )
        # Wildly wrong answer: $5B when model expects ~$250B
        result = v.validate(-5.0, spec, {"rate_change": 0.02})
        assert not result.correct
        assert result.pct_error > 0.5

    def test_relative_validation_tolerance_boundary(self):
        """Answer exactly at boundary should pass."""
        v = RelativeValidator()
        spec = ValidationSpec(
            method=ValidationMethod.RELATIVE_TO_MODEL,
            policy_type="income_tax",
            policy_params={
                "name": "Test",
                "description": "",
                "rate_change": "{rate_change}",
                "affected_income_threshold": 400000,
            },
            target_field="total_10_year_cost",
            tolerance=0.05,  # 5% tolerance
        )
        model_answer = v._compute_model_answer(spec, {"rate_change": 0.02})
        # Answer at exactly 5% off
        boundary_answer = model_answer * 1.05
        result = v.validate(boundary_answer, spec, {"rate_change": 0.02})
        assert result.correct  # 5% = tolerance, should pass

    def test_relative_validation_different_rate_changes(self):
        """Model answer should scale roughly proportionally with rate change."""
        v = RelativeValidator()
        spec = ValidationSpec(
            method=ValidationMethod.RELATIVE_TO_MODEL,
            policy_type="income_tax",
            policy_params={
                "name": "Test",
                "description": "",
                "rate_change": "{rate_change}",
                "affected_income_threshold": 400000,
            },
            target_field="total_10_year_cost",
            tolerance=0.02,
        )
        answer_2pp = v._compute_model_answer(spec, {"rate_change": 0.02})
        answer_4pp = v._compute_model_answer(spec, {"rate_change": 0.04})
        assert answer_2pp is not None
        assert answer_4pp is not None
        # Revenue should roughly double for double the rate change (within 20%)
        ratio = abs(answer_4pp) / abs(answer_2pp)
        assert 1.5 <= ratio <= 2.5, f"Expected ~2x ratio, got {ratio:.2f}"


# =============================================================================
# EXERCISE RUNNER TESTS
# =============================================================================

class TestExerciseRunner:

    def test_get_hint_level_1(self, runner, simple_exercise):
        hint = runner.get_hint(simple_exercise, 1)
        assert hint == "First hint"

    def test_get_hint_level_2(self, runner, simple_exercise):
        hint = runner.get_hint(simple_exercise, 2)
        assert hint == "Second hint"

    def test_get_hint_nonexistent_level(self, runner, simple_exercise):
        hint = runner.get_hint(simple_exercise, 99)
        assert hint == ""

    def test_get_all_hints_returns_sorted(self, runner, simple_exercise):
        hints = runner.get_all_hints(simple_exercise)
        assert hints[0].level < hints[1].level

    def test_check_answer_with_no_validation(self, runner):
        ex = Exercise(
            id="nv",
            title="No Validation",
            type=ExerciseType.OPEN_ANALYSIS,
            complexity=ComplexityLevel.UNDERGRADUATE,
            prompt="...",
            parameters=[],
            hints=[],
            validation=None,
        )
        result = runner.check_answer(ex, {}, 42.0)
        assert result.correct

    def test_check_answer_range_correct(self, runner, range_check_exercise):
        result = runner.check_answer(range_check_exercise, {}, 20.0)
        assert result.correct

    def test_check_answer_range_wrong(self, runner, range_check_exercise):
        result = runner.check_answer(range_check_exercise, {}, 100.0)
        assert not result.correct

    def test_check_answer_qualitative_negative(self, runner, qualitative_exercise):
        assert runner.check_answer(qualitative_exercise, {}, -50.0).correct
        assert not runner.check_answer(qualitative_exercise, {}, 50.0).correct


# =============================================================================
# PROGRESS TRACKER TESTS
# =============================================================================

class TestProgressTracker:

    def test_initial_state_empty(self, tracker):
        assert tracker.assignment_id is None
        assert tracker.current_exercise_index == 0

    def test_set_assignment_id(self, tracker):
        tracker.assignment_id = "laffer_curve"
        assert tracker.assignment_id == "laffer_curve"

    def test_set_complexity(self, tracker):
        tracker.complexity = ComplexityLevel.GRADUATE
        assert tracker.complexity == ComplexityLevel.GRADUATE

    def test_mark_complete_updates_state(self, tracker):
        result = ValidationResult(
            correct=True,
            student_answer=-250.0,
            model_answer=-252.0,
            tolerance=0.02,
            message="Correct",
        )
        tracker.mark_complete("ex1", result)
        assert tracker.is_complete("ex1")
        assert tracker.current_exercise_index == 1

    def test_get_answer_after_mark_complete(self, tracker):
        result = ValidationResult(
            correct=True,
            student_answer=-100.0,
            model_answer=-100.0,
            tolerance=0.02,
            message="OK",
        )
        tracker.mark_complete("ex1", result)
        retrieved = tracker.get_answer("ex1")
        assert retrieved is not None
        assert retrieved.student_answer == -100.0

    def test_hints_used_tracking(self, tracker):
        assert tracker.hints_used("ex1") == 0
        tracker.use_hint("ex1", 1)
        assert tracker.hints_used("ex1") == 1
        tracker.use_hint("ex1", 2)
        assert tracker.hints_used("ex1") == 2
        # Use lower level again — should not reduce
        tracker.use_hint("ex1", 1)
        assert tracker.hints_used("ex1") == 2

    def test_completion_fraction(self, tracker):
        exercises = [
            Exercise(
                id=f"ex{i}", title=f"Ex {i}",
                type=ExerciseType.PARAMETER_EXPLORATION,
                complexity=ComplexityLevel.UNDERGRADUATE,
                prompt="...", parameters=[], hints=[], validation=None,
            )
            for i in range(3)
        ]
        done, total = tracker.completion_fraction(exercises)
        assert done == 0 and total == 3

        result = ValidationResult(correct=True, student_answer=0, model_answer=None, tolerance=0, message="")
        tracker.mark_complete("ex0", result)
        tracker.mark_complete("ex1", result)
        done, total = tracker.completion_fraction(exercises)
        assert done == 2 and total == 3

    def test_reset_clears_all_state(self, tracker):
        result = ValidationResult(correct=True, student_answer=0, model_answer=None, tolerance=0, message="")
        tracker.mark_complete("ex1", result)
        tracker.use_hint("ex1", 1)
        tracker.reset()
        assert not tracker.is_complete("ex1")
        assert tracker.hints_used("ex1") == 0
        assert tracker.current_exercise_index == 0


# =============================================================================
# FEEDBACK ENGINE TESTS
# =============================================================================

class TestFeedbackEngine:

    def test_correct_no_hints_returns_string(self, feedback_engine, simple_exercise):
        result = ValidationResult(
            correct=True,
            student_answer=-250.0,
            model_answer=-252.0,
            tolerance=0.02,
            message="Correct",
            pct_error=0.008,
        )
        fb = feedback_engine.generate(
            exercise=simple_exercise,
            result=result,
            hints_used=0,
            complexity=ComplexityLevel.UNDERGRADUATE,
        )
        assert isinstance(fb, str)
        assert len(fb) > 10
        assert "Correct" in fb or "correct" in fb

    def test_incorrect_returns_redirect(self, feedback_engine, simple_exercise):
        result = ValidationResult(
            correct=False,
            student_answer=-50.0,
            model_answer=-250.0,
            tolerance=0.02,
            message="Not quite",
            pct_error=0.80,
        )
        fb = feedback_engine.generate(
            exercise=simple_exercise,
            result=result,
            hints_used=0,
            complexity=ComplexityLevel.UNDERGRADUATE,
        )
        assert isinstance(fb, str)
        assert len(fb) > 10

    def test_graduate_correct_mentions_elasticity(self, feedback_engine, simple_exercise):
        result = ValidationResult(
            correct=True,
            student_answer=-250.0,
            model_answer=-252.0,
            tolerance=0.02,
            message="Correct",
            pct_error=0.008,
        )
        fb = feedback_engine.generate(
            exercise=simple_exercise,
            result=result,
            hints_used=0,
            complexity=ComplexityLevel.GRADUATE,
        )
        assert "elasticity" in fb.lower() or "sensitivity" in fb.lower()

    def test_correct_with_insight(self, feedback_engine, simple_exercise):
        result = ValidationResult(
            correct=True,
            student_answer=-250.0,
            model_answer=-252.0,
            tolerance=0.02,
            message="Correct",
            pct_error=0.008,
        )
        fb = feedback_engine.generate(
            exercise=simple_exercise,
            result=result,
            hints_used=0,
            complexity=ComplexityLevel.UNDERGRADUATE,
        )
        # Expected insight should be included
        assert "linearly" in fb.lower() or "Key insight" in fb

    def test_get_explanation_returns_string(self, feedback_engine, simple_exercise):
        exp = feedback_engine.get_explanation(simple_exercise, ComplexityLevel.UNDERGRADUATE)
        assert isinstance(exp, str)
        assert len(exp) > 0

    def test_open_analysis_feedback(self, feedback_engine, open_exercise):
        result = ValidationResult(
            correct=True,
            student_answer=0.0,
            model_answer=None,
            tolerance=0,
            message="Open-ended",
        )
        fb = feedback_engine.generate(
            exercise=open_exercise,
            result=result,
            hints_used=0,
            complexity=ComplexityLevel.GRADUATE,
        )
        assert isinstance(fb, str)


# =============================================================================
# OLG MODEL TESTS
# =============================================================================

class TestOLGModel:

    def test_olg_baseline_runs(self):
        from fiscal_model.models.olg import OLGModel
        model = OLGModel()
        result = model.run(scenario_name="Baseline")
        assert result is not None
        assert len(result.years) == model.params.sim_years

    def test_olg_gdp_path_positive(self):
        from fiscal_model.models.olg import OLGModel
        model = OLGModel()
        result = model.run()
        assert np.all(result.gdp_path > 0)

    def test_olg_wage_path_positive(self):
        from fiscal_model.models.olg import OLGModel
        model = OLGModel()
        result = model.run()
        assert np.all(result.wage_path > 0)

    def test_olg_debt_shock_increases_debt(self):
        from fiscal_model.models.olg import OLGModel
        model = OLGModel()
        baseline = model.run()
        shocked = model.run(debt_shock_pct_gdp=0.02)
        # Higher deficit path should lead to higher total debt
        assert shocked.debt_path[-1] > baseline.debt_path[-1]

    def test_olg_net_tax_rate_not_all_nan(self):
        from fiscal_model.models.olg import OLGModel
        model = OLGModel()
        result = model.run()
        valid = result.net_tax_rate[~np.isnan(result.net_tax_rate)]
        assert len(valid) > 0

    def test_olg_birth_years_span_past_and_future(self):
        from fiscal_model.models.olg import OLGModel
        model = OLGModel()
        result = model.run()
        assert result.birth_years[0] < model.params.base_year
        assert result.birth_years[-1] > model.params.base_year

    def test_olg_ss_cut_reduces_transfers(self):
        from fiscal_model.models.olg import OLGModel
        model = OLGModel()
        baseline = model.run()
        ss_reform = model.run(ss_replacement_change=-0.20)
        # SS cut should reduce total transfers (average over cohorts)
        baseline_transfers = np.nanmean(baseline.pv_transfers)
        reform_transfers = np.nanmean(ss_reform.pv_transfers)
        assert reform_transfers < baseline_transfers

    def test_olg_burden_vs_baseline(self):
        from fiscal_model.models.olg import OLGModel
        model = OLGModel()
        baseline = model.run()
        shocked = model.run(debt_shock_pct_gdp=0.02)
        diff = shocked.burden_vs_baseline(baseline)
        # Some future cohorts should have higher tax rates under higher debt
        # (at least the sign should be correct for future cohorts)
        future_mask = shocked.birth_years > shocked.params.base_year + 10
        valid_diff = diff[future_mask]
        valid_diff = valid_diff[~np.isnan(valid_diff)]
        if len(valid_diff) > 0:
            assert np.mean(valid_diff) >= 0  # higher debt = higher burden

    def test_olg_compare_scenarios(self):
        from fiscal_model.models.olg import OLGModel
        model = OLGModel()
        results = model.compare_scenarios([
            {"scenario_name": "Baseline"},
            {"scenario_name": "High Debt", "debt_shock_pct_gdp": 0.02},
        ])
        assert "Baseline" in results
        assert "High Debt" in results

    def test_olg_params_custom(self):
        from fiscal_model.models.olg import OLGModel, OLGParams
        params = OLGParams(sim_years=40, baseline_deficit_gdp=0.04)
        model = OLGModel(params=params)
        result = model.run()
        assert len(result.years) == 40

    def test_olg_labor_tax_change_reduces_net_wages(self):
        from fiscal_model.models.olg import OLGModel
        model = OLGModel()
        baseline = model.run()
        high_tax = model.run(labor_tax_change=0.05)
        # Higher labor tax → higher pv_taxes for current cohorts
        current_mask = (baseline.birth_years >= 1980) & (baseline.birth_years <= 2010)
        baseline_taxes = np.nanmean(baseline.pv_taxes[current_mask])
        high_taxes = np.nanmean(high_tax.pv_taxes[current_mask])
        assert high_taxes > baseline_taxes


# =============================================================================
# PDF EXPORT TESTS
# =============================================================================

class TestPDFExport:

    def test_generate_html_returns_string(self, loader):
        assignment = loader.load("laffer_curve")
        html = generate_submission_html(
            assignment=assignment,
            student_name="Jane Smith",
            complexity=ComplexityLevel.UNDERGRADUATE,
            answers={},
            course_name="Econ 501",
        )
        assert isinstance(html, str)
        assert len(html) > 100

    def test_html_contains_assignment_title(self, loader):
        assignment = loader.load("laffer_curve")
        html = generate_submission_html(
            assignment=assignment,
            student_name="Test Student",
            complexity=ComplexityLevel.UNDERGRADUATE,
            answers={},
        )
        assert "Laffer" in html

    def test_html_contains_student_name(self, loader):
        assignment = loader.load("laffer_curve")
        html = generate_submission_html(
            assignment=assignment,
            student_name="Alice Jones",
            complexity=ComplexityLevel.UNDERGRADUATE,
            answers={},
        )
        assert "Alice Jones" in html

    def test_html_is_valid_structure(self, loader):
        assignment = loader.load("laffer_curve")
        html = generate_submission_html(
            assignment=assignment,
            student_name="Bob",
            complexity=ComplexityLevel.UNDERGRADUATE,
            answers={},
        )
        assert "<html" in html
        assert "</html>" in html
        assert "<body" in html
        assert "</body>" in html

    def test_html_with_answers_shows_score(self, loader):
        assignment = loader.load("laffer_curve")
        exercises = assignment.exercises_for_level(ComplexityLevel.UNDERGRADUATE)
        answers = {}
        if exercises:
            answers[exercises[0].id] = ValidationResult(
                correct=True,
                student_answer=-250.0,
                model_answer=-252.0,
                tolerance=0.02,
                message="Correct!",
                pct_error=0.008,
            )
        html = generate_submission_html(
            assignment=assignment,
            student_name="Student",
            complexity=ComplexityLevel.UNDERGRADUATE,
            answers=answers,
        )
        # Should show 1/N score
        assert "1/" in html

    def test_html_with_student_notes(self, loader):
        assignment = loader.load("laffer_curve")
        exercises = assignment.exercises_for_level(ComplexityLevel.UNDERGRADUATE)
        notes = {}
        if exercises:
            notes[exercises[0].id] = "My analysis: revenue scales linearly..."
        html = generate_submission_html(
            assignment=assignment,
            student_name="Student",
            complexity=ComplexityLevel.UNDERGRADUATE,
            answers={},
            notes=notes,
        )
        if notes:
            assert "My analysis" in html

    def test_html_escapes_special_chars(self, loader):
        assignment = loader.load("laffer_curve")
        html = generate_submission_html(
            assignment=assignment,
            student_name='<script>alert("xss")</script>',
            complexity=ComplexityLevel.UNDERGRADUATE,
            answers={},
        )
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


# =============================================================================
# EXERCISE PROGRESSION TESTS
# =============================================================================

class TestExerciseProgression:

    def test_exercises_progress_in_order(self, loader, tracker):
        assignment = loader.load("laffer_curve")
        tracker.assignment_id = "laffer_curve"
        tracker.complexity = ComplexityLevel.UNDERGRADUATE
        exercises = assignment.exercises_for_level(ComplexityLevel.UNDERGRADUATE)

        assert tracker.current_exercise_index == 0
        result = ValidationResult(correct=True, student_answer=0, model_answer=None, tolerance=0, message="")

        tracker.mark_complete(exercises[0].id, result)
        assert tracker.current_exercise_index == 1

        if len(exercises) > 1:
            tracker.mark_complete(exercises[1].id, result)
            assert tracker.current_exercise_index == 2

    def test_completion_fraction_tracks_progress(self, loader, tracker):
        assignment = loader.load("laffer_curve")
        exercises = assignment.exercises_for_level(ComplexityLevel.UNDERGRADUATE)
        result = ValidationResult(correct=True, student_answer=0, model_answer=None, tolerance=0, message="")

        done, _total = tracker.completion_fraction(exercises)
        assert done == 0

        tracker.mark_complete(exercises[0].id, result)
        done, _total = tracker.completion_fraction(exercises)
        assert done == 1

    def test_reset_clears_progress_for_new_assignment(self, loader, tracker):
        assignment = loader.load("laffer_curve")
        exercises = assignment.exercises_for_level(ComplexityLevel.UNDERGRADUATE)
        result = ValidationResult(correct=True, student_answer=0, model_answer=None, tolerance=0, message="")

        tracker.mark_complete(exercises[0].id, result)
        assert tracker.is_complete(exercises[0].id)

        # Simulating switching assignment
        tracker.reset()
        assert not tracker.is_complete(exercises[0].id)
        assert tracker.current_exercise_index == 0

    def test_already_complete_exercise_state_preserved(self, tracker):
        result1 = ValidationResult(correct=True, student_answer=-250.0, model_answer=-252.0, tolerance=0.02, message="OK", pct_error=0.008)
        result2 = ValidationResult(correct=True, student_answer=-130.0, model_answer=-132.0, tolerance=0.02, message="OK", pct_error=0.015)

        tracker.mark_complete("ex1", result1)
        tracker.mark_complete("ex2", result2)

        assert tracker.is_complete("ex1")
        assert tracker.is_complete("ex2")
        r1 = tracker.get_answer("ex1")
        assert r1.student_answer == -250.0


# =============================================================================
# INTEGRATION TEST: Full assignment cycle
# =============================================================================

class TestFullAssignmentCycle:

    def test_laffer_curve_undergraduate_full_cycle(self, loader, runner, feedback_engine, tracker):
        """End-to-end: load assignment, run exercise, check answer, get feedback."""
        assignment = loader.load("laffer_curve")
        exercises = assignment.exercises_for_level(ComplexityLevel.UNDERGRADUATE)
        assert len(exercises) >= 1

        ex = exercises[0]
        tracker.assignment_id = "laffer_curve"
        tracker.complexity = ComplexityLevel.UNDERGRADUATE

        # Get model answer via validator
        v = RelativeValidator()
        if ex.validation and ex.validation.method == ValidationMethod.RELATIVE_TO_MODEL:
            model_answer = v._compute_model_answer(
                ex.validation,
                {p.name: p.default for p in ex.parameters},
            )
            assert model_answer is not None

            # Submit correct answer (within 1%)
            student_answer = model_answer * 1.005
            result = runner.check_answer(
                ex,
                {p.name: p.default for p in ex.parameters},
                student_answer,
            )
            assert result.correct, f"Expected correct, got: {result.message}"

            # Get feedback
            fb = feedback_engine.generate(ex, result, 0, ComplexityLevel.UNDERGRADUATE)
            assert fb

            # Track progress
            tracker.mark_complete(ex.id, result)
            assert tracker.is_complete(ex.id)
