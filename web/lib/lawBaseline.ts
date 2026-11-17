// Three current-law yardsticks a score can be measured against. The catalog
// is site_data/law-baselines.json, written from fiscal_model.law_baselines.

export const LAW_IDS = ["current", "pre2025", "extended"] as const;
export type LawId = (typeof LAW_IDS)[number];
export const DEFAULT_LAW: LawId = "current";
export const LAW_PARAM = "law";

export type PresetRole = "live" | "already_law" | "remainder_unscored";

export type PresentationKind =
  | "live"
  | "already_law"
  | "remainder_unscored"
  | "reconstruction"
  | "current_law_score_on_other_yardstick";

export type SourcedFigure = {
  billions: number;
  window: string;
  convention: string;
  source: string;
  url: string;
  approximated: boolean;
  note: string | null;
};

export type LawInfo = {
  id: LawId;
  short_label: string;
  title: string;
  phrase: string;
  summary: string;
  lesson: string;
  cbo_vintage: string | null;
  versus_current: SourcedFigure | null;
};

export type Presentation = {
  kind: PresentationKind;
  role: PresetRole;
  display_score: 0 | "stored" | null;
  show_published: boolean;
  score_is_on_this_law: boolean;
  identity_baseline: string;
  explanation: string | null;
};

export type LawCatalog = {
  default: LawId;
  param: string;
  worked_example: string;
  laws: LawInfo[];
  preset_roles: Record<string, PresetRole>;
  classified: Record<string, Record<LawId, Presentation>>;
  live: Record<LawId, Presentation>;
  figures: {
    pl119_21_conventional: SourcedFigure;
    pl119_21_outlook: SourcedFigure;
    temps_extended_primary: SourcedFigure;
    house_passed_temps: SourcedFigure;
  };
};

export function parseLaw(value: string | string[] | null | undefined): LawId {
  const text = (Array.isArray(value) ? value[0] : value ?? "").trim().toLowerCase();
  return LAW_IDS.includes(text as LawId) ? (text as LawId) : DEFAULT_LAW;
}

/** Law from a query string such as `?law=pre2025&sort=size`. */
export function lawFromQuery(search: string): LawId {
  return parseLaw(new URLSearchParams(search.startsWith("?") ? search.slice(1) : search).get(LAW_PARAM));
}

/**
 * `href` with `law=` set, omitted when it is the default so a current-law
 * link stays a bare path. Keeps any other query and any #fragment.
 */
export function withLaw(href: string, law: LawId): string {
  const hashAt = href.indexOf("#");
  const hash = hashAt >= 0 ? href.slice(hashAt) : "";
  const rest = hashAt >= 0 ? href.slice(0, hashAt) : href;
  const queryAt = rest.indexOf("?");
  const path = queryAt >= 0 ? rest.slice(0, queryAt) : rest;
  const params = new URLSearchParams(queryAt >= 0 ? rest.slice(queryAt + 1) : "");
  if (law === DEFAULT_LAW) params.delete(LAW_PARAM);
  else params.set(LAW_PARAM, law);
  const query = params.toString().replace(/%2C/gi, ",");
  return `${path}${query ? `?${query}` : ""}${hash}`;
}

export function lawInfo(catalog: LawCatalog, law: LawId): LawInfo {
  return catalog.laws.find((row) => row.id === law) ?? catalog.laws[0];
}

export function presentPreset(catalog: LawCatalog, presetId: string, law: LawId): Presentation {
  return catalog.classified[presetId]?.[law] ?? catalog.live[law];
}

/** The conventional figure Explore should print, or null when it must not. */
export function displayedScore(stored: number | null, presentation: Presentation): number | null {
  if (presentation.display_score === 0) return 0;
  if (presentation.display_score === "stored") return stored;
  return null;
}

export function displayedPublished(stored: number | null, presentation: Presentation): number | null {
  return presentation.show_published ? stored : null;
}
