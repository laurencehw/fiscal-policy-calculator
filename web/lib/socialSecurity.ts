// Social Security trust fund ledger, a line-for-line port of
// fiscal_model/social_security/trust_fund.py. The rates are transcribed (2026
// Trustees Report and OCACT's provision tables, via site_data/social-security.json);
// only the ledger runs here. lib/socialSecurity.test.ts checks it against the
// Python ledger's own answers, which the export carries.

export type SSBaselineYear = { year: number; income_rate: number; cost_rate: number; taxable_payroll: number; interest_factor: number };

export type SSProvision = {
  provision_id: string;
  ocact_run: string;
  category: string;
  exclusive_group: string;
  label: string;
  description: string;
  ocact_change_actuarial_balance: number;
  ocact_depletion_year: number | null;
  source_url: string;
  /** Change from current law, percent of taxable payroll, first_year .. last_year + 1. */
  change_cost_rate: number[];
  change_income_rate: number[];
};

export type SSCheck = {
  provision_ids: string[];
  depletion_year: number | null;
  payable_at_depletion: number | null;
  change_in_actuarial_balance: number;
  computed_actuarial_balance: number;
  trust_fund_ratio: number[];
};

export type SSData = {
  first_year: number;
  last_year: number;
  reserves_end_2025: number;
  baseline_cost_rate_2101: number;
  trustees: { actuarial_balance: number; oasdi_depletion_year: number; oasdi_payable_pct: number; oasi_depletion: string; oasi_payable_pct: number };
  baseline: SSBaselineYear[];
  categories: Record<string, string>;
  provisions: SSProvision[];
  crfb: { crfb_item: string; measure: string; crfb: string; ours: string; our_basis: string; note: string; source_url: string }[];
  checks: SSCheck[];
};

export type SSProjection = {
  provisionIds: string[];
  years: number[];
  incomeRate: number[];
  costRate: number[];
  reservesEnd: number[];
  trustFundRatio: number[];
  depletionYear: number | null;
  payableAtDepletion: number | null;
  computedActuarialBalance: number;
  changeInActuarialBalance: number;
  /** The Trustees' published balance plus this plan's change. */
  actuarialBalance: number;
  /** Fraction of the 75-year shortfall closed (1 = 75-year balance). */
  shareClosed: number;
  /** The cut needed at depletion: 1 − income ÷ cost that year. */
  cutAtDepletion: number | null;
};

/** Catalog order, unknown ids dropped; picking a second setting of one lever replaces the first. */
export function selectOption(data: SSData, selected: string[], id: string): string[] {
  const byId = new Map(data.provisions.map((p) => [p.provision_id, p]));
  const p = byId.get(id);
  if (!p) return selected;
  if (selected.includes(id)) return selected.filter((x) => x !== id);
  const kept = selected.filter((x) => !p.exclusive_group || byId.get(x)?.exclusive_group !== p.exclusive_group);
  return orderIds(data, [...kept, id]);
}

export function orderIds(data: SSData, ids: Iterable<string>): string[] {
  const chosen = new Set(ids);
  const out: string[] = [];
  const groups = new Set<string>();
  for (const p of data.provisions) {
    if (!chosen.has(p.provision_id)) continue;
    if (p.exclusive_group && groups.has(p.exclusive_group)) continue;
    if (p.exclusive_group) groups.add(p.exclusive_group);
    out.push(p.provision_id);
  }
  return out;
}

function yearEndFactors(factors: number[]): number[] {
  const n = factors.length;
  const ext = [...factors, (factors[n - 1] * factors[n - 1]) / factors[n - 2]];
  return factors.map((_, k) => Math.sqrt(ext[k] * ext[k + 1]));
}

function run(data: SSData, ids: string[]): Omit<SSProjection, "changeInActuarialBalance" | "actuarialBalance" | "shareClosed"> {
  const chosen = data.provisions.filter((p) => ids.includes(p.provision_id));
  const rows = data.baseline.filter((r) => r.year >= data.first_year - 1 && r.year <= data.last_year);
  const yearEnd = yearEndFactors(rows.map((r) => r.interest_factor));
  const window = rows.slice(1);
  const at = (y: number) => y - data.first_year;

  const years: number[] = [];
  const income: number[] = [];
  const cost: number[] = [];
  const reserves: number[] = [];
  const ratios: number[] = [];
  let reserve = data.reserves_end_2025;
  let pvBalance = 0;
  let pvPayroll = 0;
  window.forEach((row, i) => {
    const k = i + 1;
    const inc = row.income_rate + chosen.reduce((s, p) => s + p.change_income_rate[at(row.year)], 0);
    const cst = row.cost_rate + chosen.reduce((s, p) => s + p.change_cost_rate[at(row.year)], 0);
    const payroll = row.taxable_payroll;
    ratios.push((Math.max(reserve, 0) / ((cst / 100) * payroll)) * 100);
    reserve = (reserve * yearEnd[k]) / yearEnd[k - 1] + (((inc - cst) / 100) * payroll * yearEnd[k]) / row.interest_factor;
    pvBalance += ((inc - cst) / 100) * payroll / row.interest_factor;
    pvPayroll += payroll / row.interest_factor;
    years.push(row.year);
    income.push(inc);
    cost.push(cst);
    reserves.push(reserve);
  });

  const k = reserves.findIndex((r) => r < 0);
  const depletionYear = k >= 0 ? years[k] : null;
  const payableAtDepletion = k >= 0 ? income[k] / cost[k] : null;

  const last = window[window.length - 1].taxable_payroll;
  const prev = window[window.length - 2].taxable_payroll;
  const payroll2101 = (last * last) / prev;
  const cost2101 = data.baseline_cost_rate_2101 + chosen.reduce((s, p) => s + p.change_cost_rate[at(data.last_year + 1)], 0);
  const endingTarget = ((cost2101 / 100) * payroll2101) / yearEnd[yearEnd.length - 1];
  const balance = ((data.reserves_end_2025 + pvBalance - endingTarget) / pvPayroll) * 100;

  return {
    provisionIds: ids,
    years,
    incomeRate: income,
    costRate: cost,
    reservesEnd: reserves,
    trustFundRatio: ratios,
    depletionYear,
    payableAtDepletion,
    computedActuarialBalance: balance,
    cutAtDepletion: payableAtDepletion === null ? null : 1 - payableAtDepletion,
  };
}

/** The ledger for current law plus the given OCACT options (added without interactions). */
export function project(data: SSData, provisionIds: string[] = []): SSProjection {
  const ids = orderIds(data, provisionIds);
  const plan = run(data, ids);
  const base = ids.length ? run(data, []).computedActuarialBalance : plan.computedActuarialBalance;
  const change = plan.computedActuarialBalance - base;
  return {
    ...plan,
    changeInActuarialBalance: change,
    actuarialBalance: data.trustees.actuarial_balance + change,
    shareClosed: change / -data.trustees.actuarial_balance,
  };
}
