// The shapes in ../site_data. ScoreResult mirrors the API's ScorePolicyResponse,
// whose JSON Schema is site_data/schema/score-result.v1.json; lib/data.test.ts
// checks that every property named here is in that schema.

export type YearlyEffect = {
  year: number;
  revenue_effect: number;
  behavioral_offset: number;
  dynamic_feedback: number;
  /** Conventional deficit effect, billions; positive increases the deficit. */
  final_effect: number;
  debt_service: number | null;
  dynamic_effect: number | null;
};

export type Credibility = {
  category: string;
  evidence_type: string;
  class_label: string | null;
  n_tier1_rows: number;
  mean_abs_pct_error: number | null;
  max_abs_pct_error: number | null;
  uncertainty_low: number | null;
  uncertainty_high: number | null;
  outer_low: number | null;
  outer_high: number | null;
  no_band_reason: string;
  own_row_tier_label: string | null;
  own_row_abs_pct_error: number | null;
  own_row_official_billions: number | null;
  own_row_caption: string;
  limitations: string[];
  caption: string;
};

export type ScoreResult = {
  policy_name: string;
  policy_description: string;
  baseline_vintage: string;
  budget_window: string;
  /** Conventional ten-year deficit effect, billions; positive increases the deficit. */
  ten_year_deficit_impact: number;
  static_revenue_effect: number;
  behavioral_offset: number;
  gdp_effect: number | null;
  revenue_feedback: number | null;
  debt_service: number | null;
  dynamic_adjusted_impact: number | null;
  dynamic_model: string | null;
  year_by_year: YearlyEffect[];
  credibility: Credibility | null;
  error_message: string | null;
};

export type PresetFile = { id: string; conventional: ScoreResult; dynamic: ScoreResult };

export type PresetInfo = {
  id: string;
  name: string;
  description: string;
  cbo_score: number | null;
  cbo_source: string | null;
  cbo_date: string | null;
};

export type BuildRow = {
  build_id: string;
  label: string;
  score: number;
  area: string;
  source: string;
  source_date: string;
  exclusive_groups: string[];
  subsumes: string[];
  illustrative: boolean;
};

export type ValuesPick = { policy_id: string; label: string; score: number; why: string; tags: Record<string, string> };

export type ValuesArchetype = {
  id: string;
  name: string;
  one_line: string;
  chips: string[];
  target_pct_gdp: number;
  protected: string[];
  summary: string;
  gap_billions: number;
  total_billions: number;
  picks: ValuesPick[];
};

export type Manifest = {
  schema_version: number;
  baseline_vintages: string[];
  budget_windows: string[];
  presets: number;
  build_catalog_rows: number;
  scorecard_entries: number;
  tracker_bills: number;
  tracker_last_update: string | null;
  values_archetypes: number;
  social_security_options: number;
  sign_convention: string;
};

export type TrackerRow = {
  id: string;
  congress: number;
  chamber: string;
  type: string;
  number: string;
  title: string;
  sponsor: string;
  introduced: string | null;
  latest_action: string | null;
  latest_action_date: string | null;
  status: string;
  url: string | null;
  cbo_ten_year_billions: number | null;
  auto_ten_year_billions: number | null;
  auto_confidence: string | null;
};

export type TrackerIndex = {
  last_update: string | null;
  bills: number;
  with_cbo_estimate: number;
  with_auto_score: number;
  sign_convention: string;
  rows: TrackerRow[];
};

/** One tier's error summary in the generated evidence report. */
export type EvidenceSummary = {
  n: number;
  mean_abs_error: number;
  median_abs_error: number;
  within_15pct: number;
  within_25pct?: number;
  error_mass?: number;
};

/** site_data/validation/evidence.json: the validation figures every page quotes. */
export type Evidence = {
  out_of_sample: EvidenceSummary;
  out_of_sample_classes: Record<string, EvidenceSummary & { label: string }>;
  calibrated: {
    fitted: EvidenceSummary;
    fitted_held_in_place: EvidenceSummary;
    reconstruction: EvidenceSummary;
    reconstruction_retired_held_in_place: EvidenceSummary;
    retired_targets: { n: number; policy_ids: string[] };
  };
  leave_one_out: EvidenceSummary & { not_cross_validatable: number };
  data_vintages: {
    cbo_baseline_vintage: string;
    irs_soi_tax_years: number[];
    irs_soi_latest_tax_year: number;
    microdata_calibration_year: number;
    microdata_returns_coverage_pct: number;
    microdata_agi_coverage_pct: number;
  };
};

/** One row of site_data/validation/scorecard.json. */
export type ScorecardEntry = {
  category: string;
  policy_id: string;
  policy_name: string;
  official_10yr_billions: number;
  official_source: string;
  benchmark_url: string | null;
  benchmark_date: string | null;
  model_10yr_billions: number;
  abs_percent_difference: number;
  calibrated_to_target: boolean;
  target_retired: boolean;
  holdout_status: string;
  published_range_low_billions: number | null;
  published_range_high_billions: number | null;
  within_published_range: boolean | null;
};

/** site_data/views/<id>.json: who pays and economic effects for one preset. */
export type DistGroup = {
  name: string;
  floor: number;
  ceiling: number | null;
  returns_millions: number;
  avg_tax_change: number;
  pct_of_income: number;
  share_of_total: number;
  pct_with_increase: number;
  pct_with_decrease: number;
  baseline_etr: number;
  new_etr: number;
};

export type DistGrouping = {
  engine: "microsim" | "synthetic";
  unit: string;
  year: number;
  total_tax_change_billions: number;
  pct_with_increase: number;
  pct_with_decrease: number;
  groups: DistGroup[];
};

export type Distribution = {
  available: boolean;
  reason: "not_a_tax_policy" | "not_representable" | null;
  groupings: Partial<Record<"quintile" | "decile" | "jct_dollar", DistGrouping>>;
};

export type Economic =
  | { available: false }
  | {
      available: true;
      model: string;
      conventional_billions: number;
      revenue_feedback_billions: number;
      debt_service_billions: number;
      dynamic_total_billions: number;
      gdp_percent_years: number;
      years: number[];
      gdp_level_pct: number[];
      employment_millions: number[];
      unemployment_rate_ppts: number[];
      long_rate_ppts: number[];
      revenue_feedback_by_year: number[];
      debt_service_by_year: number[];
    };

export type ModelRun = {
  model: string;
  ten_year_billions: number;
  annual_billions: number[];
  methodology: string;
  confidence: string | null;
  notes: string[];
};

export type ModelsView = {
  results: ModelRun[];
  skipped: { model: string; kind: string; reason: string }[];
  blockers: string[];
  warnings: string[];
};

export type ResultViews = { id: string; distribution: Distribution; economic: Economic; models: ModelsView };

/** site_data/states.json: the ten modelled states. */
export type StateProfile = {
  code: string;
  name: string;
  has_income_tax: boolean;
  flat_rate: number | null;
  top_rate: number;
  std_ded_single: number;
  effective_salt_rate: number;
  pct_itemizers: number;
  avg_salt_deduction_itemizers: number;
  median_household_income: number;
  notes: string;
  rate_curve: { agi: number; federal_rate: number; state_rate: number; combined_rate: number }[];
  salt_cap_lift: {
    affected_filers_millions: number;
    avg_deduction_change: number;
    federal_revenue_change_billions: number;
    effective_rate_change_ppts: number;
  };
};

export type StatesData = { year: number; salt_cap_baseline: number; states: StateProfile[] };
