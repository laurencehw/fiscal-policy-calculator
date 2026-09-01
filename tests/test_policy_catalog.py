"""Catalog schema: stable preset ids, exclusivity groups, and values tags.

Pins the three pieces of schema the redesign's Build / Values / Routing
phases consume, plus the ``build_scorable_policy_map`` regression that used
to drop 28 of 52 presets.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from fiscal_model import preset_ids as pid
from fiscal_model.app_data import PRESET_POLICIES, PRESETS_BY_ID
from fiscal_model.ui.helpers import (
    GENERIC_PRESET_CATEGORY,
    PRESET_CATEGORY_BY_FLAG,
    build_scorable_policy_map,
    preset_scoring_category,
)
from fiscal_model.ui.policy_packages import PRESET_POLICY_PACKAGES

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

REPO_ROOT = Path(__file__).resolve().parent.parent
OVERRIDES_PATH = (
    REPO_ROOT / "fiscal_model" / "data_files" / "policy_tags_overrides.yaml"
)

# Snapshot of the shipped ids, in catalog order. These go into share URLs:
# a rename breaks every link ever pasted, so an accidental edit must fail
# here rather than silently ship. Adding a preset appends a line; changing
# an existing line needs a very good reason.
EXPECTED_PRESET_IDS = (
    "custom-policy",
    "tcja-full-extension",
    "tcja-extension-no-salt-cap",
    "tcja-rates-only",
    "corporate-28pct",
    "corporate-15pct",
    "ctc-expansion-2021",
    "ctc-extension",
    "eitc-childless-expansion",
    "estate-extend-tcja",
    "estate-exemption-3-5m",
    "estate-repeal",
    "ss-cap-90pct",
    "ss-donut-250k",
    "ss-cap-eliminate",
    "niit-expand",
    "amt-extend-tcja-relief",
    "amt-repeal-individual",
    "amt-repeal-corporate",
    "aca-ptc-extend-enhanced",
    "aca-ptc-repeal",
    "cap-employer-health-exclusion",
    "salt-cap-repeal",
    "step-up-basis-eliminate",
    "charitable-deduction-cap",
    "top-rate-39-6",
    "millionaire-surtax-5pp",
    "middle-class-rate-cut-2pp",
    "across-the-board-rate-cut-5pp",
    "ultra-millionaire-surtax-3pp",
    "top-rate-45",
    "medicare-surcharge-2pp",
    "gilti-reform",
    "fdii-repeal",
    "pillar-two-adoption",
    "international-package",
    "irs-enforcement-ira",
    "irs-enforcement-double",
    "irs-enforcement-high-income",
    "drug-negotiation-expand",
    "insulin-cap-universal",
    "drug-reference-pricing",
    "drug-reform-comprehensive",
    "tariff-universal-10pct",
    "tariff-china-60pct",
    "tariff-auto-25pct",
    "tariff-steel-aluminum-25pct",
    "tariff-reciprocal",
    "ira-clean-energy-repeal",
    "carbon-tax-50",
    "carbon-tax-25",
    "ev-credit-repeal",
    "ira-clean-energy-extend",
)

# Progressivity the app declines to assert. Listed explicitly so shrinking
# *or* growing this set is a deliberate, reviewed change. Reasons live in
# fiscal_model/data_files/policy_tags_overrides.yaml.
EXPECTED_NOT_MODELED = {
    "amt-extend-tcja-relief",       # engine silent on individual AMT
    "amt-repeal-individual",        # ditto
    "drug-negotiation-expand",      # outlay-side: no household tax base
    "insulin-cap-universal",
    "drug-reference-pricing",
    "drug-reform-comprehensive",
}


# ── 1. Stable ids ───────────────────────────────────────────────────────
class TestPresetIds:
    def test_every_preset_has_an_id(self) -> None:
        missing = [
            label for label in PRESET_POLICIES if label not in pid.PRESET_ID_BY_LABEL
        ]
        assert not missing, f"Presets without a stable id: {missing}"
        assert len(pid.PRESET_ID_BY_LABEL) == len(PRESET_POLICIES) == 53

    def test_no_id_is_registered_for_a_missing_preset(self) -> None:
        orphans = [
            label for label in pid.PRESET_ID_BY_LABEL if label not in PRESET_POLICIES
        ]
        assert not orphans, f"Ids registered for presets that no longer exist: {orphans}"

    def test_ids_are_unique(self) -> None:
        ids = list(pid.PRESET_ID_BY_LABEL.values())
        assert len(ids) == len(set(ids))

    @pytest.mark.parametrize("preset_id", pid.all_preset_ids())
    def test_id_is_a_clean_slug(self, preset_id: str) -> None:
        assert SLUG_RE.match(preset_id), f"{preset_id!r} is not kebab-case ascii"
        # No emoji, no scores, no display noise.
        assert not any(ch.isdigit() and "$" in preset_id for ch in preset_id)
        assert "$" not in preset_id

    def test_id_snapshot(self) -> None:
        """Renaming a shipped id breaks every share link ever pasted."""
        assert pid.all_preset_ids() == EXPECTED_PRESET_IDS

    def test_ids_follow_catalog_order(self) -> None:
        assert pid.all_preset_labels() == tuple(PRESET_POLICIES)

    def test_round_trip(self) -> None:
        for label in PRESET_POLICIES:
            assert pid.label_for_preset_id(pid.preset_id_for_label(label)) == label

    def test_presets_by_id_view(self) -> None:
        assert len(PRESETS_BY_ID) == len(PRESET_POLICIES)
        # Same dict objects, not copies.
        for label, entry in PRESET_POLICIES.items():
            assert PRESETS_BY_ID[entry["preset_id"]] is entry
            assert pid.label_for_preset_id(entry["preset_id"]) == label


class TestResolvePreset:
    LEGACY_TCJA_LABEL = "🏛️ TCJA Full Extension (CBO: $4.6T)"

    def test_exact_legacy_label(self) -> None:
        assert pid.resolve_preset(self.LEGACY_TCJA_LABEL) == self.LEGACY_TCJA_LABEL

    def test_legacy_label_is_the_live_catalog_key(self) -> None:
        """Guards the literal above against a silent label edit upstream."""
        assert self.LEGACY_TCJA_LABEL in PRESET_POLICIES

    def test_stable_id(self) -> None:
        assert pid.resolve_preset("tcja-full-extension") == self.LEGACY_TCJA_LABEL

    def test_url_encoded_label(self) -> None:
        encoded = "%F0%9F%8F%9B%EF%B8%8F+TCJA+Full+Extension+%28CBO%3A+%244.6T%29"
        assert pid.resolve_preset(encoded) == self.LEGACY_TCJA_LABEL

    def test_emoji_stripped_and_score_stripped(self) -> None:
        assert pid.resolve_preset("TCJA Full Extension") == self.LEGACY_TCJA_LABEL
        assert (
            pid.resolve_preset("TCJA Full Extension (CBO: $4.6T)")
            == self.LEGACY_TCJA_LABEL
        )

    def test_whitespace_and_case_insensitive(self) -> None:
        assert (
            pid.resolve_preset("  tcja   full    extension  ")
            == self.LEGACY_TCJA_LABEL
        )

    def test_backslash_escaped_dollar_label(self) -> None:
        """app_data bakes `\\$` into two carbon-tax labels; both spellings work."""
        canonical = "🌱 Carbon Tax \\$50/ton (-$1.7T)"
        assert canonical in PRESET_POLICIES
        assert pid.resolve_preset(canonical) == canonical
        assert pid.resolve_preset("Carbon Tax $50/ton (-$1.7T)") == canonical
        assert pid.resolve_preset("carbon-tax-50") == canonical

    def test_every_short_display_name_resolves(self) -> None:
        from fiscal_model.ui.policy_input_presets import _short_display_name

        for label in PRESET_POLICIES:
            short = _short_display_name(label)
            assert pid.resolve_preset(short) == label, f"short name failed: {short!r}"

    def test_unknown_and_empty_return_none(self) -> None:
        assert pid.resolve_preset("not-a-policy") is None
        assert pid.resolve_preset("") is None
        assert pid.resolve_preset(None) is None

    def test_preset_id_for_token_accepts_both_forms(self) -> None:
        assert pid.preset_id_for_token(self.LEGACY_TCJA_LABEL) == "tcja-full-extension"
        assert pid.preset_id_for_token("tcja-full-extension") == "tcja-full-extension"
        assert pid.preset_id_for_token("nope") is None


# ── 2. Exclusivity ──────────────────────────────────────────────────────
class TestExclusiveGroups:
    def test_groups_are_well_formed(self) -> None:
        known = set(pid.all_preset_ids())
        for group, members in pid.EXCLUSIVE_GROUPS.items():
            assert SLUG_RE.match(group), f"group id {group!r} is not kebab-case"
            assert len(members) >= 2, f"group {group!r} needs at least two members"
            assert len(set(members)) == len(members), f"group {group!r} has duplicates"
            unknown = [m for m in members if m not in known]
            assert not unknown, f"group {group!r} names unknown presets: {unknown}"

    def test_the_documented_double_count_groups_exist(self) -> None:
        """The three cases NOTES §6.2 calls out as silently summable today."""
        assert set(pid.EXCLUSIVE_GROUPS["ss-wage-cap"]) == {
            "ss-cap-90pct",
            "ss-donut-250k",
            "ss-cap-eliminate",
        }
        assert set(pid.EXCLUSIVE_GROUPS["tcja-extension"]) == {
            "tcja-full-extension",
            "tcja-extension-no-salt-cap",
            "tcja-rates-only",
        }
        assert set(pid.EXCLUSIVE_GROUPS["salt-cap"]) == {
            "tcja-extension-no-salt-cap",
            "salt-cap-repeal",
        }

    def test_subsumption_targets_exist(self) -> None:
        known = set(pid.all_preset_ids())
        for parent, children in pid.SUBSUMES.items():
            assert parent in known
            assert children, f"{parent!r} subsumes nothing; drop the entry"
            assert all(child in known for child in children)
            assert parent not in children

    def test_catalog_entries_carry_their_groups(self) -> None:
        donut = PRESETS_BY_ID["ss-donut-250k"]
        assert donut["exclusive_group"] == "ss-wage-cap"
        assert donut["exclusive_groups"] == ("ss-wage-cap",)
        # A preset can sit in two groups; the plural field is authoritative.
        no_salt = PRESETS_BY_ID["tcja-extension-no-salt-cap"]
        assert set(no_salt["exclusive_groups"]) == {"tcja-extension", "salt-cap"}
        assert PRESETS_BY_ID["gilti-reform"]["exclusive_group"] == (
            "international-package"
        )
        assert PRESETS_BY_ID["carbon-tax-50"]["exclusive_groups"] == ("carbon-tax",)

    def test_exclusive_groups_for_accepts_labels_and_ids(self) -> None:
        by_id = pid.exclusive_groups_for(["ss-cap-90pct", "ss-donut-250k"])
        by_label = pid.exclusive_groups_for(
            ["💰 SS Cap to 90% (CBO: -$800B)", "💰 SS Donut Hole $250K (-$2.7T)"]
        )
        assert by_id == by_label == {
            "ss-wage-cap": ["ss-cap-90pct", "ss-donut-250k"]
        }

    def test_exclusive_groups_for_ignores_unknown_tokens(self) -> None:
        assert pid.exclusive_groups_for(["nope", "corporate-28pct"]) == {
            "corporate-rate": ["corporate-28pct"]
        }

    def test_conflicting_selections_flags_double_counts(self) -> None:
        conflicts = pid.conflicting_selections(
            ["ss-cap-90pct", "ss-donut-250k", "ss-cap-eliminate", "niit-expand"]
        )
        assert conflicts == [
            (
                "ss-wage-cap",
                ["ss-cap-90pct", "ss-donut-250k", "ss-cap-eliminate"],
            )
        ]

    def test_conflicting_selections_is_quiet_on_a_clean_package(self) -> None:
        assert pid.conflicting_selections(
            ["corporate-28pct", "ss-donut-250k", "step-up-basis-eliminate"]
        ) == []

    def test_conflicting_selections_covers_the_nested_tcja_case(self) -> None:
        groups = dict(
            pid.conflicting_selections(
                ["tcja-extension-no-salt-cap", "salt-cap-repeal", "tcja-rates-only"]
            )
        )
        assert set(groups) == {"tcja-extension", "salt-cap"}

    def test_subsumed_selections(self) -> None:
        assert pid.subsumed_selections(
            ["🏛️ TCJA Full Extension (CBO: $4.6T)", "ctc-extension", "niit-expand"]
        ) == [("tcja-full-extension", ["ctc-extension"])]
        assert pid.subsumed_selections(["ctc-extension"]) == []


# ── 3. Values tags ──────────────────────────────────────────────────────
class TestValuesTags:
    def test_every_catalog_policy_is_tagged(self) -> None:
        missing = [
            preset_id
            for preset_id in pid.CATALOG_PRESET_IDS
            if preset_id not in pid.POLICY_TAGS
        ]
        assert not missing, (
            f"Untagged catalog policies: {missing}. "
            "Run: python scripts/derive_policy_tags.py"
        )
        assert len(pid.CATALOG_PRESET_IDS) == 52

    def test_custom_policy_is_not_in_the_catalog(self) -> None:
        assert pid.CUSTOM_POLICY_ID not in pid.CATALOG_PRESET_IDS
        assert pid.CUSTOM_POLICY_ID not in pid.POLICY_TAGS

    @pytest.mark.parametrize("preset_id", pid.CATALOG_PRESET_IDS)
    def test_tags_are_complete_and_in_enum(self, preset_id: str) -> None:
        tags = pid.POLICY_TAGS[preset_id]
        assert set(tags) == set(pid.TAG_KEYS), f"{preset_id}: wrong tag keys"
        for key, value in tags.items():
            assert value in pid.ALLOWED_TAG_VALUES[key], (
                f"{preset_id}: {key}={value!r} outside the allowed enum"
            )

    @pytest.mark.parametrize("preset_id", pid.CATALOG_PRESET_IDS)
    def test_every_tag_has_provenance(self, preset_id: str) -> None:
        sources = pid.TAG_SOURCES[preset_id]
        assert set(sources) == set(pid.TAG_KEYS)
        assert all(str(value).strip() for value in sources.values())

    def test_tags_are_attached_to_the_catalog_entries(self) -> None:
        for preset_id in pid.CATALOG_PRESET_IDS:
            entry = PRESETS_BY_ID[preset_id]
            assert entry["tags"] == pid.POLICY_TAGS[preset_id]
        assert "tags" not in PRESETS_BY_ID[pid.CUSTOM_POLICY_ID]

    def test_not_modeled_set_is_explicit(self) -> None:
        assert set(pid.not_modeled_ids()) == EXPECTED_NOT_MODELED

    def test_not_modeled_policies_are_documented_in_the_override_file(self) -> None:
        """`not_modeled` is a claim about the model's reach; it needs a reason."""
        import yaml

        raw = yaml.safe_load(OVERRIDES_PATH.read_text(encoding="utf-8"))
        overrides = raw["overrides"]
        for preset_id in pid.not_modeled_ids():
            assert preset_id in overrides, f"{preset_id} is not_modeled with no note"
            assert overrides[preset_id].get("progressivity") == "not_modeled"
            assert str(overrides[preset_id].get("note", "")).strip()

    def test_microsim_measured_policies_did_not_silently_degrade(self) -> None:
        """The distribution engine falls back to synthetic brackets on a
        transient MemoryError, which changes the emitted tag. These eleven
        were measured on the return-level microsim path; a regeneration that
        quietly downgraded them would land here."""
        measured = {
            preset_id
            for preset_id, sources in pid.TAG_SOURCES.items()
            if sources["progressivity"] == "engine:microsim"
        }
        assert measured == {
            "ctc-expansion-2021",
            "ctc-extension",
            "eitc-childless-expansion",
            "salt-cap-repeal",
            "top-rate-39-6",
            "millionaire-surtax-5pp",
            "middle-class-rate-cut-2pp",
            "across-the-board-rate-cut-5pp",
            "ultra-millionaire-surtax-3pp",
            "top-rate-45",
            "medicare-surcharge-2pp",
        }

    def test_provenance_values_are_from_the_documented_vocabulary(self) -> None:
        prefixes = ("engine:", "fallback:", "derived:", "not_modeled:")
        for preset_id, sources in pid.TAG_SOURCES.items():
            for key, value in sources.items():
                assert value == "override" or value.startswith(prefixes), (
                    f"{preset_id}.{key} = {value!r}"
                )

    def test_overrides_are_recorded_as_such(self) -> None:
        assert (
            pid.TAG_SOURCES["ira-clean-energy-repeal"]["govt_size"] == "override"
        )
        # ...and a derived tag on the same policy is not mislabelled.
        assert pid.TAG_SOURCES["ira-clean-energy-repeal"]["direction"].startswith(
            "derived:"
        )

    def test_direction_matches_the_base(self) -> None:
        """Only transfer-base policies use the spending directions."""
        for preset_id, tags in pid.POLICY_TAGS.items():
            spending = tags["direction"] in {"cut_spending", "add_spending"}
            assert spending == (tags["base"] == "transfer"), preset_id

    def test_spot_checks(self) -> None:
        """A few tags whose values a reviewer should be able to sanity-check."""
        assert pid.tags_for("ss-donut-250k")["progressivity"] == "strong_progressive"
        assert pid.tags_for("ss-donut-250k")["base"] == "payroll"
        assert pid.tags_for("tcja-full-extension")["direction"] == "cut_revenue"
        assert pid.tags_for("tariff-universal-10pct")["base"] == "consumption"
        assert pid.tags_for("tariff-universal-10pct")["progressivity"] == "regressive"
        assert pid.tags_for("estate-exemption-3-5m")["base"] == "estate"
        assert pid.tags_for("irs-enforcement-ira")["base"] == "enforcement"
        # Accepts a label as well as an id.
        assert pid.tags_for("💰 SS Donut Hole $250K (-$2.7T)") == pid.tags_for(
            "ss-donut-250k"
        )
        assert pid.tags_for("not-a-policy") == {}


