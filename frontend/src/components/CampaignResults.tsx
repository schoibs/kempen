"use client";

import { useEffect, useState } from "react";

import type {
  AssetDownloadResponse,
  CampaignStatus,
  NarrativeStrategyResponse,
  ProductAnalysisResponse,
} from "@/lib/api/types";
import { formatBytes } from "@/lib/format";

interface CampaignResultsProps {
  productAnalysis?: ProductAnalysisResponse | null;
  narrativeStrategy?: NarrativeStrategyResponse | null;
  storyboard?: AssetDownloadResponse | null;
  video?: AssetDownloadResponse | null;
  status: CampaignStatus;
  refreshMedia: () => Promise<void>;
}

export function CampaignResults({
  productAnalysis,
  narrativeStrategy,
  storyboard,
  video,
  status,
  refreshMedia,
}: CampaignResultsProps) {
  const stoppedWithoutResult = ["failed", "cancelled"].includes(status);
  const completedWithoutResult = status === "succeeded";
  const productName = safeText(productAnalysis?.product_name, "Campaign");

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
            stopped={stoppedWithoutResult}
            completed={completedWithoutResult}
          />
        )}
        {narrativeStrategy ? (
          <NarrativeStrategyCard strategy={narrativeStrategy} />
        ) : (
          <ResultPlaceholder
            number="02"
            title="Narrative strategy"
            stopped={stoppedWithoutResult}
            completed={completedWithoutResult}
          />
        )}
        {storyboard ? (
          <StoryboardCard
            key={storyboard.download_url}
            artifact={storyboard}
            productName={productName}
            refreshMedia={refreshMedia}
          />
        ) : (
          <ResultPlaceholder
            number="03"
            title="Storyboard"
            stopped={stoppedWithoutResult}
            completed={completedWithoutResult}
          />
        )}
        {video ? (
          <VideoCard
            key={video.download_url}
            artifact={video}
            refreshMedia={refreshMedia}
          />
        ) : (
          <ResultPlaceholder
            number="04"
            title="Campaign video"
            stopped={stoppedWithoutResult}
            completed={completedWithoutResult}
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

function StoryboardCard({
  artifact,
  productName,
  refreshMedia,
}: {
  artifact: AssetDownloadResponse;
  productName: string;
  refreshMedia: () => Promise<void>;
}) {
  const { unavailable, markFailed } = useMediaAvailability(artifact);

  return (
    <article className="result-card media-card">
      <ResultCardHeading number="03" kicker="Visual direction" title="Storyboard" />
      {unavailable ? (
        <MediaUnavailable refreshMedia={refreshMedia} />
      ) : (
        <>
          <img
            className="storyboard-image"
            src={artifact.download_url}
            alt={`${productName} campaign storyboard`}
            onError={markFailed}
          />
          <div className="media-footer">
            <MediaMetadata artifact={artifact} />
            <a
              className="button button-secondary"
              href={artifact.download_url}
              target="_blank"
              rel="noreferrer"
            >
              Open full size
            </a>
          </div>
        </>
      )}
    </article>
  );
}

function VideoCard({
  artifact,
  refreshMedia,
}: {
  artifact: AssetDownloadResponse;
  refreshMedia: () => Promise<void>;
}) {
  const { unavailable, markFailed } = useMediaAvailability(artifact);

  return (
    <article className="result-card media-card media-card-dark">
      <ResultCardHeading number="04" kicker="Final cut" title="Campaign video" />
      {unavailable ? (
        <MediaUnavailable refreshMedia={refreshMedia} />
      ) : (
        <>
          <video
            className="campaign-video"
            src={artifact.download_url}
            controls
            preload="metadata"
            onError={markFailed}
          >
            Your browser does not support embedded video.
          </video>
          <div className="media-footer">
            <MediaMetadata artifact={artifact} />
            <a
              className="button button-on-dark"
              href={artifact.download_url}
              target="_blank"
              rel="noreferrer"
            >
              Open video
            </a>
          </div>
        </>
      )}
    </article>
  );
}

function ResultCardHeading({
  number,
  kicker,
  title,
}: {
  number: string;
  kicker: string;
  title: string;
}) {
  return (
    <header className="result-card-heading">
      <span>{number}</span>
      <div>
        <p className="card-kicker">{kicker}</p>
        <h3>{title}</h3>
      </div>
    </header>
  );
}

function MediaMetadata({ artifact }: { artifact: AssetDownloadResponse }) {
  return (
    <p>
      {safeText(artifact.content_type, "Media file")} · {formatBytes(artifact.size_bytes)}
    </p>
  );
}

function MediaUnavailable({ refreshMedia }: { refreshMedia: () => Promise<void> }) {
  const [isRefreshing, setIsRefreshing] = useState(false);

  async function handleRefresh() {
    setIsRefreshing(true);
    try {
      await refreshMedia();
    } finally {
      setIsRefreshing(false);
    }
  }

  return (
    <div className="media-unavailable" role="status">
      <div>
        <h4>Media link unavailable</h4>
        <p>The signed link expired or could not be loaded. Refreshing it will not regenerate the campaign.</p>
      </div>
      <button
        className="button button-secondary"
        type="button"
        disabled={isRefreshing}
        onClick={() => void handleRefresh()}
      >
        {isRefreshing ? "Refreshing link…" : "Refresh media link"}
      </button>
    </div>
  );
}

function useMediaAvailability(artifact: AssetDownloadResponse) {
  const [failed, setFailed] = useState(false);
  const [expired, setExpired] = useState(() => isExpired(artifact.download_url_expires_at));

  useEffect(() => {
    setFailed(false);
    const expiresAt = Date.parse(artifact.download_url_expires_at);
    if (Number.isNaN(expiresAt)) {
      setExpired(false);
      return;
    }

    const remainingMs = expiresAt - Date.now();
    if (remainingMs <= 0) {
      setExpired(true);
      return;
    }

    setExpired(false);
    const timer = window.setTimeout(
      () => setExpired(true),
      Math.min(remainingMs, 2_147_483_647),
    );
    return () => window.clearTimeout(timer);
  }, [artifact.download_url, artifact.download_url_expires_at]);

  return {
    unavailable: failed || expired || !artifact.download_url,
    markFailed: () => setFailed(true),
  };
}

function isExpired(value: string): boolean {
  const expiresAt = Date.parse(value);
  return !Number.isNaN(expiresAt) && expiresAt <= Date.now();
}

function ResultPlaceholder({
  number,
  title,
  stopped,
  completed,
}: {
  number: string;
  title: string;
  stopped: boolean;
  completed: boolean;
}) {
  return (
    <article className="result-placeholder">
      <span>{number}</span>
      <div>
        <h3>{title}</h3>
        <p>
          {stopped
            ? "This result was not completed before the campaign stopped."
            : completed
              ? "This result was not returned by the completed campaign."
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
