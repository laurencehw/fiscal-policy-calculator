"""
Lightweight uptime and accessibility check for the public Streamlit app.

Usage:
    python scripts/check_public_app.py
    python scripts/check_public_app.py --url https://example.streamlit.app
"""

from __future__ import annotations

import argparse
import os
import sys

import requests

DEFAULT_APP_URL = os.getenv(
    "FISCAL_POLICY_APP_URL",
    "https://fiscal-policy-calculator.streamlit.app",
).rstrip("/")

ERROR_MARKERS = (
    "You do not have access to this app or it does not exist",
    "share.streamlit.io/errors/not_found",
)


def _fetch(url: str, timeout_seconds: float) -> str:
    response = requests.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    return response.text


def _check_page(url: str, timeout_seconds: float) -> tuple[bool, str]:
    try:
        html = _fetch(url=url, timeout_seconds=timeout_seconds)
    except requests.RequestException as exc:
        return False, f"{url} failed: {exc}"

    for marker in ERROR_MARKERS:
        if marker in html:
            return False, f"{url} returned Streamlit not-found/access page."

    return True, f"{url} looks reachable."


def main() -> int:
    parser = argparse.ArgumentParser(description="Check public app availability.")
    parser.add_argument("--url", default=DEFAULT_APP_URL, help="Base app URL")
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP timeout in seconds (default: 10)",
    )
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    checks = [
        base_url,
        f"{base_url}/?mode=classroom",
    ]

    all_ok = True
    for check_url in checks:
        ok, message = _check_page(url=check_url, timeout_seconds=args.timeout)
        print(message)
        all_ok = all_ok and ok

    if all_ok:
        print("Public app checks passed.")
        return 0

    print("Public app checks failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
