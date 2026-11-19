import path from "node:path";
import type { NextConfig } from "next";

// Pages read ../site_data (written nightly by scripts/export_static.py) at build
// time, so the repository root must be in the tracing root.
const config: NextConfig = {
  outputFileTracingRoot: path.join(__dirname, ".."),
  // "/" and "/compare" are pre-rendered (site review quick win 11). Their query
  // strings still work, with or without JavaScript: these rewrites send
  // "/?vs=<id>" and "/compare?ids=<a,b>" to routes that are built ahead or
  // cached on first request, while the address bar keeps the original URL.
  // beforeFiles, because "/" and "/compare" are themselves pages.
  async rewrites() {
    return {
      beforeFiles: [
        {
          source: "/",
          has: [{ type: "query", key: "vs", value: "(?<vs>[a-z0-9-]{1,80})" }],
          destination: "/home/:vs",
        },
        {
          source: "/compare",
          has: [{ type: "query", key: "ids", value: "(?<ids>[a-z0-9,-]{1,300})" }],
          destination: "/compare/:ids",
        },
      ],
      afterFiles: [],
      fallback: [],
    };
  },
  async headers() {
    return [
      {
        // The read-only data API (documented at /data) is open to any origin.
        source: "/api/v1/:path*",
        headers: [
          { key: "Access-Control-Allow-Origin", value: "*" },
          { key: "Access-Control-Allow-Methods", value: "GET, HEAD, OPTIONS" },
        ],
      },
      {
        source: "/:path*",
        headers: [
          { key: "Content-Security-Policy", value: "frame-ancestors 'self'" },
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
        ],
      },
    ];
  },
};

export default config;
