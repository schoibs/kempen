import type { CampaignSummaryResponse } from "@/lib/api/types";
import {
  clampProgress,
  stageLabel,
  statusLabel,
  statusTone,
} from "@/lib/campaignState";

interface CampaignProgressProps {
  campaign: CampaignSummaryResponse;
  compact?: boolean;
}

export function StatusBadge({ status }: Pick<CampaignSummaryResponse, "status">) {
  return (
    <span className={`status-badge status-${statusTone(status)}`}>
      <span className="status-dot" aria-hidden="true" />
      {statusLabel(status)}
    </span>
  );
}

export function CampaignProgress({ campaign, compact = false }: CampaignProgressProps) {
  const progress = clampProgress(campaign.progress_percent);
  const completedStages = Number.isFinite(campaign.completed_stages)
    ? campaign.completed_stages
    : 0;
  const totalStages = Number.isFinite(campaign.total_stages) ? campaign.total_stages : 0;

  return (
    <div className={compact ? "progress-block progress-compact" : "progress-block"}>
      <div className="progress-copy">
        <span>{stageLabel(campaign.stage)}</span>
        <span>{progress}%</span>
      </div>
      <progress max="100" value={progress} aria-label={`Campaign progress: ${progress}%`}>
        {progress}%
      </progress>
      <p className="stage-count">
        {completedStages} of {totalStages} stages complete
      </p>
    </div>
  );
}
