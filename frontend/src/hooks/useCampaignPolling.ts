"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiClientError } from "@/lib/api/client";
import { getCampaign } from "@/lib/api/campaigns";
import type {
  CampaignAcceptedResponse,
  CampaignDetailResponse,
  CampaignStatus,
} from "@/lib/api/types";
import { isTerminalStatus } from "@/lib/campaignState";

type FatalReadState = "not-found" | "access-denied" | "error" | null;

interface CampaignPollingState {
  campaign: CampaignDetailResponse | null;
  isLoading: boolean;
  errorMessage: string | null;
  retryDelaySeconds: number | null;
  fatalState: FatalReadState;
  refresh: () => Promise<void>;
  applyAcceptedCampaign: (accepted: CampaignAcceptedResponse) => void;
}

const POLL_INTERVAL_MS = 3_000;
const BACKOFF_MS = [3_000, 6_000, 12_000, 24_000, 30_000];

export function useCampaignPolling(campaignId: string): CampaignPollingState {
  const [campaign, setCampaign] = useState<CampaignDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [retryDelaySeconds, setRetryDelaySeconds] = useState<number | null>(null);
  const [fatalState, setFatalState] = useState<FatalReadState>(null);
  const currentStatusRef = useRef<CampaignStatus | null>(null);
  const refreshRef = useRef<() => Promise<void>>(async () => undefined);

  useEffect(() => {
    let active = true;
    let inFlightPromise: Promise<void> | null = null;
    let failureCount = 0;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let controller: AbortController | null = null;

    setCampaign(null);
    currentStatusRef.current = null;
    setIsLoading(true);
    setErrorMessage(null);
    setRetryDelaySeconds(null);
    setFatalState(null);

    function clearTimer() {
      if (timer !== null) {
        clearTimeout(timer);
        timer = null;
      }
    }

    function schedule(delayMs: number) {
      clearTimer();
      if (!active || document.hidden) {
        return;
      }
      timer = setTimeout(() => {
        void readCampaign();
      }, delayMs);
    }

    function readCampaign(force = false): Promise<void> {
      if (!active || (!force && document.hidden)) {
        return Promise.resolve();
      }
      if (inFlightPromise !== null) {
        return force
          ? inFlightPromise.then(() => readCampaign(true))
          : inFlightPromise;
      }

      inFlightPromise = performRead().finally(() => {
        inFlightPromise = null;
      });
      return inFlightPromise;
    }

    async function performRead() {
      clearTimer();
      controller = new AbortController();

      try {
        const nextCampaign = await getCampaign(campaignId, controller.signal);
        if (!active) {
          return;
        }

        currentStatusRef.current = nextCampaign.status;
        failureCount = 0;
        setCampaign(nextCampaign);
        setErrorMessage(null);
        setRetryDelaySeconds(null);
        setFatalState(null);
        setIsLoading(false);

        if (!isTerminalStatus(nextCampaign.status)) {
          schedule(POLL_INTERVAL_MS);
        }
      } catch (error) {
        if (!active || isAbortError(error)) {
          return;
        }

        setIsLoading(false);
        if (error instanceof ApiClientError && error.status === 404) {
          setFatalState("not-found");
          setErrorMessage(error.message);
          return;
        }
        if (error instanceof ApiClientError && [401, 403].includes(error.status)) {
          setFatalState("access-denied");
          setErrorMessage(error.message);
          return;
        }

        const transient = !(error instanceof ApiClientError) || error.status >= 500;
        if (!transient) {
          setFatalState("error");
          setErrorMessage(error instanceof Error ? error.message : "The campaign could not be loaded.");
          return;
        }

        setErrorMessage(
          error instanceof ApiClientError
            ? error.message
            : "Campaign updates are temporarily unavailable.",
        );
        if (
          currentStatusRef.current === null ||
          !isTerminalStatus(currentStatusRef.current)
        ) {
          const delayMs = BACKOFF_MS[Math.min(failureCount, BACKOFF_MS.length - 1)];
          failureCount += 1;
          setRetryDelaySeconds(delayMs / 1_000);
          schedule(delayMs);
        } else {
          setRetryDelaySeconds(null);
        }
      }
    }

    function refresh(): Promise<void> {
      return readCampaign(true);
    }

    function resumePolling() {
      if (document.hidden) {
        clearTimer();
        return;
      }
      if (
        currentStatusRef.current === null ||
        !isTerminalStatus(currentStatusRef.current)
      ) {
        void readCampaign();
      }
    }

    refreshRef.current = refresh;
    document.addEventListener("visibilitychange", resumePolling);
    window.addEventListener("focus", resumePolling);
    void readCampaign(true);

    return () => {
      active = false;
      clearTimer();
      controller?.abort();
      document.removeEventListener("visibilitychange", resumePolling);
      window.removeEventListener("focus", resumePolling);
    };
  }, [campaignId]);

  const refresh = useCallback(() => refreshRef.current(), []);
  const applyAcceptedCampaign = useCallback((accepted: CampaignAcceptedResponse) => {
    if (accepted.id !== campaignId) {
      return;
    }
    currentStatusRef.current = accepted.status;
    setCampaign((current) => current === null || current.id !== accepted.id
      ? current
      : {
          ...current,
          ...accepted,
          error: accepted.status === "queued" ? null : current.error,
          completed_at: accepted.status === "queued" ? null : current.completed_at,
        });
  }, [campaignId]);

  return {
    campaign,
    isLoading,
    errorMessage,
    retryDelaySeconds,
    fatalState,
    refresh,
    applyAcceptedCampaign,
  };
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}
