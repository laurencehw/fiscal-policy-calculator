"""Copy the engine into this folder before Vercel bundles it.

Vercel builds the ``engine`` folder as its own project, so the API module and
the ``fiscal_model`` package are copied in from the repository root. The copies
are ignored by git. Files the API never reads (the bill tracker's databases,
caches) are left out.
"""

from __future__ import annotations

import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SKIP = shutil.ignore_patterns(
    "__pycache__", "*.pyc", "bills.db", "bills_populated.db", "assistant_usage.db", "cache"
)


def main(dest: Path = HERE) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "api.py", dest / "api.py")
    target = dest / "fiscal_model"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(ROOT / "fiscal_model", target, ignore=SKIP)
    print(f"copied api.py and fiscal_model/ into {dest}")


if __name__ == "__main__":
    main()
