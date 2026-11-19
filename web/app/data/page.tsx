import type { Metadata } from "next";
import Link from "next/link";
import { snapshotIndex } from "@/lib/data";
import { API_BASE, latestEntry } from "@/lib/research";
import { longDate } from "@/lib/share";
import { REPO_URL, siteUrl } from "@/lib/site";

export const metadata: Metadata = {
  title: "Data and citation",
  description: "Frozen snapshots of every scored figure, a read-only JSON API, and how to cite the calculator.",
  alternates: { canonical: "/data" },
};

const ENDPOINTS: { path: string; returns: string }[] = [
  { path: "", returns: "A list of the endpoints below, and the latest snapshot." },
  {
    path: "/presets",
    returns:
      "Every Explore preset with its ten-year conventional and dynamic figures and the published score it is checked against.",
  },
  {
    path: "/presets/{id}",
    returns:
      "One preset in full: the static and behavioural components, year-by-year paths, published score, law status and error band.",
  },
  { path: "/build", returns: "Build's list prices." },
  { path: "/validation", returns: "The validation tiers Methods quotes, by policy class." },
  { path: "/snapshots", returns: "Every frozen snapshot, oldest first, with its sha256." },
  { path: "/snapshots/{ref}", returns: "One snapshot in full. ref is a snapshot id, a scores date, or latest." },
];

export default function DataPage() {
  const index = snapshotIndex();
  const latest = latestEntry(index);
  const api = `${siteUrl()}${API_BASE}`;
  const rows = [...index.snapshots].reverse();
  const example = latest?.id ?? "2026-11-19-c504675255ed";
  return (
    <>
      <header>
        <span className="eyebrow">Data</span>
        <h1>Data and citation</h1>
        <p className="lede">
          Every scored figure on the site can be downloaded as JSON, cited, and fetched again later exactly as it was on
          the day you used it.
        </p>
      </header>

      <section className="reading" aria-labelledby="snapshots-head">
        <h2 id="snapshots-head">Frozen snapshots</h2>
        <p>
          I re-run every preset each night. When a scored figure moves by $0.1 billion or more, the export writes a
          snapshot: each preset&apos;s conventional and dynamic ten-year figures and their year-by-year paths, the
          published score each is checked against, Build&apos;s list prices and the validation tiers. A snapshot is never
          rewritten, and each one records the sha256 of the one before it, so a number you quote from one can be checked
          by anyone later.
        </p>
        <p>
          A snapshot is named by its scores date and a fingerprint of the figures, for example <code>{example}</code>.
          The scores date is the <code>v=</code> date that every share link and citation on the site carries, so a link
          someone sent you can be matched to its snapshot. When the figures moved more than once in a day, the date alone
          gives the last snapshot of that day. The snapshots before 19 November 2026 were rebuilt from the exports in the
          repository&apos;s history, and each names the commit it came from.
        </p>
        {rows.length ? (
          <div className="tablewrap">
            <table className="sheet words">
              <caption className="sr-only">Frozen snapshots, newest first</caption>
              <thead>
                <tr>
                  <th scope="col">Scores date</th>
                  <th scope="col">Snapshot</th>
                  <th scope="col">Presets</th>
                  <th scope="col">sha256</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((entry) => (
                  <tr key={entry.id}>
                    <td>{longDate(entry.scores_date)}</td>
                    <td>
                      <a href={`${API_BASE}/snapshots/${entry.id}`}>{entry.id}</a>
                    </td>
                    <td>{entry.presets}</td>
                    <td>
                      <code title={entry.sha256}>{entry.sha256.slice(0, 12)}…</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="note">No snapshot has been exported yet.</p>
        )}
      </section>

      <section className="reading" aria-labelledby="api-head">
        <h2 id="api-head">The JSON API</h2>
        <p>
          The API is read-only and needs no key. It serves the snapshots and nothing else, so the current figures are
          simply the newest snapshot. Every response opens with the snapshot id, the scores date, the sign convention and
          a link back to this page. Figures are billions of nominal dollars over the budget window, and a positive figure
          adds to the deficit.
        </p>
        <div className="tablewrap">
          <table className="sheet words">
            <caption className="sr-only">Endpoints</caption>
            <thead>
              <tr>
                <th scope="col">GET</th>
                <th scope="col">Returns</th>
              </tr>
            </thead>
            <tbody>
              {ENDPOINTS.map((row) => (
                <tr key={row.path}>
                  <td>
                    <code>
                      {API_BASE}
                      {row.path}
                    </code>
                  </td>
                  <td>{row.returns}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p>From the command line:</p>
        <pre className="codeblock">
          <code>{`curl ${api}/presets/top-rate-45`}</code>
        </pre>
        <p>In Python, with pandas:</p>
        <pre className="codeblock">
          <code>{`import pandas as pd, requests

presets = requests.get("${api}/presets").json()["presets"]
df = pd.DataFrame(presets)

# The figures as they stood on a day, from the v= date on a link:
old = requests.get("${api}/snapshots/2026-11-17").json()`}</code>
        </pre>
        <p>In R, with jsonlite:</p>
        <pre className="codeblock">
          <code>{`library(jsonlite)

presets <- fromJSON("${api}/presets")$presets
one <- fromJSON("${api}/presets/top-rate-45")$preset
years <- one$conventional$year_by_year`}</code>
        </pre>
        <p>
          The scoring engine behind <Link href="/tailor">Tailor</Link> is not part of this API. It computes new policies
          on request, so its answers are not frozen. To score your own policy reproducibly, run the Python model from the{" "}
          <a href={REPO_URL}>repository</a> at the commit you cite.
        </p>
      </section>

      <section className="reading" aria-labelledby="read-head">
        <h2 id="read-head">Reading the figures</h2>
        <p>
          A snapshot carries the same caveats as the pages. I would report the validation tiers separately: the
          out-of-sample tier is the test, while calibrated presets agree with their targets because I tuned them to.{" "}
          <Link href="/methods">Methods</Link> explains each tier. Presets scored against law from before July 2025 say so
          in their <code>law_status</code> field, and Build&apos;s list prices are standalone scores that the site adds up
          rather than scoring jointly.
        </p>
        <p>
          The fingerprint covers each preset&apos;s two ten-year figures, Build&apos;s list prices and the baseline
          vintage. The year-by-year paths, published scores, labels and validation tiers in a snapshot are recorded as
          they stood when that fingerprint was first exported.
        </p>
      </section>

      <section className="reading" aria-labelledby="cite-head">
        <h2 id="cite-head">How to cite</h2>
        <p>
          For one figure, use the &ldquo;Cite as&rdquo; block on its <Link href="/explore">Explore</Link>,{" "}
          <Link href="/compare">Compare</Link> or <Link href="/build">Build</Link> page. It gives a one-line citation
          with the scores date in the link. If you use the API, please also give the snapshot id, which pins the exact
          figures. I release the data under CC BY 4.0, like the site&apos;s written content, and the code under MIT (see{" "}
          <Link href="/about">About</Link>).
        </p>
      </section>
    </>
  );
}
