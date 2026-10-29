"use client";
// Ask: a conversation with the citation-grounded assistant, streamed from the engine.
import { Fragment, useEffect, useRef, useState } from "react";
import { QUESTION_MAX, parseAnswer, readFrames, type Inline, type Turn } from "@/lib/ask";

const STARTERS = [
  "What does CBO project for the 10-year deficit, and what's driving it?",
  "How does the TCJA full extension affect each income decile?",
  "Compare PWBM and CBO on a corporate-rate increase.",
  "Explain dynamic scoring as this calculator applies it.",
  "When is the Social Security trust fund projected to be depleted?",
  "Score a 25% corporate rate and tell me what it costs.",
];

type Status = { status: "idle" } | { status: "asking" } | { status: "error"; message: string };

export function Ask() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [pending, setPending] = useState("");
  const [question, setQuestion] = useState("");
  const [status, setStatus] = useState<Status>({ status: "idle" });
  const abort = useRef<AbortController | null>(null);
  const started = useRef(false);

  async function ask(text: string) {
    const q = text.trim();
    if (!q || status.status === "asking") return;
    const history = turns;
    setTurns([...history, { role: "user", content: q }]);
    setQuestion("");
    setPending("");
    setStatus({ status: "asking" });
    const controller = new AbortController();
    abort.current = controller;
    let answer = "";
    try {
      const response = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, history }),
        signal: controller.signal,
      });
      if (!response.ok || !response.body) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.error ?? "The assistant did not answer. Try again in a moment.");
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let finished = false;
      while (!finished) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const { frames, rest } = readFrames(buffer);
        buffer = rest;
        for (const frame of frames) {
          if (frame.event === "token") {
            answer += frame.data;
            setPending(answer);
          } else if (frame.event === "error") {
            let detail = "The assistant stopped with an error. Try again in a moment.";
            try {
              detail = JSON.parse(frame.data).detail ?? detail;
            } catch {}
            throw new Error(detail);
          } else if (frame.event === "done") {
            finished = true;
          }
        }
      }
      if (!answer.trim()) throw new Error("The assistant returned an empty answer. Try asking again.");
      setTurns((cur) => [...cur, { role: "assistant", content: answer }]);
      setPending("");
      setStatus({ status: "idle" });
    } catch (e) {
      if (controller.signal.aborted) {
        if (answer.trim()) setTurns((cur) => [...cur, { role: "assistant", content: `${answer}\n\n> Stopped before the answer finished.` }]);
        else setTurns((cur) => cur.slice(0, -1));
        setPending("");
        setStatus({ status: "idle" });
        return;
      }
      // A failed question comes off the conversation so it can be asked again.
      setTurns((cur) => cur.slice(0, -1));
      setQuestion(q);
      setPending("");
      setStatus({ status: "error", message: e instanceof Error ? e.message : "Something went wrong." });
    } finally {
      abort.current = null;
    }
  }

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const q = new URLSearchParams(window.location.search).get("q");
    if (q) setQuestion(q.slice(0, QUESTION_MAX));
  }, []);

  const asking = status.status === "asking";

  return (
    <div className="ask">
      {turns.length === 0 && !asking ? (
        <div className="starters">
          {STARTERS.map((s) => (
            <button key={s} type="button" className="card" onClick={() => void ask(s)}>
              <span>{s}</span>
            </button>
          ))}
        </div>
      ) : null}

      <div className="conversation" aria-live="polite">
        {turns.map((t, i) =>
          t.role === "user" ? (
            <p key={i} className="asked">
              {t.content}
            </p>
          ) : (
            <AnswerView key={i} text={t.content} final />
          ),
        )}
        {asking ? (
          pending ? (
            <AnswerView text={pending} final={false} />
          ) : (
            <p className="note">Thinking. The assistant looks things up before it answers, which can take half a minute.</p>
          )
        ) : null}
      </div>

      {status.status === "error" ? <p className="note warn">{status.message}</p> : null}

      <form
        className="tailorform askform"
        onSubmit={(e) => {
          e.preventDefault();
          void ask(question);
        }}
      >
        <label className="field">
          <span>{turns.length ? "Follow-up question" : "Your question"}</span>
          <textarea
            rows={3}
            value={question}
            maxLength={QUESTION_MAX}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void ask(question);
              }
            }}
            placeholder="Ask about the budget, a tax or spending policy, or a score on this site"
          />
        </label>
        <div className="buttons">
          {asking ? (
            <button type="button" className="quiet" onClick={() => abort.current?.abort()}>
              Stop
            </button>
          ) : (
            <button type="submit" disabled={!question.trim()}>
              Ask
            </button>
          )}
          {turns.length && !asking ? (
            <button
              type="button"
              className="quiet"
              onClick={() => {
                setTurns([]);
                setStatus({ status: "idle" });
              }}
            >
              New conversation
            </button>
          ) : null}
        </div>
      </form>
    </div>
  );
}

function Inlines({ parts }: { parts: Inline[] }) {
  return (
    <>
      {parts.map((p, i) => {
        if (p.t === "text") return <Fragment key={i}>{p.v}</Fragment>;
        if (p.t === "b") return <b key={i}>{p.v}</b>;
        if (p.t === "code") return <code key={i}>{p.v}</code>;
        if (p.t === "link")
          return (
            <a key={i} href={p.href} rel="noopener noreferrer nofollow" target="_blank">
              {p.v}
            </a>
          );
        return (
          <sup key={i} className="fn">
            {p.href ? (
              <a href={p.href} rel="noopener noreferrer nofollow" target="_blank">
                [{p.n}]
              </a>
            ) : (
              `[${p.n}]`
            )}
          </sup>
        );
      })}
    </>
  );
}

function AnswerView({ text, final }: { text: string; final: boolean }) {
  const { blocks, sources } = parseAnswer(text, final);
  return (
    <div className="answer">
      {blocks.map((b, i) => {
        if (b.t === "h")
          return (
            <h3 key={i}>
              <Inlines parts={b.v} />
            </h3>
          );
        if (b.t === "p")
          return (
            <p key={i}>
              <Inlines parts={b.v} />
            </p>
          );
        if (b.t === "quote")
          return (
            <p key={i} className="note">
              <Inlines parts={b.v} />
            </p>
          );
        const List = b.t === "ul" ? "ul" : "ol";
        return (
          <List key={i}>
            {b.items.map((item, j) => (
              <li key={j}>
                <Inlines parts={item} />
              </li>
            ))}
          </List>
        );
      })}
      {sources.length ? (
        <div className="sources">
          <span className="tag">Sources</span>
          <ol>
            {sources.map((s) => (
              <li key={s.n} value={s.n}>
                {s.href ? (
                  <a href={s.href} rel="noopener noreferrer nofollow" target="_blank">
                    {s.text.replace(/https?:\/\/\S+/g, "").replace(/[,;\s]+$/, "") || s.href}
                  </a>
                ) : (
                  s.text
                )}
              </li>
            ))}
          </ol>
        </div>
      ) : null}
    </div>
  );
}
