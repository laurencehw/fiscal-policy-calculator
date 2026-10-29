"""Vercel's entry point: the repository's FastAPI app, unchanged.

On Vercel, ``build.py`` has copied ``api.py`` and ``fiscal_model/`` next to this
file. Run locally from the repository, the parent folder is used instead.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if not (_HERE / "api.py").exists():
    sys.path.insert(0, str(_HERE.parent))

from api import app  # noqa: E402

__all__ = ["app"]
