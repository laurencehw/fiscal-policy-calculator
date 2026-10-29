import assert from "node:assert/strict";
import { test } from "node:test";
import { clientAddress, parseAnswer, readFrames, safeHref, validateAsk, unescapeDollars } from "./ask";

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
