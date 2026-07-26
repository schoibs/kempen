"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiClientError } from "@/lib/api/client";
import { getCampaign } from "@/lib/api/campaigns";
import type { CampaignDetailResponse, CampaignStatus } from "@/lib/api/types";
import { isTerminalStatus } from "@/lib/campaignState";

type FatalReadState = "not-found" | "access-denied" | "error" | null;

interface CampaignPollingState {
  campaign: CampaignDetailResponse | null;
  isLoading: boolean;
  errorMessage: string | null;
  retryDelaySeconds: number | null;
  fatalState: FatalReadState;
  refresh: () => void;
}

const POLL_INTERVAL_MS = 3_000;
const BACKOFF_MS = [3_000, 6_000, 12_000, 24_000, 30_000];

export function useCampaignPolling(campaignId: string): CampaignPollingState {
  const [campaign, setCampaign] = useState<CampaignDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [retryDelaySeconds, setRetryDelaySeconds] = useState<number | null>(null);
  const [fatalState, setFatalState] = useState<FatalReadState>(null);
  const refreshRef = useRef<() => void>(() => undefined);

  useEffect(() => {
    let active = true;
    let inFlight = false;
    let failureCount = 0;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let controller: AbortController | null = null;
    let currentStatus: CampaignStatus | null = null;

    setCampaign(null);
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

    async function readCampaign(force = false) {
      if (!active || inFlight || (!force && document.hidden)) {
        return;
      }

      clearTimer();
      inFlight = true;
      controller = new AbortController();

      try {
        const nextCampaign = await getCampaign(campaignId, controller.signal);
        if (!active) {
          return;
        }

        currentStatus = nextCampaign.status;
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
        if (currentStatus === null || !isTerminalStatus(currentStatus)) {
          const delayMs = BACKOFF_MS[Math.min(failureCount, BACKOFF_MS.length - 1)];
          failureCount += 1;
          setRetryDelaySeconds(delayMs / 1_000);
          schedule(delayMs);
        } else {
          setRetryDelaySeconds(null);
        }
      } finally {
        inFlight = false;
      }
    }

    function refresh() {
      void readCampaign(true);
    }

    function resumePolling() {
      if (document.hidden) {
        clearTimer();
        return;
      }
      if (currentStatus === null || !isTerminalStatus(currentStatus)) {
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

  return { campaign, isLoading, errorMessage, retryDelaySeconds, fatalState, refresh };
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}
