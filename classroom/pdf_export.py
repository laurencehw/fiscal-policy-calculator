"""
PDF / HTML Export for Student Submissions

Generates a formatted HTML report that can be printed to PDF from
the browser. No additional dependencies required beyond the stdlib.

Usage::

    html = generate_submission_html(
        assignment=assignment,
        student_name="Jane Smith",
        complexity=ComplexityLevel.UNDERGRADUATE,
        answers={"ex1": result1, "ex2": result2},
        notes={"ex1": "I found that...", "ex2": "..."},
    )
    # Streamlit download button:
    st.download_button("Download Report", html, "submission.html", "text/html")
"""

from __future__ import annotations

import datetime

from .engine import Assignment, ComplexityLevel, ValidationResult


def generate_submission_html(
    assignment: Assignment,
    student_name: str,
    complexity: ComplexityLevel,
    answers: dict[str, ValidationResult],
    notes: dict[str, str] | None = None,
    course_name: str = "",
    date: datetime.date | None = None,
) -> str:
    """
    Generate a self-contained HTML submission report.

    Parameters
    ----------
    assignment
        The assignment object.
    student_name
        Student's full name.
    complexity
        Selected complexity level.
    answers
        Dict mapping exercise_id → ValidationResult.
    notes
        Optional dict of exercise_id → student notes/reflections.
    course_name
        Optional course name to include in the header.
    date
        Submission date. Defaults to today.
    """
    if date is None:
        date = datetime.date.today()
    if notes is None:
        notes = {}

    exercises = assignment.exercises_for_level(complexity)
    completed = sum(1 for e in exercises if e.id in answers and answers[e.id].correct)
    total = len(exercises)

    html = _html_head(assignment.title, student_name)
    html += _html_header(assignment, student_name, course_name, complexity, date, completed, total)

    for exercise in exercises:
        result = answers.get(exercise.id)
        note = notes.get(exercise.id, "")
        html += _html_exercise_block(exercise, result, note)

    html += _html_footer()
    return html


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _html_head(title: str, student: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_esc(title)} — {_esc(student)}</title>
  <style>
    body {{
      font-family: Georgia, serif;
      max-width: 800px;
      margin: 40px auto;
      padding: 0 20px;
      color: #1a1a1a;
      line-height: 1.6;
    }}
    h1 {{ font-size: 1.6em; margin-bottom: 4px; color: #0a3d62; }}
    h2 {{ font-size: 1.2em; color: #0a3d62; margin-top: 2em; }}
    h3 {{ font-size: 1.0em; color: #2c3e50; }}
    .meta {{ font-size: 0.9em; color: #555; margin-bottom: 1.5em; }}
    .progress {{ font-size: 1.0em; font-weight: bold; color: #27ae60;
                 border: 1px solid #27ae60; padding: 6px 12px;
                 border-radius: 4px; display: inline-block; margin-bottom: 1.5em; }}
    .exercise {{
      border-left: 4px solid #3498db;
      padding: 12px 16px;
      margin-bottom: 2em;
      background: #fafafa;
    }}
    .exercise.correct {{ border-left-color: #27ae60; }}
    .exercise.incorrect {{ border-left-color: #e74c3c; }}
    .exercise.skipped {{ border-left-color: #bdc3c7; }}
    .label {{ font-size: 0.75em; font-weight: bold; text-transform: uppercase;
              letter-spacing: 0.06em; color: #888; margin-bottom: 4px; }}
    .prompt {{ font-style: italic; color: #333; margin: 8px 0; }}
    .answer-row {{ display: flex; gap: 2em; flex-wrap: wrap; margin: 8px 0; }}
    .answer-box {{ background: #fff; border: 1px solid #ddd; padding: 8px 12px;
                   border-radius: 4px; min-width: 120px; }}
    .answer-box .value {{ font-size: 1.2em; font-weight: bold; color: #0a3d62; }}
    .status-correct {{ color: #27ae60; font-weight: bold; }}
    .status-incorrect {{ color: #e74c3c; font-weight: bold; }}
    .status-skipped {{ color: #888; }}
    .note {{ background: #fffde7; border: 1px solid #f0c000;
              padding: 8px 12px; margin-top: 8px; border-radius: 4px; }}
    .insight {{ background: #e8f5e9; border: 1px solid #a5d6a7;
                padding: 8px 12px; margin-top: 8px; border-radius: 4px;
                font-size: 0.92em; }}
    .footer {{ margin-top: 3em; padding-top: 1em; border-top: 1px solid #ddd;
               font-size: 0.8em; color: #888; }}
    @media print {{
      body {{ margin: 20px; }}
      .exercise {{ break-inside: avoid; }}
    }}
  </style>
</head>
<body>
"""


def _html_header(
    assignment: Assignment,
    student: str,
    course: str,
    complexity: ComplexityLevel,
    date: datetime.date,
    completed: int,
    total: int,
) -> str:
    level_label = complexity.value.title()
    course_line = f"<br><b>Course:</b> {_esc(course)}" if course else ""
    progress_pct = int(completed / total * 100) if total > 0 else 0
    return f"""
<h1>{_esc(assignment.title)}</h1>
<div class="meta">
  <b>Student:</b> {_esc(student)}{course_line}<br>
  <b>Level:</b> {level_label}<br>
  <b>Date:</b> {date.strftime('%B %d, %Y')}<br>
  <b>Assignment:</b> {_esc(assignment.id)}
</div>
<div class="progress">
  Score: {completed}/{total} exercises ({progress_pct}%)
</div>

<h2>Learning Objectives</h2>
<ul>
{''.join(f'  <li>{_esc(obj)}</li>' for obj in assignment.learning_objectives)}
</ul>
"""


def _html_exercise_block(exercise, result: ValidationResult | None, note: str) -> str:
    if result is None:
        status_class = "skipped"
        status_text = '<span class="status-skipped">Not attempted</span>'
        answer_html = ""
    elif result.correct:
        status_class = "correct"
        status_text = '<span class="status-correct">Correct</span>'
        answer_html = _answer_html(result)
    else:
        status_class = "incorrect"
        status_text = '<span class="status-incorrect">Incorrect</span>'
        answer_html = _answer_html(result)

    note_html = ""
    if note.strip():
        note_html = f'<div class="note"><b>Student notes:</b><br>{_esc(note)}</div>'

    insight_html = ""
    if exercise.expected_insight and result is not None:
        insight_html = (
            f'<div class="insight"><b>Key insight:</b> '
            f'{_esc(exercise.expected_insight)}</div>'
        )

    return f"""
<div class="exercise {status_class}">
  <div class="label">{_esc(exercise.type.value.replace("_", " "))}</div>
  <h3>{_esc(exercise.title)}</h3>
  <div>Status: {status_text}</div>
  {f'<div class="prompt">{_esc(exercise.prompt[:300])}...</div>' if len(exercise.prompt) > 300 else f'<div class="prompt">{_esc(exercise.prompt)}</div>'}
  {answer_html}
  {note_html}
  {insight_html}
</div>
"""


def _answer_html(result: ValidationResult) -> str:
    model_part = ""
    if result.model_answer is not None:
        model_part = f"""
      <div class="answer-box">
        <div class="label">Model estimate</div>
        <div class="value">${abs(result.model_answer):.1f}B</div>
      </div>"""
    pct_part = ""
    if result.pct_error is not None:
        pct_part = f"""
      <div class="answer-box">
        <div class="label">% error</div>
        <div class="value">{result.pct_error*100:.1f}%</div>
      </div>"""
    return f"""
  <div class="answer-row">
    <div class="answer-box">
      <div class="label">Your answer</div>
      <div class="value">${abs(result.student_answer):.1f}B</div>
    </div>{model_part}{pct_part}
  </div>
  <p style="font-size:0.9em;color:#555;">{_esc(result.message)}</p>"""


def _html_footer() -> str:
    return """
<div class="footer">
  Generated by Fiscal Policy Calculator — Classroom Mode<br>
  Model uses CBO-style static scoring with ETI behavioral offsets.
  Estimates validated against official CBO/JCT scores within 15%.
</div>
</body>
</html>
"""


def _esc(text: str) -> str:
    """Minimal HTML escaping."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
