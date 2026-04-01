"""
Classroom Mode for Fiscal Policy Calculator

URL activation: ?mode=classroom&assignment=laffer_curve

Provides pre-built assignment templates for economics courses at
undergraduate, graduate, and advanced levels. Assignments cover:

1. laffer_curve          — ETI, behavioral responses, revenue-maximizing rates
2. tcja_analysis         — TCJA extension, SALT cap, dynamic scoring
3. distributional_incidence — Tax incidence, quintile analysis, regressive/progressive
4. progressive_vs_flat   — Flat tax design, distributional effects
5. deficit_financing     — Multipliers, crowding out, debt sustainability
6. trade_tariff          — Tariff revenue, consumer prices, retaliation
7. olg_generational      — OLG model, generational accounts, SS reform

Usage::

    from classroom.engine import AssignmentLoader, ExerciseRunner, ProgressTracker
    from classroom.feedback import FeedbackEngine
    from classroom.pdf_export import generate_submission_html

    loader = AssignmentLoader()
    assignment = loader.load("laffer_curve")
    runner = ExerciseRunner()
    feedback_engine = FeedbackEngine()
"""

from .engine import (
    Assignment,
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
from .feedback import FeedbackEngine
from .pdf_export import generate_submission_html

__all__ = [
    "Assignment",
    "AssignmentLoader",
    "ComplexityLevel",
    "Exercise",
    "ExerciseParameter",
    "ExerciseRunner",
    "ExerciseType",
    "FeedbackEngine",
    "Hint",
    "ProgressTracker",
    "RelativeValidator",
    "ValidationMethod",
    "ValidationResult",
    "ValidationSpec",
    "generate_submission_html",
]
