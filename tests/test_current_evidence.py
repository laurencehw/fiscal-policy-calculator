"""The validation figures every surface quotes come from one generated report.

``planning/ROUTE_TO_9.md`` priority 2: *generate headline metrics and
data-vintage summaries from one versioned report* so the README, the pages, the
API and the validation reports cannot disagree. When PR #173 moved the
out-of-sample tier 18.0% -> 15.2% on the same 44 rows, the About page, the
Methodology page and two strings the Ask assistant hands the model kept
printing 18.0% and "35/44", and so did the live headline sentences in
``CLAUDE.md``, the README and ``docs/`` that the docs PR after it missed.

This file is what makes the report a measurement rather than a claim:

1. the committed report is this tree's computation (regenerate with
   ``python scripts/build_current_evidence.py``);
2. the surfaces print what the report says, and degrade to saying less — never
   to a wrong number — when it cannot be read;
3. the **live** headline sentences in the docs agree with it. Dated history is
   deliberately not pinned: a sentence that says "PR #169 took the tier to
   18.0%" is true forever, and only a sentence that claims to be current can go
   stale.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from fiscal_model.validation import current_evidence as ce

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGENERATE = "python scripts/build_current_evidence.py"


@pytest.fixture(scope="module")
def live_payload() -> dict:
    """This tree's report, computed once for the module (about 15s)."""
    from scripts.build_current_evidence import compute_payload

    return compute_payload()


@pytest.fixture(scope="module")
def report() -> dict:
    ce.reset_cache()
    data = ce.load_evidence()
    assert data is not None, f"current_evidence.json is missing. Run: {REGENERATE}"
    return data


# ---------------------------------------------------------------------------
# 1. The gate: the committed report is this tree's report
# ---------------------------------------------------------------------------


def test_the_committed_report_is_this_trees_computation(live_payload, report) -> None:
    assert report == live_payload, (
        "current_evidence.json is stale or hand-edited: a change moved a "
        f"validation tier. Run: {REGENERATE}, then update the live headline "
        "sentences this file pins (test_the_docs_* below list them)."
    )


def test_the_generator_is_byte_stable(live_payload, tmp_path) -> None:
    """No timestamp and a fixed key order, so regenerating is a no-op diff."""
    first = ce.write_payload(live_payload, path=tmp_path / "a.json")
    second = ce.write_payload(live_payload, path=tmp_path / "b.json")
    ce.reset_cache()
    assert first.read_bytes() == second.read_bytes() == ce.EVIDENCE_PATH.read_bytes()


def test_the_report_says_what_regenerates_it(report) -> None:
    assert report["generated_by"] == "scripts/build_current_evidence.py"
    assert "do not hand-edit" in report["_note"]


def test_the_report_agrees_with_cold_holdouts_own_summary(live_payload) -> None:
    """Copied, never recomputed: the pooled tier is build_report()'s summary."""
    from scripts.cold_holdout import build_report

    summary = build_report()["out_of_sample"]["summary"]
    for field in ("n", "mean_abs_error", "median_abs_error", "within_15pct", "within_25pct"):
        assert live_payload["out_of_sample"][field] == summary[field], field


def test_the_pooled_mass_is_the_sum_of_the_class_masses(report) -> None:
    classes = report["out_of_sample_classes"].values()
    assert sum(block["n"] for block in classes) == report["out_of_sample"]["n"]
    assert round(sum(block["error_mass"] for block in classes), 1) == pytest.approx(
        report["out_of_sample"]["error_mass"], abs=0.05
    )


def test_every_quoted_row_is_in_the_report(report) -> None:
    assert set(report["quoted_rows"]) == set(ce.QUOTED_ROW_IDS)


def test_a_surface_never_quotes_a_row_the_report_lacks() -> None:
    from fiscal_model.ui.tabs import methodology

    quoted = {
        policy_id
        for rows in (
            methodology._OUT_OF_SAMPLE_SAMPLE_ROWS,
            methodology._CALIBRATED_SAMPLE_ROWS,
            methodology._RECONSTRUCTION_SAMPLE_ROWS,
        )
        for policy_id, _label, _source in rows
    }
    assert quoted <= set(ce.QUOTED_ROW_IDS)


