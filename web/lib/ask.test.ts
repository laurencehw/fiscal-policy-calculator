import assert from "node:assert/strict";
import { test } from "node:test";
import {
  BODY_BYTES_MAX,
  HISTORY_MESSAGES_MAX,
  HISTORY_TOTAL_CHARS_MAX,
  clientAddress,
  finalAnswer,
  parseAnswer,
  readCappedText,
  readFrames,
  safeHref,
  sameOrigin,
  trimHistory,
  validateAsk,
  unescapeDollars,
  type Turn,
} from "./ask";

test("a question is checked and history is held to roles and length", () => {
  assert.deepEqual(validateAsk({ question: "  What is the deficit? " }), { question: "What is the deficit?", history: [] });
  assert.equal(typeof validateAsk({ question: "" }), "string");
  assert.equal(typeof validateAsk({ question: "x".repeat(2001) }), "string");
  assert.equal(typeof validateAsk({ question: "q", history: [{ role: "system", content: "x" }] }), "string");
  const ok = validateAsk({ question: "q", history: [{ role: "user", content: "a" }, { role: "assistant", content: "b".repeat(9000) }] });
  assert.ok(typeof ok !== "string" && ok.history[1].content.length === 8000);
});

test("the visitor's address is the first forwarded one", () => {
  assert.equal(clientAddress("203.0.113.5, 10.0.0.1", null), "203.0.113.5");
  assert.equal(clientAddress(null, "198.51.100.2"), "198.51.100.2");
  assert.equal(clientAddress(null, null), "unknown");
});

test("server-sent frames are split, multi-line data rejoined, and a partial frame kept", () => {
  const { frames, rest } = readFrames("event: token\ndata: Hello\n\nevent: token\ndata: line one\ndata: line two\n\nevent: do");
  assert.deepEqual(frames, [
    { event: "token", data: "Hello" },
    { event: "token", data: "line one\nline two" },
  ]);
  assert.equal(rest, "event: do");
});

test("citations link to their sources and orphan markers drop once complete", () => {
  const text = [
    "Debt rose **sharply** [^1] and more [^2].",
    "",
    "- first point",
    "- second [^1]",
    "",
    "## Sources",
    '[^1]: CBO (2026), "Budget Outlook", https://www.cbo.gov/publication/61882',
    "> ✂️ Answer cut off at the length limit.",
  ].join("\n");
  const a = parseAnswer(text);
  assert.equal(a.sources.length, 1);
  assert.equal(a.sources[0].href, "https://www.cbo.gov/publication/61882");
  const p = a.blocks[0];
  assert.equal(p.t, "p");
  if (p.t !== "p") return;
  assert.deepEqual(p.v[1], { t: "b", v: "sharply" });
  assert.equal(p.v.filter((x) => x.t === "cite").length, 1, "the [^2] with no entry is dropped");
  assert.equal(a.blocks[1].t, "ul");
  assert.equal(a.blocks.at(-1)?.t, "quote");
  const streaming = parseAnswer("Debt rose [^2]", false);
  assert.ok(streaming.blocks[0].t === "p" && streaming.blocks[0].v.some((x) => x.t === "cite"));
});

test("only web links are linked", () => {
  assert.equal(safeHref("javascript:alert(1)"), undefined);
  assert.equal(safeHref("https://bea.gov/x"), "https://bea.gov/x");
  const a = parseAnswer("[click](javascript:alert(1)) and [ok](https://bls.gov)");
  const p = a.blocks[0];
  assert.ok(p.t === "p" && !p.v.some((x) => x.t === "link" && x.href.startsWith("javascript")));
});

test("escaped dollars read as dollars, display math as plain text", () => {
  const { blocks } = parseAnswer(
    "Medicare cost \\$1.0 trillion.\n\n$$\\Delta(\\text{debt/GDP}) = \\frac{\\text{primary deficit}}{\\text{GDP}} + (r - g) \\times \\frac{\\text{debt}}{\\text{GDP}}$$\n\nwhen *r* exceeds *g*\n\n---\n\nEnd.",
  );
  assert.deepEqual(blocks[0], { t: "p", v: [{ t: "text", v: "Medicare cost $1.0 trillion." }] });
  assert.deepEqual(blocks[1], { t: "math", v: "Δ(debt/GDP) = (primary deficit) / GDP + (r - g) × debt / GDP" });
  assert.deepEqual(blocks[2], {
    t: "p",
    v: [{ t: "text", v: "when " }, { t: "i", v: "r" }, { t: "text", v: " exceeds " }, { t: "i", v: "g" }],
  });
  assert.deepEqual(blocks[3], { t: "hr" });
  assert.equal(unescapeDollars("cap (\\$5.00 of \\$5.00)"), "cap ($5.00 of $5.00)");
});

