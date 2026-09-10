"""Estimator-disagreement ranges — what *other* houses scored, beside our number.

A model number quoted alone reads as a consensus. Where two or more scorekeepers
have published an estimate of the same reform and they disagree, the honest
display is the spread and the model's position in it. This module builds that
object; it renders nothing and decides nothing.

Two kinds of range live here, because the record supplies two kinds:

**Converted per-point yields** (:func:`corporate_estimator_range`). Four houses
scored a corporate statutory-rate change on CBO's February 2024 baseline over
FY2025-2034. Each published total divided by its own rate step is a dollars-per-
point figure, and multiplying that by the step of the policy at hand converts it
to a comparable ten-year total. The four rows come from
``fiscal_model/data_files/validation/corporate_rate_scores.csv``, assembled for
``planning/memos/CORPORATE_PER_POINT_YIELD.md``; ``per_point_billions`` is a
column of that file. Nothing here re-transcribes a source.

**Published ranges** (:func:`published_range_for`). Some benchmarks already
carry a range rather than a point, because the houses that scored them disagree
by more than an editorial midpoint can hide: ``trump_corporate_15``
[+595.0, +673.1], ``pillar_two_adoption`` [-102.6, +56.5], ``reciprocal_tariffs``
[-1,800, -1,400]. Those live in ``fiscal_model/validation/target_revisions.py``
and are read from it live, never copied.

**The metric that makes per-point dollars comparable**, and the one thing this
module computes that the CSV does not carry, is the memo's section 4 marginal
share::

    average_base_per_year = baseline_corporate_receipts_10yr / statutory_rate / 10
    marginal_share        = |per_point_billions| * 10 / average_base_per_year

the share of the average corporate base that one statutory point actually
reaches. It is what makes "$135.7B per point" and "$192.8B per point"
commensurable, and ``tests/test_corporate_estimator_range.py`` pins the four it
produces against the memo's own printed table.

**Purity.** No Streamlit import, no module-scope validation import, no clock and
no randomness. The only I/O is one cached read of a CSV that ships with the
package. ``fiscal_model.validation`` is imported lazily inside
:func:`published_range_for` and :func:`scope_verdict_for`, so nothing here is
on an import path that does not ask for it.

**That laziness buys nothing where this module actually sits, and the reason is
worth writing down**: importing *any* module under ``fiscal_model.ui`` runs
``fiscal_model/ui/__init__.py``, whose eager re-export chain pulls in the whole
of ``fiscal_model.validation`` — 22 submodules, measured, from
``fiscal_model.ui.styles`` as readily as from ``fiscal_model.ui.dependencies``.
So the lazy import is a property of this file and not of its package, and it is
kept because the file is the piece Wave C's H4 reuses. Fixing the package's
``__init__`` is a cold-start question of its own (``planning/memos/COLD_START.md``)
and belongs to whoever owns that file, not to a presentation lane.

Wave C's H4 generalises the display side of this to other policy classes; the
dataclasses are deliberately free of corporate knowledge, and only
:func:`corporate_estimator_range` and the constants above it know what a
corporate rate is.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

__all__ = [
    "CORPORATE_AVERAGE_BASE_BILLIONS_PER_YEAR",
    "CORPORATE_BASELINE_LABEL",
    "CORPORATE_RECORD_WINDOW",
    "EstimatorEstimate",
    "EstimatorRange",
    "PerPointYield",
    "PublishedRange",
    "corporate_estimator_range",
    "corporate_per_point_record",
    "published_range_for",
    "scope_verdict_for",
]


# ---------------------------------------------------------------------------
# The corporate record: one window, one baseline, four estimators
# ---------------------------------------------------------------------------

#: The window every row used below is scored on. Selecting on it picks out
#: exactly the four rows ``CORPORATE_PER_POINT_YIELD.md`` section 4b tabulates —
#: JCT's Option 64, Treasury's FY2025 Green Book, PWBM's FY2025 Budget analysis
#: and Tax Foundation's June 2024 Biden Budget analysis — and no others. Rows on
#: other windows are in the CSV and are deliberately *not* converted: the memo's
#: section 4 shows the shares drift across windows as CBO's projected receipts
#: move, so mixing windows would compare a forecast difference with a modelling
#: one.
CORPORATE_RECORD_WINDOW = "FY2025-2034"

#: CBO's own projected corporate income tax receipts over that window, and the
#: statutory rate they are collected at. ``The Budget and Economic Outlook: 2024
#: to 2034`` (February 2024, publication 59710) Table 1-1 — the vintage
#: ``BaselineVintage.CBO_FEB_2024`` names, the one CBO's December 2024 *Options*
#: volume prices its revenue options against, and the one
#: ``scripts/corporate_yield_reconciliation.py`` normalises every share to. The
#: figures are that script's ``BASELINES["cbo_feb_2024"]``; a test asserts they
#: still agree with it.
CORPORATE_RECEIPTS_10YR_BILLIONS = 5094.0
CORPORATE_STATUTORY_RATE = 0.21

#: The base which, taxed at the statutory rate, reproduces the receipts the
#: vintage projects: $2,425.7B/yr. Not a measured profit level — it is the
#: denominator that removes the baseline level from a per-point comparison.
CORPORATE_AVERAGE_BASE_BILLIONS_PER_YEAR = (
    CORPORATE_RECEIPTS_10YR_BILLIONS / CORPORATE_STATUTORY_RATE / 10.0
)

CORPORATE_BASELINE_LABEL = "CBO's February 2024 baseline (pub. 59710, Table 1-1)"

#: Where the record lives, and the memo that assembled it.
CORPORATE_RECORD_PATH = (
    Path(__file__).resolve().parents[1]
    / "data_files"
    / "validation"
    / "corporate_rate_scores.csv"
)
CORPORATE_RECORD_MEMO = "planning/memos/CORPORATE_PER_POINT_YIELD.md"

#: How the CSV's ``scope`` column reads on screen. A row whose scope this map
#: does not know keeps its raw value rather than being silently relabelled.
_SCOPE_LABELS = {
    "rate_only": "rate only",
    "rate_plus_gilti": "rate + GILTI",
    "graduated": "graduated schedule",
}


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PerPointYield:
    """One published score, reduced to dollars per percentage point.

    ``per_point_billions`` is arithmetic on the printed total
    (``ten_year_billions / rate_change_pp``) and is never a figure the source
    itself prints — the CSV's own header says so, and says why it is not
    comparable across scopes, rate levels or windows. It is **computed here**
    rather than read from the CSV's column of the same name, which is rounded
    to three decimals: at Treasury's +7.0pp step the rounded column returns
    -1,349.943 against a printed -1,349.941, and a display that cannot
    reproduce its own source's figure to the dollar invites the reader to
    wonder what else was rounded. ``published_per_point_billions`` keeps the
    column so a test can check the two still agree.
    """

    estimator: str
    document: str
    scope: str
    published_10yr_billions: float
    published_step_pp: float
    published_per_point_billions: float

    @property
    def per_point_billions(self) -> float:
        return self.published_10yr_billions / self.published_step_pp

    @property
    def scope_label(self) -> str:
        return _SCOPE_LABELS.get(self.scope, self.scope)

    @property
    def marginal_share(self) -> float:
        """Share of the vintage's average base one statutory point reaches."""
        return (
            abs(self.per_point_billions)
            * 10.0
            / CORPORATE_AVERAGE_BASE_BILLIONS_PER_YEAR
        )


