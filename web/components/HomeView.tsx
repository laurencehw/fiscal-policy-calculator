// The home page for one pair of proposals. "/" renders the default pair at build
// time; "/?vs=<id>" is rewritten (next.config.ts) to /home/<id>, so the swap
// still works as a plain GET form with JavaScript off and every pair is cached.
import Link from "next/link";
import { Compare } from "@/components/Compare";
import { HomeSwap } from "@/components/HomeSwap";
import { presets } from "@/lib/data";
import { compareHref } from "@/lib/compare";
import { compareCards } from "@/lib/compareData";
import { HOME_TIER_NOTE, homeCandidates, homeRowLine, homeSectionParagraphs, STARTING_POINTS, trustStrip, workedRows } from "@/lib/home";

export function HomeView({ pair }: { pair: [string, string] }) {
  const rows = workedRows();
  const candidates = homeCandidates();
  const trust = trustStrip();
  return (
    <>
      <header>
        <h1>What would a policy do to the deficit?</h1>
        <p className="lede">
          Pick one of {presets().length} U.S. tax and spending proposals and see how much it would add to or cut from
          the federal deficit over the next ten years. Where an official estimate exists, it sits beside the
          calculator&apos;s, so you can see how close they are.
        </p>
        <nav className="actions homehero" aria-label="Start here">
          <Link href="/explore" className="button primary">
            Pick a proposal
          </Link>
          <Link href="/build">Build a package</Link>
        </nav>
      </header>

      <section className="homeexample" id="example" aria-label="Two proposals compared">
        <div className="homeexamplehead">
          <div className="note hometip">
            <span>Two proposals side by side.</span>
            <details className="whytip">
              <summary>Why these two?</summary>
              <p>{HOME_TIER_NOTE}</p>
            </details>
          </div>
          <HomeSwap first={pair[0]} second={pair[1]} options={candidates} />
        </div>
        <Compare cards={compareCards(pair)} />
        <p className="trust">
          {trust.text} <Link href="/methods">How the scores are checked</Link>
        </p>
        <nav className="actions homeactions" aria-label="Compare">
          <Link href={compareHref(pair)} className="primary">
            Compare these, or add a third
          </Link>
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
