"""R1's gate: CBO's own tables, read back out of the transcription.

The lane's falsification conditions live here
(``planning/lanes/R1_baseline_transcription.md`` section 4). The load-bearing
one is the first: if the February 2026 vintage's FY2026-2035 deficits do not
sum to the figure CBO's own document prints, nothing else in the lane is worth
reading.
"""

from __future__ import annotations

import csv
import functools
import hashlib
import importlib.util
import urllib.error
import urllib.request

import numpy as np
import pytest

from fiscal_model import cbo_baseline_data as cbo_data
from fiscal_model.baseline import (
    CORPORATE_RECEIPTS_SOURCING,
    VINTAGE_SOURCING,
    BaselineVintage,
    CBOBaseline,
    cbo_baseline_budget,
    vintage_assumptions,
)

#: CBO's own printed FY2026-2035 total, February 2026 edition. The sum of
#: ``proj_deficit_total`` over those ten fiscal years in
#: ``cbo-data/data/budget/ten_year_budget/annual_fy_2026-02.csv``.
CBO_FEB_2026_TEN_YEAR_DEFICIT = 23_143.3

#: What the reconstruction returned for the same window before this lane, and
#: the reason R1 outranked every score-ranked item in the plan: it is the
#: number on the landing page, in Build's target strip and in Ask's
#: ``get_cbo_baseline``.
RECONSTRUCTED_TEN_YEAR_DEFICIT = 29_529.1


