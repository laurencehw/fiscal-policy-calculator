import { ImageResponse } from "next/og";
import { SITE_DESCRIPTION } from "@/lib/site";

export const alt = "Fiscal Policy Calculator";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

/** The card a shared link shows: the site's paper, its title, and a small bar chart in the deficit colors. */
export default function OpenGraphImage() {
  const bars = [
    { h: 120, c: "#1f5e7a" },
    { h: 200, c: "#b14c28" },
    { h: 280, c: "#b14c28" },
    { h: 90, c: "#1f5e7a" },
  ];
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          background: "#fbfaf6",
          color: "#1b1b1a",
          padding: "72px 80px",
          justifyContent: "space-between",
          alignItems: "flex-end",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", maxWidth: 720 }}>
          <div style={{ fontSize: 30, color: "#5f5c55", letterSpacing: 1 }}>fiscal.lwilsesamson.com</div>
          <div style={{ fontSize: 84, fontWeight: 700, lineHeight: 1.05, marginTop: 24 }}>Fiscal Policy Calculator</div>
          <div style={{ fontSize: 34, lineHeight: 1.35, marginTop: 28, color: "#3a3833" }}>{SITE_DESCRIPTION}</div>
        </div>
        <div style={{ display: "flex", alignItems: "flex-end", gap: 18, borderBottom: "4px solid #1b1b1a", paddingBottom: 0 }}>
          {bars.map((bar, i) => (
            <div key={i} style={{ width: 54, height: bar.h, background: bar.c }} />
          ))}
        </div>
      </div>
    ),
    size,
  );
}