# ---------------------------------------------------------------------------
# 2. The surfaces print the report, and say less when it is missing
# ---------------------------------------------------------------------------


def _headline_fragment(report: dict) -> str:
    oos = report["out_of_sample"]
    return f"{oos['mean_abs_error']}% mean / {oos['median_abs_error']}% median"


def test_about_prints_the_reports_figures(report) -> None:
    from app_pages import about

    text = about._how_to_read()
    oos = report["out_of_sample"]
    fitted = report["calibrated"]["fitted"]
    assert _headline_fragment(report) in text
    assert f"{oos['within_25pct']}/{oos['n']} within 25%" in text
    assert f"{fitted['mean_abs_error']}% mean over {fitted['n']} fitted" in text
    assert text == about._HOW_TO_READ


def test_methodology_prints_the_reports_figures(report) -> None:
    from fiscal_model.ui.tabs import methodology

    note = methodology._out_of_sample_note()
    oos = report["out_of_sample"]
    assert f"mean abs error {oos['mean_abs_error']}%" in note
    assert f"{oos['within_25pct']}/{oos['n']} within 25%" in note
    table = methodology._evidence_table("x", methodology._OUT_OF_SAMPLE_SAMPLE_ROWS)
    row = report["quoted_rows"]["cbo_opt64_corporate_rate_1pp"]
    assert f"{row['abs_percent_error']:.1f}%" in table


def test_ask_quotes_the_policys_own_class(report) -> None:
    from fiscal_model.assistant import tools
    from fiscal_model.policies import PolicyType, TaxPolicy

    policy = TaxPolicy(
        name="probe",
        description="+2pp above $400K",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.02,
        affected_income_threshold=400_000,
    )
    note = tools._generic_path_note(policy)
    ordinary = report["out_of_sample_classes"]["ordinary_rate_change"]
    assert f"by {ordinary['mean_abs_error']}% on average over {ordinary['n']}" in note
    corporate = report["out_of_sample_classes"]["corporate"]
    assert f"{corporate['mean_abs_error']}%" in tools._corporate_path_note()
    assert f"{report['out_of_sample']['mean_abs_error']}% mean" in tools._tier_contrast()


def test_every_surface_says_less_rather_than_guess_when_the_report_is_missing(
    monkeypatch, tmp_path
) -> None:
    # Imported before the report is hidden: ``about`` builds a module-level
    # constant at import, and importing it here for the first time would freeze
    # the fallback text into the module for every later test in this worker.
    from app_pages import about
    from fiscal_model.assistant import tools
    from fiscal_model.policies import PolicyType, TaxPolicy
    from fiscal_model.ui.tabs import methodology

    monkeypatch.setattr(ce, "EVIDENCE_PATH", tmp_path / "missing.json")
    ce.reset_cache()
    try:
        policy = TaxPolicy(
            name="probe",
            description="d",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.01,
            affected_income_threshold=0,
        )
        texts = [
            about._how_to_read(),
            methodology._out_of_sample_note(),
            methodology._evidence_table("x", methodology._CALIBRATED_SAMPLE_ROWS),
            tools._generic_path_note(policy),
            tools._corporate_path_note(),
            tools._tier_contrast(),
        ]
    finally:
        ce.reset_cache()
    for text in texts:
        assert not re.search(r"\d+\.\d%", text), f"printed a figure it could not read: {text!r}"


#: A tier figure typed into a surface — "15.2% mean ... over 44", "1.6% over
#: 15", "mean abs error 18.0%", "35/44 within 25%". The surfaces format these
#: from the report; a literal here is the defect this file exists to prevent
#: coming back. Checked against the pre-report sources, it flags all three.
_TYPED_TIER_FIGURE = re.compile(
    r"\d+\.\d% mean[^\"\n]{0,60}over \d+"
    r"|\d+\.\d% over \d+"
    r"|mean abs(?:olute)? error \d+\.\d%"
    r"|\d+/\d+ within (?:15|25)%"
)


