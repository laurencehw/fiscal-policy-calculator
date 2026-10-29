import Link from "next/link";
import { manifest, presets } from "@/lib/data";

export default function Home() {
  const m = manifest();
  return (
    <header>
      <h1>Fiscal Policy Calculator</h1>
      <p className="lede">
        What a tax or spending proposal does to the federal deficit over ten years, on CBO&apos;s{" "}
        {m.baseline_vintages.join(" and ")} baseline.
      </p>
      <p className="sentence">
        <Link href="/explore">Explore {presets().length} proposals</Link>, each scored conventionally and with
        macroeconomic feedback, and each shown beside the published score it is checked against.
      </p>
      <p className="note">{m.sign_convention}</p>
    </header>
  );
}
