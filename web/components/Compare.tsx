// The Compare page's body: one card per proposal, each with a small multiple on
// the shared axis, then the difference line or the sentence saying why there is
// none. Server-rendered from site_data; only the picker needs JavaScript.
import Link from "next/link";
import { CompareChart } from "@/components/CompareChart";
import { EstimateTag } from "@/components/EstimateTag";
import { compareHref, difference, sharedAxis, toggleId, type CompareItem } from "@/lib/compare";
import { money } from "@/lib/format";
import type { EstimateIdentity } from "@/lib/identity";

export type CompareCard = {
  item: CompareItem;
  calculator: EstimateIdentity;
  published: { value: number; identity: EstimateIdentity; date: string | null } | null;
};

/** The tier and what it means, without saying the tier twice when the limitation already opens with it. */
function checkedAs(identity: EstimateIdentity): string {
  const tier = identity.tierLabel || "not benchmarked";
  const limit = identity.limitation.trim();
  if (!limit) return `${tier}.`;
  if (limit.toLowerCase().startsWith(tier.toLowerCase())) return limit;
  return `${tier}. ${limit}`;
}

export function Compare({ cards }: { cards: CompareCard[] }) {
  const items = cards.map((card) => card.item);
  const ids = items.map((item) => item.id);
  const axis = sharedAxis(items);
  const diff = difference(items);
  return (
    <>
      <div className={`comparegrid n${cards.length}`}>
        {cards.map(({ item, calculator, published }) => (
          <section className="comparecard chart" key={item.id} aria-labelledby={`cmp-${item.id}`}>
            <div className="head">
              <h2 id={`cmp-${item.id}`}>
                <Link href={`/explore/${item.id}`}>{item.name}</Link>
              </h2>
            </div>
            <div className="stage">
              <span className="q">Ten-year deficit effect, conventional</span>
              <span className={`v ${item.tenYear > 0 ? "adds" : "reduces"}`}>{money(item.tenYear)}</span>
              <EstimateTag identity={calculator} />
            </div>
            <CompareChart
              years={item.years}
              lo={axis.lo}
              hi={axis.hi}
              ticks={axis.ticks}
              label={`Annual deficit effect of ${item.name}, ${item.window}, on the axis shared by every proposal on this page`}
            />
            <dl className="comparefacts">
              <dt>Published</dt>
              <dd>
                {published ? (
                  <>
                    <span className="fig">{money(published.value)}</span> <EstimateTag identity={published.identity} />
                    {published.date ? <span className="tag"> {published.date}</span> : null}
                  </>
                ) : (
                  "No published score is carried for this proposal."
                )}
              </dd>
              <dt>Checked as</dt>
              <dd>
                {checkedAs(calculator)}
              </dd>
            </dl>
            <p className="foot">
              <a href={compareHref(toggleId(ids, item.id))}>Remove from comparison</a>
            </p>
          </section>
        ))}
      </div>
      <p className={diff.drawn ? "difference sentence" : "difference note"} id="difference">
        {diff.drawn ? diff.sentence : diff.reason}
      </p>
    </>
  );
}
