// Who pays, economic effects and other scoring models: the sections under a
// headline score, on Explore (from the nightly export) and Tailor (live).
import { EconomicEffects } from "@/components/EconomicEffects";
import { EstimateTag } from "@/components/EstimateTag";
import { ScoringModels } from "@/components/ScoringModels";
import { WhoPays } from "@/components/WhoPays";
import type { EstimateIdentity } from "@/lib/identity";
import type { Views } from "@/lib/types";

export function ResultSections({
  views,
  conventional,
  dynamic,
}: {
  views: Views;
  conventional?: EstimateIdentity;
  dynamic?: EstimateIdentity;
}) {
  return (
    <>
      <section className="chart" id="who-pays">
        <div className="head">
          <h2>Who pays</h2>
          <span className="tag">first year, by income group</span>
          {conventional ? <EstimateTag identity={conventional} /> : null}
        </div>
        <WhoPays dist={views.distribution} />
      </section>
      <section className="chart" id="economy">
        <div className="head">
          <h2>Economic effects</h2>
          <span className="tag">difference from the CBO baseline</span>
          {dynamic ? <EstimateTag identity={dynamic} /> : null}
        </div>
        <EconomicEffects econ={views.economic} />
      </section>
      <section className="chart" id="models">
        <div className="head">
          <h2>Other scoring models</h2>
          <span className="tag">exploratory</span>
        </div>
        <ScoringModels view={views.models} />
      </section>
    </>
  );
}
