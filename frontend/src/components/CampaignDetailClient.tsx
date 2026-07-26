"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";

import { CampaignProgress, StatusBadge } from "@/components/CampaignProgress";
import { CampaignResults } from "@/components/CampaignResults";
import { useCampaignPolling } from "@/hooks/useCampaignPolling";
import { formatDateTime } from "@/lib/format";

export function CampaignDetailClient({ campaignId }: { campaignId: string }) {
  const {
    campaign,
    isLoading,
    errorMessage,
    retryDelaySeconds,
    fatalState,
    refresh,
  } = useCampaignPolling(campaignId);
  const [copyMessage, setCopyMessage] = useState<string | null>(null);

  async function copyCampaignId() {
    try {
      await navigator.clipboard.writeText(campaignId);
      setCopyMessage("Campaign ID copied.");
    } catch {
      setCopyMessage("Could not copy the campaign ID.");
    }
  }

  if (fatalState === "not-found") {
    return <DetailError title="Campaign not found" message="This campaign may not exist or may no longer be available." />;
  }

  if (fatalState === "access-denied") {
    return <DetailError title="Campaign unavailable" message="You do not have access to this campaign." />;
  }

  if (isLoading && campaign === null) {
    return <DetailSkeleton />;
  }

  if (campaign === null) {
    return (
      <DetailError
        title="We couldn’t load this campaign"
        message={errorMessage ?? "The campaign service is temporarily unavailable."}
        action={<button className="button button-primary" type="button" onClick={refresh}>Try again</button>}
      />
    );
  }

  const input = campaign.input;
  const results = campaign.results;

  return (
    <div className="detail-page">
      <Link href="/" className="back-link">
        <span aria-hidden="true">←</span> All campaigns
      </Link>

      {errorMessage && (
        <div className="notice notice-warning" role="status">
          <div>
            <strong>Live updates paused.</strong>
            <p>
              {errorMessage}
              {retryDelaySeconds ? ` Retrying in ${retryDelaySeconds} seconds.` : ""}
            </p>
          </div>
          <button type="button" className="text-button" onClick={refresh}>Try now</button>
        </div>
      )}

      <header className="detail-hero">
        <div className="detail-hero-copy">
          <div className="detail-meta-row">
            <StatusBadge status={campaign.status} />
            <time dateTime={campaign.created_at}>{formatDateTime(campaign.created_at)}</time>
          </div>
          <p className="eyebrow">Campaign workspace</p>
          <h1>{campaignId}</h1>
          <p>One view of the brief, live pipeline progress, and emerging creative direction.</p>
        </div>
        <div className="detail-actions">
          <button className="button button-secondary" type="button" onClick={() => void copyCampaignId()}>
            Copy campaign ID
          </button>
          <button className="button button-secondary" type="button" onClick={refresh}>
            Refresh
          </button>
          <span className="sr-only" aria-live="polite">{copyMessage}</span>
        </div>
      </header>

      <div className="detail-overview-grid">
        <section className="detail-panel progress-panel" aria-labelledby="progress-title">
          <div className="panel-heading">
            <span>Live pipeline</span>
            <h2 id="progress-title">Production progress</h2>
          </div>
          <CampaignProgress campaign={campaign} />
          <p className="updated-copy">Last updated {formatDateTime(campaign.updated_at)}</p>
        </section>

        <section className="detail-panel brief-panel" aria-labelledby="brief-title">
          <div className="panel-heading">
            <span>Campaign brief</span>
            <h2 id="brief-title">Creative inputs</h2>
          </div>
          {input ? (
            <dl className="input-summary">
              <div className="input-summary-wide">
                <dt>Theme</dt>
                <dd>{input.campaign_theme}</dd>
              </div>
              <div className="input-summary-wide">
                <dt>Audience</dt>
                <dd>{input.target_audience}</dd>
              </div>
              <div>
                <dt>Duration</dt>
                <dd>{input.target_duration_sec} seconds</dd>
              </div>
              <div>
                <dt>Frame</dt>
                <dd>{input.aspect_ratio}</dd>
              </div>
            </dl>
          ) : (
            <p className="muted-copy">Campaign inputs are unavailable.</p>
          )}
        </section>
      </div>

      {campaign.error && (
        <section className="campaign-error" aria-labelledby="campaign-error-title">
          <div>
            <p className="eyebrow">Campaign stopped</p>
            <h2 id="campaign-error-title">{campaign.error.code.replaceAll("_", " ")}</h2>
          </div>
          <p>{campaign.error.message}</p>
        </section>
      )}

      <CampaignResults
        productAnalysis={results?.product_analysis}
        narrativeStrategy={results?.narrative_strategy}
        status={campaign.status}
      />
    </div>
  );
}

function DetailError({
  title,
  message,
  action,
}: {
  title: string;
  message: string;
  action?: ReactNode;
}) {
  return (
    <div className="route-state">
      <span className="route-state-mark" aria-hidden="true">404</span>
      <p className="eyebrow">Campaign library</p>
      <h1>{title}</h1>
      <p>{message}</p>
      <div className="route-state-actions">
        {action}
        <Link href="/" className="button button-secondary">Return to campaigns</Link>
      </div>
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="detail-page detail-skeleton" aria-label="Loading campaign" aria-busy="true">
      <span className="skeleton skeleton-small" />
      <div className="detail-hero">
        <div>
          <span className="skeleton skeleton-small" />
          <span className="skeleton skeleton-heading" />
          <span className="skeleton skeleton-line" />
        </div>
      </div>
      <div className="detail-overview-grid">
        <div className="detail-panel"><span className="skeleton skeleton-panel" /></div>
        <div className="detail-panel"><span className="skeleton skeleton-panel" /></div>
      </div>
    </div>
  );
}
