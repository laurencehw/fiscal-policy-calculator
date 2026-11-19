import { test } from "node:test";
import assert from "node:assert/strict";
import { preset, presets, views } from "./data";
import { currentLawFigure } from "./lawStatus";
import { checkClause, incomeFloor, roughMoney, sizeClause, takeaway, whoClause } from "./takeaway";
import type { Credibility, DistGrouping } from "./types";

const group = (floor: number, share: number) => ({
  name: `${floor}`,
  floor,
  ceiling: null,
  returns_millions: 1,
  avg_tax_change: 0,
  pct_of_income: 0,
  share_of_total: share,
  pct_with_increase: 0,
  pct_with_decrease: 0,
  baseline_etr: 0,
  new_etr: 0,
});
const table = (total: number, shares: [number, number][]): DistGrouping => ({
  engine: "microsim",
  unit: "tax_unit",
  year: 2026,
  total_tax_change_billions: total,
  pct_with_increase: 0,
  pct_with_decrease: 0,
  groups: shares.map(([f, s]) => group(f, s)),
});
const cred = (over: Partial<Credibility>): Credibility => ({
  category: "Generic",
  evidence_type: "",
  class_label: null,
  n_tier1_rows: 0,
  mean_abs_pct_error: null,
  max_abs_pct_error: null,
  uncertainty_low: null,
  uncertainty_high: null,
  outer_low: null,
  outer_high: null,
  no_band_reason: "",
  own_row_tier: null,
  own_row_tier_label: null,
  own_row_abs_pct_error: null,
  own_row_official_billions: null,
  own_row_caption: "",
  limitations: [],
  caption: "",
  ...over,
});

test("sizes read as a yearly average without a sign", () => {
  assert.equal(roughMoney(-1036.7), "$1.0T");
  assert.equal(roughMoney(103.7), "$104B");
  assert.equal(roughMoney(-6.06), "$6.1B");
  assert.equal(incomeFloor(1_000_000), "$1M");
  assert.equal(incomeFloor(200_000), "$200K");
  const years = Array.from({ length: 10 }, (_, i) => ({ year: 2026 + i }) as never);
  assert.equal(sizeClause({ ten_year_deficit_impact: -1036.7, year_by_year: years }), "Cuts the deficit by about $104B a year");
  assert.equal(sizeClause({ ten_year_deficit_impact: 600, year_by_year: years }), "Adds about $60B a year to the deficit");
  assert.equal(sizeClause({ ten_year_deficit_impact: 0, year_by_year: years }), "Leaves the deficit about where it is");
});

test("who pays names the fewest top bands holding three quarters of the change", () => {
  const top = table(64, [[0, 0], [500_000, 0.107], [1_000_000, 0.893]]);
  assert.equal(whoClause(top), "about 89% of it paid by people with incomes over $1M");
  const cut = table(-460, [[50_000, 0.1], [100_000, 0.4], [200_000, 0.2], [500_000, 0.1], [1_000_000, 0.2]]);
  assert.equal(whoClause(cut), "about 90% of it going to people with incomes over $100K");
  // Three quarters reached only at $50K: no floor worth naming.
  assert.equal(whoClause(table(-460, [[50_000, 0.3], [100_000, 0.3], [200_000, 0.4]])), "");
  assert.equal(whoClause(table(100, [[0, 0.5], [50_000, 0.5]])), "");
  // Bands pulling in opposite directions: say nothing.
  assert.equal(whoClause(table(10, [[200_000, -0.4], [1_000_000, 1.4]])), "");
  assert.equal(whoClause(undefined), "");
});

test("the check clause is honest about fitted, unpublished and class-only figures", () => {
  assert.match(checkClause(cred({ own_row_tier: "fitted", own_row_official_billions: -800, own_row_abs_pct_error: 0 })), /agree by design/);
  assert.match(
    checkClause(cred({ own_row_tier: "out_of_sample", own_row_official_billions: -245.9, own_row_abs_pct_error: 24.8 })),
    /about 25% off the published score of -\$245\.9B\.$/,
  );
  assert.match(
    checkClause(cred({ own_row_tier: "reconstruction", own_row_official_billions: -60, own_row_abs_pct_error: 258 })),
    /a large miss/,
  );
  assert.match(
    checkClause(cred({ own_row_tier: "reconstruction", own_row_official_billions: -500, own_row_abs_pct_error: 93 }), false),
    /not a published estimate/,
  );
  assert.match(
    checkClause(cred({ class_label: "ordinary rate change", n_tier1_rows: 11, mean_abs_pct_error: 15 })),
    /income tax rate changes\), this calculator has missed published scores by about 15% on average/,
  );
  assert.equal(checkClause(null), "There is no published score to check it against.");
});

test("every preset gets a takeaway built only from figures on its page", () => {
  for (const info of presets()) {
    const file = preset(info.id);
    assert.ok(file, info.id);
    const lawNow = currentLawFigure(info.status, (other) => preset(other)?.conventional.ten_year_deficit_impact ?? null);
    const text = takeaway({
      c: file.conventional,
      table: views(info.id)?.distribution.groupings.jct_dollar,
      status: info.status,
      currentLaw: lawNow,
      isPublished: info.cbo_published !== false,
    });
    assert.ok(text.length > 30 && text.length < 260, `${info.id}: ${text}`);
    assert.doesNotMatch(text, /undefined|NaN|null/, info.id);
    if (info.status?.pre_2025_law && info.status.current_law) assert.match(text, /P\.L\. 119-21/, info.id);
    // An unpublished reference figure is never called a published score.
    if (info.cbo_published === false) assert.doesNotMatch(text, /off the published score|calibrated to a published/, info.id);
  }
});

test("the top-rate page opens the way the review asked", () => {
  const file = preset("top-rate-45");
  assert.ok(file);
  const text = takeaway({ c: file.conventional, table: views("top-rate-45")?.distribution.groupings.jct_dollar });
  assert.match(text, /^Cuts the deficit by about \$\d+B a year, .* paid by people with incomes over \$1M\./);
});