@dataclass(frozen=True)
class EstimatorEstimate:
    """One estimator's figure, converted to the policy at hand.

    Kept free of corporate specifics so Wave C's H4 can build these from a
    published range, a class-level error distribution or anything else that
    yields "this house says X".
    """

    estimator: str
    document: str
    scope_label: str
    value_billions: float
    #: The published figure this was converted from, and how. Empty when the
    #: estimate *is* the published figure.
    derivation: str = ""
    marginal_share: float | None = None


@dataclass(frozen=True)
class PublishedRange:
    """A benchmark whose target is a range because its scorekeepers disagree."""

    policy_id: str
    low_billions: float
    high_billions: float
    #: The in-range point the scorecard measures error against, when the ledger
    #: carries one. ``None`` on every range row registered so far — the bounds
    #: are the record and ``source_name`` says which house anchors it.
    anchor_billions: float | None
    source_name: str
    source_document: str

    def contains(self, value: float) -> bool:
        return self.low_billions <= value <= self.high_billions

    def distance(self, value: float) -> float:
        """Distance to the nearer bound; 0.0 inside."""
        if value < self.low_billions:
            return self.low_billions - value
        if value > self.high_billions:
            return value - self.high_billions
        return 0.0


@dataclass(frozen=True)
class EstimatorRange:
    """What the houses say, what we say, and how far apart those are.

    ``estimates`` is ordered low to high by signed value, which is the order a
    reader scans. ``basis`` and ``caveat`` are carried as data rather than built
    in the caption, so a second surface — or Wave C's generalisation — renders
    the same sentences without restating them.
    """

    subject: str
    window: str
    baseline_label: str
    estimates: tuple[EstimatorEstimate, ...]
    model_billions: float
    basis: str
    caveat: str
    model_per_point_billions: float | None = None
    model_marginal_share: float | None = None
    #: Provisions this run prices that no estimator in ``estimates`` prices.
    #: Non-empty means the comparison is not like-for-like and the caption says so.
    bundled: tuple[str, ...] = field(default_factory=tuple)

    @property
    def low_billions(self) -> float:
        return min(e.value_billions for e in self.estimates)

    @property
    def high_billions(self) -> float:
        return max(e.value_billions for e in self.estimates)

    @property
    def model_position(self) -> str:
        """``"inside"``, ``"larger"`` or ``"smaller"``.

        Signed containment first, then magnitude — because every estimate here
        carries the policy's own direction, "outside" is only ever interesting
        as "prices this reform bigger than any of them" or "smaller than all of
        them", and a deficit-reduction figure below a negative bound is the
        *larger* effect.
        """
        if self.low_billions <= self.model_billions <= self.high_billions:
            return "inside"
        widest = max(abs(self.low_billions), abs(self.high_billions))
        return "larger" if abs(self.model_billions) > widest else "smaller"

    @property
    def distance_to_range_billions(self) -> float:
        """Distance from the nearer bound; 0.0 inside."""
        if self.model_billions < self.low_billions:
            return self.low_billions - self.model_billions
        if self.model_billions > self.high_billions:
            return self.model_billions - self.high_billions
        return 0.0

    @property
    def estimates_below_model_share(self) -> int:
        """How many estimators price a point at less of the base than we do.

        Counted rather than asserted: the claim "above every published
        estimator" is true of ``reported`` at every step and of ``derived`` at
        +1pp, and false of ``derived`` at +7pp, so no caption may hard-code it.
        """
        if self.model_marginal_share is None:
            return 0
        return sum(
            1
            for e in self.estimates
            if e.marginal_share is not None
            and e.marginal_share < self.model_marginal_share
        )


