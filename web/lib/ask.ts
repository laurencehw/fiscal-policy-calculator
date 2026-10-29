// Ask: request checks, the server-sent event reader, and the answer's own
// small markdown (paragraphs, lists, bold, links, [^N] citations, a Sources
// list). Parsed to plain data so the page renders it without raw HTML.

export type Turn = { role: "user" | "assistant"; content: string };

export type AskInput = { question: string; history: Turn[] };

export const QUESTION_MAX = 2000;
const HISTORY_TURNS_MAX = 20;
const HISTORY_CHARS_MAX = 8000;

export function validateAsk(body: unknown): AskInput | string {
  if (!body || typeof body !== "object") return "Expected an object.";
  const b = body as Record<string, unknown>;
  if (typeof b.question !== "string" || !b.question.trim()) return "Type a question first.";
  if (b.question.length > QUESTION_MAX) return `Questions are limited to ${QUESTION_MAX} characters.`;
  const history: Turn[] = [];
  if (b.history !== undefined) {
    if (!Array.isArray(b.history)) return "History must be a list.";
    if (b.history.length > HISTORY_TURNS_MAX * 2) return "This conversation is too long. Start a new one.";
    for (const t of b.history) {
      if (!t || typeof t !== "object") return "Bad history entry.";
      const { role, content } = t as Record<string, unknown>;
      if ((role !== "user" && role !== "assistant") || typeof content !== "string") return "Bad history entry.";
      history.push({ role, content: content.slice(0, HISTORY_CHARS_MAX) });
    }
  }
  return { question: b.question.trim(), history };
}

/** The first address in X-Forwarded-For, which Vercel sets to the visitor's. */
export function clientAddress(forwardedFor: string | null, realIp: string | null): string {
  const first = (forwardedFor ?? "").split(",")[0]?.trim();
  return first || (realIp ?? "").trim() || "unknown";
}

// ---- Server-sent events ----

export type SseFrame = { event: string; data: string };

/** Split a buffer into complete frames; the rest waits for more bytes. */
export function readFrames(buffer: string): { frames: SseFrame[]; rest: string } {
  const frames: SseFrame[] = [];
  const parts = buffer.replace(/\r\n/g, "\n").split("\n\n");
  const rest = parts.pop() ?? "";
  for (const part of parts) {
    let event = "message";
    const data: string[] = [];
    for (const line of part.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) data.push(line.slice(5).startsWith(" ") ? line.slice(6) : line.slice(5));
    }
    if (data.length || event !== "message") frames.push({ event, data: data.join("\n") });
  }
  return { frames, rest };
}

// ---- The answer's markdown ----

export type Inline =
  | { t: "text"; v: string }
  | { t: "b"; v: string }
  | { t: "i"; v: string }
  | { t: "code"; v: string }
  | { t: "link"; v: string; href: string }
  | { t: "cite"; n: number; href?: string };

export type Block =
  | { t: "h"; v: Inline[] }
  | { t: "p"; v: Inline[] }
  | { t: "quote"; v: Inline[] }
  | { t: "math"; v: string }
  | { t: "hr" }
  | { t: "ul" | "ol"; items: Inline[][] };

export type Source = { n: number; text: string; href?: string };

export type Answer = { blocks: Block[]; sources: Source[] };

const SOURCES_HEADING = /^\s*(?:#{2,}\s*Sources|\*\*Sources\*\*)\s*$/m;
const SOURCE_ENTRY = /^\s*\[\^(\d+)\]:\s*(.*)$/gm;
const URL_RE = /https?:\/\/[^\s)\]}>"']+/;

export function safeHref(url: string): string | undefined {
  try {
    const u = new URL(url);
    return u.protocol === "https:" || u.protocol === "http:" ? u.toString() : undefined;
  } catch {
    return undefined;
  }
}

/** The engine escapes every dollar sign (a backslash before it) so Streamlit won't read it as math. */
export function unescapeDollars(text: string): string {
  return text.replace(/\\\$/g, "$");
}

const SYMBOLS: Record<string, string> = {
  Delta: "Δ", delta: "δ", times: "×", cdot: "·", approx: "≈", le: "≤", leq: "≤", ge: "≥", geq: "≥",
  ne: "≠", neq: "≠", pm: "±", alpha: "α", beta: "β", gamma: "γ", sigma: "σ", tau: "τ", pi: "π",
  rho: "ρ", epsilon: "ε", varepsilon: "ε", eta: "η", theta: "θ", lambda: "λ", mu: "μ", sum: "Σ",
  to: "→", rightarrow: "→", infty: "∞", left: "", right: "", quad: " ", qquad: " ",
};

