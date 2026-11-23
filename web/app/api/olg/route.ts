// A long-run reform in the overlapping-generations model, from the engine's /olg.
import { NextResponse } from "next/server";
import { forward, readBody, refuse, refuseCrossSite } from "@/lib/engine";
import { validateOlg } from "@/lib/olg";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

export async function POST(request: Request) {
  const crossSite = refuseCrossSite(request);
  if (crossSite) return crossSite;
  const body = await readBody(request);
  if (body instanceof NextResponse) return body;
  const input = validateOlg(body);
  if (typeof input === "string") return refuse(400, input);
  return forward("/olg", input, request);
}
