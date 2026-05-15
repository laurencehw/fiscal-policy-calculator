"""
Knowledge-snapshot starter generator for the Ask assistant.

Given an authoritative URL (CBO, JCT, PWBM, Yale Budget Lab, TPC, BEA,
BLS, SSA, etc.), fetches the page or PDF, extracts text via the same
allowlist-enforced pipeline the assistant uses at runtime, and writes a
Markdown stub into ``fiscal_model/assistant/knowledge/`` with a
properly-formed frontmatter block. The user then **hand-edits** the
file — pruning, summarizing, and verifying numbers — before it joins
the canon.

Usage:

    python scripts/refresh_knowledge.py \\
        --url https://www.cbo.gov/publication/61116 \\
        --slug cbo_outlook_2026 \\
        --title "An Update to the Budget and Economic Outlook" \\
        --org CBO \\
        --year 2026

    # PDF works too — pdfplumber is used automatically:
    python scripts/refresh_knowledge.py \\
        --url https://www.cbo.gov/system/files/...../report.pdf \\
        --slug cbo_long_term_outlook_2025

    # Just preview the extraction without writing a file:
    python scripts/refresh_knowledge.py --url ... --slug ... --dry-run

The script enforces the same domain allowlist as the live ``fetch_url``
tool. Unknown domains are rejected.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from textwrap import indent

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _slugify(s: str) -> str:
    out = []
    for ch in s.strip().lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in " -_/":
            out.append("_")
    slug = "".join(out).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug


def _frontmatter(
    *,
    source: str,
    title: str,
    org: str,
    year: str,
    keywords: list[str],
) -> str:
    kw_line = ", ".join(keywords) if keywords else ""
    return (
        "---\n"
        f"source: {source}\n"
        f"title: {title}\n"
        f"org: {org}\n"
        f"year: {year}\n"
        f"keywords: [{kw_line}]\n"
        "---\n"
    )


def _starter_body(*, title: str, source: str, extracted_text: str) -> str:
    """Render a starter Markdown body the user can prune and rewrite."""
    snippet = extracted_text.strip()
    # Trim hard so the user is forced to summarize rather than paste.
    if len(snippet) > 3000:
        snippet = snippet[:3000] + "\n\n[…truncated; full text fetched at refresh time…]"
    return (
        f"# {title}\n\n"
        "> **TODO** — hand-edit before committing. Replace the raw extraction "
        "below with a faithful **summary** of the source's key points and "
        "numbers. Preserve any figures exactly as published. Add five to "
        "fifteen `keywords` in the frontmatter so BM25 search finds it.\n\n"
        f"Source: {source}\n\n"
        "## Raw extraction (auto-generated; replace)\n\n"
        f"```\n{snippet}\n```\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        required=True,
        help="Authoritative URL to fetch. Must be on the assistant's allowlist.",
    )
    parser.add_argument(
        "--slug",
        help="Filename stem (without .md). If omitted, derived from title or URL.",
    )
    parser.add_argument(
        "--title",
        default="",
        help="Document title. If omitted, the URL is used.",
    )
    parser.add_argument(
        "--org",
        default="",
        help="Issuing organization (e.g. CBO, JCT, PWBM). Required for the "
        "frontmatter; the script asks if not provided.",
    )
    parser.add_argument(
        "--year",
        default="",
        help="Publication year (YYYY). Required for the frontmatter.",
    )
    parser.add_argument(
        "--keywords",
        default="",
        help="Comma-separated initial keywords. The user should extend this list.",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=8000,
        help="Cap on extracted text length (default 8000).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print to stdout instead of writing a file.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the destination file if it already exists.",
    )
    args = parser.parse_args()

    # Imports here so --help doesn't fail if a dep is missing.
    from fiscal_model.assistant.sources import allowlisted_domain
    from fiscal_model.assistant.tools import AssistantTools

    domain = allowlisted_domain(args.url)
    if domain is None:
        print(
            f"ERROR: URL {args.url!r} is not on the assistant's allowlist.\n"
            "Update fiscal_model/assistant/sources.py first.",
            file=sys.stderr,
        )
        return 2

    # Reuse the live tool implementation — same fetch + extraction logic
    # the assistant uses at runtime. None of the other deps matter for fetch.
    tools = AssistantTools(
        scorer=None,
        baseline=None,
        cbo_score_map={},
        presets={},
    )
    result = tools.dispatch("fetch_url", {"url": args.url, "max_chars": args.max_chars})
    if "error" in result:
        err = result["error"]
        print(f"ERROR fetching {args.url}: {err}", file=sys.stderr)
        if "403" in err or "Forbidden" in err:
            print(
                "\nHint: this domain (commonly CBO, SSA) blocks bot requests "
                "regardless of User-Agent. Two workarounds:\n"
                "  1. Open the page in a browser, copy the relevant text, and "
                "create the snapshot file by hand using the frontmatter format "
                "documented in fiscal_model/assistant/knowledge/README.md.\n"
                "  2. At runtime the assistant's `web_search` tool reaches "
                "these sources via Anthropic's server-side infrastructure, "
                "which is not bot-blocked. You don't necessarily need a "
                "local snapshot.",
                file=sys.stderr,
            )
        return 1
    text = result.get("text", "")
    if not text:
        print(f"ERROR: empty extraction from {args.url}", file=sys.stderr)
        return 1

    title = args.title or args.url
    slug = args.slug or _slugify(args.title or domain + "_" + args.url.rsplit("/", 1)[-1])
    if not slug:
        slug = "snapshot"

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]

    body = _frontmatter(
        source=args.url,
        title=title,
        org=args.org or "TODO",
        year=args.year or "TODO",
        keywords=keywords,
    ) + "\n" + _starter_body(title=title, source=args.url, extracted_text=text)

    if args.dry_run:
        print(body)
        return 0

    dest_dir = ROOT / "fiscal_model" / "assistant" / "knowledge"
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / f"{slug}.md"
    if path.exists() and not args.overwrite:
        print(
            f"ERROR: {path} already exists. Pass --overwrite to replace, or "
            f"choose a different --slug.",
            file=sys.stderr,
        )
        return 1
    path.write_text(body, encoding="utf-8")
    print(f"Wrote {path.relative_to(ROOT)} ({len(text):,} chars extracted)")
    print()
    print("Next steps:")
    print("  1. Open the file and replace the 'Raw extraction' block with a")
    print("     faithful prose summary of the source's key points.")
    print("  2. Add 5-15 keywords to the frontmatter.")
    print("  3. Set 'org' and 'year' if they are still TODO.")
    print("  4. Commit and the assistant will pick it up on next BM25 build.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
