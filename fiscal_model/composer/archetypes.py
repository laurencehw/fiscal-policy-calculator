"""
Loader for ``archetypes.yaml`` — the five starting philosophies.

Read once per process and cached: the YAML is shipped data, not user input, and
Streamlit reruns the whole script on every widget interaction.

The archetype path is deliberately the *offline* path. Nothing in this module
touches the network or an API key; picking a card produces a
:class:`~fiscal_model.composer.values_schema.ValuesVector` directly, and the
deterministic selector does the rest. That is what makes "works with no LLM
configured" a structural property rather than a promise.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .values_schema import PROTECTED_RULE_BY_KEY, ValuesVector

ARCHETYPES_PATH = Path(__file__).with_name("archetypes.yaml")

#: The sentence frame used when a vector has no archetype behind it — free
#: text, a share link, or a hand-edited reflection panel.
DEFAULT_RATIONALE_TEMPLATE = "{policy} covers {share} of the gap{contrast} — {driver}."


@dataclass(frozen=True)
class Archetype:
    """One starting philosophy, as read off the YAML."""

    id: str
    name: str
    one_line: str
    vector: ValuesVector
    rationale_template: str = DEFAULT_RATIONALE_TEMPLATE
    #: Three short value-language chips, shown on the card (wireframe ⑫).
    chips: tuple[str, ...] = ()

    def validate(self) -> list[str]:
        problems: list[str] = []
        if not self.id or " " in self.id:
            problems.append(f"archetype id {self.id!r} must be a non-empty slug")
        if not self.name:
            problems.append(f"archetype {self.id!r} has no name")
        if not self.one_line:
            problems.append(f"archetype {self.id!r} has no one_line")
        if "{policy}" not in self.rationale_template:
            problems.append(
                f"archetype {self.id!r} rationale_template must reference {{policy}}"
            )
        problems.extend(
            f"archetype {self.id!r}: {problem}" for problem in self.vector.validate()
        )
        return problems


_CACHE: dict[str, Archetype] | None = None
_MIGRATION_CACHE: dict[str, str] | None = None


def _coerce_vector(raw: Any) -> ValuesVector:
    data = dict(raw or {})
    protected = [
        str(key) for key in (data.get("protected") or ()) if str(key) in PROTECTED_RULE_BY_KEY
    ]
    data["protected"] = protected
    return ValuesVector.from_dict(data)


def _load() -> tuple[dict[str, Archetype], dict[str, str]]:
    payload = yaml.safe_load(ARCHETYPES_PATH.read_text(encoding="utf-8")) or {}
    archetypes: dict[str, Archetype] = {}
    for entry in payload.get("archetypes") or ():
        if not isinstance(entry, dict):
            continue
        archetype = Archetype(
            id=str(entry.get("id") or "").strip(),
            name=str(entry.get("name") or "").strip(),
            one_line=" ".join(str(entry.get("one_line") or "").split()),
            vector=_coerce_vector(entry.get("vector")),
            rationale_template=" ".join(
                str(entry.get("rationale_template") or DEFAULT_RATIONALE_TEMPLATE).split()
            ),
            chips=tuple(str(chip) for chip in (entry.get("chips") or ())),
        )
        problems = archetype.validate()
        if problems:
            raise ValueError("Invalid archetype in archetypes.yaml: " + "; ".join(problems))
        if archetype.id in archetypes:
            raise ValueError(f"duplicate archetype id {archetype.id!r} in archetypes.yaml")
        archetypes[archetype.id] = archetype

    migrations = {
        str(key): str(value)
        for key, value in (payload.get("migrated_from_package_studio") or {}).items()
    }
    unknown = sorted(set(migrations.values()) - set(archetypes))
    if unknown:
        raise ValueError(f"migration record points at unknown archetypes: {unknown}")
    return archetypes, migrations


def load_archetypes(*, refresh: bool = False) -> dict[str, Archetype]:
    """Every archetype, keyed by stable id, in file order. Cached."""
    global _CACHE, _MIGRATION_CACHE
    if _CACHE is None or refresh:
        _CACHE, _MIGRATION_CACHE = _load()
    return dict(_CACHE)


def archetype_ids() -> tuple[str, ...]:
    """Stable ids, in card order."""
    return tuple(load_archetypes())


def get_archetype(archetype_id: Any) -> Archetype | None:
    """One archetype by id; ``None`` for anything unknown (URLs are untrusted)."""
    token = str(archetype_id or "").strip().lower()
    return load_archetypes().get(token) if token else None


def package_studio_migrations() -> dict[str, str]:
    """Old Package Studio philosophy label -> the archetype it folded into."""
    load_archetypes()
    return dict(_MIGRATION_CACHE or {})


def rationale_template_for(archetype_id: Any) -> str:
    """Sentence frame for a given archetype, or the neutral default."""
    archetype = get_archetype(archetype_id)
    return archetype.rationale_template if archetype else DEFAULT_RATIONALE_TEMPLATE


__all__ = [
    "ARCHETYPES_PATH",
    "DEFAULT_RATIONALE_TEMPLATE",
    "Archetype",
    "archetype_ids",
    "get_archetype",
    "load_archetypes",
    "package_studio_migrations",
    "rationale_template_for",
]
