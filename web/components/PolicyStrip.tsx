// The "US economic policy" strip shared with monetary.lwilsesamson.com.
// Links come from lwilsesamson.com/nav.json (read at build time; redeploy to pick up a change), with a local copy as fallback.
import fallback from "@/lib/policy-strip.default.json";

type Strip = typeof fallback;
const NAV_URL = "https://lwilsesamson.com/nav.json";

async function getStrip(): Promise<Strip> {
  try {
    const res = await fetch(NAV_URL, { cache: "force-cache", signal: AbortSignal.timeout(5000) });
    if (!res.ok) return fallback;
    const nav = (await res.json()) as Strip;
    return Array.isArray(nav?.items) && nav.items.length ? nav : fallback;
  } catch {
    return fallback;
  }
}

export async function PolicyStrip() {
  const nav = await getStrip();
  return (
    <nav className="policystrip noprint" aria-label={nav.label}>
      <span className="policystrip-label">{nav.label}:</span>
      {nav.items.map((it) => (
        <a key={it.key} href={it.href} aria-current={it.key === "fiscal" ? "page" : undefined}>
          {it.label}
        </a>
      ))}
      <a className="policystrip-home" href={nav.home.href}>
        {nav.home.label}
      </a>
    </nav>
  );
}
