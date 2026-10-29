// Checks one Classroom answer on the engine's /classroom/check. Model-checked
// exercises re-run the model at the student's own slider settings.
import { NextResponse } from "next/server";
import { validateCheck } from "@/lib/classroom";
import { forward, readBody, refuse } from "@/lib/engine";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

export async function POST(request: Request) {
  const body = await readBody(request);
  if (body instanceof NextResponse) return body;
  const input = validateCheck(body);
  if (typeof input === "string") return refuse(400, input);
  return forward("/classroom/check", input);
}
