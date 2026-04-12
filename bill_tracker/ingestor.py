"""
Congress.gov API client for bill ingestion.

API docs: https://api.congress.gov/
Free API key required: https://api.congress.gov/sign-up/
Store key as CONGRESS_API_KEY environment variable or Streamlit secret.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import requests

from fiscal_model.time_utils import utc_now

logger = logging.getLogger(__name__)

CONGRESS_API_BASE = "https://api.congress.gov/v3"

# CRS subject tags with fiscal implications — used to filter bills
FISCAL_SUBJECTS = [
    "Taxation",
    "Budget and appropriations",
    "Income tax",
    "Corporate taxes",
    "Social security",
    "Medicare",
    "Health care costs and insurance",
    "Tax administration and collection, taxpayers",
    "Capital gains tax",
    "Estate tax, gifts, and trusts",
    "Payroll taxes",
    "Tax credits and withholding",
    "Defense spending and national security",
    "Government spending",
    "Federal budget deficit and debt",
]

STATUS_MAP = {
    "Introduced in House": "introduced",
    "Introduced in Senate": "introduced",
    "Referred to Committee": "committee",
    "Committee Consideration and Mark-up Session Held": "committee",
    "Passed House": "passed_chamber",
    "Passed Senate": "passed_chamber",
    "Became Public Law": "enacted",
    "Signed by President": "enacted",
}


def _normalize_status(latest_action: str) -> str:
    """Map congress.gov action text to simplified status."""
    action_lower = latest_action.lower()
    if any(kw in action_lower for kw in ("signed by president", "became public law", "enacted")):
        return "enacted"
    if any(kw in action_lower for kw in ("passed house", "passed senate", "passed chamber")):
        return "passed_chamber"
    if any(kw in action_lower for kw in ("reported", "markup", "ordered to be reported")):
        return "committee"
    if "referred" in action_lower:
        return "committee"
    return "introduced"


@dataclass
class BillMetadata:
    """Metadata for a single bill from congress.gov."""

    bill_id: str                         # e.g. "hr-1234-119"
    congress: int                        # 119
    chamber: str                         # "house" | "senate"
    number: str                          # "1234"
    bill_type: str                       # "hr" | "s" | "hjres" | "sjres"
    title: str
    sponsor: str
    introduced_date: datetime | None
    latest_action: str
    latest_action_date: datetime | None
    status: str                          # "introduced" | "committee" | "passed_chamber" | "enacted"
    crs_subjects: list[str] = field(default_factory=list)
    has_cbo_score: bool = False
    summary: str | None = None
    url: str = ""
    last_fetched: datetime = field(default_factory=utc_now)


def _make_bill_id(congress: int, bill_type: str, number: str) -> str:
    return f"{bill_type}-{number}-{congress}"


class BillIngestor:
    """
    Fetches and parses bills from the congress.gov v3 API.

    Rate limit: 5,000 requests/day (free tier). With daily incremental
    updates, this is well within budget.
    """

    def __init__(self, api_key: str | None = None, rate_limit_delay: float = 0.2):
        self.api_key = api_key or os.environ.get("CONGRESS_API_KEY", "")
        self._delay = rate_limit_delay  # seconds between requests

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def fetch_recent_bills(
        self,
        congress: int = 119,
        subjects: list[str] | None = None,
        since_date: datetime | None = None,
        limit: int = 250,
    ) -> list[BillMetadata]:
        """
        Fetch bills with fiscal subjects from the current Congress.

        Args:
            congress: Congress number (119 = 2025–2027).
            subjects: CRS subject filter. Defaults to FISCAL_SUBJECTS.
            since_date: Only return bills updated since this date.
            limit: Max bills to return per call.
        """
        if subjects is None:
            subjects = FISCAL_SUBJECTS

        bills: list[BillMetadata] = []
        offset = 0
        page_size = min(limit, 250)

        while len(bills) < limit:
            params = self._base_params()
            params["limit"] = page_size
            params["offset"] = offset
            params["sort"] = "updateDate+desc"
            if since_date:
                params["fromDateTime"] = since_date.strftime("%Y-%m-%dT%H:%M:%SZ")

            data = self._get(f"/bill/{congress}", params=params)
            if not data:
                break

            raw_bills = data.get("bills", [])
            if not raw_bills:
                break

            for raw in raw_bills:
                meta = self._parse_bill_metadata(raw, congress)
                if meta:
                    bills.append(meta)

            if len(raw_bills) < page_size:
                break  # no more pages

            offset += page_size
            time.sleep(self._delay)

        return bills[:limit]

    def fetch_bill_summary(self, bill_id: str) -> str | None:
        """Fetch CRS plain-language summary for a specific bill."""
        parts = bill_id.split("-")
        if len(parts) != 3:
            return None
        bill_type, number, congress = parts
        data = self._get(f"/bill/{congress}/{bill_type}/{number}/summaries")
        if not data:
            return None
        summaries = data.get("summaries", [])
        if not summaries:
            return None
        # Return the most recent summary text
        latest = sorted(summaries, key=lambda s: s.get("updateDate", ""), reverse=True)[0]
        return latest.get("text", "").strip() or None

    def fetch_enrolled_bills(self, congress: int = 119) -> list[BillMetadata]:
        """Fetch only bills that have been enacted into law."""
        params = self._base_params()
        params["limit"] = 250
        data = self._get(f"/bill/{congress}", params=params)
        if not data:
            return []
        bills = []
        for raw in data.get("bills", []):
            meta = self._parse_bill_metadata(raw, congress)
            if meta and meta.status == "enacted":
                bills.append(meta)
        return bills

    def fetch_bill_detail(self, bill_id: str) -> BillMetadata | None:
        """Fetch full metadata for a single bill by ID."""
        parts = bill_id.split("-")
        if len(parts) != 3:
            return None
        bill_type, number, congress = parts
        data = self._get(f"/bill/{congress}/{bill_type}/{number}")
        if not data:
            return None
        raw = data.get("bill", {})
        return self._parse_bill_metadata(raw, int(congress))

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _base_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {"format": "json"}
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    def _get(self, path: str, params: dict | None = None) -> dict | None:
        url = CONGRESS_API_BASE + path
        try:
            resp = requests.get(url, params=params or self._base_params(), timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as e:
            logger.warning("congress.gov HTTP %s for %s: %s", e.response.status_code, path, e)
            return None
        except Exception as e:
            logger.warning("congress.gov request failed for %s: %s", path, e)
            return None

    def _parse_bill_metadata(self, raw: dict, congress: int) -> BillMetadata | None:
        """Parse a raw bill dict from the congress.gov API response."""
        try:
            bill_type = raw.get("type", "").lower()
            number = str(raw.get("number", ""))
            title = raw.get("title", "") or raw.get("shortTitle", "Unknown Title")

            # Sponsor
            sponsors = raw.get("sponsors", [])
            if sponsors:
                s = sponsors[0]
                sponsor = f"{s.get('firstName', '')} {s.get('lastName', '')}".strip()
                party = s.get("party", "")
                state = s.get("state", "")
                if party and state:
                    sponsor = f"{sponsor} ({party}-{state})"
                if not sponsor:
                    sponsor = s.get("fullName", "") or "Unknown"
            else:
                sponsor_field = raw.get("sponsor") or {}
                sponsor = sponsor_field.get("fullName", "") or "Unknown"

            # Dates
            introduced_date = _parse_date(raw.get("introducedDate", ""))
            latest_action_info = raw.get("latestAction", {})
            latest_action = latest_action_info.get("text", "")
            latest_action_date = _parse_date(latest_action_info.get("actionDate", ""))

            # Chamber
            origin_chamber = raw.get("originChamber", "").lower()
            chamber = "house" if origin_chamber == "house" else "senate"

            # Subjects
            policy_area = raw.get("policyArea", {})
            subjects = []
            if policy_area:
                subjects.append(policy_area.get("name", ""))

            bill_id = _make_bill_id(congress, bill_type, number)
            congress_url = f"https://www.congress.gov/bill/{_ordinal(congress)}-congress/{chamber}-bill/{number}"

            return BillMetadata(
                bill_id=bill_id,
                congress=congress,
                chamber=chamber,
                number=number,
                bill_type=bill_type,
                title=title,
                sponsor=sponsor,
                introduced_date=introduced_date,
                latest_action=latest_action,
                latest_action_date=latest_action_date,
                status=_normalize_status(latest_action),
                crs_subjects=[s for s in subjects if s],
                has_cbo_score=False,
                summary=None,
                url=congress_url,
                last_fetched=utc_now(),
            )
        except Exception as e:
            logger.debug("Failed to parse bill metadata: %s", e)
            return None


def _parse_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def _ordinal(n: int) -> str:
    """119 → '119th'"""
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    return f"{n}{suffix}"
