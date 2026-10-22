"""Social Security (OASDI) trust fund ledger and OCACT option menu.

See :mod:`fiscal_model.social_security.trust_fund` and
``planning/lanes/SS1_trust_fund_page.md``.
"""

from fiscal_model.social_security.trust_fund import (
    CATEGORY_LABELS,
    ExclusiveGroupError,
    Projection,
    Provision,
    load_catalog,
    project,
    provisions_by_id,
    validate_selection,
)

__all__ = [
    "CATEGORY_LABELS",
    "ExclusiveGroupError",
    "Projection",
    "Provision",
    "load_catalog",
    "project",
    "provisions_by_id",
    "validate_selection",
]