@pytest.mark.parametrize(
    "relative",
    [
        "app_pages/about.py",
        "fiscal_model/ui/tabs/methodology.py",
        "fiscal_model/assistant/tools.py",
    ],
)
def test_no_surface_types_a_tier_figure(relative) -> None:
    source = (PROJECT_ROOT / relative).read_text(encoding="utf-8")
    assert not _TYPED_TIER_FIGURE.findall(source), (
        f"{relative} types a validation tier figure; read it from "
        "fiscal_model.validation.current_evidence instead"
    )


# ---------------------------------------------------------------------------
# 3. The live headline sentences in the docs agree with the report
# ---------------------------------------------------------------------------
#
# Each pattern matches one sentence that claims to be current. Every match must
# agree with the report, and each pattern must match at least once, so a
# sentence that is rephrased has to be re-pinned rather than silently dropped.

_N = r"(?P<n>\d+)"
_MEAN = r"(?P<mean>[\d.]+)"
_MEDIAN = r"(?P<median>[\d.]+)"
_W15 = r"(?P<w15>\d+)/(?P<n15>\d+) within 15%"
_W25 = r"(?P<w25>\d+)/(?P<n25>\d+) within 25%"
_CLASS_SPAN = r"running (?P<lo>[\d.]+)% to (?P<hi>[\d.]+)%"

_OUT_OF_SAMPLE_SENTENCES: tuple[tuple[str, str], ...] = (
    (
        "README.md",
        rf"across \*\*{_N}\*\* pre-registered cases run \*\*{_MEAN}% mean error, "
        rf"{_MEDIAN}% median, {_W15}, {_W25}\*\*",
    ),
    (
        "README.md",
        rf"\*\*{_N} out-of-sample cases, mean abs error {_MEAN}%, {_W15}, {_W25}\*\* "
        rf"\(median {_MEDIAN}%",
    ),
    (
        "CLAUDE.md",
        rf"genuine out-of-sample predictions \(\*\*{_N}\*\* pre-registered cases, "
        rf"\*\*{_MEAN}% mean, {_MEDIAN}% median, {_W15}, {_W25}\*\*, and eight policy "
        rf"classes {_CLASS_SPAN}",
    ),
    (
        "CLAUDE.md",
        rf"\*\*{_N} pre-registered cases, mean abs error {_MEAN}% \(median {_MEDIAN}%\), "
        rf"{_W15}, {_W25}, error mass (?P<mass>[\d.]+)\*\*",
    ),
    (
        "docs/VALIDATION.md",
        rf"\*\*{_N} out-of-sample cases, mean abs error {_MEAN}%, {_W15}, {_W25}\*\* "
        rf"\(median {_MEDIAN}%; error mass (?P<mass>[\d.]+)\)",
    ),
    (
        "docs/VALIDATION.md",
        rf"Tier 1 out-of-sample \(\*\*{_MEAN}%\*\* mean / {_MEDIAN}% median, "
        rf"n=\*\*{_N}\*\* pre-registered; {_W15}, {_W25}, and itself eight policy "
        rf"classes {_CLASS_SPAN}",
    ),
    (
        "docs/VALIDATION.md",
        rf"Live Tier 1 is \*\*{_N} cases @ {_MEAN}% mean / {_MEDIAN}% median\*\*",
    ),
    (
        "docs/METHODOLOGY.md",
        rf"\*\*{_N} pre-registered cases, mean absolute error {_MEAN}% "
        rf"\(median {_MEDIAN}%\); (?P<w15>\d+) of (?P<n15>\d+)\s+within 15%, "
        rf"(?P<w25>\d+) of (?P<n25>\d+) within 25%\*\*",
    ),
    ("README.md", rf"\*\*eight policy classes {_CLASS_SPAN}\*\*"),
    ("CLAUDE.md", rf"The live mass is \*\*(?P<mass>[\d.]+) over {_N}\*\*"),
)


def _matches(relative: str, pattern: str) -> list[re.Match]:
    text = (PROJECT_ROOT / relative).read_text(encoding="utf-8")
    found = list(re.finditer(pattern, text))
    assert found, (
        f"{relative}: no sentence matches the pinned live headline pattern "
        f"{pattern!r}. If the sentence was rephrased, update the pattern here too."
    )
    return found


