// Ask: forwards a question to the engine's /ask/stream and streams the answer
// back. Each visitor is counted under a daily id made from their address, so
// the engine's per-visitor limit applies without the site storing addresses.
import { createHash } from "node:crypto";
import { NextResponse } from "next/server";
import { clientAddress, validateAsk } from "@/lib/ask";
import { forwardStream, readBody, refuse } from "@/lib/engine";

export const dynamic = "force-dynamic";
export const maxDuration = 120;

function visitorId(request: Request): string {
  const address = clientAddress(request.headers.get("x-forwarded-for"), request.headers.get("x-real-ip"));
  const day = new Date().toISOString().slice(0, 10);
  const salt = process.env.ASK_VISITOR_SALT ?? process.env.FISCAL_ENGINE_BYPASS ?? "fiscal-calculator";
  return `web-${createHash("sha256").update(`${salt}|${day}|${address}`).digest("hex").slice(0, 24)}`;
}

export async function POST(request: Request) {
  const body = await readBody(request);
  if (body instanceof NextResponse) return body;
  const input = validateAsk(body);
  if (typeof input === "string") return refuse(400, input);
  return forwardStream(
    "/ask/stream",
    { question: input.question, history: input.history, session_id: visitorId(request), enable_web_search: true },
    115_000,
  );
}
