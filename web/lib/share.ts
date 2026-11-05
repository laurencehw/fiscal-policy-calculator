// Share links and citations. Every link the site hands out carries
// `v=<scores date>`, the day the scored figures last changed (manifest.json's
// `scores_date`). A page opened from a link with an older `v` says the numbers
// have been recomputed since, rather than letting a reader think a figure they
// were sent is the one on screen. Classroom's frozen links keep their stricter
// refusal (lib/frozen.ts): a frozen link is an assignment, not a starting point.
import { identityLine, type EstimateIdentity } from "./identity";

const DATE = /^\d{4}-\d{2}-\d{2}$/;

/** The link's `v`, or "" when it has none or it is not a date. */
export function linkVersion(value: string | string[] | null | undefined): string {
  const text = (Array.isArray(value) ? value[0] : value ?? "").trim();
  return DATE.test(text) ? text : "";
}

/** `href` with `v=` set to the scores date. Works on a path with or without a query or a #fragment. */
export function withVersion(href: string, scoresDate: string): string {
  if (!DATE.test(scoresDate)) return href;
  const hashAt = href.indexOf("#");
  const hash = hashAt >= 0 ? href.slice(hashAt) : "";
  const rest = hashAt >= 0 ? href.slice(0, hashAt) : href;
  const queryAt = rest.indexOf("?");
  const path = queryAt >= 0 ? rest.slice(0, queryAt) : rest;
  const params = new URLSearchParams(queryAt >= 0 ? rest.slice(queryAt + 1) : "");
  params.set("v", scoresDate);
  return `${path}?${params.toString().replace(/%2C/gi, ",")}${hash}`;
}

const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

/** "2026-11-05" → "5 November 2026". */
export function longDate(iso: string): string {
  if (!DATE.test(iso)) return iso;
  const [y, m, d] = iso.split("-").map(Number);
  return `${d} ${MONTH_NAMES[m - 1]} ${y}`;
}

/**
 * The sentence an old link gets, or null when the link is current or carries
 * no version. A link from before the current scores date was made on figures
 * that have since been recomputed; one from after it (a link made on a newer
 * deployment) is treated the same way, since the figures still differ.
 */
export function staleNotice(v: string, scoresDate: string): string | null {
  if (!v || !DATE.test(scoresDate) || v === scoresDate) return null;
  return `This link was made on figures dated ${longDate(v)}. I recomputed the numbers on ${longDate(scoresDate)}, so what you see here may differ from what the sender saw.`;
}

export type Citation = { text: string; url: string };

/**
 * A citation built from the same identity as the figure's tag, so the two
 * never disagree about window, baseline or producer.
 */
export function citation(args: {
  title: string;
  identity: EstimateIdentity;
  path: string;
  scoresDate: string;
  site: string;
  author?: string;
}): Citation {
  const url = withVersion(`${args.site}${args.path}`, args.scoresDate);
  const author = args.author ?? "Wilse-Samson, Laurence";
  const dated = DATE.test(args.scoresDate) ? ` Figures dated ${longDate(args.scoresDate)}.` : "";
  const text = `${author}. "${args.title}." Fiscal Policy Calculator. ${identityLine(args.identity)}.${dated} ${url}`;
  return { text, url };
}
