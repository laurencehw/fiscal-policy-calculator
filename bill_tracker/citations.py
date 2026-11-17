"""Parse CBO estimate titles into the bill they are scoring.

CBO titles often mention a budget resolution they are *not* scoring
(``Pursuant to Title II of H. Con. Res. 14``). Matching on any citation in the
title is how H.Con.Res. 14 inherited P.L. 119-21 estimates. The subject of an
estimate is the citation *before* a ``pursuant to`` clause, or a Public Law
number mapped to the enacted bill.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

PINNED_PATH = Path(__file__).parent / "pinned_corrections.json"

# Longer forms first so "H. Con. Res." is not eaten as "H.R." / "H. Res."
_CITE_RE = re.compile(
    r"""
    (?:
        (?P<pl>Public\s+Law|P\.L\.)\s+(?P<pl_num>\d+-\d+)
        |
        (?P<type>
            H\.\s*Con\.\s*Res\.|S\.\s*Con\.\s*Res\.|
            H\.\s*J\.\s*Res\.|S\.\s*J\.\s*Res\.|
            H\.\s*Res\.|S\.\s*Res\.|
            H\.\s*R\.|S\.
        )
        \s*(?P<num>\d+)
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

_TYPE_ALIASES = {
    "h.r.": "hr",
    "s.": "s",
    "h.j.res.": "hjres",
    "s.j.res.": "sjres",
    "h.res.": "hres",
    "s.res.": "sres",
    "h.con.res.": "hconres",
    "s.con.res.": "sconres",
}

REF_MAP = {
    "hr": "H.R.",
    "s": "S.",
    "hjres": "H.J.Res.",
    "sjres": "S.J.Res.",
    "hres": "H.Res.",
    "sres": "S.Res.",
    "hconres": "H. Con. Res.",
    "sconres": "S. Con. Res.",
}

CONCURRENT_RESOLUTION_TYPES = frozenset({"hconres", "sconres"})


def bill_type_of(bill_id: str) -> str:
    return (bill_id or "").split("-", 1)[0].lower()


def congress_from_bill_id(bill_id: str) -> int:
    parts = (bill_id or "").split("-")
    if len(parts) >= 3 and parts[-1].isdigit():
        return int(parts[-1])
    return 119


def is_concurrent_resolution(bill_id: str) -> bool:
    """Budget resolutions (and other concurrent resolutions) are not laws."""
    return bill_type_of(bill_id) in CONCURRENT_RESOLUTION_TYPES


def bill_id_to_ref(bill_id: str) -> str:
    """Convert ``hr-1234-119`` → ``H.R. 1234``."""
    parts = (bill_id or "").split("-")
    if len(parts) < 2:
        return ""
    bill_type = parts[0].lower()
    number = parts[1]
    ref = REF_MAP.get(bill_type, bill_type.upper())
    return f"{ref} {number}"


def _compact_type(raw: str) -> str:
    return re.sub(r"\s+", "", raw).lower()


@lru_cache(maxsize=1)
def public_law_map() -> dict[str, str]:
    """P.L. number → tracker bill_id, from pinned_corrections.json."""
    if not PINNED_PATH.exists():
        return {"119-21": "hr-1-119"}
    try:
        payload = __import__("json").loads(PINNED_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"119-21": "hr-1-119"}
    raw = payload.get("public_laws") if isinstance(payload, dict) else None
    if not isinstance(raw, dict):
        return {"119-21": "hr-1-119"}
    return {str(k): str(v) for k, v in raw.items()}


def subject_clause(title: str) -> str:
    """The part of a CBO title that names the scored measure, not its parent."""
    return re.split(r"pursuant\s+to", title or "", maxsplit=1, flags=re.IGNORECASE)[0]


def first_citation(text: str) -> dict[str, str] | None:
    match = _CITE_RE.search(text or "")
    if not match:
        return None
    if match.group("pl_num"):
        return {"kind": "pl", "number": match.group("pl_num")}
    compact = _compact_type(match.group("type") or "")
    bill_type = _TYPE_ALIASES.get(compact)
    if not bill_type:
        return None
    return {"kind": bill_type, "number": match.group("num")}


def subject_bill_id(title: str, congress: int = 119) -> str | None:
    """Bill the CBO title is scoring, or None if it cannot be read cleanly."""
    cite = first_citation(subject_clause(title))
    if cite is None:
        return None
    if cite["kind"] == "pl":
        return public_law_map().get(cite["number"])
    return f"{cite['kind']}-{cite['number']}-{congress}"


def ref_in_subject(bill_ref: str, title: str) -> bool:
    """True if ``bill_ref`` appears in the subject clause with a number boundary.

    ``H.R. 1`` matches ``H.R. 1,`` and not ``H.R. 10``. Citations after
    ``pursuant to`` are ignored.
    """
    if not bill_ref:
        return False
    pattern = re.compile(rf"(?<![\w.]){re.escape(bill_ref)}(?!\d)", re.IGNORECASE)
    return bool(pattern.search(subject_clause(title)))


def title_bill_id_mismatch(bill_id: str, title: str, congress: int = 119) -> str | None:
    """Human-readable mismatch, or None if the title is consistent with bill_id."""
    subject = subject_bill_id(title, congress=congress)
    if subject is None:
        return None
    if subject != bill_id:
        return f"title scores {subject}, assigned {bill_id}"
    return None
