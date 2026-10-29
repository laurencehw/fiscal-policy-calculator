const FALLBACK_SITE_URL = "https://fiscal.lwilsesamson.com";

/** The author's site. Linked from the footer. */
export const AUTHOR_URL = "https://lwilsesamson.com/";

/** The repository: methods, code and every published figure the model is checked against. */
export const REPO_URL = "https://github.com/laurencehw/fiscal-policy-calculator";

/** Absolute site origin, with no trailing slash. */
export function siteUrl(): string {
  const configured = process.env.NEXT_PUBLIC_SITE_URL?.trim();
  return (configured || FALLBACK_SITE_URL).replace(/\/+$/, "");
}

export const SITE_DESCRIPTION =
  "Ten-year budget estimates for U.S. tax and spending proposals, each shown beside the published score it is checked against.";