# ---------------------------------------------------------------------------
# The record
# ---------------------------------------------------------------------------


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        body = (line for line in handle if not line.startswith("#"))
        return list(csv.DictReader(body))


@lru_cache(maxsize=1)
def corporate_per_point_record() -> tuple[PerPointYield, ...]:
    """The four FY2025-2034 corporate-rate scores, dollars per point.

    Cached because the file ships with the package and cannot change under a
    running process. Returns an empty tuple rather than raising if the file is
    missing or malformed: a caption that cannot be built is a caption that is
    not shown, never a result surface that fails to render.
    """
    try:
        rows = _read_rows(CORPORATE_RECORD_PATH)
    except (OSError, csv.Error):  # pragma: no cover — defensive
        return ()

    out: list[PerPointYield] = []
    for row in rows:
        if row.get("window") != CORPORATE_RECORD_WINDOW:
            continue
        try:
            step = float(row["rate_change_pp"])
            total = float(row["ten_year_billions"])
            per_point = float(row["per_point_billions"])
        except (KeyError, TypeError, ValueError):  # pragma: no cover — defensive
            continue
        if step == 0.0:
            continue
        out.append(
            PerPointYield(
                estimator=row.get("estimator", "").strip(),
                document=row.get("document", "").strip(),
                scope=row.get("scope", "").strip(),
                published_10yr_billions=total,
                published_step_pp=step,
                published_per_point_billions=per_point,
            )
        )
    out.sort(key=lambda y: abs(y.per_point_billions))
    return tuple(out)


# ---------------------------------------------------------------------------
# Corporate: the converted range
# ---------------------------------------------------------------------------

_CORPORATE_BASIS = (
    "each house's own published ten-year score divided by its own rate step, "
    "times this policy's step"
)

_CORPORATE_CAVEAT = (
    "Per-point dollars are not comparable across rate levels or scopes, which "
    "is why this is a range and not a consensus: Treasury's row moves the GILTI "
    "effective rate with the statutory rate, a rate cut is not a rate increase "
    "run backwards (Tax Foundation's Options 2.0 is the one edition pricing "
    "both directions in one model, and a point of cut costs about 29% more than "
    "a point of increase yields), and a run that also extends bonus "
    "depreciation prices something none of the four does."
)


