// Tailor's inputs, shared by the form, its ?query, and the /api/score route.
// The link format is the Streamlit app's /tailor contract
// (fiscal_model/ui/share_links.py), limited to what the engine's /score scores:
// an individual rate change above a threshold, a change to the rates on capital
// gains and qualified dividends above a threshold, or a corporate rate change.

export type TailorKind = "income" | "capital_gains" | "corporate";

const KINDS: TailorKind[] = ["income", "capital_gains", "corporate"];
const isKind = (v: unknown): v is TailorKind => typeof v === "string" && (KINDS as string[]).includes(v);

export type TailorInput = {
  kind: TailorKind;
  /** Percentage points; -10 to 10. */
  rate: number;
  /** Dollars of income above which the change applies; 0 for corporate. */
  who: number;
  /** Years the change lasts, 1 to 10. */
  duration: number;
  dynamic: boolean;
  /** Elasticity of taxable income (individual income tax only); defaults to 0.25. */
  eti?: number;
};

export const RATE_MIN = -10;
export const RATE_MAX = 10;
export const WHO_MAX = 10_000_000;
export const ETI_MIN = 0;
export const ETI_MAX = 0.8;
export const DEFAULT_ETI = 0.25;

export const WHO_CHOICES: { token: string; dollars: number; label: string }[] = [
  { token: "all", dollars: 0, label: "Everyone" },
  { token: "top50k", dollars: 50_000, label: "Above $50,000" },
  { token: "top100k", dollars: 100_000, label: "Above $100,000" },
  { token: "top200k", dollars: 200_000, label: "Above $200,000" },
  { token: "top400k", dollars: 400_000, label: "Above $400,000" },
  { token: "top500k", dollars: 500_000, label: "Above $500,000" },
  { token: "top1m", dollars: 1_000_000, label: "Above $1 million" },
];

export const DEFAULT_INPUT: TailorInput = { kind: "income", rate: 2.6, who: 400_000, duration: 10, dynamic: false };

const ALIASES: Record<string, number> = { everyone: 0, millionaires: 1_000_000 };

/** ?who= as the app reads it: an enum, a bare number, or 400k / $1M shorthand. */
export function parseWho(value: string | null): number | null {
  if (value === null) return null;
  let token = value.trim().toLowerCase().replace(/[$,+\s_-]/g, "");
  const named = WHO_CHOICES.find((c) => c.token === token);
  if (named) return named.dollars;
  if (token in ALIASES) return ALIASES[token];
  if (token.startsWith("top")) token = token.slice(3);
  const match = /^(\d+(?:\.\d+)?)([kmb]?)$/.exec(token);
  if (!match) return null;
  const amount = Number(match[1]) * { "": 1, k: 1e3, m: 1e6, b: 1e9 }[match[2] as "" | "k" | "m" | "b"];
  return amount >= 0 && amount <= WHO_MAX ? Math.floor(amount) : null;
}

function number(value: string | null): number | null {
  if (value === null) return null;
  const n = Number(value.replace(/%|pp|,/g, "").trim());
  return value.trim() !== "" && Number.isFinite(n) ? n : null;
}

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

/** Read a /tailor query. Each parameter decodes on its own; a bad one keeps the default. */
export function fromQuery(params: URLSearchParams): { input: TailorInput; run: boolean } {
  const input: TailorInput = { ...DEFAULT_INPUT };
  const type = params.get("type")?.trim().toLowerCase();
  if (isKind(type)) input.kind = type;
  const rate = number(params.get("rate"));
  if (rate !== null) input.rate = clamp(rate, RATE_MIN, RATE_MAX);
  const who = parseWho(params.get("who"));
  if (who !== null) input.who = who;
  const duration = number(params.get("duration"));
  if (duration !== null) input.duration = clamp(Math.trunc(duration), 1, 10);
  const dyn = params.get("dynamic");
  if (dyn !== null) input.dynamic = ["1", "true", "yes", "on"].includes(dyn.trim().toLowerCase());
  const eti = number(params.get("eti"));
  if (eti !== null && input.kind === "income") {
    const clamped = Math.round(clamp(eti, ETI_MIN, ETI_MAX) * 100) / 100;
    if (Math.abs(clamped - DEFAULT_ETI) > 1e-6) input.eti = clamped;
  }
  if (input.kind === "corporate") input.who = 0;
  if (input.kind !== "income") delete input.eti;
  const run = ["1", "true", "yes", "on"].includes((params.get("run") ?? "").trim().toLowerCase());
  return { input, run };
}

