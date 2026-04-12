"""
CBO cost estimate fetcher.

CBO publishes estimates as HTML, PDF, and via a JSON feed at:
  https://www.cbo.gov/data/cost-estimates  (stable JSON API, preferred)

No official API key required.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import requests

from fiscal_model.time_utils import UTC, parse_utc_timestamp, utc_now

logger = logging.getLogger(__name__)

CBO_BASE = "https://www.cbo.gov"
CBO_ESTIMATES_JSON = "https://www.cbo.gov/data/cost-estimates"


@dataclass
class CBOCostEstimate:
    """A single CBO cost estimate for a bill."""

    bill_id: str                            # Linked congress.gov bill ID (may be empty if unmatched)
    title: str
    estimate_date: datetime
    ten_year_cost_billions: float           # Positive = costs money, Negative = raises revenue
    annual_costs: list[float] = field(default_factory=list)
    budget_function: str = ""
    dynamic_estimate: float | None = None
    pdf_url: str = ""
    cbo_url: str = ""


class CBOScoreFetcher:
    """
    Fetches CBO cost estimates from cbo.gov.

    Primary source: JSON feed at /data/cost-estimates
    Fallback: HTML scraping of individual estimate pages
    """

    def __init__(self, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "FiscalPolicyCalculator/1.0"})

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def fetch_recent_estimates(
        self,
        since_date: datetime | None = None,
        limit: int = 100,
    ) -> list[CBOCostEstimate]:
        """
        Fetch recent CBO cost estimates from the JSON feed.

        The CBO JSON API returns estimates sorted by date, newest first.
        """
        params: dict[str, Any] = {"_format": "json"}
        data = self._get_json(CBO_ESTIMATES_JSON, params=params)
        if not data:
            return []

        estimates = []
        items = data if isinstance(data, list) else data.get("data", [])

        for item in items[:limit * 2]:  # over-fetch to allow date filtering
            est = self._parse_estimate_item(item)
            if est is None:
                continue
            if since_date and est.estimate_date < since_date:
                continue
            estimates.append(est)
            if len(estimates) >= limit:
                break

        return estimates

    def match_to_bill(self, bill_id: str, bill_title: str = "") -> CBOCostEstimate | None:
        """
        Attempt to match a congress.gov bill to a CBO cost estimate.

        Matching strategy:
        1. Exact bill number match in CBO metadata
        2. Fuzzy title match (threshold: 0.65)
        """
        estimates = self.fetch_recent_estimates(limit=200)
        return self.match_to_bill_from_estimates(
            bill_id=bill_id,
            bill_title=bill_title,
            estimates=estimates,
        )

    def match_to_bill_from_estimates(
        self,
        bill_id: str,
        bill_title: str,
        estimates: list[CBOCostEstimate],
    ) -> CBOCostEstimate | None:
        """
        Match a bill against a pre-fetched list of estimates.

        This avoids re-fetching CBO data for every bill in a pipeline run.
        """
        if not estimates:
            return None

        # Parse bill number from bill_id (e.g. "hr-1234-119" → "H.R. 1234")
        bill_ref = _bill_id_to_ref(bill_id)
        bill_title_lower = bill_title.lower().strip()

        best_match: CBOCostEstimate | None = None
        best_score = 0.0

        for est in estimates:
            title_lower = est.title.lower()

            # Exact bill number match
            if bill_ref and bill_ref.lower() in title_lower:
                return CBOCostEstimate(
                    bill_id=bill_id,
                    title=est.title,
                    estimate_date=est.estimate_date,
                    ten_year_cost_billions=est.ten_year_cost_billions,
                    annual_costs=list(est.annual_costs),
                    budget_function=est.budget_function,
                    dynamic_estimate=est.dynamic_estimate,
                    pdf_url=est.pdf_url,
                    cbo_url=est.cbo_url,
                )

            # Fuzzy title match
            if bill_title_lower:
                score = SequenceMatcher(None, bill_title_lower, title_lower).ratio()
                if score > best_score and score >= 0.65:
                    best_score = score
                    best_match = est

        if not best_match:
            return None

        return CBOCostEstimate(
            bill_id=bill_id,
            title=best_match.title,
            estimate_date=best_match.estimate_date,
            ten_year_cost_billions=best_match.ten_year_cost_billions,
            annual_costs=list(best_match.annual_costs),
            budget_function=best_match.budget_function,
            dynamic_estimate=best_match.dynamic_estimate,
            pdf_url=best_match.pdf_url,
            cbo_url=best_match.cbo_url,
        )

    def parse_estimate_html(self, url: str) -> CBOCostEstimate | None:
        """
        Parse a CBO estimate HTML page to extract the cost table.

        CBO's HTML estimates follow a consistent structure with a summary
        table near the top of the page.
        """
        try:
            resp = self._session.get(url, timeout=self._timeout)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            logger.warning("Failed to fetch CBO HTML estimate from %s: %s", url, e)
            return None

        return self._parse_html_content(html, url=url)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_json(self, url: str, params: dict | None = None) -> Any:
        try:
            resp = self._session.get(url, params=params, timeout=self._timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning("CBO JSON fetch failed for %s: %s", url, e)
            return None

    def _parse_estimate_item(self, item: dict) -> CBOCostEstimate | None:
        """Parse a single item from the CBO JSON feed."""
        try:
            title = item.get("title", "")
            # Date field varies across CBO API versions
            date_str = (
                item.get("publishedAt")
                or item.get("date")
                or item.get("field_estimated_date", "")
                or ""
            )
            estimate_date = _parse_date(date_str)

            # Cost extraction — CBO JSON may include a "cost" field or we
            # extract from title/description
            cost_raw = item.get("cost") or item.get("estimatedCost") or item.get("field_cbo_cost")
            ten_year_cost = _parse_cost_billions(cost_raw) if cost_raw else 0.0

            # URL
            cbo_url = item.get("url", "") or item.get("path", "")
            if cbo_url and not cbo_url.startswith("http"):
                cbo_url = CBO_BASE + cbo_url

            # Budget function
            budget_function = item.get("budgetFunction", "") or item.get("field_budget_function", "")

            return CBOCostEstimate(
                bill_id="",
                title=title,
                estimate_date=estimate_date,
                ten_year_cost_billions=ten_year_cost,
                budget_function=str(budget_function),
                cbo_url=cbo_url,
            )
        except Exception as e:
            logger.debug("Failed to parse CBO estimate item: %s", e)
            return None

    def _parse_html_content(self, html: str, url: str = "") -> CBOCostEstimate | None:
        """Extract cost data from a CBO HTML estimate page."""
        try:
            # Try to find the 10-year total in common CBO page patterns
            # CBO uses patterns like "$X.X billion" or "($X.X billion)"
            cost_pattern = re.compile(
                r"(?:10-year|ten-year|over.*?10|total.*?cost).*?"
                r"\$?([\d,]+\.?\d*)\s*(?:billion|million|trillion)",
                re.IGNORECASE | re.DOTALL,
            )
            match = cost_pattern.search(html[:50000])  # only scan first 50K chars

            ten_year_cost = 0.0
            if match:
                amount_str = match.group(1).replace(",", "")
                amount = float(amount_str)
                # Determine unit from surrounding text
                unit_text = html[match.start():match.end()].lower()
                if "trillion" in unit_text:
                    amount *= 1000
                elif "million" in unit_text:
                    amount /= 1000
                ten_year_cost = amount

            # Extract title from <title> tag
            title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else "Unknown"

            return CBOCostEstimate(
                bill_id="",
                title=title,
                estimate_date=utc_now(),
                ten_year_cost_billions=ten_year_cost,
                cbo_url=url,
            )
        except Exception as e:
            logger.debug("Failed to parse CBO HTML content: %s", e)
            return None


def _parse_date(date_str: str) -> datetime:
    parsed = parse_utc_timestamp(date_str)
    if parsed is not None:
        return parsed
    for fmt in ("%m/%d/%Y",):
        try:
            return datetime.strptime(date_str[:10], fmt).replace(tzinfo=UTC)
        except (ValueError, TypeError):
            continue
    return datetime(1970, 1, 1, tzinfo=UTC)


def _parse_cost_billions(cost_raw: Any) -> float:
    """Parse a cost value (string or number) to billions of dollars."""
    if isinstance(cost_raw, (int, float)):
        return float(cost_raw)
    if not isinstance(cost_raw, str):
        cost_raw = str(cost_raw)
    # Strip non-numeric except minus, dot
    cleaned = re.sub(r"[^\d.\-]", "", cost_raw.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _bill_id_to_ref(bill_id: str) -> str:
    """Convert 'hr-1234-119' → 'H.R. 1234'."""
    parts = bill_id.split("-")
    if len(parts) < 2:
        return ""
    bill_type = parts[0].upper()
    number = parts[1]
    ref_map = {"HR": "H.R.", "S": "S.", "HJRES": "H.J.Res.", "SJRES": "S.J.Res."}
    ref = ref_map.get(bill_type, bill_type)
    return f"{ref} {number}"


def load_fallback_estimates(path: str | Path) -> list[CBOCostEstimate]:
    """
    Load manually curated CBO scores from JSON.

    Accepted formats:
    1) {"scores": [ ... ]} or
    2) [ ... ]

    Required keys per entry:
    - bill_id
    - ten_year_cost_billions
    """
    file_path = Path(path)
    if not file_path.exists():
        return []

    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to parse fallback CBO file %s: %s", file_path, exc)
        return []

    items = payload.get("scores", []) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        logger.warning("Fallback CBO file %s has invalid structure.", file_path)
        return []

    estimates: list[CBOCostEstimate] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        bill_id = str(raw.get("bill_id", "")).strip()
        if not bill_id:
            continue

        try:
            ten_year = float(raw.get("ten_year_cost_billions"))
        except (TypeError, ValueError):
            logger.warning(
                "Skipping fallback CBO score for %s due to invalid ten_year_cost_billions.",
                bill_id,
            )
            continue

        estimate_date = _parse_date(str(raw.get("estimate_date", "")))
        if estimate_date.year == 1970:
            estimate_date = utc_now()

        annual_costs_raw = raw.get("annual_costs", [])
        annual_costs: list[float] = []
        if isinstance(annual_costs_raw, list):
            for value in annual_costs_raw:
                try:
                    annual_costs.append(float(value))
                except (TypeError, ValueError):
                    continue

        estimates.append(
            CBOCostEstimate(
                bill_id=bill_id,
                title=str(raw.get("title", "")),
                estimate_date=estimate_date,
                ten_year_cost_billions=ten_year,
                annual_costs=annual_costs,
                budget_function=str(raw.get("budget_function", "")),
                dynamic_estimate=(
                    float(raw["dynamic_estimate"])
                    if raw.get("dynamic_estimate") is not None
                    else None
                ),
                pdf_url=str(raw.get("pdf_url", "")),
                cbo_url=str(raw.get("cbo_url", "")),
            )
        )

    return estimates