/** LaTeX from a ``$$...$$`` block as readable plain text: fractions as a / b, Greek letters as symbols. */
export function plainMath(tex: string): string {
  let s = tex.trim();
  const group = (v: string) => (/^[\w.ΔΣ]+$/u.test(v.trim()) ? v.trim() : `(${v.trim()})`);
  for (let i = 0; i < 10; i++) {
    const before = s;
    s = s.replace(/\\(?:text|mathrm|mathit|textbf|operatorname)\{([^{}]*)\}/g, "$1");
    s = s.replace(/\\[dt]?frac\{([^{}]*)\}\{([^{}]*)\}/g, (_m, a: string, b: string) => `${group(a)} / ${group(b)}`);
    if (s === before) break;
  }
  s = s.replace(/\\([A-Za-z]+)/g, (_m, name: string) => (name in SYMBOLS ? SYMBOLS[name] : name));
  s = s.replace(/\\([%$&#_,;!])/g, (_m, c: string) => (c === "," || c === ";" || c === "!" ? " " : c));
  s = s.replace(/[{}]/g, "").replace(/\s+/g, " ");
  return s.trim();
}

function inline(text: string, sources: Map<number, Source>, final: boolean): Inline[] {
  const out: Inline[] = [];
  const pattern = /\[\^(\d+)\]|\*\*([^*]+)\*\*|`([^`]+)`|\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)|(https?:\/\/[^\s)\]}>"']+)|(?<![*\w])\*(?![\s*])([^*\n]+?)(?<!\s)\*(?![*\w])/g;
  let last = 0;
  for (const m of text.matchAll(pattern)) {
    const at = m.index ?? 0;
    if (at > last) out.push({ t: "text", v: text.slice(last, at) });
    last = at + m[0].length;
    if (m[1]) {
      const n = Number(m[1]);
      const source = sources.get(n);
      // A marker with no Sources entry carries nothing to follow, once the answer is complete.
      if (source || !final) out.push({ t: "cite", n, href: source?.href });
    } else if (m[2]) out.push({ t: "b", v: m[2] });
    else if (m[3]) out.push({ t: "code", v: m[3] });
    else if (m[4] && m[5]) {
      const href = safeHref(m[5]);
      out.push(href ? { t: "link", v: m[4], href } : { t: "text", v: m[4] });
    } else if (m[6]) {
      const href = safeHref(m[6]);
      out.push(href ? { t: "link", v: m[6], href } : { t: "text", v: m[6] });
    } else if (m[7]) out.push({ t: "i", v: m[7] });
  }
  if (last < text.length) out.push({ t: "text", v: text.slice(last) });
  return out;
}

/** Parse an answer, streaming (``final`` false) or complete. */
export function parseAnswer(raw: string, final = true): Answer {
  // Display math first: once the escapes are gone, a currency sign and a math delimiter look alike.
  const maths: string[] = [];
  const text = unescapeDollars(
    raw.replace(/(?<!\\)\$\$([\s\S]+?)(?<!\\)\$\$/g, (_m, tex: string) => {
      maths.push(plainMath(tex));
      return `\n\n\u0000MATH${maths.length - 1}\u0000\n\n`;
    }),
  );
  const heading = SOURCES_HEADING.exec(text);
  const body = heading ? text.slice(0, heading.index) : text;
  const tail = heading ? text.slice(heading.index + heading[0].length) : "";

  const sources = new Map<number, Source>();
  for (const m of tail.matchAll(SOURCE_ENTRY)) {
    const entry = m[2].trim();
    const url = URL_RE.exec(entry)?.[0];
    sources.set(Number(m[1]), { n: Number(m[1]), text: entry, href: url ? safeHref(url) : undefined });
  }
  // Notes the server appends after Sources (a cut-off answer, stripped citations) stay visible.
  const notes = tail
    .split("\n")
    .filter((l) => l.trimStart().startsWith(">"))
    .join("\n");

  const blocks: Block[] = [];
  const lines = `${body.trimEnd()}${notes ? `\n\n${notes}` : ""}`.split("\n");
  let para: string[] = [];
  let list: { t: "ul" | "ol"; items: string[] } | null = null;
  const flush = () => {
    if (para.length) blocks.push({ t: "p", v: inline(para.join(" "), sources, final) });
    para = [];
    if (list) blocks.push({ t: list.t, items: list.items.map((i) => inline(i, sources, final)) });
    list = null;
  };
  for (const raw of lines) {
    const line = raw.trimEnd();
    const bullet = /^\s*[-*•]\s+(.*)$/.exec(line);
    const numbered = /^\s*\d+[.)]\s+(.*)$/.exec(line);
    const head = /^\s*#{1,6}\s+(.*)$/.exec(line);
    const quote = /^\s*>\s?(.*)$/.exec(line);
    const math = /^\s*\u0000MATH(\d+)\u0000\s*$/.exec(line);
    if (!line.trim()) flush();
    else if (math) {
      flush();
      blocks.push({ t: "math", v: maths[Number(math[1])] });
    } else if (/^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/.test(line)) {
      flush();
      blocks.push({ t: "hr" });
    } else if (head) {
      flush();
      blocks.push({ t: "h", v: inline(head[1], sources, final) });
    } else if (quote) {
      flush();
      blocks.push({ t: "quote", v: inline(quote[1], sources, final) });
    } else if (bullet || numbered) {
      const kind = bullet ? "ul" : "ol";
      if (para.length || (list && list.t !== kind)) flush();
      list ??= { t: kind, items: [] };
      list.items.push((bullet ?? numbered)![1]);
    } else if (list && /^\s{2,}/.test(raw)) {
      list.items[list.items.length - 1] += ` ${line.trim()}`;
    } else {
      if (list) flush();
      para.push(line.trim());
    }
  }
  flush();
  return { blocks, sources: [...sources.values()].sort((a, b) => a.n - b.n) };
}
