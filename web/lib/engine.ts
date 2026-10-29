// Forwards a checked request to the engine (engine/ in this repository, deployed
// as its own Vercel project). The browser never sees the engine's address or key.
//
// FISCAL_ENGINE_URL        the engine's origin, e.g. https://fiscal-engine-….vercel.app
// FISCAL_ENGINE_KEY        a secret from the engine's FISCAL_API_KEYS, sent as X-API-Key
// FISCAL_ENGINE_BYPASS     optional: the engine project's protection-bypass secret,
//                          while its deployments sit behind Vercel login
import { NextResponse } from "next/server";

export function refuse(status: number, message: string) {
  return NextResponse.json({ error: message }, { status, headers: { "Cache-Control": "no-store" } });
}

/** Read the browser's JSON body, or a 400 response. */
export async function readBody(request: Request): Promise<unknown | NextResponse> {
  try {
    return await request.json();
  } catch {
    return refuse(400, "Expected a JSON body.");
  }
}

function engineBase(): string | undefined {
  return process.env.FISCAL_ENGINE_URL?.trim().replace(/\/+$/, "") || undefined;
}

function engineHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (process.env.FISCAL_ENGINE_KEY) headers["X-API-Key"] = process.env.FISCAL_ENGINE_KEY;
  if (process.env.FISCAL_ENGINE_BYPASS) headers["x-vercel-protection-bypass"] = process.env.FISCAL_ENGINE_BYPASS;
  return headers;
}

/** POST ``payload`` to the engine at ``path`` and relay its answer in the site's terms. */
export async function forward(path: string, payload: unknown): Promise<NextResponse> {
  const base = engineBase();
  if (!base) return refuse(503, "Live scoring is not connected yet. Presets on Explore still work.");
  const headers = engineHeaders();

  let response: Response;
  try {
    response = await fetch(`${base}${path}`, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(55_000),
      cache: "no-store",
    });
  } catch {
    return refuse(504, "The engine did not answer in time. Try again in a moment.");
  }
  if (response.status === 429) return refuse(429, "Too many requests just now. Try again in a minute.");
  if (!response.ok) {
    // The engine's own message for a refused policy (422) is meant for people; anything else is not.
    if (response.status === 422) {
      const detail = await response.json().catch(() => null);
      const text = typeof detail?.detail === "string" ? detail.detail : "The engine could not score this policy.";
      return refuse(422, text);
    }
    return refuse(502, "The engine returned an error. Try again in a moment.");
  }
  return NextResponse.json(await response.json(), { headers: { "Cache-Control": "no-store" } });
}

/**
 * POST to an engine endpoint that answers with server-sent events and pass the
 * stream through as it arrives. Refusals before the stream starts (the daily
 * budget, a visitor's limit) carry the engine's own sentence, which is written
 * for people.
 */
export async function forwardStream(path: string, payload: unknown, timeoutMs: number): Promise<Response> {
  const base = engineBase();
  if (!base) return refuse(503, "Ask is not connected yet.");
  let response: Response;
  try {
    response = await fetch(`${base}${path}`, {
      method: "POST",
      headers: engineHeaders(),
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(timeoutMs),
      cache: "no-store",
    });
  } catch {
    return refuse(504, "The engine did not answer in time. Try again in a moment.");
  }
  if (!response.ok || !response.body) {
    const detail = await response.json().catch(() => null);
    const text = typeof detail?.detail === "string" ? detail.detail : null;
    if (response.status === 429) return refuse(429, text ?? "Too many questions just now. Try again later.");
    if (response.status === 503) return refuse(503, "Ask is not available right now.");
    return refuse(502, "The assistant returned an error. Try again in a moment.");
  }
  return new Response(response.body, {
    headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-store", "X-Accel-Buffering": "no" },
  });
}