def _expected_out_of_sample(report: dict) -> dict[str, str]:
    oos = report["out_of_sample"]
    lowest, highest = sorted(
        report["out_of_sample_classes"].values(), key=lambda block: block["mean_abs_error"]
    )[:: len(report["out_of_sample_classes"]) - 1]
    return {
        "n": str(oos["n"]),
        "n15": str(oos["n"]),
        "n25": str(oos["n"]),
        "mean": f"{oos['mean_abs_error']}",
        "median": f"{oos['median_abs_error']}",
        "w15": str(oos["within_15pct"]),
        "w25": str(oos["within_25pct"]),
        "mass": f"{oos['error_mass']}",
        "lo": f"{lowest['mean_abs_error']}",
        "hi": f"{highest['mean_abs_error']}",
    }


@pytest.mark.parametrize(
    "relative,pattern",
    _OUT_OF_SAMPLE_SENTENCES,
    ids=[f"{path}:{i}" for i, (path, _) in enumerate(_OUT_OF_SAMPLE_SENTENCES)],
)
def test_the_docs_live_out_of_sample_headline_matches_the_report(
    report, relative, pattern
) -> None:
    expected = _expected_out_of_sample(report)
    for match in _matches(relative, pattern):
        for field, value in match.groupdict().items():
            assert value == expected[field], (
                f"{relative}: the live out-of-sample headline says {field}={value} "
                f"where the generated report says {expected[field]}: "
                f"{match.group(0)!r}"
            )


_CALIBRATED_SENTENCES: tuple[tuple[str, str, str], ...] = (
    # (file, pattern, report tier) — each pattern's groups are mean and n.
    ("README.md", r"\(\*\*(?P<mean>[\d.]+)% over (?P<n>\d+) benchmarks\*\*", "fitted"),
    (
        "README.md",
        r"benchmarks\*\*, or \*\*(?P<mean>[\d.]+)% over (?P<n>\d+)\*\* with the",
        "fitted_held_in_place",
    ),
    (
        "README.md",
        r"\*\*(?P<n>\d+) \*unfitted\* module reconstructions miss by (?P<mean>[\d.]+)% mean\*\*",
        "reconstruction",
    ),
    (
        "README.md",
        r"is \*\*(?P<mean>[\d.]+)% over (?P<n>\d+)\*\*, printed on the line beneath",
        "reconstruction_retired_held_in_place",
    ),
    (
        "CLAUDE.md",
        r"fitted calibrated reference models \(\*\*(?P<mean>[\d.]+)% over (?P<n>\d+)\*\* benchmarks",
        "fitted",
    ),
    (
        "CLAUDE.md",
        r"`cap_charitable`, or \*\*(?P<mean>[\d.]+)% over (?P<n>\d+)\*\* with the six rows",
        "fitted_held_in_place",
    ),
    (
        "CLAUDE.md",
        r"unfitted module reconstructions \(\*\*(?P<mean>[\d.]+)% over (?P<n>\d+) scored\*\*",
        "reconstruction",
    ),
    (
        "CLAUDE.md",
        r"the day they were withdrawn is (?P<mean>[\d.]+)% over (?P<n>\d+)\*\*",
        "reconstruction_retired_held_in_place",
    ),
)


@pytest.mark.parametrize(
    "relative,pattern,tier",
    _CALIBRATED_SENTENCES,
    ids=[f"{path}:{tier}" for path, _, tier in _CALIBRATED_SENTENCES],
)
def test_the_docs_live_calibrated_headlines_match_the_report(
    report, relative, pattern, tier
) -> None:
    block = report["calibrated"][tier]
    for match in _matches(relative, pattern):
        assert match.group("mean") == f"{block['mean_abs_error']}", (relative, match.group(0))
        assert match.group("n") == str(block["n"]), (relative, match.group(0))


