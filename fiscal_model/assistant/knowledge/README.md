---
source: https://www.cbo.gov/
title: Curated knowledge corpus (internal)
org: app authors
year: 2026
keywords: [readme, knowledge, corpus, how to add a snapshot]
---

# Knowledge corpus

This directory holds hand-maintained Markdown snapshots of authoritative
public-finance material. The assistant searches it via BM25 before
falling back to live web search.

## Adding a new snapshot

### Option A — `scripts/refresh_knowledge.py` (recommended)

For fetch-friendly sources (TPC, PWBM, Yale Budget Lab, JCT, BEA, BLS,
FRED), let the helper script seed a stub:

```bash
python scripts/refresh_knowledge.py \
    --url https://www.taxpolicycenter.org/publications/<slug> \
    --slug tpc_<topic>_<year> \
    --title "Full title from the page" \
    --org TPC \
    --year 2026 \
    --keywords "tpc, distribution, tcja, decile, after-tax-income"
```

The script fetches the page (using the same allowlist-enforced pipeline
the assistant uses at runtime), dumps the extracted text into a stub
file, and tells you what to edit. **You must replace the raw extraction
with a faithful summary** — the script's output is a starting point,
not a final snapshot.

For CBO and SSA, the script will fail with a `403 Forbidden` because
those sites hard-block bots. Two workarounds:

- Open the page in a browser, copy text, write the snapshot by hand.
- Trust the assistant's `web_search` tool at runtime — Anthropic's
  server-side fetch is not bot-blocked, so a local snapshot is not
  strictly required.

### Option B — by hand

Create a file `<short_slug>.md` with the following frontmatter:

```yaml
---
source: https://www.cbo.gov/publication/12345
title: An Update to the Budget and Economic Outlook: 2026 to 2036
org: CBO
year: 2026
keywords: [deficit, baseline, primary deficit, projections, debt, gdp]
---
```

The `source:` URL is what the assistant will cite. The `keywords:` line
is critical for recall — list synonyms (e.g., "primary deficit", "primary
balance", "fiscal balance" all in one entry). Add five to fifteen keywords
per file.

The body should be a faithful prose summary of the source, with key
numbers preserved exactly as published. Do **not** add commentary the
source does not contain. If you must editorialize, do it under a
`## Editor's note` heading so the model can distinguish.

## Refresh cadence

Snapshots have an implicit shelf life. Re-run them whenever:

- A new CBO Budget and Economic Outlook is released (twice a year).
- A new SS Trustees Report drops (typically spring).
- A major fiscal bill is scored by CBO/JCT.
- Penn Wharton or Yale Budget Lab publish a relevant analysis.

The assistant does not know how stale a snapshot is — keep the `year:`
field accurate so it can flag age when citing.
