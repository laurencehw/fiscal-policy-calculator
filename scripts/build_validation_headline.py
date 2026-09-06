#!/usr/bin/env python3
"""
Regenerate the pinned validation headline counts the page footer prints.

The footer's clause — *"N policies benchmarked against published scores"* — is
a validation claim, so ``N`` may not be typed by hand and may not go stale.
Computing it live meant running every specialized validator over all 81
scorecard rows on the critical path of the first script run: 7.65s of the
landing page's 8.40s (``planning/memos/COLD_START.md`` §3). This script writes
the count to ``fiscal_model/data_files/validation/headline_counts.json``, the
footer reads that, and ``tests/test_validation_headline.py`` recomputes the
scorecard and fails if the two ever disagree.

Run it whenever a benchmark is added, retired, or reclassified — the test says
so by name when you forget.

Usage::

    python scripts/build_validation_headline.py
    python scripts/build_validation_headline.py --check   # CI-style, no write
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fiscal_model.ui.validation_headline import (  # noqa: E402
    HEADLINE_PATH,
    build_payload,
    load_headline,
    reset_cache,
    write_payload,
)
from fiscal_model.validation.scorecard import compute_scorecard  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if the committed artifact differs from the live "
        "scorecard, without writing. What CI would run.",
    )
    args = parser.parse_args(argv)

    summary = compute_scorecard()
    payload = build_payload(summary)

    reset_cache()
    committed = load_headline()

    if args.check:
        if committed == payload:
            print(
                f"OK: {HEADLINE_PATH.name} matches the live scorecard "
                f"({payload['published_entries']} published of "
                f"{payload['total_entries']})"
            )
            return 0
        print("STALE: committed artifact does not match the live scorecard")
        print("  committed:", json.dumps(committed, sort_keys=True))
        print("  live:     ", json.dumps(payload, sort_keys=True))
        print("  fix: python scripts/build_validation_headline.py")
        return 1

    write_payload(payload)
    changed = committed != payload
    print(f"{'wrote' if changed else 'unchanged'}: {HEADLINE_PATH}")
    print(
        f"  published_entries={payload['published_entries']} "
        f"total_entries={payload['total_entries']} "
        f"model_estimate_entries={payload['model_estimate_entries']} "
        f"unclassified_entries={payload['unclassified_entries']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
