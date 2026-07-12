#!/usr/bin/env python3
"""
Regenerate requirements-lock.txt from requirements.txt via pip-compile.

Requires: pip install pip-tools

Usage:
    python scripts/compile_requirements_lock.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    req = ROOT / "requirements.txt"
    lock = ROOT / "requirements-lock.txt"
    if not req.exists():
        print(f"Missing {req}", file=sys.stderr)
        return 1

    cmd = [
        sys.executable,
        "-m",
        "piptools",
        "compile",
        str(req),
        "-o",
        str(lock),
        "--resolver=backtracking",
        "--allow-unsafe",
        "--generate-hashes=false",
    ]
    print("Running:", " ".join(cmd))
    try:
        subprocess.run(cmd, cwd=ROOT, check=True)
    except FileNotFoundError:
        print(
            "pip-tools not installed. Run: pip install pip-tools",
            file=sys.stderr,
        )
        return 1
    except subprocess.CalledProcessError as exc:
        return int(exc.returncode or 1)

    print(f"Wrote {lock}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
