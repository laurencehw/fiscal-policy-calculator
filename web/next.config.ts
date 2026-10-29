import path from "node:path";
import type { NextConfig } from "next";

// Pages read ../site_data (written nightly by scripts/export_static.py) at build
// time, so the repository root must be in the tracing root.
const config: NextConfig = {
  outputFileTracingRoot: path.join(__dirname, ".."),
  async headers() {
    return [
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
