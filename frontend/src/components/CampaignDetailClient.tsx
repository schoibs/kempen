"use client";

import Link from "next/link";
import { useRef, useState, type ReactNode } from "react";

import { CampaignProgress, StatusBadge } from "@/components/CampaignProgress";
import { CampaignResults } from "@/components/CampaignResults";
import { useCampaignPolling } from "@/hooks/useCampaignPolling";
import { ApiClientError } from "@/lib/api/client";
import { cancelCampaign, retryCampaign } from "@/lib/api/campaigns";
import type { CampaignDetailResponse } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";

export function CampaignDetailClient({ campaignId }: { campaignId: string }) {
  const {
    campaign,
    isLoading,
    errorMessage,
    retryDelaySeconds,
    fatalState,
    refresh,
    applyAcceptedCampaign,
  } = useCampaignPolling(campaignId);
  const [copyMessage, setCopyMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [activeAction, setActiveAction] = useState<"cancel" | "retry" | null>(null);
  const cancelDialogRef = useRef<HTMLDialogElement>(null);
  const retryIdempotencyKeyRef = useRef<string | null>(null);

  async function copyCampaignId() {
    try {
      await navigator.clipboard.writeText(campaignId);
      setCopyMessage("Campaign ID copied.");
    } catch {
      setCopyMessage("Could not copy the campaign ID.");
    }
  }

  async function handleCancel() {
    setActiveAction("cancel");
    setActionError(null);
    setActionMessage(null);
    try {
      const accepted = await cancelCampaign(campaignId);
      applyAcceptedCampaign(accepted);
      setActionMessage(
        accepted.status === "cancelled"
          ? "Campaign cancelled."
          : "Cancellation requested. Updates will continue until processing stops.",
      );
      await refresh();
    } catch (error) {
      setActionError(actionErrorMessage(error, "The campaign could not be cancelled."));
      if (isStaleActionError(error)) {
        await refresh();
      }
    } finally {
      setActiveAction(null);
    }
  }

  async function handleRetry() {
    const idempotencyKey = retryIdempotencyKeyRef.current ?? crypto.randomUUID();
    retryIdempotencyKeyRef.current = idempotencyKey;
    setActiveAction("retry");
    setActionError(null);
    setActionMessage(null);
    try {
      const accepted = await retryCampaign(campaignId, idempotencyKey);
      retryIdempotencyKeyRef.current = null;
      applyAcceptedCampaign(accepted);
      setActionMessage("Retry accepted. Generation is continuing from the last completed checkpoint.");
      await refresh();
    } catch (error) {
      if (!isAmbiguousRetryError(error)) {
        retryIdempotencyKeyRef.current = null;
      }
      setActionError(actionErrorMessage(error, "The campaign retry could not be confirmed."));
      if (isStaleActionError(error)) {
        await refresh();
      }
    } finally {
      setActiveAction(null);
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
        action={<button className="button button-primary" type="button" onClick={() => void refresh()}>Try again</button>}
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
          <button type="button" className="text-button" onClick={() => void refresh()}>Try now</button>
        </div>
      )}

      {actionError && (
        <div className="notice notice-error" role="alert">
          <div>
            <strong>Action not completed.</strong>
            <p>{actionError}</p>
          </div>
          <button type="button" className="text-button" onClick={() => setActionError(null)}>Dismiss</button>
        </div>
      )}

      {actionMessage && (
        <div className="notice notice-success" role="status">
          <div>
            <strong>Campaign updated.</strong>
            <p>{actionMessage}</p>
          </div>
          <button type="button" className="text-button" onClick={() => setActionMessage(null)}>Dismiss</button>
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
          <button className="button button-secondary" type="button" onClick={() => void refresh()}>
            Refresh
          </button>
          {(["queued", "running"].includes(campaign.status) || campaign.status === "cancel_requested") && (
            <button
              className="button button-danger"
              type="button"
              disabled={campaign.status === "cancel_requested" || activeAction !== null}
              onClick={() => cancelDialogRef.current?.showModal()}
            >
              {campaign.status === "cancel_requested"
                ? "Cancellation pending"
                : activeAction === "cancel"
                  ? "Requesting cancellation…"
                  : "Cancel campaign"}
            </button>
          )}
          {campaign.status === "failed" && campaign.error?.retryable === true && (
            <button
              className="button button-primary"
              type="button"
              disabled={activeAction !== null}
              onClick={() => void handleRetry()}
            >
              {activeAction === "retry" ? "Retrying…" : "Retry campaign"}
            </button>
          )}
          <span className="sr-only" aria-live="polite">{copyMessage}</span>
        </div>
      </header>

      <dialog
        ref={cancelDialogRef}
        className="confirmation-dialog"
        aria-labelledby="cancel-dialog-title"
        aria-describedby="cancel-dialog-description"
      >
        <form method="dialog">
          <p className="eyebrow">Confirm cancellation</p>
          <h2 id="cancel-dialog-title">Stop this campaign?</h2>
          <p id="cancel-dialog-description">
            Active provider work may not stop immediately and may already have incurred cost.
            Any completed results will remain available.
          </p>
          <div className="confirmation-actions">
            <button className="button button-secondary" type="submit">Keep campaign running</button>
            <button
              className="button button-danger"
              type="button"
              disabled={activeAction !== null}
              onClick={() => {
                cancelDialogRef.current?.close();
                void handleCancel();
              }}
            >
              Confirm cancellation
            </button>
          </div>
        </form>
      </dialog>

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

      <CampaignStatePanel campaign={campaign} />

      <CampaignResults
        productAnalysis={results?.product_analysis}
        narrativeStrategy={results?.narrative_strategy}
        storyboard={results?.storyboard}
        video={results?.video}
        status={campaign.status}
        refreshMedia={refresh}
      />
    </div>
  );
}

function CampaignStatePanel({ campaign }: { campaign: CampaignDetailResponse }) {
  if (campaign.status === "succeeded") {
    return (
      <section className="campaign-state campaign-state-success" aria-labelledby="campaign-state-title">
        <div>
          <p className="eyebrow">Campaign complete</p>
          <h2 id="campaign-state-title">Ready to review</h2>
        </div>
        <p>
          The campaign finished successfully. Review the structured direction, storyboard, and video below.
          {campaign.completed_at ? ` Completed ${formatDateTime(campaign.completed_at)}.` : ""}
        </p>
      </section>
    );
  }

  if (campaign.status === "failed") {
    return (
      <section className="campaign-state campaign-state-error" aria-labelledby="campaign-state-title">
        <div>
          <p className="eyebrow">Campaign stopped</p>
          <h2 id="campaign-state-title">
            {campaign.error ? humanizeCode(campaign.error.code) : "Generation failed"}
          </h2>
        </div>
        <p>
          {campaign.error?.message ?? "Campaign generation failed."}
          {campaign.error?.retryable
            ? " You can retry from the last completed checkpoint."
            : " This failure cannot be retried."}
        </p>
      </section>
    );
  }

  if (campaign.status === "cancelled") {
    return (
      <section className="campaign-state campaign-state-cancelled" aria-labelledby="campaign-state-title">
        <div>
          <p className="eyebrow">Campaign cancelled</p>
          <h2 id="campaign-state-title">Generation stopped</h2>
        </div>
        <p>The campaign is not complete. Any results finished before cancellation remain available below.</p>
      </section>
    );
  }

  if (campaign.status === "cancel_requested") {
    return (
      <section className="campaign-state campaign-state-pending" aria-labelledby="campaign-state-title">
        <div>
          <p className="eyebrow">Cancellation pending</p>
          <h2 id="campaign-state-title">Stopping active work</h2>
        </div>
        <p>Cancellation is being processed. This page will keep checking until the campaign stops.</p>
      </section>
    );
  }

  return null;
}

function actionErrorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiClientError ? error.message : fallback;
}

function isStaleActionError(error: unknown): boolean {
  return error instanceof ApiClientError && ["CAMPAIGN_TERMINAL", "INVALID_CAMPAIGN_STATE"].includes(
    error.problem?.code ?? "",
  );
}

function isAmbiguousRetryError(error: unknown): boolean {
  return !(error instanceof ApiClientError) || error.status >= 500;
}

function humanizeCode(value: string): string {
  const label = value.replaceAll("_", " ").trim().toLowerCase();
  return label ? label.charAt(0).toUpperCase() + label.slice(1) : "Generation failed";
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