# ── 4. The silent-drop regression ───────────────────────────────────────
class TestScorablePolicyMap:
    def test_every_preset_is_categorised(self) -> None:
        """28 of 52 presets used to fall through this map entirely."""
        mapped = build_scorable_policy_map(PRESET_POLICIES)
        expected = {
            label for label in PRESET_POLICIES if label != pid.CUSTOM_POLICY_LABEL
        }
        assert set(mapped) == expected
        assert len(mapped) == 52

    def test_each_preset_lands_in_exactly_one_category(self) -> None:
        known = {category for _, category in PRESET_CATEGORY_BY_FLAG}
        known.add(GENERIC_PRESET_CATEGORY)
        mapped = build_scorable_policy_map(PRESET_POLICIES)
        for label, entry in mapped.items():
            assert entry["category"] in known, f"{label}: {entry['category']}"
            assert isinstance(entry["category"], str)

    def test_previously_dropped_areas_are_present(self) -> None:
        mapped = build_scorable_policy_map(PRESET_POLICIES)
        categories = {entry["category"] for entry in mapped.values()}
        for category in (
            "International Tax",
            "IRS Enforcement",
            "Drug Pricing",
            "Trade / Tariffs",
            "Climate / Energy",
            "Income Tax",
        ):
            assert category in categories, f"{category} still missing from the map"

    def test_map_carries_preset_ids(self) -> None:
        mapped = build_scorable_policy_map(PRESET_POLICIES)
        assert mapped["🌍 Repeal FDII (-$200B)"]["preset_id"] == "fdii-repeal"

    def test_no_preset_package_is_empty(self) -> None:
        """4 of the 12 curated packages resolved to nothing before the fix."""
        mapped = build_scorable_policy_map(PRESET_POLICIES)
        empty: dict[str, list[str]] = {}
        for name, package in PRESET_POLICY_PACKAGES.items():
            resolvable = [p for p in package["policies"] if p in mapped]
            if not resolvable:
                empty[name] = package["policies"]
        assert not empty, f"Packages that resolve to no policies: {empty}"

    def test_every_package_policy_resolves(self) -> None:
        mapped = build_scorable_policy_map(PRESET_POLICIES)
        unresolved = {
            name: [p for p in package["policies"] if p not in mapped]
            for name, package in PRESET_POLICY_PACKAGES.items()
        }
        unresolved = {k: v for k, v in unresolved.items() if v}
        assert not unresolved, f"Package policies missing from the map: {unresolved}"

    def test_unscorable_stubs_are_still_excluded(self) -> None:
        stub = {
            "Custom Policy": {"rate_change": -2.0, "threshold": 500000},
            "Unknown Module": {"is_unknown": True},
            "TCJA Example": {"is_tcja": True},
        }
        mapped = build_scorable_policy_map(stub)
        assert set(mapped) == {"TCJA Example"}
        assert preset_scoring_category({"is_unknown": True}) is None
        assert preset_scoring_category({}) is None
        assert preset_scoring_category({"rate_change": 1.0}) == GENERIC_PRESET_CATEGORY
