// A per-visitor id for the engine's rate limiter. The site sends one engine key
// for every visitor, so without this the engine counted the whole site as one
// caller and one busy visitor could 429 everyone. The id is a salted hash of the
// visitor's address and the day: the engine can tell visitors apart without
// the address leaving the site, and the id changes daily.
//
// FISCAL_VISITOR_SALT   a long random secret, set on the web project. Unset, each
//                       server process draws its own random salt, which still
//                       separates visitors (it only means ids differ between
//                       instances). Never reuse another secret as the salt.
import { createHash, randomBytes } from "node:crypto";

/** The header the engine reads, and trusts only alongside a valid API key. */
export const VISITOR_HEADER = "X-Fiscal-Visitor";

let processSalt: string | undefined;

/** The configured salt, or one random salt drawn once per process. */
export function visitorSalt(env: Record<string, string | undefined> = process.env): string {
  const configured = env.FISCAL_VISITOR_SALT?.trim();
  if (configured) return configured;
  processSalt ??= randomBytes(32).toString("hex");
  return processSalt;
}

/** The first address in X-Forwarded-For (Vercel sets it to the visitor's), else X-Real-IP. */
export function firstForwardedAddress(forwardedFor: string | null, realIp: string | null): string {
  const first = (forwardedFor ?? "").split(",")[0]?.trim();
  return first || (realIp ?? "").trim() || "unknown";
}

/** ``v-`` and 32 hex characters: matches the engine's accepted pattern. */
export function visitorId(address: string, salt: string, day: string = new Date().toISOString().slice(0, 10)): string {
  return `v-${createHash("sha256").update(`${salt}|${day}|${address}`).digest("hex").slice(0, 32)}`;
}

/** The visitor id for a request's headers. */
export function visitorIdFromHeaders(headers: Pick<Headers, "get">, salt: string = visitorSalt()): string {
  return visitorId(firstForwardedAddress(headers.get("x-forwarded-for"), headers.get("x-real-ip")), salt);
}
