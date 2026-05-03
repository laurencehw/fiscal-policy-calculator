#!/usr/bin/env python3
"""
Start the Streamlit app locally and verify core routes return the app shell.

This is a CI smoke check, not a full browser test. It catches deployment-class
failures where Streamlit cannot boot, bind a port, or serve the calculator and
classroom-mode entry URLs.

Usage:
    python scripts/check_streamlit_boot.py
    python scripts/check_streamlit_boot.py --timeout 45
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENTRYPOINT = PROJECT_ROOT / "app.py"
USER_AGENT = "fiscal-policy-calculator-streamlit-smoke/1.0"
ERROR_MARKERS = (
    "You do not have access to this app or it does not exist",
    "share.streamlit.io/errors/not_found",
    "Traceback (most recent call last)",
)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _build_command(entrypoint: Path, port: int) -> list[str]:
    return [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(entrypoint),
        "--server.headless=true",
        f"--server.port={port}",
        "--server.address=127.0.0.1",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]


def _route_checks(base_url: str) -> list[dict[str, str]]:
    return [
        {"name": "calculator", "url": f"{base_url}/"},
        {"name": "classroom", "url": f"{base_url}/?mode=classroom"},
    ]


def _fetch(url: str, timeout_seconds: float) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read().decode("utf-8", errors="replace")


def _looks_like_streamlit_shell(html: str) -> bool:
    lower = html.lower()
    return "<html" in lower and "streamlit" in lower and "<script" in lower


def _check_route(name: str, url: str, timeout_seconds: float) -> dict[str, object]:
    start = time.perf_counter()
    try:
        html = _fetch(url, timeout_seconds=timeout_seconds)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        return {
            "name": name,
            "url": url,
            "ok": False,
            "latency_ms": round((time.perf_counter() - start) * 1000, 1),
            "message": f"{name} route failed: {exc}",
        }

    if not html.strip():
        ok = False
        message = f"{name} route returned an empty response body."
    elif any(marker in html for marker in ERROR_MARKERS):
        ok = False
        message = f"{name} route returned a known error page."
    elif not _looks_like_streamlit_shell(html):
        ok = False
        message = f"{name} route did not return a Streamlit app shell."
    else:
        ok = True
        message = f"{name} route returned a Streamlit app shell."

    return {
        "name": name,
        "url": url,
        "ok": ok,
        "latency_ms": round((time.perf_counter() - start) * 1000, 1),
        "message": message,
    }


def _terminate(process: subprocess.Popen[str]) -> str:
    if process.poll() is None:
        process.terminate()
    try:
        stdout, _ = process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, _ = process.communicate(timeout=10)
    return stdout or ""


def _wait_for_server(
    *,
    process: subprocess.Popen[str],
    url: str,
    timeout_seconds: float,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    last_report: dict[str, object] | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return {
                "ok": False,
                "message": f"Streamlit process exited early with code {process.returncode}.",
            }
        last_report = _check_route("calculator", url, timeout_seconds=2.0)
        if last_report["ok"]:
            return {"ok": True, "message": "Streamlit server is accepting requests."}
        time.sleep(1.0)

    message = "Timed out waiting for Streamlit server."
    if last_report is not None:
        message += f" Last check: {last_report['message']}"
    return {"ok": False, "message": message}


def _issues_from_checks(checks: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "surface": "streamlit_boot",
            "severity": "fail",
            "name": check["name"],
            "url": check["url"],
            "message": check["message"],
            "latency_ms": check["latency_ms"],
        }
        for check in checks
        if not check["ok"]
    ]


def run_boot_check(*, entrypoint: Path, timeout_seconds: float) -> dict[str, object]:
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    command = _build_command(entrypoint=entrypoint, port=port)
    process = subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    process_output = ""
    checks: list[dict[str, object]] = []
    startup = {"ok": False, "message": "Streamlit server was not checked."}
    try:
        startup = _wait_for_server(
            process=process,
            url=f"{base_url}/",
            timeout_seconds=timeout_seconds,
        )
        if startup["ok"]:
            checks = [
                _check_route(
                    name=check["name"],
                    url=check["url"],
                    timeout_seconds=10.0,
                )
                for check in _route_checks(base_url)
            ]
    finally:
        process_output = _terminate(process)

    if not startup["ok"]:
        checks = [
            {
                "name": "startup",
                "url": base_url,
                "ok": False,
                "latency_ms": 0.0,
                "message": startup["message"],
            }
        ]

    issues = _issues_from_checks(checks)
    return {
        "overall": "ok" if not issues else "failed",
        "entrypoint": str(entrypoint),
        "base_url": base_url,
        "checks": checks,
        "issues": issues,
        "process_returncode": process.returncode,
        "process_output_tail": process_output[-4000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a local Streamlit boot smoke check.")
    parser.add_argument(
        "--entrypoint",
        default=str(DEFAULT_ENTRYPOINT),
        help="Streamlit entrypoint to run.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=45.0,
        help="Seconds to wait for Streamlit to start.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the boot report as JSON.",
    )
    args = parser.parse_args()

    payload = run_boot_check(
        entrypoint=Path(args.entrypoint).resolve(),
        timeout_seconds=args.timeout,
    )
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for check in payload["checks"]:
            print(f"{check['message']} ({check['latency_ms']} ms)")
        if payload["overall"] == "ok":
            print("Streamlit boot checks passed.")
        else:
            print()
            print("Issues:")
            for issue in payload["issues"]:
                print(f"- {issue['name']}: {issue['message']}")
            print("Streamlit boot checks failed.")

    return 0 if payload["overall"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
