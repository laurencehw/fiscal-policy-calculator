"""The footer's benchmark count: pinned, exact, and off the first-paint path.

``planning/memos/COLD_START.md`` §3 measured the page footer computing the
**entire 81-row validation scorecard** to print one clause — 7.65s of the
landing page's 8.40s first script run. The clause is a validation claim, so the
fix could not be "print a smaller number" or "print it later, roughly": it had
to keep printing *this tree's* count.

So the count is a generated artifact
(``scripts/build_validation_headline.py`` →
``fiscal_model/data_files/validation/headline_counts.json``), and this file is
what makes it trustworthy. The first test recomputes the scorecard and fails if
the artifact has drifted; without it the whole design would be a hand-typed
number wearing a JSON costume.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from fiscal_model.ui import validation_headline as vh
from fiscal_model.ui.helpers import validated_policy_count

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 1. The gate: the pinned number is this tree's number
# ---------------------------------------------------------------------------


def test_the_pinned_count_is_the_scorecard_count() -> None:
    """The one test that makes the artifact a measurement rather than a claim."""
    from fiscal_model.validation.scorecard import cached_default_scorecard

    summary = cached_default_scorecard()
    assert vh.pinned_published_entries() == summary.published_entries, (
        "The footer prints a benchmark count that no longer matches the "
        "scorecard. Run: python scripts/build_validation_headline.py"
    )


def test_the_whole_payload_is_reproducible_from_the_scorecard() -> None:
    """Not just the headline: every count in the file is regenerated, so a
    hand edit to any of them fails here rather than sitting in the tree."""
    from fiscal_model.validation.scorecard import cached_default_scorecard

    live = vh.build_payload(cached_default_scorecard())
    committed = json.loads(vh.HEADLINE_PATH.read_text(encoding="utf-8"))
    assert committed == live, (
        "headline_counts.json is stale or hand-edited. "
        "Run: python scripts/build_validation_headline.py"
    )


def test_the_artifact_says_what_regenerates_it() -> None:
    data = vh.load_headline()
    assert data is not None
    assert data["generated_by"] == "scripts/build_validation_headline.py"
    assert "do not hand-edit" in data["_note"]


def test_the_generator_is_byte_stable_on_an_unchanged_tree(tmp_path) -> None:
    """No timestamp, no ordering wobble — regenerating must be a no-op diff."""
    from fiscal_model.validation.scorecard import cached_default_scorecard

    payload = vh.build_payload(cached_default_scorecard())
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    vh.write_payload(payload, path=first)
    vh.write_payload(payload, path=second)
    assert first.read_bytes() == second.read_bytes()
    assert first.read_bytes() == vh.HEADLINE_PATH.read_bytes()


# ---------------------------------------------------------------------------
# 2. The point of the exercise: first paint does not touch the scorecard
# ---------------------------------------------------------------------------


# Run in a fresh interpreter, because the assertion is about a process that
# has computed nothing yet and pytest's own process has computed plenty.
#
# The probe asks whether the scorecard's ``lru_cache`` is still **empty** after
# the footer's clause has been produced — not whether its module was imported.
# The module is imported either way and always was: ``fiscal_model/ui/__init__``
# reaches ``dependencies`` → ``assistant`` → ``validation.cbo_scores``, and
# ``fiscal_model/validation/__init__`` re-exports ``cached_default_scorecard``.
# That import is ~1.6s and is not this lane's to remove. The ~5.8s *compute*
# behind it is, and an empty cache is exactly the evidence that it did not run.
_FIRST_PAINT_PROBE = """
import json, sys
sys.path.insert(0, PROJECT_ROOT)
from fiscal_model.ui import tabs_controller
clause = tabs_controller._footer_validation_clause()
banner = tabs_controller._benchmark_count_clause()
from fiscal_model.validation.scorecard import cached_default_scorecard
print("@@RESULT@@" + json.dumps({
    "clause": clause,
    "banner": banner,
    "scorecard_cache_size": cached_default_scorecard.cache_info().currsize,
}))
"""


def _probe_fresh_process() -> dict:
    source = f"PROJECT_ROOT = {str(PROJECT_ROOT)!r}\n" + _FIRST_PAINT_PROBE
    proc = subprocess.run(
        [sys.executable, "-c", source],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=300,
    )
    for line in proc.stdout.splitlines():
        if line.startswith("@@RESULT@@"):
            return json.loads(line[len("@@RESULT@@") :])
    raise AssertionError(f"probe failed:\n{proc.stdout[-2000:]}\n{proc.stderr[-4000:]}")


def test_the_footer_clause_never_computes_the_scorecard_on_a_cold_process() -> None:
    """The whole fix, stated as an invariant.

    Not "it is fast" — timings are machine-dependent and would flake. The
    assertion is structural: a fresh process that has produced both clauses has
    an **empty** scorecard cache, so the 81-row computation that was 7.65s of
    the landing page's 8.40s first run did not happen. And it produced a real
    clause anyway, which is the half that makes it a fix rather than a deletion.
    """
    result = _probe_fresh_process()
    assert result["scorecard_cache_size"] == 0, (
        "the footer clause computed the validation scorecard on a cold "
        "process — the cold-start regression COLD_START.md §3 is back"
    )
    assert result["clause"].endswith("policies benchmarked against published scores · ")
    assert result["banner"].startswith(result["clause"].split(" policies")[0])


def test_a_cold_process_prints_the_same_clause_a_warm_one_does() -> None:
    """Byte-identical, cold and warm. A deferred clause that said something
    different on the first run would be a different claim, not a faster one."""
    from fiscal_model.validation.scorecard import cached_default_scorecard

    warm = f"{cached_default_scorecard().published_entries} policies benchmarked against published scores · "
    cold = _probe_fresh_process()["clause"]
    assert cold == warm


def test_the_clause_text_is_exactly_what_it_was() -> None:
    """Pin the footer's wording as well as its number. This lane moved *when*
    the count is obtained and nothing about what the footer says."""
    from fiscal_model.ui import tabs_controller

    n = vh.pinned_published_entries()
    assert tabs_controller._footer_validation_clause() == (
        f"{n} policies benchmarked against published scores · "
    )
    assert tabs_controller._benchmark_count_clause() == (
        f"{n} policies benchmarked against published scores from CBO, JCT, "
        "Treasury, SSA and independent scorekeepers — "
    )


# ---------------------------------------------------------------------------
# 3. Source precedence and the fallbacks
# ---------------------------------------------------------------------------


class TestPrecedence:
    def test_a_computed_scorecard_wins_over_the_artifact(self, monkeypatch) -> None:
        """When the true answer is already in memory it is free, so it is used
        — which is also why a stale artifact self-corrects rather than
        outvoting a scorecard the process has actually computed."""
        from types import SimpleNamespace

        import fiscal_model.validation.scorecard as scorecard_mod

        class _Memo:
            def cache_info(self):
                return SimpleNamespace(currsize=1)

            def __call__(self):
                return SimpleNamespace(published_entries=4242)

        monkeypatch.setattr(scorecard_mod, "cached_default_scorecard", _Memo())
        assert validated_policy_count() == 4242
        assert validated_policy_count(allow_compute=False) == 4242

    def test_the_artifact_answers_when_nothing_is_computed(self, monkeypatch) -> None:
        from types import SimpleNamespace

        import fiscal_model.validation.scorecard as scorecard_mod

        calls: list[int] = []

        class _ColdMemo:
            def cache_info(self):
                return SimpleNamespace(currsize=0)

            def __call__(self):
                calls.append(1)
                return SimpleNamespace(published_entries=4242)

        monkeypatch.setattr(scorecard_mod, "cached_default_scorecard", _ColdMemo())
        pinned = vh.pinned_published_entries()
        assert validated_policy_count() == pinned
        assert validated_policy_count(allow_compute=False) == pinned
        assert calls == [], "the artifact path must never compute the scorecard"

    def test_a_missing_artifact_still_computes_rather_than_lying(
        self, monkeypatch
    ) -> None:
        """Deleting the artifact costs the old 5.8s; it never costs the truth."""
        from types import SimpleNamespace

        import fiscal_model.validation.scorecard as scorecard_mod

        class _ColdMemo:
            def cache_info(self):
                return SimpleNamespace(currsize=0)

            def __call__(self):
                return SimpleNamespace(published_entries=4242)

        monkeypatch.setattr(scorecard_mod, "cached_default_scorecard", _ColdMemo())
        monkeypatch.setattr(vh, "pinned_published_entries", lambda: None)
        assert validated_policy_count() == 4242
        # ...and with compute forbidden there is nothing left to answer with.
        assert validated_policy_count(allow_compute=False) == 0

    def test_zero_only_when_every_source_has_failed(self, monkeypatch) -> None:
        """The fallback used to be a hard-coded 25, which asserted coverage at
        precisely the moment the thing that measures it had failed."""
        import fiscal_model.validation.scorecard as scorecard_mod

        def _boom():
            raise RuntimeError("scorecard unavailable")

        monkeypatch.setattr(scorecard_mod, "cached_default_scorecard", _boom)
        monkeypatch.setattr(vh, "pinned_published_entries", lambda: None)
        assert validated_policy_count() == 0


class TestArtifactReader:
    def test_a_corrupt_file_reads_as_none_not_as_a_number(
        self, monkeypatch, tmp_path
    ) -> None:
        bad = tmp_path / "headline_counts.json"
        bad.write_text("{not json", encoding="utf-8")
        monkeypatch.setattr(vh, "HEADLINE_PATH", bad)
        vh.reset_cache()
        try:
            assert vh.load_headline() is None
            assert vh.pinned_published_entries() is None
        finally:
            vh.reset_cache()

    @pytest.mark.parametrize("value", ["75", None, -1, True, 3.5])
    def test_a_non_count_reads_as_none(self, monkeypatch, tmp_path, value) -> None:
        bad = tmp_path / "headline_counts.json"
        bad.write_text(json.dumps({"published_entries": value}), encoding="utf-8")
        monkeypatch.setattr(vh, "HEADLINE_PATH", bad)
        vh.reset_cache()
        try:
            assert vh.pinned_published_entries() is None
        finally:
            vh.reset_cache()

    def test_the_check_mode_of_the_generator_passes_on_a_clean_tree(self) -> None:
        proc = subprocess.run(
            [sys.executable, "scripts/build_validation_headline.py", "--check"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=600,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
