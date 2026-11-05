import Link from "next/link";
import { Compare } from "@/components/Compare";
import { HomeSwap } from "@/components/HomeSwap";
import { manifest, presets } from "@/lib/data";
import { compareHref } from "@/lib/compare";
import { compareCards } from "@/lib/compareData";
import { homeCandidates, homePair, homeRowLine, homeSectionParagraphs, STARTING_POINTS, trustStrip, workedRows } from "@/lib/home";

export default async function Home({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const params = await searchParams;
  const m = manifest();
  const rows = workedRows();
  const pair = homePair(params.vs);
  const candidates = homeCandidates();
  const trust = trustStrip();
  return (
    <>
      <header>
        <h1>What a proposal does to the deficit</h1>
        <p className="lede">
          Ten-year estimates of {presets().length} U.S. tax and spending proposals on CBO&apos;s{" "}
          {m.baseline_vintages.join(" and ")} baseline. Each shows this calculator&apos;s score and, where one exists, the
          published score it is checked against.
        </p>
      </header>

      <section className="homeexample" id="example" aria-label="Two proposals compared">
        <div className="homeexamplehead">
          <p className="note">
            Two proposals side by side. Both read off the out-of-sample tier, so neither agrees with a published score by
            construction.
          </p>
          <HomeSwap first={pair[0]} second={pair[1]} options={candidates} />
        </div>
        <Compare cards={compareCards(pair)} />
        <p className="trust">
          {trust.text} <Link href="/methods">How the scores are checked</Link>
        </p>
        <nav className="actions homeactions" aria-label="Start">
          <Link href={compareHref(pair)} className="primary">
            Compare policies
          </Link>
          <Link href="/build">Build a package</Link>
        </nav>
      </section>

      <section className="starts" aria-label="Starting points">
        {STARTING_POINTS.map((start) => (
          <Link key={start.href} href={start.href} className="door">
            <b>{start.question}</b>
            <span>{start.answer}</span>
          </Link>
        ))}
      </section>

      <section className="reading">
        <h2>How to read a figure</h2>
        {homeSectionParagraphs().map((text) => (
          <p key={text}>{text}</p>
        ))}
        <ul>
          {rows.map((row) => (
            <li key={row.id}>
              <Link href={row.href}>{row.name}</Link>
              {homeRowLine(row).slice(row.name.length)}
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
