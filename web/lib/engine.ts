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

/** POST ``payload`` to the engine at ``path`` and relay its answer in the site's terms. */
export async function forward(path: string, payload: unknown): Promise<NextResponse> {
  const base = process.env.FISCAL_ENGINE_URL?.trim().replace(/\/+$/, "");
  if (!base) return refuse(503, "Live scoring is not connected yet. Presets on Explore still work.");

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (process.env.FISCAL_ENGINE_KEY) headers["X-API-Key"] = process.env.FISCAL_ENGINE_KEY;
  if (process.env.FISCAL_ENGINE_BYPASS) headers["x-vercel-protection-bypass"] = process.env.FISCAL_ENGINE_BYPASS;

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
