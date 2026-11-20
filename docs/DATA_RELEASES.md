# Data releases and DOIs

The site's figures are cited three ways, from the narrowest to the broadest:

1. **One figure.** The "Cite as" block on an Explore, Compare or Build page. Its link carries `v=<scores date>`.
2. **One set of figures.** A frozen snapshot, `site_data/snapshots/<scores_date>-<fingerprint>.json`, also served at `/api/v1/snapshots/<id>` and listed on `/data`. Snapshots are written by `scripts/site_snapshots.py` and never rewritten.
3. **The calculator as a whole.** `CITATION.cff` (GitHub's "Cite this repository") and, once it exists, the Zenodo DOI.

## How a DOI is minted

Zenodo's GitHub integration archives every **published GitHub release** of a repository it is switched on for, and gives each one a version DOI. It also gives all versions together one *concept* DOI, which always resolves to the newest. Zenodo reads `.zenodo.json` for the record's title, authors, licence and description.

A Zenodo record cannot be deleted once published. Only the owner of the GitHub and Zenodo accounts should turn this on.

### One-time setup (Laurence)

1. Sign in at <https://zenodo.org> with GitHub (*Log in → GitHub*).
2. Open *Account → GitHub*, find `laurencehw/fiscal-policy-calculator` and flip its switch on. Zenodo installs a webhook on the repository; nothing is published yet.
3. Optional: add an ORCID to `CITATION.cff` and `.zenodo.json` before the first release, since the first record keeps it.

### Cutting a release

Run the **Data release** workflow (*Actions → Data release → Run workflow*) and type `release` in the box. It:

- names the release `data-<scores_date>-<fingerprint>` after the figures the site serves now, and refuses if that release already exists;
- attaches that snapshot file and puts its sha256 in the notes;
- publishes the release, which Zenodo archives within a few minutes.

A release cut by hand on GitHub works the same way; the workflow only keeps the names and notes consistent.

A release per scores change would mint a DOI every time a preset moves, which on an active week is daily. I suggest cutting one when the figures are worth citing: after a wave of model changes, or before a paper or a class uses them.

### After the first release

Copy the concept DOI (the one labelled "Cite all versions") from the Zenodo record. Then:

- add it to `CITATION.cff` as `doi:` and to the README badge;
- set it in the site (`web/lib/site.ts`), so the "Cite as" block, its BibTeX and RIS, and `/data` carry it.