def test_claude_mds_class_table_matches_the_report_and_the_workflow(report) -> None:
    """Three sources, one table: the report's class means and the CI ceilings."""
    from tests.test_ci_workflow import (
        VALIDATION_DASHBOARD_WORKFLOW_PATH,
        _per_class_ceilings,
    )

    text = (PROJECT_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    table = text.split("| Class | n | mean | CI ceiling |", 1)[1].split("\n\n", 1)[0]
    rows = re.findall(
        r"^\| (?P<label>[A-Za-z -]+?) \| (?P<n>\d+) \| \**(?P<mean>[\d.]+)%\** \| (?P<ceiling>\d+) \|",
        table,
        flags=re.M,
    )
    by_label = {block["label"]: (slug, block) for slug, block in report["out_of_sample_classes"].items()}
    ceilings = _per_class_ceilings(VALIDATION_DASHBOARD_WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert {label for label, *_ in rows} == set(by_label), "the table must list every class once"
    for label, n, mean, ceiling in rows:
        slug, block = by_label[label]
        assert int(n) == block["n"], label
        assert mean == f"{block['mean_abs_error']}", label
        assert float(ceiling) == ceilings[slug], f"{label}: CLAUDE.md's ceiling is not the workflow's"


def test_the_documented_ci_gate_commands_are_the_workflows() -> None:
    """``CLAUDE.md``'s Commands block and ``docs/VALIDATION.md`` quote the gates
    CI actually runs; a lane that re-derives them changes all three together."""
    from tests.test_ci_workflow import (
        VALIDATION_DASHBOARD_WORKFLOW_PATH,
        _cold_holdout_gate_lines,
        _per_class_ceilings,
    )

    workflow = VALIDATION_DASHBOARD_WORKFLOW_PATH.read_text(encoding="utf-8")
    pooled, _ = _cold_holdout_gate_lines(workflow)
    pooled_args = re.search(r"--max-mean-error \d+ --min-within-25pct \d+", pooled).group(0)
    ceilings = _per_class_ceilings(workflow)

    claude = (PROJECT_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    commands = claude.split("## Commands", 1)[1].split("\n## ", 1)[0]
    assert f"python scripts/cold_holdout.py {pooled_args}" in commands
    documented = {
        slug: float(value)
        for slug, value in re.findall(r"\b([a-z_]+)=(\d+)\b", commands.split("--max-class-mean-error", 1)[1])
        if slug in ceilings
    }
    assert documented == ceilings

    validation = (PROJECT_ROOT / "docs" / "VALIDATION.md").read_text(encoding="utf-8")
    assert f"runs `python scripts/cold_holdout.py {pooled_args}` as a blocking step" in validation


def test_the_readmes_data_vintages_match_the_report(report) -> None:
    vintages = report["data_vintages"]
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    year = re.search(r"\| IRS Statistics of Income \| (\d{4})", readme)
    assert year and int(year.group(1)) == vintages["irs_soi_latest_tax_year"]
    coverage = re.search(r"carries \*\*([\d.]+)% of returns but ([\d.]+)% of AGI\*\*", readme)
    assert coverage, "README's microdata coverage sentence is missing"
    assert float(coverage.group(1)) == pytest.approx(vintages["microdata_returns_coverage_pct"], abs=0.5)
    assert float(coverage.group(2)) == pytest.approx(vintages["microdata_agi_coverage_pct"], abs=0.5)


def test_the_readmes_catalog_count_is_the_catalogs() -> None:
    from fiscal_model.app_data import PRESET_POLICIES
    from fiscal_model.ui.policy_input_presets import ILLUSTRATIVE_CATEGORY, _preset_category

    categories = [
        _preset_category(spec) for label, spec in PRESET_POLICIES.items() if label != "Custom Policy"
    ]
    areas = {category for category in categories if category != ILLUSTRATIVE_CATEGORY}
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    heading = re.search(r"### (\d+) pre-built proposals across (\d+) policy areas", readme)
    assert heading, "README's catalog heading is missing"
    assert int(heading.group(1)) == len(categories)
    assert int(heading.group(2)) == len(areas)


def test_the_report_file_is_valid_json_with_sorted_keys() -> None:
    raw = ce.EVIDENCE_PATH.read_text(encoding="utf-8")
    assert raw == json.dumps(json.loads(raw), indent=2, sort_keys=True) + "\n"
