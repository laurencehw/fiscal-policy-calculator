// Ask: forwards a question to the engine's /ask/stream and streams the answer
// back. Each visitor is counted under a daily id made from their address, so
// the engine's per-visitor limit applies without the site storing addresses.
//
// ASK_VISITOR_SALT   the salt for those ids. Set it in every environment: without
//                    it each server instance draws its own random salt, so one
//                    visitor's id (and their per-visitor limit) differs between
//                    instances and resets when an instance is recycled.
import { createHash, randomBytes } from "node:crypto";
import { clientAddress, readCappedText, sameOrigin, validateAsk } from "@/lib/ask";
import { forwardStream, refuse } from "@/lib/engine";

export const dynamic = "force-dynamic";
export const maxDuration = 120;

// Never a deployment secret reused for another purpose, and never a constant
// anyone could read in this repository.
const PROCESS_SALT = randomBytes(16).toString("hex");

function visitorId(request: Request): string {
  const address = clientAddress(request.headers.get("x-forwarded-for"), request.headers.get("x-real-ip"));
  const day = new Date().toISOString().slice(0, 10);
  const salt = process.env.ASK_VISITOR_SALT?.trim() || PROCESS_SALT;
  return `web-${createHash("sha256").update(`${salt}|${day}|${address}`).digest("hex").slice(0, 24)}`;
}

export async function POST(request: Request) {
  // A local same-origin check; replace with the shared helper once it lands.
  if (!sameOrigin(request.headers.get("origin"), request.headers.get("host"))) {
    return refuse(403, "Ask only answers this site's own pages.");
  }
  // Capped before parsing: an oversized body is refused without being held in full.
  const text = await readCappedText(request).catch(() => undefined);
  if (text === undefined) return refuse(400, "Expected a JSON body.");
  if (text === null) return refuse(413, "This conversation is too long. Start a new one.");
  let body: unknown;
  try {
    body = JSON.parse(text);
  } catch {
    return refuse(400, "Expected a JSON body.");
  }
  const input = validateAsk(body);
  if (typeof input === "string") return refuse(400, input);
  return forwardStream(
    "/ask/stream",
    { question: input.question, history: input.history, session_id: visitorId(request), enable_web_search: true },
    115_000,
  );
}
