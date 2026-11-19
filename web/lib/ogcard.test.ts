import { test } from "node:test";
import assert from "node:assert/strict";
import { preset, presets } from "./data";
import { currentLawFigure } from "./lawStatus";
import { ogCard } from "./ogcard";
import { money } from "./format";

const cardFor = (id: string) => {
  const info = presets().find((row) => row.id === id)!;
  const file = preset(id)!;
  const lawNow = currentLawFigure(info.status, (other) => preset(other)?.conventional.ten_year_deficit_impact ?? null);
  const sameAs = info.status?.pre_2025_law ? info.status.current_law?.same_as : null;
  const bars = sameAs ? preset(sameAs)!.conventional.year_by_year.map((row) => row.final_effect) : [];
  return { info, file, card: ogCard(file.conventional, info, lawNow, bars) };
};

test("every proposal's card leads with the figure its page leads with", () => {
  for (const info of presets()) {
    const { file, card } = cardFor(info.id);
    assert.ok(card.name.length > 0, info.id);
    assert.doesNotMatch(`${card.figure} ${card.measures} ${card.aside}`, /undefined|NaN|null/, info.id);
    if (!info.status?.pre_2025_law || !info.status.current_law || info.status.current_law.kind === "not_computed") {
      assert.equal(card.figure, money(file.conventional.ten_year_deficit_impact), info.id);
    }
    // An unpublished reference figure is never printed as a published score.
    if (!info.cbo_published) assert.doesNotMatch(card.aside, /^Published score/, info.id);
  }
});

test("a proposal that is already law shows $0 on current law and the pre-2025 figure beneath", () => {
  const { file, card } = cardFor("tcja-full-extension");
  assert.equal(card.figure, "$0");
  assert.equal(card.bars.length, 0);
  assert.equal(card.aside, `Against pre-2025 law: ${money(file.conventional.ten_year_deficit_impact)}`);
});

test("a same-as proposal draws the other proposal's path, not its own pre-2025 one", () => {
  const { info, card } = cardFor("tcja-extension-no-salt-cap");
  const other = preset(info.status!.current_law!.same_as!)!.conventional;
  assert.equal(card.figure, money(other.ten_year_deficit_impact));
  assert.deepEqual(card.bars, other.year_by_year.map((row) => row.final_effect));
});
