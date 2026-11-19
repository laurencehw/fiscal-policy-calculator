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

export type Citation = {
  /** The one-line citation the page prints and "Copy citation" copies. */
  text: string;
  url: string;
  /** The same reference as a BibTeX @misc entry, for LaTeX and Zotero. */
  bibtex: string;
  /** The same reference as RIS, for EndNote, Mendeley and Zotero. */
  ris: string;
  /** A file name stem for the .bib and .ris downloads. */
  fileStem: string;
};

/**
 * A citation built from the same identity as the figure's tag, so the two
 * never disagree about window, baseline or producer. The BibTeX and RIS forms
 * carry the same title, link, figures date and tag as the one-line text.
 */
export function citation(args: {
  title: string;
  identity: EstimateIdentity;
  path: string;
  scoresDate: string;
  site: string;
  author?: string;
  /** A DOI for the data release these figures belong to, when there is one. */
  doi?: string;
}): Citation {
  const url = withVersion(`${args.site}${args.path}`, args.scoresDate);
  const author = args.author ?? "Wilse-Samson, Laurence";
  const dated = DATE.test(args.scoresDate) ? ` Figures dated ${longDate(args.scoresDate)}.` : "";
  const doi = (args.doi ?? "").trim();
  const doiPart = doi ? ` doi:${doi}.` : "";
  const tag = identityLine(args.identity);
  const text = `${author}. "${args.title}." Fiscal Policy Calculator. ${tag}.${dated}${doiPart} ${url}`;
  const note = `${tag}.${dated}`;
  const fileStem = citationStem(args.title);
  return {
    text,
    url,
    bibtex: bibtexEntry({ author, title: args.title, url, note, doi, scoresDate: args.scoresDate, key: citationKey(author, args.title, args.scoresDate) }),
    ris: risRecord({ author, title: args.title, url, note, doi, scoresDate: args.scoresDate }),
    fileStem,
  };
}

/** "Top Rate to 45%" → "top-rate-to-45". */
export function citationStem(title: string): string {
  const stem = asciiFold(title)
    .replace(/[^A-Za-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .toLowerCase()
    .slice(0, 60)
    .replace(/-$/, "");
  return stem || "citation";
}

/** A BibTeX key: author surname, year, and the first three words of the title. */
export function citationKey(author: string, title: string, scoresDate: string): string {
  const surname = asciiFold(author.split(",")[0]).replace(/[^A-Za-z]/g, "").toLowerCase() || "anon";
  const year = DATE.test(scoresDate) ? scoresDate.slice(0, 4) : "nd";
  const words = asciiFold(title)
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((word) => word.length > 0 && !STOP_WORDS.has(word))
    .slice(0, 3)
    .join("");
  return `${surname}${year}${words}`;
}

const STOP_WORDS = new Set(["a", "an", "the", "of", "to", "and", "for", "on", "in"]);

function asciiFold(text: string): string {
  return text.normalize("NFKD").replace(/[\u0300-\u036f]/g, "");
}

/** BibTeX's special characters, escaped so a title like "Top Rate to 45%" compiles. */
export function bibtexEscape(text: string): string {
  // One pass, so the braces a replacement adds are never escaped again.
  return text.replace(/[\\{}%&$#_~^]/g, (ch) => BIBTEX_ESCAPES[ch] ?? ch);
}

const BIBTEX_ESCAPES: Record<string, string> = {
  "\\": "\\textbackslash{}",
  "~": "\\textasciitilde{}",
  "^": "\\textasciicircum{}",
  "{": "\\{",
  "}": "\\}",
  "%": "\\%",
  "&": "\\&",
  $: "\\$",
  "#": "\\#",
  _: "\\_",
};

function bibtexEntry(args: { key: string; author: string; title: string; url: string; note: string; doi: string; scoresDate: string }): string {
  const fields: [string, string][] = [
    // Double braces keep the title's capitals as written.
    ["author", `{${bibtexEscape(args.author)}}`],
    ["title", `{{${bibtexEscape(args.title)}}}`],
    ["howpublished", "{Fiscal Policy Calculator}"],
  ];
  if (DATE.test(args.scoresDate)) {
    const [y, m] = args.scoresDate.split("-").map(Number);
    fields.push(["year", `{${y}}`], ["month", MONTH_KEYS[m - 1]], ["date", `{${args.scoresDate}}`]);
  }
  if (args.doi) fields.push(["doi", `{${bibtexEscape(args.doi)}}`]);
  // \url{} would need the url package; a bare url field is what biblatex and Zotero read.
  fields.push(["url", `{${args.url}}`], ["note", `{${bibtexEscape(args.note)}}`]);
  const body = fields.map(([name, value]) => `  ${name} = ${value}`).join(",\n");
  return `@misc{${args.key},\n${body}\n}\n`;
}

const MONTH_KEYS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];

function risRecord(args: { author: string; title: string; url: string; note: string; doi: string; scoresDate: string }): string {
  const line = (tag: string, value: string) => `${tag}  - ${value.replace(/[\r\n]+/g, " ")}`;
  const lines = [line("TY", "ELEC"), line("AU", args.author), line("TI", args.title), line("T2", "Fiscal Policy Calculator")];
  if (DATE.test(args.scoresDate)) {
    lines.push(line("PY", args.scoresDate.slice(0, 4)), line("DA", args.scoresDate.replace(/-/g, "/")));
  }
  if (args.doi) lines.push(line("DO", args.doi));
  lines.push(line("UR", args.url), line("N1", args.note), "ER  - ");
  // RIS records end each line with CRLF.
  return `${lines.join("\r\n")}\r\n`;
}
