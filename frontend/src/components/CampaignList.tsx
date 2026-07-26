"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { CampaignProgress, StatusBadge } from "@/components/CampaignProgress";
import { listCampaigns } from "@/lib/api/campaigns";
import type {
  CampaignSummaryResponse,
  KnownCampaignStatus,
} from "@/lib/api/types";
import { ApiClientError } from "@/lib/api/client";
import { isTerminalStatus } from "@/lib/campaignState";
import { formatDateTime, shortenId } from "@/lib/format";

type StatusFilter = "" | KnownCampaignStatus;
type LoadingState = "initial" | "refresh" | "more" | null;

const FILTER_OPTIONS: Array<{ value: StatusFilter; label: string }> = [
  { value: "", label: "All campaigns" },
  { value: "queued", label: "Queued" },
  { value: "running", label: "Running" },
  { value: "cancel_requested", label: "Cancellation requested" },
  { value: "succeeded", label: "Succeeded" },
  { value: "failed", label: "Failed" },
  { value: "cancelled", label: "Cancelled" },
];

const STALE_AFTER_MS = 30_000;

export function CampaignList() {
  const [filter, setFilter] = useState<StatusFilter>("");
  const [items, setItems] = useState<CampaignSummaryResponse[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState<LoadingState>("initial");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const activeRequest = useRef<AbortController | null>(null);
  const lastLoadedAt = useRef(0);

  const loadFirstPage = useCallback(
    async (initial: boolean) => {
      activeRequest.current?.abort();
      const controller = new AbortController();
      activeRequest.current = controller;
      setLoading(initial ? "initial" : "refresh");
      setErrorMessage(null);

      try {
        const response = await listCampaigns({
          status: filter || undefined,
          signal: controller.signal,
        });
        if (controller.signal.aborted) {
          return;
        }
        setItems(response.items);
        setNextCursor(response.next_cursor);
        lastLoadedAt.current = Date.now();
      } catch (error) {
        if (!isAbortError(error)) {
          setErrorMessage(toMessage(error, "Recent campaigns could not be loaded."));
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(null);
        }
        if (activeRequest.current === controller) {
          activeRequest.current = null;
        }
      }
    },
    [filter],
  );

  useEffect(() => {
    setItems([]);
    setNextCursor(null);
    lastLoadedAt.current = 0;
    void loadFirstPage(true);
    return () => activeRequest.current?.abort();
  }, [loadFirstPage]);

  useEffect(() => {
    function refreshIfStale() {
      if (
        !document.hidden &&
        Date.now() - lastLoadedAt.current >= STALE_AFTER_MS &&
        activeRequest.current === null
      ) {
        void loadFirstPage(false);
      }
    }

    window.addEventListener("focus", refreshIfStale);
    document.addEventListener("visibilitychange", refreshIfStale);
    return () => {
      window.removeEventListener("focus", refreshIfStale);
      document.removeEventListener("visibilitychange", refreshIfStale);
    };
  }, [loadFirstPage]);

  async function loadMore() {
    if (!nextCursor || loading !== null) {
      return;
    }

    const controller = new AbortController();
    activeRequest.current = controller;
    setLoading("more");
    setErrorMessage(null);
    try {
      const response = await listCampaigns({
        status: filter || undefined,
        cursor: nextCursor,
        signal: controller.signal,
      });
      setItems((current) => mergeCampaigns(current, response.items));
      setNextCursor(response.next_cursor);
      lastLoadedAt.current = Date.now();
    } catch (error) {
      if (!isAbortError(error)) {
        setErrorMessage(toMessage(error, "More campaigns could not be loaded."));
      }
    } finally {
      if (!controller.signal.aborted) {
        setLoading(null);
      }
      if (activeRequest.current === controller) {
        activeRequest.current = null;
      }
    }
  }

  return (
    <section className="campaigns-section" aria-labelledby="recent-campaigns-title">
      <div className="section-heading-row">
        <div>
          <p className="eyebrow">Campaign library</p>
          <h2 id="recent-campaigns-title">Recent campaigns</h2>
          <p className="section-description">
            Follow work in progress and revisit completed campaign stories.
          </p>
        </div>
        <div className="list-controls">
          <label className="filter-control">
            <span>Status</span>
            <select
              value={filter}
              onChange={(event) => setFilter(event.target.value as StatusFilter)}
              disabled={loading === "initial"}
            >
              {FILTER_OPTIONS.map((option) => (
                <option key={option.value || "all"} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <button
            className="button button-secondary"
            type="button"
            onClick={() => void loadFirstPage(false)}
            disabled={loading !== null}
          >
            {loading === "refresh" ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>

      {errorMessage && (
        <div className="notice notice-error" role="alert">
          <div>
            <strong>Campaigns are out of reach.</strong>
            <p>{errorMessage}</p>
          </div>
          <button
            type="button"
            className="text-button"
            onClick={() => void loadFirstPage(items.length === 0)}
          >
            Try again
          </button>
        </div>
      )}

      {loading === "initial" && items.length === 0 ? (
        <CampaignListSkeleton />
      ) : items.length === 0 ? (
        <div className="empty-state">
          <span className="empty-mark" aria-hidden="true">K</span>
          <h3>{filter ? "No matching campaigns" : "Your campaign library is ready"}</h3>
          <p>
            {filter
              ? "Try another status or refresh to check for new work."
              : "Created campaigns will appear here with live progress and results."}
          </p>
          {filter && (
            <button className="button button-secondary" type="button" onClick={() => setFilter("")}>
              View all campaigns
            </button>
          )}
        </div>
      ) : (
        <div className="campaign-grid">
          {items.map((campaign) => (
            <CampaignSummaryCard campaign={campaign} key={campaign.id} />
          ))}
        </div>
      )}

      {nextCursor && (
        <div className="load-more-row">
          <button
            type="button"
            className="button button-secondary"
            onClick={() => void loadMore()}
            disabled={loading !== null}
          >
            {loading === "more" ? "Loading more…" : "Load more"}
          </button>
        </div>
      )}
    </section>
  );
}

function CampaignSummaryCard({ campaign }: { campaign: CampaignSummaryResponse }) {
  return (
    <article className="campaign-card">
      <div className="campaign-card-topline">
        <StatusBadge status={campaign.status} />
        <time dateTime={campaign.created_at}>{formatDateTime(campaign.created_at)}</time>
      </div>
      <div>
        <p className="card-kicker">Campaign</p>
        <h3 title={campaign.id}>{shortenId(campaign.id)}</h3>
        <span className="sr-only">Full campaign ID: {campaign.id}</span>
      </div>
      {!isTerminalStatus(campaign.status) && <CampaignProgress campaign={campaign} compact />}
      {isTerminalStatus(campaign.status) && (
        <p className="terminal-summary">
          {campaign.completed_stages} of {campaign.total_stages} stages complete
        </p>
      )}
      <Link className="card-link" href={`/campaigns/${encodeURIComponent(campaign.id)}`}>
        View campaign <span aria-hidden="true">→</span>
      </Link>
    </article>
  );
}

function CampaignListSkeleton() {
  return (
    <div className="campaign-grid" aria-label="Loading recent campaigns" aria-busy="true">
      {[0, 1, 2].map((item) => (
        <div className="campaign-card skeleton-card" key={item} aria-hidden="true">
          <span className="skeleton skeleton-small" />
          <span className="skeleton skeleton-title" />
          <span className="skeleton skeleton-line" />
          <span className="skeleton skeleton-button" />
        </div>
      ))}
    </div>
  );
}

function mergeCampaigns(
  current: CampaignSummaryResponse[],
  additional: CampaignSummaryResponse[],
): CampaignSummaryResponse[] {
  const byId = new Map(current.map((campaign) => [campaign.id, campaign]));
  for (const campaign of additional) {
    byId.set(campaign.id, campaign);
  }
  return Array.from(byId.values());
}

function toMessage(error: unknown, fallback: string): string {
  return error instanceof ApiClientError ? error.message : fallback;
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}
