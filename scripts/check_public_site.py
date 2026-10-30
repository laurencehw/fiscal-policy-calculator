"""
Uptime check for the public Next.js site (fiscal.lwilsesamson.com).

``check_public_app.py`` watches the frozen Streamlit app; this watches the site
people now use: the home page, Explore, one preset page, and a live score
through ``/api/score`` (which proves the site can reach the engine).

Usage:
    python scripts/check_public_site.py
    python scripts/check_public_site.py --url https://preview.example.app --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

import requests

DEFAULT_SITE_URL = os.getenv("FISCAL_SITE_URL", "https://fiscal.lwilsesamson.com").rstrip("/")
USER_AGENT = "fiscal-policy-calculator-healthcheck/1.0"
UTC = timezone.utc

# A page counts as up only if it carries text it always prints, so a blank
# shell or a hosting error page with status 200 still fails.
PAGES = (
    ("/", "Fiscal Policy Calculator"),
    ("/explore", "Explore"),
    ("/explore/tcja-full-extension", "TCJA Full Extension"),
)
SCORE_REQUEST: dict[str, Any] = {"kind": "income", "rate": 1, "who": 400_000, "duration": 10, "dynamic": False}


def _timed(fn):
    start = time.perf_counter()
    ok, message = fn()
    return ok, message, round((time.perf_counter() - start) * 1000, 1)


def check_page(base_url: str, path: str, marker: str, timeout_seconds: float) -> dict:
    url = f"{base_url}{path}"

    def run() -> tuple[bool, str]:
        try:
            response = requests.get(url, timeout=timeout_seconds, headers={"User-Agent": USER_AGENT})
            response.raise_for_status()
        except requests.RequestException as exc:
            return False, f"{url} failed: {exc}"
        if marker not in response.text:
            return False, f"{url} answered but does not contain {marker!r}."
        return True, f"{url} looks reachable."

    ok, message, latency = _timed(run)
    return {"url": url, "ok": ok, "latency_ms": latency, "message": message}


def check_score(base_url: str, timeout_seconds: float) -> dict:
    url = f"{base_url}/api/score"

    def run() -> tuple[bool, str]:
        try:
            response = requests.post(
                url, json=SCORE_REQUEST, timeout=timeout_seconds, headers={"User-Agent": USER_AGENT}
            )
            response.raise_for_status()
            body = response.json()
        except (requests.RequestException, ValueError) as exc:
            return False, f"{url} failed: {exc}"
        value = body.get("ten_year_deficit_impact") if isinstance(body, dict) else None
        if not isinstance(value, (int, float)):
            return False, f"{url} answered without a ten-year score."
        return True, f"{url} scored a test policy at {value:,.1f}B."

    ok, message, latency = _timed(run)
    return {"url": url, "ok": ok, "latency_ms": latency, "message": message}


def build_report(base_url: str, timeout_seconds: float) -> dict:
    checks = [check_page(base_url, path, marker, timeout_seconds) for path, marker in PAGES]
    # The engine can take several seconds to wake, so the score gets a longer allowance.
    checks.append(check_score(base_url, max(timeout_seconds, 60.0)))
    issues = [
        {"surface": "public_site", "severity": "fail", **{k: c[k] for k in ("url", "latency_ms", "message")}}
        for c in checks
        if not c["ok"]
    ]
    return {
        "overall": "ok" if not issues else "failed",
        "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "checks": checks,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the public site's availability.")
    parser.add_argument("--url", default=DEFAULT_SITE_URL, help="Base site URL")
    parser.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout in seconds for pages")
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable health report.")
    args = parser.parse_args()

    payload = build_report(args.url.rstrip("/"), args.timeout)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for check in payload["checks"]:
            print(f"{check['message']} ({check['latency_ms']} ms)")
        print("Public site checks passed." if payload["overall"] == "ok" else "Public site checks failed.")
    return 0 if payload["overall"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
