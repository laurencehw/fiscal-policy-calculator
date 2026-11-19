import { ImageResponse } from "next/og";
import { preset, presets } from "@/lib/data";
import { currentLawFigure } from "@/lib/lawStatus";
import { ogCard } from "@/lib/ogcard";

export const alt = "A proposal's ten-year deficit effect, from the Fiscal Policy Calculator";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const dynamicParams = false;

export function generateStaticParams() {
  return presets().map((info) => ({ id: info.id }));
}

const INK = "#1b1b1a";
const MUTED = "#5f5c55";
const COLOR = { adds: "#b14c28", reduces: "#1f5e7a", none: INK } as const;

/** One card per proposal: its name, the figure the page leads with, and the published score beside it. */
export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const file = preset(id);
  const info = presets().find((row) => row.id === id);
  if (!file || !info) return new Response("Not found", { status: 404 });
  const lawNow = currentLawFigure(info.status, (other) => preset(other)?.conventional.ten_year_deficit_impact ?? null);
  const sameAs = info.status?.pre_2025_law ? info.status.current_law?.same_as : null;
  const sameAsBars = sameAs ? (preset(sameAs)?.conventional.year_by_year.map((row) => row.final_effect) ?? []) : [];
  const card = ogCard(file.conventional, info, lawNow, sameAsBars);
  const peak = Math.max(1, ...card.bars.map((v) => Math.abs(v)));
  const allSame = card.bars.every((v) => v >= 0) || card.bars.every((v) => v <= 0);
  const nameSize = card.name.length > 48 ? 52 : card.name.length > 30 ? 62 : 72;
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: "#fbfaf6",
          color: INK,
          padding: "60px 72px",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ fontSize: 26, color: MUTED, letterSpacing: 1 }}>Fiscal Policy Calculator · fiscal.lwilsesamson.com</div>
          <div style={{ fontSize: nameSize, fontWeight: 700, lineHeight: 1.08, marginTop: 20, maxWidth: 1050 }}>{card.name}</div>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <div style={{ display: "flex", flexDirection: "column", maxWidth: 700 }}>
            <div style={{ fontSize: 26, color: MUTED }}>{card.measures}</div>
            <div style={{ fontSize: 112, fontWeight: 700, lineHeight: 1.05, color: COLOR[card.tone], marginTop: 6 }}>{card.figure}</div>
            <div style={{ fontSize: 32, marginTop: 4 }}>{card.meaning}</div>
            <div style={{ fontSize: 26, color: MUTED, marginTop: 18, borderTop: `2px solid ${INK}`, paddingTop: 12 }}>{card.aside}</div>
          </div>
          {card.bars.length ? (
            <div
              style={{
                display: "flex",
                alignItems: allSame && card.bars.every((v) => v <= 0) ? "flex-start" : "flex-end",
                gap: 8,
                height: 220,
                borderBottom: allSame && card.bars.every((v) => v <= 0) ? "none" : `3px solid ${INK}`,
                borderTop: allSame && card.bars.every((v) => v <= 0) ? `3px solid ${INK}` : "none",
              }}
            >
              {card.bars.map((v, i) => (
                <div
                  key={i}
                  style={{ width: 26, height: Math.max(2, Math.round((Math.abs(v) / peak) * 210)), background: COLOR[v > 0 ? "adds" : v < 0 ? "reduces" : "none"] }}
                />
              ))}
            </div>
          ) : null}
        </div>
      </div>
    ),
    size,
  );
}
