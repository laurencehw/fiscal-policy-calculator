"""
Lightweight uptime and accessibility check for the public Streamlit app.

Usage:
    python scripts/check_public_app.py
    python scripts/check_public_app.py --url https://example.streamlit.app
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

DEFAULT_APP_URL = os.getenv(
    "FISCAL_POLICY_APP_URL",
    "https://fiscal-policy-calculator.streamlit.app",
).rstrip("/")

ERROR_MARKERS = (
    "You do not have access to this app or it does not exist",
    "share.streamlit.io/errors/not_found",
)
USER_AGENT = "fiscal-policy-calculator-healthcheck/1.0"
UTC = timezone.utc


def _fetch(url: str, timeout_seconds: float) -> str:
    response = requests.get(
        url,
        timeout=timeout_seconds,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    return response.text


def _check_page(url: str, timeout_seconds: float) -> tuple[bool, str]:
    try:
        html = _fetch(url=url, timeout_seconds=timeout_seconds)
    except requests.RequestException as exc:
        return False, f"{url} failed: {exc}"

    if not html.strip():
        return False, f"{url} returned an empty response body."

    for marker in ERROR_MARKERS:
        if marker in html:
            return False, f"{url} returned Streamlit not-found/access page."

    return True, f"{url} looks reachable."


def _check_page_report(url: str, timeout_seconds: float) -> dict:
    """Return a JSON-serializable health record for one URL."""
    start = time.perf_counter()
    ok, message = _check_page(url=url, timeout_seconds=timeout_seconds)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return {
        "url": url,
        "ok": ok,
        "latency_ms": round(elapsed_ms, 1),
        "message": message,
    }


def _issues_from_reports(reports: list[dict]) -> list[dict]:
    """Flatten failed URL checks for artifact consumers."""
    return [
        {
            "surface": "public_app",
            "severity": "fail",
            "url": report["url"],
            "latency_ms": report["latency_ms"],
            "message": report["message"],
        }
        for report in reports
        if not report["ok"]
    ]


def _build_report(base_url: str, timeout_seconds: float) -> dict:
    checks = [
        base_url,
        f"{base_url}/?mode=classroom",
    ]
    reports = [
        _check_page_report(url=check_url, timeout_seconds=timeout_seconds)
        for check_url in checks
    ]
    issues = _issues_from_reports(reports)
    return {
        "overall": "ok" if not issues else "failed",
        "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "checks": reports,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check public app availability.")
    parser.add_argument("--url", default=DEFAULT_APP_URL, help="Base app URL")
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP timeout in seconds (default: 10)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a machine-readable health report.",
    )
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    payload = _build_report(base_url=base_url, timeout_seconds=args.timeout)

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for report in payload["checks"]:
            print(f"{report['message']} ({report['latency_ms']} ms)")

        if payload["overall"] == "ok":
            print("Public app checks passed.")
        else:
            print()
            print("Issues:")
            for issue in payload["issues"]:
                print(f"- {issue['url']}: {issue['message']}")
            print("Public app checks failed.")

    return 0 if payload["overall"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
