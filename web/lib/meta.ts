// Page metadata with its own Open Graph and Twitter text. Next.js replaces a
// parent's openGraph object rather than merging it, so a page that set only
// `description` used to share the layout's og:description with every other
// page (site review quick win 8). Every page goes through this instead.
import type { Metadata } from "next";

export const SITE_NAME = "Fiscal Policy Calculator";

/** The site's card (app/opengraph-image.tsx). A route with its own card file overrides it. */
const SITE_CARD = { url: "/opengraph-image", width: 1200, height: 630, alt: SITE_NAME };

export function pageMeta({ title, description, path }: { title: string; description: string; path: string }): Metadata {
  const full = `${title} · ${SITE_NAME}`;
  return {
    title,
    description,
    alternates: { canonical: path },
    openGraph: { type: "website", siteName: SITE_NAME, title: full, description, url: path, images: [SITE_CARD] },
    twitter: { card: "summary_large_image", title: full, description, images: [SITE_CARD.url] },
  };
}