@functools.lru_cache(maxsize=1)
def fetch_script():
    """``scripts/fetch_cbo_baseline.py`` as a module.

    It lives outside any package, so it is loaded by path rather than imported.
    The tests below read its pin table directly, because the whole point of a
    pin is that the file and its generator cannot drift apart without something
    saying so.
    """
    script = cbo_data.DATA_DIR.parents[2] / "scripts" / "fetch_cbo_baseline.py"
    module_spec = importlib.util.spec_from_file_location(
        "_fetch_cbo_baseline", script
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


# ── The headline ───────────────────────────────────────────────────────────


def test_feb_2026_reproduces_cbos_own_ten_year_deficit():
    """Section 4 falsification 1. Everything else is downstream of this."""
    projection = CBOBaseline(
        start_year=2026, vintage=BaselineVintage.CBO_FEB_2026, use_real_data=True
    ).generate()
    total = float(projection.deficit.sum())
    assert total == pytest.approx(CBO_FEB_2026_TEN_YEAR_DEFICIT, abs=0.05)
    # And it is a long way from what it replaced, or the lane did nothing.
    assert abs(total - RECONSTRUCTED_TEN_YEAR_DEFICIT) > 6_000.0


def test_both_loader_paths_agree_for_a_transcribed_vintage():
    """``use_real_data`` must not change a vintage CBO publishes in full.

    Before PR #130 the two paths disagreed by 8.6% and 35.5% on the corporate
    line alone. Where CBO publishes the whole budget table they must now agree
    to the cent, on every category.
    """
    real = CBOBaseline(start_year=2026, use_real_data=True).generate()
    fallback = CBOBaseline(start_year=2026, use_real_data=False).generate()
    for field in (
        "individual_income_tax", "corporate_income_tax", "payroll_taxes",
        "other_revenues", "social_security", "medicare", "medicaid",
        "other_mandatory", "defense_discretionary", "nondefense_discretionary",
        "net_interest", "debt_held_by_public", "nominal_gdp",
    ):
        assert np.allclose(getattr(real, field), getattr(fallback, field)), field


@pytest.mark.parametrize(
    ("vintage", "start_year"),
    [
        (BaselineVintage.CBO_JAN_2025, 2025),
        (BaselineVintage.CBO_JAN_2025, 2026),
        (BaselineVintage.CBO_FEB_2026, 2026),
    ],
)
def test_the_generated_deficit_is_cbos_own_line(vintage, start_year):
    """Not just the total: each year's deficit is CBO's ``proj_deficit_total``.

    ``other_mandatory`` is a residual against CBO's outlay total, so this is
    the check that the residual is doing what it claims and not absorbing a
    mapping error somewhere else.
    """
    budget = cbo_baseline_budget(vintage)
    assert budget is not None
    published = budget["deficit_total"]
    projection = CBOBaseline(
        start_year=start_year, vintage=vintage, use_real_data=True
    ).generate()
    for offset, year in enumerate(range(start_year, start_year + 10)):
        if year not in published:
            continue
        assert projection.deficit[offset] == pytest.approx(-published[year], abs=0.05)


def test_the_other_mandatory_residual_is_never_negative():
    """A negative residual would mean a gross line was read for a net one."""
    for vintage in BaselineVintage:
        if cbo_baseline_budget(vintage) is None:
            continue
        projection = CBOBaseline(
            start_year=2026, vintage=vintage, use_real_data=True
        ).generate()
        assert np.all(projection.other_mandatory > 0), vintage


# ── The grade says what was actually transcribed ───────────────────────────


def test_feb_2024_has_an_economic_table_and_no_budget_table():
    """And the grade may not round that up to "sourced".

    ``cbo-data``'s ``ten_year_budget`` carries 2024-06, 2025-01 and 2026-02.
    June 2024 is publication 60039, a different document -- its FY2025 deficit
    is $1,937.9B against the January 2025 edition's $1,865.3B for the same
    year -- so borrowing it would be a false provenance claim.
    """
    assert cbo_data.has_economic_table("cbo_feb_2024") is True
    assert cbo_data.has_budget_table("cbo_feb_2024") is False
    assert cbo_baseline_budget(BaselineVintage.CBO_FEB_2024) is None
    assert VINTAGE_SOURCING[BaselineVintage.CBO_FEB_2024] == {
        "economic": "transcribed",
        "budget": "reconstructed",
    }


def test_the_grade_is_computed_from_the_data_not_declared():
    """Remove a vintage's block and its grade must fall, without an edit."""
    from fiscal_model.baseline import vintage_sourcing

    original = cbo_data.budget_tables
    try:
        cbo_data.budget_tables = lambda: {}
        assert vintage_sourcing(BaselineVintage.CBO_FEB_2026)["budget"] == (
            "reconstructed"
        )
    finally:
        cbo_data.budget_tables = original
    assert vintage_sourcing(BaselineVintage.CBO_FEB_2026)["budget"] == "transcribed"


def test_every_corporate_line_is_now_a_published_path():
    """The grade ``baseline.py`` said may not otherwise be reported as CBO's.

    Two vintages reach it through ``cbo_baseline/`` and February 2024 through
    ``data_files/corporate/cbo_corporate_receipts.csv`` (PR #121's
    transcription of publication 59710 Table 1-1).
    """
    for vintage in BaselineVintage:
        assert CORPORATE_RECEIPTS_SOURCING[vintage] == "published_path"


def test_provenance_names_a_repository_commit_and_digest_per_transcribed_line():
    for vintage in BaselineVintage:
        baseline = CBOBaseline(
            start_year=2026, vintage=vintage, use_real_data=False
        )
        provenance = baseline.vintage_provenance
        assert "economic" in provenance
        for record in provenance.values():
            assert record["repository"].startswith("https://github.com/US-CBO/")
            assert len(record["commit_sha"]) == 40
            assert len(record["sha256"]) == 64
            assert record["fetch_date"]


# ── The transcription is CBO's, byte for byte ──────────────────────────────


def _raw_rows(name: str) -> list[dict[str, str]]:
    path = cbo_data.DATA_DIR / name
    with open(path, encoding="utf-8", newline="") as handle:
        body = [line for line in handle if not line.startswith("#")]
    return list(csv.DictReader(body))


def test_the_csvs_carry_the_cbo_variable_behind_every_row():
    """So a mapping decision is auditable without rerunning the fetch script."""
    for name in ("cbo_budget_baseline.csv", "cbo_economic_baseline.csv"):
        rows = _raw_rows(name)
        assert rows
        assert all(row["cbo_variable"] for row in rows)


def test_the_discretionary_split_sums_to_cbos_own_total():
    """Section 4 falsification 4 -- the check that fired on the first run.

    January 2025 publishes the defence/nondefence split of outlays only in its
    timing-adjusted form, and a timing-adjusted pair does not sum to the
    unadjusted total in a year where 1 October falls on a weekend. The
    transcription therefore takes the split as a share and apportions it onto
    ``proj_outlays_discretionary``.
    """
    for vintage in BaselineVintage:
        budget = cbo_baseline_budget(vintage)
        if budget is None:
            continue
        for year, total in budget["discretionary_total"].items():
            split = (
                budget["defense_discretionary"][year]
                + budget["nondefense_discretionary"][year]
            )
            assert split == pytest.approx(total, abs=0.01), (vintage, year)


def test_revenue_components_sum_to_cbos_published_total():
    """Section 4 falsification 2. Catches a dropped customs column."""
    for vintage in BaselineVintage:
        budget = cbo_baseline_budget(vintage)
        if budget is None:
            continue
        for year, total in budget["revenues_total"].items():
            parts = sum(
                budget.get(name, {}).get(year, 0.0)
                for name in (
                    "individual_income_tax", "corporate_income_tax",
                    "payroll_taxes", "other_revenues_core",
                    "other_revenues_customs",
                )
            )
            assert parts == pytest.approx(total, abs=0.35), (vintage, year)


def test_only_february_2026_splits_customs_out_of_other_revenues():
    """A real difference between editions, and the loader must absorb it."""
    feb_2026 = cbo_baseline_budget(BaselineVintage.CBO_FEB_2026)
    jan_2025 = cbo_baseline_budget(BaselineVintage.CBO_JAN_2025)
    assert "other_revenues_customs" in feb_2026
    assert "other_revenues_customs" not in jan_2025


# ── The assumptions are CBO's, and they are not what they replaced ─────────


def test_the_feb_2026_ten_year_note_rises_where_the_literals_fell():
    """The macro survey's finding 1, asserted rather than recalled.

    The hand-entered block ran 4.5% down to 3.9%; CBO's own February 2026
    fiscal table runs 4.10% up to 4.38%. A baseline whose interest-rate path
    points the wrong way prices debt service the wrong way.
    """
    rates = vintage_assumptions(BaselineVintage.CBO_FEB_2026)["interest_rate_10yr"]
    assert rates[0] == pytest.approx(0.0410, abs=5e-4)
    assert rates[-1] == pytest.approx(0.0438, abs=5e-4)
    assert rates[-1] > rates[0]


def test_a_vintage_without_an_economic_block_falls_back_rather_than_borrowing():
    """The behaviour that keeps a provenance claim honest."""
    from fiscal_model.baseline import _HAND_ENTERED_ASSUMPTIONS

    original = cbo_data.economic_tables
    try:
        cbo_data.economic_tables = lambda: {}
        fallback = vintage_assumptions(BaselineVintage.CBO_FEB_2026)
        hand = _HAND_ENTERED_ASSUMPTIONS[BaselineVintage.CBO_FEB_2026]
        for key, series in hand.items():
            assert np.allclose(fallback[key], series)
    finally:
        cbo_data.economic_tables = original


# ── The index reads published levels rather than extrapolating them ────────


def test_the_index_reads_cbos_own_pre_window_level():
    """The SOI anchor is a tax year several years before the window.

    ``nominal_income_index``'s rule is unchanged; this is the one extension --
    a year CBO publishes is read, not back-extrapolated from the window's first
    growth rate.
    """
    projection = CBOBaseline(
        start_year=2026, vintage=BaselineVintage.CBO_FEB_2026, use_real_data=True
    ).generate()
    published = cbo_data.nominal_gdp_table("cbo_feb_2026")
    assert published is not None
    for year in (2023, 2024, 2025):
        assert projection.nominal_income_index(year) == pytest.approx(
            published[year]
        )


def test_the_projection_factor_moved_and_the_size_is_the_lanes_own():
    """Section 3.1's mechanism, in one assertion.

    CBO's own FY2023 -> FY2025 nominal growth is 10.70% where the hand-entered
    February 2026 block assumed 8.99%, which is why ten Tier 1 rows and eight
    shipped presets moved and why the tier got worse rather than better.
    """
    published = cbo_data.nominal_gdp_table("cbo_feb_2026")
    cbo_growth = published[2025] / published[2023] - 1.0
    assert cbo_growth == pytest.approx(0.1070, abs=5e-4)

    from fiscal_model.baseline import _HAND_ENTERED_ASSUMPTIONS

    hand = _HAND_ENTERED_ASSUMPTIONS[BaselineVintage.CBO_FEB_2026]
    step = 1.0 + float(hand["real_gdp_growth"][0]) + float(hand["inflation"][0])
    assert step ** 2 - 1.0 == pytest.approx(0.0899, abs=5e-4)


# ── The report behind the data release ─────────────────────────────────────


def test_the_transcription_reproduces_publication_61882s_own_headlines():
    """The data release is 51118; the *report* is publication 61882.

    ``The Budget and Economic Outlook: 2026 to 2036`` (February 2026) prints
    three round figures in its own summary, and the transcribed table has to
    return all three or the CSV is not that document's. They are pinned here
    rather than in prose because the app quotes a *fourth* number from the
    same table -- $23,143.3B over FY2026-2035, the app's own window -- and a
    reader who meets only that one has no way to tell it apart from a
    disagreement with CBO. CBO's headline ten-year window is FY2027-2036.
    """
    budget = cbo_baseline_budget(BaselineVintage.CBO_FEB_2026)
    deficits = budget["deficit_total"]

    # "a deficit of $1.9 trillion in 2026"
    assert deficits[2026] == pytest.approx(-1_852.7, abs=0.05)
    # "$24.4 trillion over the 2027-2036 period" -- CBO's own ten-year window
    cbo_window = sum(deficits[year] for year in range(2027, 2037))
    assert cbo_window == pytest.approx(-24_406.0, abs=0.05)
    # "$3.1 trillion in 2036"
    assert deficits[2036] == pytest.approx(-3_115.4, abs=0.05)

    # And the app's own window is a different decade of the same table, not a
    # second figure: FY2026-2035, which is what every surface prints.
    app_window = sum(deficits[year] for year in range(2026, 2036))
    assert app_window == pytest.approx(-CBO_FEB_2026_TEN_YEAR_DEFICIT, abs=0.05)
    assert abs(cbo_window) > abs(app_window)


def test_provenance_quotes_the_publication_the_fetch_script_declares():
    """``PROVENANCE.csv`` is generated, so the script is the source of truth.

    The February 2026 rows named publication 51118 -- CBO's generic budget and
    economic data page, which is the *release*, not the report. The report is
    61882. This pins every vintage's publication string to the one the
    generator declares, so the file and its generator cannot drift again
    without a test saying so.
    """
    module = fetch_script()
    declared = {key: entry["publication"] for key, entry in module.VINTAGES.items()}
    assert "publication 61882" in declared["cbo_feb_2026"]
    assert "publication 61172" in declared["cbo_jan_2025"]
    assert "publication 59710" in declared["cbo_feb_2024"]

    path = cbo_data.DATA_DIR / "PROVENANCE.csv"
    with open(path, encoding="utf-8", newline="") as handle:
        body = [line for line in handle if not line.startswith("#")]
    rows = list(csv.DictReader(body))
    assert rows, "PROVENANCE.csv carries no rows"
    for row in rows:
        assert row["publication"] == declared[row["vintage"]], (
            f"{row['vintage']}/{row['kind']} quotes a publication the fetch "
            "script no longer declares"
        )


# ── The pins reproduce, and they reproduce from the URL ────────────────────
#
# PR #163 tried to regenerate PROVENANCE.csv and could not: the pinned SHA-256
# for cbo_feb_2024/economic did not match what its own URL served, the script's
# guard refused to write, and the field that needed changing was edited by
# hand instead. The cause was not that one file. ALL SIX pins were digests of a
# ``git clone`` working tree on Windows, where ``core.autocrlf=true`` rewrites
# LF to CRLF on checkout, so not one of them was the digest of anything the
# pinned URL could serve.
#
# These tests are the gate, and they are deliberately in two halves: the
# offline half proves the pins describe bytes this repository holds, the
# network half proves those bytes are still what CBO publishes. The old script
# would have passed a check of the first kind every single time, which is why
# neither half is sufficient alone.


def _vendored(module, key: str):
    repo, path = key.split("/", 1)
    return module._local_path(repo, path, module.SOURCE_CACHE)


def test_no_vendored_copy_sits_under_a_directory_gitignore_excludes():
    """The cache is flattened for a reason, and the reason is load-bearing.

    ``.gitignore`` carries a bare ``data/``, which matches a directory of that
    name at any depth. The first draft of this cache mirrored the upstream
    layout -- ``cbo-data/data/economic/...`` -- and git committed **one of six
    files**, leaving five untracked: every check green locally, where the files
    are on disk, and red in CI, where they are not.
    """
    module = fetch_script()
    for key in module.DIGESTS:
        cached = _vendored(module, key)
        relative = cached.relative_to(module.SOURCE_CACHE)
        assert "data" not in relative.parts[:-1], (
            f"{key} is cached under a directory named 'data', which "
            ".gitignore excludes at any depth"
        )


def test_every_pin_is_the_digest_of_the_vendored_source_bytes():
    """The offline half. No network, so CI verifies this on every run."""
    module = fetch_script()
    assert module.DIGESTS, "the fetch script pins nothing"
    for key, recorded in module.DIGESTS.items():
        cached = _vendored(module, key)
        assert cached.exists(), f"{key}: no vendored copy at {cached}"
        digest = hashlib.sha256(cached.read_bytes()).hexdigest()
        assert digest == recorded, (
            f"{key}: vendored bytes hash {digest}, pin says {recorded}"
        )


def test_the_vendored_sources_carry_no_crlf():
    """The defect itself, asserted rather than remembered.

    CBO commits these files with LF endings -- git's own blob SHA-1 for each
    one matches the LF form and not the CRLF form, which is how we know LF is
    what CBO stored rather than merely what the CDN happened to return.
    ``sources/.gitattributes`` marks them ``-text`` so no checkout converts
    them; this fails if that guard is ever dropped.
    """
    module = fetch_script()
    for key in module.DIGESTS:
        raw = _vendored(module, key).read_bytes()
        assert b"\r\n" not in raw, (
            f"{key}: the vendored copy carries CRLF, so this checkout converted "
            "line endings -- check sources/.gitattributes"
        )


def test_the_vendored_sources_are_not_a_second_source_of_record():
    """``sources/`` is evidence, not data the app reads.

    The loader must keep reading the three generated CSVs, so a stray reader
    pointed at the raw upstream files would be a second source of record with
    no identity checks behind it.
    """
    module = fetch_script()
    assert module.SOURCE_CACHE.is_dir()
    assert module.SOURCE_CACHE.parent == cbo_data.DATA_DIR
    for name in ("cbo_budget_baseline.csv", "cbo_economic_baseline.csv",
                 "PROVENANCE.csv"):
        assert (cbo_data.DATA_DIR / name).exists()
        assert not (module.SOURCE_CACHE / name).exists()


def test_provenance_records_the_digest_the_fetch_script_pins():
    """PROVENANCE.csv is generated, so the script is the source of truth.

    This is the check that failed on PR #163's branch and was worked around by
    hand. It now fails loudly instead.
    """
    module = fetch_script()
    path = cbo_data.DATA_DIR / "PROVENANCE.csv"
    with open(path, encoding="utf-8", newline="") as handle:
        body = [line for line in handle if not line.startswith("#")]
    rows = [row for row in csv.DictReader(body) if row["sha256"]]
    assert rows, "PROVENANCE.csv records no digest at all"
    for row in rows:
        key = f"cbo-data/{row['file_path']}"
        assert key in module.DIGESTS, f"{key} is recorded but not pinned"
        assert row["sha256"] == module.DIGESTS[key], (
            f"{row['vintage']}/{row['kind']} records a digest the fetch script "
            "no longer pins"
        )
        assert row["commit_sha"] == module.REPOS["cbo-data"]["commit"]


def test_the_whole_transcription_replays_offline_from_the_vendored_sources():
    """``--offline-check``: pins, the three identities and the BFM cross-check.

    Not just the digests. If the vendored bytes were ever replaced by something
    that hashed correctly but parsed differently, the identity checks catch it.
    """
    assert fetch_script().main(["--offline-check"]) == 0


def test_check_refuses_to_answer_the_network_question_from_a_local_tree():
    """``--check`` means "is the pin still what the URL serves".

    Answering it from a checkout is exactly the mistake that produced the six
    wrong pins, so the combination is refused rather than quietly honoured.
    """
    module = fetch_script()
    with pytest.raises(SystemExit):
        module.main(["--check", "--source-dir", str(module.SOURCE_CACHE)])


def test_an_unpinned_file_is_an_error_rather_than_a_new_pin():
    """The mechanism that minted the wrong pins, closed.

    The old ``read_source`` assigned every digest it computed back into the pin
    table, so running the script against any tree at all produced a table of
    "pins" describing that tree. An unpinned key must now stop the run.
    """
    module = fetch_script()
    with pytest.raises(SystemExit):
        module.read_source("cbo-data", "data/not/pinned.csv", module.SOURCE_CACHE)


def test_the_mismatch_message_names_the_line_ending_cause():
    """A bare "digest differs" is what made this take two lanes to find."""
    module = fetch_script()
    key = "cbo-data/data/economic/economic_projections/fiscal_2024-02.csv"
    served = _vendored(module, key).read_bytes()
    crlf = served.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    assert "CRLF rewritten to LF" in module._diagnose(crlf, module.DIGESTS[key])

    # And the historical direction: the digest this repository used to carry
    # for this file is the CRLF rendering of the bytes it now pins.
    was_recorded = hashlib.sha256(crlf).hexdigest()
    assert was_recorded == (
        "0814e9a029d6e75b8e2d92993f4b297ce6ea49b51ef127e250f99b1115e12126"
    )
    assert "core.autocrlf=true" in module._diagnose(served, was_recorded)


def test_each_pinned_url_still_serves_the_bytes_the_pin_records():
    """The network half. Skipped offline; a real failure if upstream re-tags.

    This is the check the offline half cannot make and the version of this
    script that shipped the wrong pins never made at all.
    """
    module = fetch_script()
    for key, recorded in module.DIGESTS.items():
        repo, path = key.split("/", 1)
        url = module._raw_url(repo, path)
        try:
            with urllib.request.urlopen(url, timeout=60) as handle:
                raw = handle.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            pytest.skip(f"no network: {exc}")
        assert hashlib.sha256(raw).hexdigest() == recorded, (
            f"{url} no longer serves the bytes this repository pins"
        )
