"""Preset descriptions shown on Explore must be plain-language, not maintainer notes."""

from __future__ import annotations

import re

from fiscal_model.app_data import PRESET_POLICIES

INTERNAL = re.compile(r"Phase E|provenance pass|\*\*|🟡")
STALE_SAVES = re.compile(r"Saves ~\\?\$100B|Saves ~\\?\$500B|Saves ~\\?\$1\.1T")
EMOJI = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")


def test_preset_descriptions_are_plain_language():
    for label, entry in PRESET_POLICIES.items():
        desc = entry["description"]
        assert INTERNAL.search(desc) is None, f"{label}: {desc}"
        assert STALE_SAVES.search(desc) is None, f"{label}: {desc}"
        assert EMOJI.search(desc) is None, f"{label}: {desc}"