test("a lone asterisk is not italics", () => {
  const { blocks } = parseAnswer("3 * 4 = 12 and 5 * 6 = 30");
  assert.deepEqual(blocks[0], { t: "p", v: [{ t: "text", v: "3 * 4 = 12 and 5 * 6 = 30" }] });
});

test("history is capped in messages and in total characters", () => {
  const msgs = (n: number, len: number): Turn[] =>
    Array.from({ length: n }, (_, i) => ({ role: i % 2 ? "assistant" : "user", content: "x".repeat(len) }));
  assert.equal(typeof validateAsk({ question: "q", history: msgs(HISTORY_MESSAGES_MAX + 1, 1) }), "string");
  assert.equal(typeof validateAsk({ question: "q", history: msgs(3, 6000) }), "string");
  const atLimit = msgs(HISTORY_MESSAGES_MAX, HISTORY_TOTAL_CHARS_MAX / HISTORY_MESSAGES_MAX);
  assert.notEqual(typeof validateAsk({ question: "q", history: atLimit }), "string");
});

test("a long conversation is trimmed to its newest turns, starting with a question", () => {
  const turns: Turn[] = Array.from({ length: 30 }, (_, i) => ({
    role: i % 2 ? "assistant" : "user",
    content: `${i} ${"y".repeat(1500)}`,
  }));
  const kept = trimHistory(turns);
  assert.equal(kept[0].role, "user");
  assert.equal(kept[kept.length - 1].content, turns[29].content);
  assert.ok(kept.length <= HISTORY_MESSAGES_MAX);
  assert.ok(kept.reduce((n, t) => n + t.content.length, 0) <= HISTORY_TOTAL_CHARS_MAX);
  assert.notEqual(typeof validateAsk({ question: "q", history: kept }), "string");
  assert.deepEqual(trimHistory([]), []);
});

test("the body is capped before it is parsed", async () => {
  const small = new Request("https://site.test/api/ask", { method: "POST", body: JSON.stringify({ question: "q" }) });
  assert.equal(await readCappedText(small), '{"question":"q"}');
  const declared = new Request("https://site.test/api/ask", {
    method: "POST",
    body: "x",
    headers: { "content-length": String(BODY_BYTES_MAX + 1) },
  });
  assert.equal(await readCappedText(declared), null);
  // No declared length: the stream is cut off once it passes the cap.
  const chunks = [new Uint8Array(40), new Uint8Array(40)];
  const stream = new ReadableStream<Uint8Array>({
    pull(controller) {
      const next = chunks.shift();
      if (next) controller.enqueue(next);
      else controller.close();
    },
  });
  const init = { method: "POST", body: stream, duplex: "half" } as RequestInit;
  assert.equal(await readCappedText(new Request("https://site.test/api/ask", init), 64), null);
});

test("only a same-host Origin, or none, passes", () => {
  assert.equal(sameOrigin(null, "fiscal.example.com"), true);
  assert.equal(sameOrigin("https://fiscal.example.com", "fiscal.example.com"), true);
  assert.equal(sameOrigin("http://localhost:3000", "localhost:3000"), true);
  assert.equal(sameOrigin("https://evil.example", "fiscal.example.com"), false);
  assert.equal(sameOrigin("null", "fiscal.example.com"), false);
  assert.equal(sameOrigin("https://fiscal.example.com", null), false);
});

test("the done frame's final text replaces the streamed answer", () => {
  const done = JSON.stringify({ final_text: "Clean [citation needed]." });
  assert.equal(finalAnswer(done, "Raw [^3]."), "Clean [citation needed].");
  assert.equal(finalAnswer(JSON.stringify({ model: "m" }), "Raw."), "Raw.");
  assert.equal(finalAnswer("not json", "Raw."), "Raw.");
});
