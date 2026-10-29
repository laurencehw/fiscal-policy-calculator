// The result views behind a Tailor score (who pays, economic effects, other
// models), from the engine's /score/views.
import { NextResponse } from "next/server";
import { forward, readBody, refuse } from "@/lib/engine";
import { engineRequest, validate } from "@/lib/tailor";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

export async function POST(request: Request) {
  const body = await readBody(request);
  if (body instanceof NextResponse) return body;
  const input = validate(body);
  if (typeof input === "string") return refuse(400, input);
  return forward("/score/views", engineRequest(input));
}
