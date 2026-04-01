"""
Pedagogical Feedback Engine

Generates contextual feedback messages and explanations for student answers.
Feedback adapts to complexity level, whether the student used hints, and
how close their answer was to the model estimate.
"""

from __future__ import annotations

from .engine import ComplexityLevel, Exercise, ValidationResult


class FeedbackEngine:
    """
    Produces pedagogical feedback for exercise attempts.

    Feedback is tiered:
    - **Correct, no hints**: positive reinforcement + deepen insight
    - **Correct, hints used**: affirm + note dependency
    - **Incorrect, close**: encouragement + directional hint
    - **Incorrect, far off**: stronger redirect
    - **Open analysis**: prompt reflection questions
    """

    # Threshold for "close" — within 20% for undergrad, 10% for grad/advanced
    CLOSE_THRESHOLDS = {
        ComplexityLevel.UNDERGRADUATE: 0.20,
        ComplexityLevel.GRADUATE: 0.10,
        ComplexityLevel.ADVANCED: 0.05,
    }

    def generate(
        self,
        exercise: Exercise,
        result: ValidationResult,
        hints_used: int,
        complexity: ComplexityLevel,
    ) -> str:
        """Return a multi-sentence feedback string."""
        if result.model_answer is None:
            # Open analysis or qualitative
            return self._open_feedback(exercise, result, complexity)

        if result.correct:
            return self._correct_feedback(exercise, result, hints_used, complexity)
        else:
            return self._incorrect_feedback(exercise, result, hints_used, complexity)

    def _correct_feedback(
        self,
        exercise: Exercise,
        result: ValidationResult,
        hints_used: int,
        complexity: ComplexityLevel,
    ) -> str:
        base = "Correct! "
        if hints_used == 0:
            base += "You worked through this without any hints — well done. "
        elif hints_used == 1:
            base += "You used one hint — that's fine at this stage. "
        else:
            base += f"You used {hints_used} hints to get there. "

        if result.pct_error is not None:
            base += (
                f"Your estimate was {result.pct_error*100:.1f}% off the model's "
                f"${abs(result.model_answer):.1f}B score. "
            )

        # Add the expected insight if available
        if exercise.expected_insight:
            base += f"\n\n**Key insight:** {exercise.expected_insight}"

        if complexity == ComplexityLevel.GRADUATE:
            base += (
                "\n\nFor further exploration: consider how sensitivity to the "
                "elasticity assumption changes your estimate, and how CBO's "
                "conventional vs. dynamic scores differ."
            )
        elif complexity == ComplexityLevel.ADVANCED:
            base += (
                "\n\nFor research-level analysis: examine how model uncertainty "
                "interacts with distributional assumptions, and compare your "
                "estimate to published PWBM or Yale Budget Lab scores."
            )
        return base

    def _incorrect_feedback(
        self,
        exercise: Exercise,
        result: ValidationResult,
        hints_used: int,
        complexity: ComplexityLevel,
    ) -> str:
        close_thresh = self.CLOSE_THRESHOLDS[complexity]
        is_close = (result.pct_error is not None and result.pct_error <= close_thresh)

        if is_close:
            msg = (
                f"Close! Your estimate (${result.student_answer:.1f}B) is "
                f"{result.pct_error*100:.1f}% off — just outside the "
                f"{result.tolerance*100:.0f}% acceptance window. "
            )
            if result.student_answer > result.model_answer:
                msg += "Your estimate is a bit high. "
            else:
                msg += "Your estimate is a bit low. "
            if hints_used < 3:
                msg += "Try using a hint to refine your approach."
            else:
                msg += "Review your parameter assumptions and try again."
        else:
            msg = (
                f"Not quite. The model gives ${abs(result.model_answer):.1f}B; "
                f"your answer was ${result.student_answer:.1f}B "
                f"({result.pct_error*100:.0f}% off). "
            )
            if hints_used == 0:
                msg += "Try using the first hint to orient yourself."
            else:
                msg += (
                    "Check that you are using the right base (taxable income "
                    "× number of affected filers × rate change), then apply "
                    "the behavioral offset."
                )

        return msg

    def _open_feedback(
        self,
        exercise: Exercise,
        result: ValidationResult,
        complexity: ComplexityLevel,
    ) -> str:
        if result.correct:
            reflection_prompts = {
                ComplexityLevel.UNDERGRADUATE: (
                    "Good work. Reflect on how the results changed as you varied "
                    "parameters. What surprised you?"
                ),
                ComplexityLevel.GRADUATE: (
                    "Well done. Now consider: how sensitive is your conclusion to "
                    "the elasticity assumption? What does this imply for policy "
                    "uncertainty?"
                ),
                ComplexityLevel.ADVANCED: (
                    "Solid analysis. For the memo: explicitly quantify uncertainty "
                    "bounds and compare your model to at least one external "
                    "estimate (CBO, JCT, PWBM)."
                ),
            }
            return reflection_prompts[complexity]
        else:
            return result.message

    def get_explanation(self, exercise: Exercise, complexity: ComplexityLevel) -> str:
        """
        Return a post-exercise explanatory note suitable for the given level.

        This is shown after the student submits (correct or not).
        """
        if exercise.expected_insight:
            base = exercise.expected_insight
        else:
            base = "Review your methodology and compare to the model estimate."

        addendum = {
            ComplexityLevel.UNDERGRADUATE: "",
            ComplexityLevel.GRADUATE: (
                " At the graduate level, you should be able to derive this "
                "analytically from the static revenue formula and ETI."
            ),
            ComplexityLevel.ADVANCED: (
                " For original research, consider publishing your parameter "
                "sensitivity results and comparing to published institutional scores."
            ),
        }
        return base + addendum[complexity]
