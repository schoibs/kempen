import type {
  CampaignStage,
  CampaignStatus,
  KnownCampaignStage,
  KnownCampaignStatus,
} from "./api/types";

const STATUS_LABELS: Record<KnownCampaignStatus, string> = {
  queued: "Queued",
  running: "Running",
  cancel_requested: "Cancellation requested",
  succeeded: "Succeeded",
  failed: "Failed",
  cancelled: "Cancelled",
};

const STAGE_LABELS: Record<KnownCampaignStage, string> = {
  validating_input: "Validating product image",
  analyzing_product: "Analyzing product",
  building_narrative: "Building campaign narrative",
  generating_storyboard: "Generating storyboard",
  generating_video: "Generating video",
  finalizing: "Finalizing campaign",
};

const TERMINAL_STATUSES = new Set<CampaignStatus>(["succeeded", "failed", "cancelled"]);

export function statusLabel(status: CampaignStatus): string {
  return status in STATUS_LABELS
    ? STATUS_LABELS[status as KnownCampaignStatus]
    : humanizeUnknown(status, "Unknown status");
}

export function stageLabel(stage: CampaignStage): string {
  return stage in STAGE_LABELS
    ? STAGE_LABELS[stage as KnownCampaignStage]
    : humanizeUnknown(stage, "Stage unavailable");
}

export function statusTone(status: CampaignStatus): string {
  return ["queued", "running", "cancel_requested", "succeeded", "failed", "cancelled"].includes(
    status,
  )
    ? status
    : "unknown";
}

export function isTerminalStatus(status: CampaignStatus): boolean {
  return TERMINAL_STATUSES.has(status);
}

export function clampProgress(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.min(100, Math.max(0, Math.round(value)));
}

function humanizeUnknown(value: string, fallback: string): string {
  const label = value.replaceAll("_", " ").trim();
  if (!label) {
    return fallback;
  }
  return label.charAt(0).toUpperCase() + label.slice(1);
}
