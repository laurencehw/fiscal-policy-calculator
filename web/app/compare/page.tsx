import type { Metadata } from "next";
import Link from "next/link";
import { Compare, type CompareCard } from "@/components/Compare";
import { CompareSearch, type CompareOption } from "@/components/CompareSearch";
import { manifest, presets, presetsByArea } from "@/lib/data";
import { compareCards } from "@/lib/compareData";
import { CiteBlock } from "@/components/CiteBlock";
import { StaleLink } from "@/components/StaleLink";
import { citation } from "@/lib/share";
import { siteUrl } from "@/lib/site";
import { DEFAULT_PAIR, MAX_COMPARE, compareHref, droppedSentences, parseIds } from "@/lib/compare";
import { shortLabel } from "@/lib/format";
import { withoutTier } from "@/lib/identity";

export const metadata: Metadata = {
  title: "Compare",
  description: "Up to three proposals side by side: ten-year deficit effects, the year-by-year path on one axis, and the published scores.",
  alternates: { canonical: "/compare" },
};

export default async function ComparePage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const params = await searchParams;
  const index = presets();
  const known = new Set(index.map((info) => info.id));
  const parsed = parseIds(params.ids, known);
  const options: CompareOption[] = presetsByArea().flatMap((group) =>
    group.presets.map((info) => ({ id: info.id, name: shortLabel(info.name), area: group.area })),
  );
  const cards: CompareCard[] = compareCards(parsed.ids);
  const dropped = droppedSentences(parsed);
  const scoresDate = manifest().scores_date ?? "";
  // One citation for the page: the proposals by name, on the calculator's conventional
  // identity without a tier, since each card carries its own.
  const cite = cards.length
    ? citation({
        title: `Comparison of ${cards.map((card) => card.item.name).join("; ")}`,
        identity: withoutTier(cards[0].calculator),
        path: compareHref(cards.map((card) => card.item.id)),
        scoresDate,
        site: siteUrl(),
      })
    : null;
  const nameOf = (id: string) => options.find((option) => option.id === id)?.name ?? id;
  return (
    <div className="work">
      <header>
        <span className="eyebrow">Compare</span>
        <h1>Compare proposals</h1>
        <p className="sentence">
          Up to {MAX_COMPARE} proposals side by side. Every year-by-year chart uses the same axis, so bars of equal
          height are equal dollars. I never add the figures up: each is scored on its own.
        </p>
        <StaleLink scoresDate={scoresDate} />
      </header>

      {dropped.length ? (
        <div className="note dropped" role="status">
          {dropped.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </div>
      ) : null}

      <CompareSearch options={options} ids={parsed.ids} />

      {cards.length ? (
        <>
          <Compare cards={cards} />
          {cite ? <CiteBlock text={cite.text} /> : null}
        </>
      ) : (
        <p className="note">
          Pick a proposal above, or start from{" "}
          <Link href={compareHref([...DEFAULT_PAIR])}>
            {nameOf(DEFAULT_PAIR[0])} beside {nameOf(DEFAULT_PAIR[1])}
          </Link>
          , two figures read off the out-of-sample tier.
        </p>
      )}
    </div>
  );
}
