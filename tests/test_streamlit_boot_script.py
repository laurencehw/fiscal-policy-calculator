"""
Unit tests for scripts/check_streamlit_boot.py.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_streamlit_boot.py"


@pytest.fixture
def streamlit_boot_script():
    spec = importlib.util.spec_from_file_location("_check_streamlit_boot_test", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_script_file_exists():
    assert SCRIPT_PATH.exists()


def test_streamlit_shell_detection(streamlit_boot_script):
    assert streamlit_boot_script._looks_like_streamlit_shell(
        "<html><head><script src='streamlit/static.js'></script></head></html>"
    )
    assert not streamlit_boot_script._looks_like_streamlit_shell("<html><body>plain</body></html>")


def test_route_checks_cover_calculator_and_classroom(streamlit_boot_script):
    checks = streamlit_boot_script._route_checks("http://127.0.0.1:8501")

    assert checks == [
        {"name": "calculator", "url": "http://127.0.0.1:8501/"},
        {"name": "classroom", "url": "http://127.0.0.1:8501/?mode=classroom"},
    ]


def test_issues_from_checks_flatten_failures(streamlit_boot_script):
    issues = streamlit_boot_script._issues_from_checks([
        {
            "name": "calculator",
            "url": "http://127.0.0.1:8501/",
            "ok": True,
            "latency_ms": 10.0,
            "message": "ok",
        },
        {
            "name": "classroom",
            "url": "http://127.0.0.1:8501/?mode=classroom",
            "ok": False,
            "latency_ms": 12.0,
            "message": "failed",
        },
    ])

    assert issues == [
        {
            "surface": "streamlit_boot",
            "severity": "fail",
            "name": "classroom",
            "url": "http://127.0.0.1:8501/?mode=classroom",
            "message": "failed",
            "latency_ms": 12.0,
        }
    ]


def test_command_runs_streamlit_with_headless_file_watcher_disabled(streamlit_boot_script):
    command = streamlit_boot_script._build_command(Path("app.py"), 8765)

    assert command[:4] == [sys.executable, "-m", "streamlit", "run"]
    assert "app.py" in command
    assert "--server.headless=true" in command
    assert "--server.port=8765" in command
    assert "--server.fileWatcherType=none" in command


def test_json_mode_prints_machine_readable_report(streamlit_boot_script, monkeypatch, capsys):
    monkeypatch.setattr(
        streamlit_boot_script,
        "run_boot_check",
        lambda **kwargs: {
            "overall": "ok",
            "entrypoint": str(kwargs["entrypoint"]),
            "checks": [],
            "issues": [],
        },
    )
    monkeypatch.setattr(sys, "argv", ["check_streamlit_boot", "--json"])

    assert streamlit_boot_script.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["overall"] == "ok"
    assert payload["issues"] == []
