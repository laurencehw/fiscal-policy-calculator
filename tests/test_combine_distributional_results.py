"""
Tests for the distributional-result combiner.

``_combine_distributional_results`` aggregates multiple engine outputs
by weighted dollar effect, not by naive share-sum. This is the
infrastructure that *would* be used if the ARP benchmark gets a
composite policy factory (CTC + EITC + Recovery Rebate) — see
docs/VALIDATION_NOTES.md §2.
"""

from __future__ import annotations

from types import SimpleNamespace

from fiscal_model.validation.benchmark_runners import (
    _combine_distributional_results,
)


def _fake_result(total: float, rows: list[tuple[str, float, float]]):
    """Build a fake DistributionalAnalysis-shaped object for tests."""
    return SimpleNamespace(
        total_tax_change=total,
        results=[
            SimpleNamespace(
                income_group=SimpleNamespace(name=name),
                tax_change_avg=avg,
                share_of_total_change=share,
            )
            for name, avg, share in rows
        ],
    )


def test_combine_handles_empty():
    assert _combine_distributional_results([]) is None


def test_combine_single_result_is_identity_up_to_renormalization():
    res = _fake_result(100.0, [("A", -50.0, -0.4), ("B", -50.0, -0.6)])
    combined = _combine_distributional_results([res])
    # Single input: shares should come through renormalized to sum to
    # ±1.0 — sign matches the input (positive shares because the
    # combiner takes abs on dollar effects).
    shares = {r.income_group.name: r.share_of_total_change for r in combined.results}
    assert abs(abs(shares["A"]) + abs(shares["B"]) - 1.0) < 1e-9


def test_combine_weights_by_total_magnitude():
    """
    Two components: A with total=100B and B with total=10B. A should
    dominate the combined distribution by roughly 10:1.
    """
    big = _fake_result(100.0, [("X", 0, 1.0)])  # 100% to X
    small = _fake_result(10.0, [("Y", 0, 1.0)])  # 100% to Y
    combined = _combine_distributional_results([big, small])
    shares = {r.income_group.name: r.share_of_total_change for r in combined.results}
    assert abs(shares["X"] - (100 / 110)) < 1e-9
    assert abs(shares["Y"] - (10 / 110)) < 1e-9


def test_combine_sums_overlapping_groups():
    """Groups that appear in multiple components should sum correctly."""
    a = _fake_result(100.0, [("Bottom", -10, -0.5), ("Top", -10, -0.5)])
    b = _fake_result(100.0, [("Bottom", -10, -0.2), ("Top", -10, -0.8)])
    combined = _combine_distributional_results([a, b])
    shares = {r.income_group.name: r.share_of_total_change for r in combined.results}
    # A contributes: Bottom 0.5 * 100 = 50, Top 0.5 * 100 = 50.
    # B contributes: Bottom 0.2 * 100 = 20, Top 0.8 * 100 = 80.
    # Combined: Bottom 70/200 = 0.35, Top 130/200 = 0.65.
    assert abs(shares["Bottom"] - 0.35) < 1e-9
    assert abs(shares["Top"] - 0.65) < 1e-9


def test_combine_skips_zero_magnitude_components():
    """A component with zero total_tax_change should not corrupt the combine."""
    zero = _fake_result(0.0, [("X", 0, 1.0)])
    real = _fake_result(100.0, [("Y", 0, 1.0)])
    combined = _combine_distributional_results([zero, real])
    shares = {r.income_group.name: r.share_of_total_change for r in combined.results}
    assert "Y" in shares and abs(shares["Y"] - 1.0) < 1e-9
    # The zero-magnitude component's group should not appear.
    assert "X" not in shares
