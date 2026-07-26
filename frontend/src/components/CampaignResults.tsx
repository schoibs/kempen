import type {
  CampaignStatus,
  NarrativeStrategyResponse,
  ProductAnalysisResponse,
} from "@/lib/api/types";

interface CampaignResultsProps {
  productAnalysis?: ProductAnalysisResponse | null;
  narrativeStrategy?: NarrativeStrategyResponse | null;
  status: CampaignStatus;
}

export function CampaignResults({
  productAnalysis,
  narrativeStrategy,
  status,
}: CampaignResultsProps) {
  const terminalWithoutResult = ["failed", "cancelled"].includes(status);

  return (
    <section className="results-section" aria-labelledby="results-title">
      <div className="detail-section-heading">
        <p className="eyebrow">Creative intelligence</p>
        <h2 id="results-title">Campaign story</h2>
      </div>
      <div className="results-stack">
        {productAnalysis ? (
          <ProductAnalysisCard analysis={productAnalysis} />
        ) : (
          <ResultPlaceholder
            number="01"
            title="Product analysis"
            unavailable={terminalWithoutResult}
          />
        )}
        {narrativeStrategy ? (
          <NarrativeStrategyCard strategy={narrativeStrategy} />
        ) : (
          <ResultPlaceholder
            number="02"
            title="Narrative strategy"
            unavailable={terminalWithoutResult}
          />
        )}
      </div>
    </section>
  );
}

function ProductAnalysisCard({ analysis }: { analysis: ProductAnalysisResponse }) {
  const visibleFacts = stringList(analysis.visible_facts);
  const additionalFacts = stringList(analysis.additional_facts);
  const color = analysis.primary_colors;
  const colorHex = typeof color?.hex === "string" && /^#[0-9A-Fa-f]{6}$/.test(color.hex)
    ? color.hex
    : null;

  return (
    <article className="result-card">
      <header className="result-card-heading">
        <span>01</span>
        <div>
          <p className="card-kicker">Product analysis</p>
          <h3>{safeText(analysis.product_name, "Unnamed product")}</h3>
        </div>
      </header>
      <dl className="result-summary-grid">
        <div>
          <dt>Category</dt>
          <dd>{safeText(analysis.category)}</dd>
        </div>
        <div>
          <dt>Primary color</dt>
          <dd className="color-value">
            {colorHex && (
              <span className="color-swatch" style={{ backgroundColor: colorHex }} aria-hidden="true" />
            )}
            <span>
              {safeText(color?.name)}
              {colorHex ? ` · ${colorHex.toUpperCase()}` : ""}
            </span>
          </dd>
        </div>
      </dl>
      <div className="fact-columns">
        <FactList title="What we can see" facts={visibleFacts} />
        <FactList title="What research adds" facts={additionalFacts} />
      </div>
    </article>
  );
}

function NarrativeStrategyCard({ strategy }: { strategy: NarrativeStrategyResponse }) {
  const tones = stringList(strategy.tone).slice(0, 3);
  const beats = [
    ["Story premise", strategy.story_premise],
    ["Opening hook", strategy.hook],
    ["Creative tension", strategy.conflict],
  ] as const;

  return (
    <article className="result-card result-card-dark">
      <header className="result-card-heading">
        <span>02</span>
        <div>
          <p className="card-kicker">Narrative strategy</p>
          <h3>{safeText(strategy.concept, "Concept in development")}</h3>
        </div>
      </header>
      {tones.length > 0 && (
        <div className="tone-list" aria-label="Campaign tone">
          {tones.map((tone) => (
            <span key={tone}>{tone}</span>
          ))}
        </div>
      )}
      <dl className="story-beats">
        {beats.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{safeText(value)}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

function FactList({ title, facts }: { title: string; facts: string[] }) {
  return (
    <div>
      <h4>{title}</h4>
      {facts.length > 0 ? (
        <ul>
          {facts.map((fact, index) => (
            <li key={`${index}-${fact}`}>{fact}</li>
          ))}
        </ul>
      ) : (
        <p className="muted-copy">No details available yet.</p>
      )}
    </div>
  );
}

function ResultPlaceholder({
  number,
  title,
  unavailable,
}: {
  number: string;
  title: string;
  unavailable: boolean;
}) {
  return (
    <article className="result-placeholder">
      <span>{number}</span>
      <div>
        <h3>{title}</h3>
        <p>
          {unavailable
            ? "This result was not completed before the campaign stopped."
            : "Waiting for the campaign pipeline to reach this stage."}
        </p>
      </div>
    </article>
  );
}

function safeText(value: unknown, fallback = "Not available"): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function stringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
    : [];
}
