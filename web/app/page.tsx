import Link from "next/link";
import { manifest, presets } from "@/lib/data";
import { homeRowLine, homeSectionParagraphs, workedRows } from "@/lib/home";

export default function Home() {
  const m = manifest();
  const rows = workedRows();
  return (
    <>
      <header>
        <h1>What a proposal does to the deficit</h1>
        <p className="lede">
          A ten-year estimate on CBO&apos;s {m.baseline_vintages.join(" and ")} baseline.{" "}
          <Link href="/explore">Explore {presets().length} proposals</Link>, each with this calculator&apos;s
          conventional score and, where one exists, the published score beside it.
        </p>
      </header>
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
