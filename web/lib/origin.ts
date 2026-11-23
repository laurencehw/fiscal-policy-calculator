// Refuses cross-site POSTs to the site's engine proxies. A browser attaches an
// Origin header to every cross-origin POST, so a page elsewhere that tries to
// spend this site's engine quota from its visitors' browsers is turned away.
// Requests with no Origin (curl, server-side callers, some same-origin
// navigations) pass: they are not the browser-borne case this guards.
import { siteUrl } from "@/lib/site";

const LOCAL_HOSTNAMES = new Set(["localhost", "127.0.0.1", "[::1]", "::1"]);

function hostOf(url: string): string | null {
  try {
    return new URL(url).host.toLowerCase();
  } catch {
    return null;
  }
}

export type OriginOptions = {
  /** The site's configured origin (NEXT_PUBLIC_SITE_URL or the default). */
  siteOrigin?: string;
  /** Allow http://localhost etc. (true outside production). */
  allowLocalhost?: boolean;
};

/**
 * True when the request is same-site: no Origin header, or an Origin whose host
 * is the host the request was sent to, or the site's configured host. "null"
 * (sandboxed frames, some redirects) is refused.
 */
export function isSameOrigin(headers: Pick<Headers, "get">, options: OriginOptions = {}): boolean {
  const origin = headers.get("origin");
  if (origin === null || origin === "") return true;
  const originHost = hostOf(origin);
  if (!originHost) return false;

  const allowLocalhost = options.allowLocalhost ?? process.env.NODE_ENV !== "production";
  if (allowLocalhost) {
    try {
      if (LOCAL_HOSTNAMES.has(new URL(origin).hostname.toLowerCase())) return true;
    } catch {
      return false;
    }
  }

  const requestHost = (headers.get("x-forwarded-host") ?? headers.get("host") ?? "").split(",")[0]?.trim().toLowerCase();
  if (requestHost && originHost === requestHost) return true;

  const siteHost = hostOf(options.siteOrigin ?? siteUrl());
  return siteHost !== null && originHost === siteHost;
}
