"""
Classroom Mode — Streamlit Interface

Activated via URL parameter: ?mode=classroom&assignment=laffer_curve

Renders assignment exercises with parameter sliders, answer submission,
hint system, feedback, and PDF export. Progress persists in session state.

Instructor links:
  ?mode=classroom&assignment=laffer_curve&level=undergraduate
  ?mode=classroom&assignment=tcja_analysis&level=graduate
"""

from __future__ import annotations

import contextlib

import streamlit as st

from classroom.engine import (
    AssignmentLoader,
    ComplexityLevel,
    ExerciseRunner,
    ExerciseType,
    ProgressTracker,
    ValidationResult,
)
from classroom.feedback import FeedbackEngine
from classroom.pdf_export import generate_submission_html
from fiscal_model.ui.helpers import PUBLIC_APP_URL
from fiscal_model.ui.runtime_logging import (
    build_runtime_metadata,
    configure_runtime_logger,
    log_runtime_event,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ASSIGNMENT_LABELS = {
    "laffer_curve": "Laffer Curve: Revenue and Incentives",
    "tcja_analysis": "TCJA: 2017 Tax Cuts and Jobs Act",
    "distributional_incidence": "Tax Incidence: Who Bears the Burden?",
    "progressive_vs_flat": "Progressive vs. Flat Tax",
    "deficit_financing": "Deficit Financing: Multipliers and Sustainability",
    "trade_tariff": "Tariffs: Revenue, Prices, and Retaliation",
    "olg_generational": "Generational Burden: OLG Model",
}

COMPLEXITY_LABELS = {
    ComplexityLevel.UNDERGRADUATE: "Undergraduate",
    ComplexityLevel.GRADUATE: "Graduate",
    ComplexityLevel.ADVANCED: "Advanced / Research",
}

TYPE_ICONS = {
    ExerciseType.PARAMETER_EXPLORATION: "🔧",
    ExerciseType.TARGET_FINDING: "🎯",
    ExerciseType.COMPARISON: "⚖️",
    ExerciseType.OPEN_ANALYSIS: "📝",
}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def render_classroom_app() -> None:
    """Render the full classroom UI."""
    st.set_page_config(
        page_title="Classroom Mode — Fiscal Policy Calculator",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    loader = AssignmentLoader()
    runner = ExerciseRunner()
    feedback_engine = FeedbackEngine()
    tracker = ProgressTracker(st.session_state)

    # Read URL params
    params = st.query_params
    url_assignment = params.get("assignment", "")
    url_level = params.get("level", "")

    _render_sidebar(loader, tracker, url_assignment, url_level)

    if tracker.assignment_id:
        try:
            assignment = loader.load(tracker.assignment_id)
        except FileNotFoundError:
            st.error(f"Assignment '{tracker.assignment_id}' not found.")
            return

        exercises = assignment.exercises_for_level(tracker.complexity)
        if not exercises:
            st.warning(
                f"No exercises available for {tracker.complexity.value} level "
                f"in this assignment."
            )
            return

        _render_main_area(
            assignment=assignment,
            exercises=exercises,
            runner=runner,
            feedback_engine=feedback_engine,
            tracker=tracker,
        )
    else:
        _render_welcome(loader)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def _render_sidebar(loader, tracker, url_assignment: str, url_level: str) -> None:
    with st.sidebar:
        st.title("📚 Classroom Mode")
        st.caption("Fiscal Policy Calculator")
        st.divider()

        # Assignment selector
        available = loader.list_assignments()
        labels = [ASSIGNMENT_LABELS.get(a, a) for a in available]

        # Pre-select from URL param
        default_idx = 0
        if url_assignment and url_assignment in available:
            default_idx = available.index(url_assignment)
            if not tracker.assignment_id:
                tracker.assignment_id = url_assignment

        selected_label = st.selectbox(
            "Assignment",
            options=labels,
            index=default_idx,
            key="sb_assignment_label",
        )
        if selected_label in labels:
            selected_id = available[labels.index(selected_label)]
            if selected_id != tracker.assignment_id:
                tracker.assignment_id = selected_id
                tracker.reset()
                st.rerun()

        # Complexity selector
        level_options = list(COMPLEXITY_LABELS.keys())
        level_labels = list(COMPLEXITY_LABELS.values())

        default_level = ComplexityLevel.UNDERGRADUATE
        if url_level:
            with contextlib.suppress(ValueError):
                default_level = ComplexityLevel(url_level)

        complexity_label = st.selectbox(
            "Complexity Level",
            options=level_labels,
            index=level_options.index(default_level),
            key="sb_complexity",
        )
        new_complexity = level_options[level_labels.index(complexity_label)]
        if new_complexity != tracker.complexity:
            tracker.complexity = new_complexity
            tracker.reset()
            st.rerun()

        st.divider()

        # Student name (for PDF export)
        st.text_input("Your Name", key="student_name", placeholder="e.g., Jane Smith")
        st.text_input("Course (optional)", key="course_name", placeholder="e.g., Econ 501")

        st.divider()

        # Progress
        if tracker.assignment_id:
            try:
                assignment = loader.load(tracker.assignment_id)
                exercises = assignment.exercises_for_level(tracker.complexity)
                done, total = tracker.completion_fraction(exercises)
                st.metric("Progress", f"{done}/{total}", f"{int(done/total*100) if total else 0}%")
            except FileNotFoundError:
                pass

        # Reset button
        if st.button("↺ Reset Progress", key="btn_reset"):
            tracker.reset()
            st.rerun()

        st.divider()

        # Instructor link generator
        with st.expander("📎 Share Assignment Link"):
            if tracker.assignment_id:
                link = (
                    f"{PUBLIC_APP_URL}/?mode=classroom"
                    f"&assignment={tracker.assignment_id}"
                    f"&level={tracker.complexity.value}"
                )
                st.code(link, language=None)
                st.caption("Share this link with students to pre-load the assignment.")


# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------

def _render_welcome(loader) -> None:
    st.title("📚 Classroom Mode")
    st.markdown(
        "Welcome to **Classroom Mode**. Select an assignment from the sidebar to begin."
    )

    available = loader.list_assignments()
    if available:
        st.subheader("Available Assignments")
        cols = st.columns(2)
        for i, aid in enumerate(available):
            with cols[i % 2]:
                label = ASSIGNMENT_LABELS.get(aid, aid)
                st.markdown(f"**{label}**")
                st.caption(f"`{aid}`")
    else:
        st.info("No assignments found. Check the `classroom/assignments/` directory.")


def _render_main_area(assignment, exercises, runner, feedback_engine, tracker) -> None:
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(assignment.title)
        level_label = COMPLEXITY_LABELS[tracker.complexity]
        st.caption(f"{level_label} level · {assignment.estimated_minutes} min estimated")
    with col2:
        done, total = tracker.completion_fraction(exercises)
        pct = int(done / total * 100) if total else 0
        st.metric("Progress", f"{done}/{total}", f"{pct}%")

    # Description
    with st.expander("About this assignment", expanded=False):
        st.markdown(assignment.description)
        if assignment.learning_objectives:
            st.subheader("Learning Objectives")
            for obj in assignment.learning_objectives:
                st.markdown(f"- {obj}")

    st.divider()

    # Exercises
    for idx, exercise in enumerate(exercises):
        _render_exercise(
            exercise=exercise,
            idx=idx,
            runner=runner,
            feedback_engine=feedback_engine,
            tracker=tracker,
        )

    # Export
    st.divider()
    _render_export(assignment, exercises, tracker)


def _render_exercise(exercise, idx, runner, feedback_engine, tracker) -> None:
    is_done = tracker.is_complete(exercise.id)
    icon = TYPE_ICONS.get(exercise.type, "•")
    status = "✅" if is_done else f"{idx + 1}."

    header = f"{status} {icon} **{exercise.title}**"
    if is_done:
        result = tracker.get_answer(exercise.id)
        if result and result.correct:
            header += "  ✓"

    with st.expander(header, expanded=(not is_done)):
        st.markdown(f"*{exercise.type.value.replace('_', ' ').title()}*")
        st.markdown(exercise.prompt)

        if not exercise.parameters:
            # Open analysis — just submit a text note
            _render_open_exercise(exercise, runner, feedback_engine, tracker)
            return

        # Parameter sliders
        student_params: dict[str, float] = {}
        for param in exercise.parameters:
            val = st.slider(
                label=f"{param.label} {f'({param.unit})' if param.unit else ''}",
                min_value=float(param.min),
                max_value=float(param.max),
                value=float(param.default),
                step=float(param.step),
                key=f"param_{exercise.id}_{param.name}",
                help=param.description or None,
            )
            student_params[param.name] = val

        # Hint system
        hints_used = tracker.hints_used(exercise.id)
        if exercise.hints:
            max_hint = max(h.level for h in exercise.hints)
            hcol1, hcol2 = st.columns([1, 4])
            with hcol1:
                if hints_used < max_hint:
                    if st.button(f"💡 Hint {hints_used + 1}", key=f"hint_{exercise.id}"):
                        tracker.use_hint(exercise.id, hints_used + 1)
                        st.rerun()
            with hcol2:
                if hints_used > 0:
                    hint_text = runner.get_hint(exercise, hints_used)
                    if hint_text:
                        st.info(f"**Hint {hints_used}:** {hint_text}")

        # Answer input (for exercises with numeric validation)
        if exercise.validation and exercise.validation.method.value != "none":
            answer = st.number_input(
                "Your 10-year estimate ($B, negative = revenue gain/deficit reduction)",
                value=0.0,
                step=1.0,
                key=f"answer_{exercise.id}",
            )

            if st.button("Submit Answer", key=f"submit_{exercise.id}", type="primary"):
                result = runner.check_answer(exercise, student_params, answer)
                fb = feedback_engine.generate(
                    exercise=exercise,
                    result=result,
                    hints_used=hints_used,
                    complexity=tracker.complexity,
                )
                if result.correct:
                    st.success(fb)
                    tracker.mark_complete(exercise.id, result)
                    st.rerun()
                else:
                    st.warning(fb)
        else:
            # No numeric validation (range_check on a percentage, etc.)
            _render_range_or_open_exercise(exercise, student_params, runner, feedback_engine, tracker, hints_used)

        # Show result if already done
        if is_done:
            result = tracker.get_answer(exercise.id)
            if result:
                st.success(result.message)
            if exercise.expected_insight:
                st.info(f"**Key insight:** {exercise.expected_insight}")


def _render_range_or_open_exercise(exercise, student_params, runner, feedback_engine, tracker, hints_used) -> None:
    """Handle range_check and no-validation exercises."""
    if exercise.validation and exercise.validation.method.value == "range_check":
        answer = st.number_input(
            "Your estimate",
            value=0.0,
            step=0.5,
            key=f"answer_{exercise.id}",
        )
        if st.button("Submit", key=f"submit_{exercise.id}", type="primary"):
            result = runner.check_answer(exercise, student_params, answer)
            fb = feedback_engine.generate(
                exercise=exercise, result=result,
                hints_used=hints_used, complexity=tracker.complexity,
            )
            if result.correct:
                st.success(fb)
                tracker.mark_complete(exercise.id, result)
                st.rerun()
            else:
                st.warning(fb)
    else:
        _render_open_exercise(exercise, runner, feedback_engine, tracker)


def _render_open_exercise(exercise, runner, feedback_engine, tracker) -> None:
    """Render an open-ended (no automated validation) exercise."""
    st.text_area(
        "Your analysis / reflection",
        height=200,
        key=f"open_{exercise.id}",
        placeholder="Enter your analysis here...",
    )
    if st.button("Mark Complete", key=f"submit_{exercise.id}", type="primary"):
        dummy_result = ValidationResult(
            correct=True,
            student_answer=0.0,
            model_answer=None,
            tolerance=0,
            message="Open-ended exercise — marked complete.",
        )
        tracker.mark_complete(exercise.id, dummy_result)
        fb = feedback_engine.generate(
            exercise=exercise,
            result=dummy_result,
            hints_used=tracker.hints_used(exercise.id),
            complexity=tracker.complexity,
        )
        st.success(fb)
        st.rerun()


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def _render_export(assignment, exercises, tracker) -> None:
    st.subheader("📄 Export Submission")

    done, total = tracker.completion_fraction(exercises)
    st.markdown(
        f"Completed **{done}/{total}** exercises at "
        f"**{COMPLEXITY_LABELS[tracker.complexity]}** level."
    )

    student_name = st.session_state.get("student_name", "").strip() or "Student"
    course_name = st.session_state.get("course_name", "").strip()

    answers = {
        eid: tracker.get_answer(eid)
        for eid in [e.id for e in exercises]
        if tracker.is_complete(eid)
    }

    if st.button("Generate Submission Report", type="secondary"):
        html = generate_submission_html(
            assignment=assignment,
            student_name=student_name,
            complexity=tracker.complexity,
            answers=answers,
            course_name=course_name,
        )
        st.download_button(
            label="📥 Download HTML Report (print to PDF)",
            data=html,
            file_name=f"{assignment.id}_{student_name.replace(' ', '_')}.html",
            mime="text/html",
            key="dl_report",
        )
        st.caption(
            "Open the downloaded file in your browser and use "
            "File → Print → Save as PDF to produce a PDF submission."
        )


# ---------------------------------------------------------------------------
# Standalone runner (for testing outside main app)
# ---------------------------------------------------------------------------

def main() -> None:
    """Bootstrap the classroom app with structured startup logging."""
    logger = configure_runtime_logger(__name__)
    log_runtime_event(logger, "app_boot", **build_runtime_metadata(entrypoint="classroom_app.py", mode="classroom"))
    try:
        render_classroom_app()
    except Exception:
        logger.exception("Classroom app bootstrap failed")
        raise


if __name__ == "__main__":
    main()
