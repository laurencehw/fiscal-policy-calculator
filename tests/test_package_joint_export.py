"""Bet 4: site_data/package-joint.json is package_interactions, exported as is.

The Build page's calculator total reads this file, so it must not drift from the
module it is written from, and it must carry shares only (never the microsim's
dollar levels, which are not on the list-price scale).
"""

from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from fiscal_model import package_interactions as pi  # noqa: E402

SHIPPED = ROOT / "site_data" / "package-joint.json"


@pytest.fixture(scope="module")
def shipped() -> dict:
    return json.loads(SHIPPED.read_text(encoding="utf-8"))


def test_channels_match_the_module(shipped):
    assert set(shipped["channels"]) == set(pi.INTERACTION_CHANNELS)
    for build_id, channels in pi.INTERACTION_CHANNELS.items():
        assert shipped["channels"][build_id] == sorted(channels - {"tcja_composite"})
    assert shipped["measurable"] == sorted(pi.MICROSIM_MEASURABLE_IDS)


def test_pair_kinds_match_the_classifier(shipped):
    expected = {
        (a, b): pi._pair_key(pi._channels(a), pi._channels(b))
        for a, b in combinations(sorted(pi.MICROSIM_MEASURABLE_IDS), 2)
    }
    assert {(p["a"], p["b"]): p["kind"] for p in shipped["pairs"]} == expected
    kinds = {(p["a"], p["b"]): p["kind"] for p in shipped["pairs"]}
    assert kinds[("eitc-childless-expansion", "top-rate-39-6")] == pi.KIND_STRUCTURALLY_ADDITIVE
    assert kinds[("salt-cap-repeal", "top-rate-39-6")] == pi.KIND_INTERACTING


def test_only_shares_are_exported(shipped):
    for pair in shipped["pairs"]:
        assert set(pair) == {"a", "b", "kind", "share", "reference"}


def test_measured_share_is_reproduced_exactly(shipped):
    pair = next(p for p in shipped["pairs"] if p["kind"] == pi.KIND_INTERACTING)
    m = pi.measured_interaction_share(pair["a"], pair["b"])
    assert m is not None
    assert pair["share"] == m.share
    assert pair["reference"] == m.reference == "top-rate-39-6"
    assert round(m.share * 100, 2) == -16.35


def test_pairwise_overlaps_are_exact_for_the_measurable_set():
    ids = sorted(pi.MICROSIM_MEASURABLE_IDS)
    reforms = {i: dict(pi.microsim_reform(i)) for i in ids}
    alone = {i: pi.joint_tax_change([reforms[i]]) for i in ids}
    pairwise = sum(
        pi.joint_tax_change([reforms[a], reforms[b]]) - alone[a] - alone[b]
        for a, b in combinations(ids, 2)
    )
    triple = pi.joint_tax_change([reforms[i] for i in ids]) - sum(alone.values())
    assert abs(triple - pairwise) < 0.01


def test_export_function_writes_what_is_shipped(shipped):
    import export_static

    payload = export_static.package_joint_payload()
    assert payload["channels"] == shipped["channels"]
    assert payload["channel_labels"] == shipped["channel_labels"]
    assert [(p["a"], p["b"], p["kind"]) for p in payload["pairs"]] == [
        (p["a"], p["b"], p["kind"]) for p in shipped["pairs"]
    ]
