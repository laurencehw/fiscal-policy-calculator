import type { MetadataRoute } from "next";
import { classroomIndex, presets } from "@/lib/data";
import { NAV_ITEMS } from "@/lib/nav";
import { siteUrl } from "@/lib/site";

/** Every page a visitor can reach: the sections, the reference pages, each preset and assignment. */
export default function sitemap(): MetadataRoute.Sitemap {
  const base = siteUrl();
  const paths = [
    "/",
    ...NAV_ITEMS.map((item) => item.href),
    "/contact",
    "/privacy",
    ...presets().map((info) => `/explore/${info.id}`),
    ...classroomIndex().map((row) => `/classroom/${row.id}`),
  ];
  return paths.map((path) => ({ url: `${base}${path}` }));
}
