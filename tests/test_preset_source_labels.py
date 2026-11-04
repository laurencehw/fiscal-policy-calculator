"""A preset's label and description must name the same producer as its score record.

The Nov 2026 site review found the corporate-28% page calling its reference a
CBO estimate in the heading and the description while the calibration caption,
correctly, called it U.S. Treasury. The label is display text, so it can drift
from ``CBO_SCORE_MAP[label]["source"]``; this pins the two together.
"""

from __future__ import annotations

import re

import pytest

from fiscal_model.app_data import CBO_SCORE_MAP, PRESET_POLICIES

PRODUCERS = ("CBO", "JCT", "Treasury", "TPC", "CRFB", "PWBM", "Tax Foundation")
_LABEL_SOURCE = re.compile(r"\((" + "|".join(PRODUCERS) + r"):")
_DESC_SOURCE = re.compile(r"\b(" + "|".join(PRODUCERS) + r") estimate\b")


def _cases():
    for label, preset in PRESET_POLICIES.items():
        record = CBO_SCORE_MAP.get(label)
        if not record or not record.get("source"):
            continue
        yield pytest.param(label, preset.get("description", ""), record["source"], id=label)


@pytest.mark.parametrize(("label", "description", "source"), list(_cases()))
def test_label_and_description_name_the_recorded_producer(label, description, source):
    named = _LABEL_SOURCE.search(label)
    if named:
        assert named.group(1) in source, f"label says {named.group(1)}, record says {source}"
    said = _DESC_SOURCE.search(description)
    if said:
        assert said.group(1) in source, f"description says {said.group(1)}, record says {source}"


def test_congress_gov_url_uses_the_measure_type_not_the_chamber():
    from bill_tracker.ingestor import congress_gov_url

    assert congress_gov_url(119, "hconres", "14") == (
        "https://www.congress.gov/bill/119th-congress/house-concurrent-resolution/14"
    )
    assert congress_gov_url(119, "hr", "1").endswith("/house-bill/1")
    assert congress_gov_url(119, "sjres", "3").endswith("/senate-joint-resolution/3")
    assert congress_gov_url(119, "hres", "7").endswith("/house-resolution/7")
    assert congress_gov_url(119, "bogus", "7") is None