def corporate_estimator_range(
    *,
    rate_change_pp: float,
    model_billions: float,
    bundled: Sequence[str] = (),
) -> EstimatorRange | None:
    """The four published corporate-rate scores, converted to this rate step.

    ``rate_change_pp`` is signed in percentage points (+7.0 for 21% -> 28%,
    -6.0 for 21% -> 15%). ``model_billions`` is the model's own ten-year figure
    on the repository's deficit convention, so the conversion sign matches it
    without a flip: every published row is stored deficit-signed too.

    Returns ``None`` when there is no statutory rate step to price — a corporate
    policy that changes only the book minimum tax, say — because a per-point
    yield has nothing to multiply, and ``None`` when the record cannot be read.

    ``bundled`` names provisions this run prices that the published rows do not.
    When it is non-empty the model's marginal share is **suppressed**: the share
    would divide a bundled total by a rate step and report the quotient as a
    property of the rate, which for the shipped 21% -> 15% preset returns 102.5%
    of the vintage's average base — a figure that reads as a base defect and is
    mostly ``extend_bonus_depreciation=True``.
    """
    if not rate_change_pp:
        return None
    record = corporate_per_point_record()
    if not record:
        return None

    estimates = tuple(
        sorted(
            (
                EstimatorEstimate(
                    estimator=yield_.estimator,
                    document=yield_.document,
                    scope_label=yield_.scope_label,
                    value_billions=yield_.per_point_billions * rate_change_pp,
                    derivation=(
                        f"${yield_.published_10yr_billions:+,.1f}B at "
                        f"{yield_.published_step_pp:+.1f}pp"
                    ),
                    marginal_share=yield_.marginal_share,
                )
                for yield_ in record
            ),
            key=lambda e: e.value_billions,
        )
    )

    model_per_point = model_billions / rate_change_pp
    bundled = tuple(bundled)
    model_share = (
        None
        if bundled
        else abs(model_per_point) * 10.0 / CORPORATE_AVERAGE_BASE_BILLIONS_PER_YEAR
    )

    return EstimatorRange(
        subject=f"a {abs(rate_change_pp):.1f}pp corporate rate "
        f"{'increase' if rate_change_pp > 0 else 'cut'}",
        window=CORPORATE_RECORD_WINDOW.replace("FY2025-2034", "FY2025–2034"),
        baseline_label=CORPORATE_BASELINE_LABEL,
        estimates=estimates,
        model_billions=model_billions,
        basis=_CORPORATE_BASIS,
        caveat=_CORPORATE_CAVEAT,
        model_per_point_billions=model_per_point,
        model_marginal_share=model_share,
        bundled=bundled,
    )


# ---------------------------------------------------------------------------
# Published ranges and scope verdicts — read live from the registries
# ---------------------------------------------------------------------------


def published_range_for(policy_id: str) -> PublishedRange | None:
    """The live calibrated target for ``policy_id``, when it is a range.

    Policy-agnostic by construction: it answers for ``trump_corporate_15``,
    ``pillar_two_adoption`` and ``reciprocal_tariffs`` alike, which is what Wave
    C's H4 needs from it. Returns ``None`` for a point target, an unknown id, or
    a registry that will not import.
    """
    if not policy_id:
        return None
    try:
        from fiscal_model.validation.target_revisions import live_target_for

        target = live_target_for(policy_id)
    except Exception:  # pragma: no cover — defensive
        return None
    if target is None or not target.is_range:
        return None
    anchor = getattr(target, "official_10yr_billions", None)
    return PublishedRange(
        policy_id=policy_id,
        low_billions=float(target.published_low_10yr_billions),
        high_billions=float(target.published_high_10yr_billions),
        anchor_billions=None if anchor is None else float(anchor),
        source_name=str(getattr(target, "source_name", "") or ""),
        source_document=str(getattr(target, "source_document", "") or ""),
    )


def scope_verdict_for(policy_id: str) -> str:
    """``BenchmarkSource.scope_differs`` for ``policy_id``, or ``""``.

    The repository's own sentence naming what a published row prices that the
    module's shape does not — filled only where the figures agree and the
    reforms do not. Read rather than restated, so a correction to the verdict
    reaches the app without a second edit.
    """
    if not policy_id:
        return ""
    try:
        from fiscal_model.validation.benchmark_sources import source_for

        source = source_for(policy_id)
    except Exception:  # pragma: no cover — defensive
        return ""
    return str(getattr(source, "scope_differs", "") or "") if source else ""
