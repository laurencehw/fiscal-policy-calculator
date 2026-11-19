// Responses for the read-only data API: JSON, open to any origin, cacheable.
import { NextResponse } from "next/server";

export function json(body: unknown, { immutable = false }: { immutable?: boolean } = {}): NextResponse {
  return jsonText(JSON.stringify(body, null, 2), { immutable });
}

export function jsonText(text: string, { immutable = false }: { immutable?: boolean } = {}): NextResponse {
  return new NextResponse(text, {
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
      // A snapshot never changes; everything else follows the nightly export.
      "Cache-Control": immutable ? "public, max-age=31536000, immutable" : "public, max-age=3600",
    },
  });
}

export function notFound(message: string): NextResponse {
  return NextResponse.json(
    { error: message, documentation: "/data" },
    { status: 404, headers: { "Access-Control-Allow-Origin": "*" } },
  );
}