/** The link for an input, in the app's spelling, so it opens the same run in either. */
export function toQuery(input: TailorInput): string {
  const parts = [`type=${input.kind}`, `rate=${input.rate}`];
  if (input.kind !== "corporate") {
    parts.push(`who=${WHO_CHOICES.find((c) => c.dollars === input.who)?.token ?? String(input.who)}`);
    if (input.kind === "income" && input.eti !== undefined && Math.abs(input.eti - DEFAULT_ETI) > 1e-6) {
      parts.push(`eti=${input.eti}`);
    }
  }
  parts.push(`duration=${input.duration}`, `dynamic=${input.dynamic ? 1 : 0}`, "run=1");
  return parts.join("&");
}

/** Check a request body from the browser; return the input or a reason it was refused. */
export function validate(body: unknown): TailorInput | string {
  if (!body || typeof body !== "object") return "Expected a JSON object.";
  const b = body as Record<string, unknown>;
  if (!isKind(b.kind)) return "kind must be income, capital_gains or corporate.";
  const nums = { rate: b.rate, who: b.who, duration: b.duration };
  for (const [key, value] of Object.entries(nums)) {
    if (typeof value !== "number" || !Number.isFinite(value)) return `${key} must be a number.`;
  }
  const rate = b.rate as number;
  const who = b.who as number;
  const duration = b.duration as number;
  if (rate < RATE_MIN || rate > RATE_MAX) return `rate must be between ${RATE_MIN} and ${RATE_MAX} points.`;
  if (rate === 0) return "rate must not be zero.";
  if (who < 0 || who > WHO_MAX) return "who must be between 0 and 10,000,000.";
  if (b.kind === "corporate" && who !== 0) return "A corporate rate change has no income threshold.";
  if (!Number.isInteger(duration) || duration < 1 || duration > 10) return "duration must be 1 to 10 years.";
  const kind: TailorKind = b.kind;
  const out: TailorInput = { kind, rate, who, duration, dynamic: b.dynamic === true };
  if (b.eti !== undefined) {
    if (typeof b.eti !== "number" || !Number.isFinite(b.eti)) return "eti must be a number.";
    if (b.eti < ETI_MIN || b.eti > ETI_MAX) return `eti must be between ${ETI_MIN} and ${ETI_MAX}.`;
    if (b.kind === "income" && Math.abs(b.eti - DEFAULT_ETI) > 1e-6) {
      out.eti = Math.round(b.eti * 100) / 100;
    }
  }
  return out;
}

/** A short name for the run, used as the engine's policy name and the page heading. */
export function describe(input: TailorInput): string {
  const sign = input.rate > 0 ? "+" : "";
  const pts = `${sign}${input.rate} point${Math.abs(input.rate) === 1 ? "" : "s"}`;
  if (input.kind === "corporate") return `Corporate rate ${pts}`;
  const who = WHO_CHOICES.find((c) => c.dollars === input.who);
  const above = input.who === 0 ? "on all taxable income" : `above $${input.who.toLocaleString("en-US")}`;
  if (input.kind === "capital_gains") {
    return `Capital gains and dividends rate ${pts} ${input.who === 0 ? "for everyone" : `above $${input.who.toLocaleString("en-US")}`}`;
  }
  return `Income tax ${pts} ${who && input.who === 0 ? "for everyone" : above}`;
}

/** The engine's /score request body for an input. */
export function engineRequest(input: TailorInput): Record<string, unknown> {
  return {
    name: describe(input),
    description: `${describe(input)}, for ${input.duration} year${input.duration === 1 ? "" : "s"}.`,
    rate_change: Math.round(input.rate * 1e6) / 1e8,
    income_threshold: input.kind === "corporate" ? 0 : input.who,
    elasticity: input.kind === "income" ? (input.eti ?? DEFAULT_ETI) : DEFAULT_ETI,
    duration_years: input.duration,
    dynamic: true,
    policy_type: { income: "income_tax", capital_gains: "capital_gains_tax", corporate: "corporate_tax" }[input.kind],
  };
}
