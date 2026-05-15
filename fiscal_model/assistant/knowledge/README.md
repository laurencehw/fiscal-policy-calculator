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
