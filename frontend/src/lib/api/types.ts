export const CAMPAIGN_STATUSES = [
  "queued",
  "running",
  "cancel_requested",
  "succeeded",
  "failed",
  "cancelled",
] as const;

export const CAMPAIGN_STAGES = [
  "validating_input",
  "analyzing_product",
  "building_narrative",
  "generating_storyboard",
  "generating_video",
  "finalizing",
] as const;

export const ASPECT_RATIOS = ["auto", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16"] as const;

export type KnownCampaignStatus = (typeof CAMPAIGN_STATUSES)[number];
export type KnownCampaignStage = (typeof CAMPAIGN_STAGES)[number];
export type CampaignStatus = KnownCampaignStatus | (string & {});
export type CampaignStage = KnownCampaignStage | (string & {});
export type AspectRatio = (typeof ASPECT_RATIOS)[number];

export interface ApiFieldError {
  location: Array<string | number>;
  message: string;
}

export interface ApiProblem {
  type?: string;
  title: string;
  status: number;
  code: string;
  detail: string;
  request_id?: string;
  errors: ApiFieldError[];
}

export interface UploadIntentRequest {
  filename: string;
  content_type: "image/jpeg" | "image/png" | "image/webp";
  size_bytes: number;
  sha256?: string;
}

export interface AssetSummary {
  id: string;
  status: string;
  content_type: string;
  size_bytes: number;
}

export interface UploadDescriptor {
  method: "PUT";
  url: string;
  headers: Record<string, string>;
  expires_at: string;
}

export interface UploadIntentResponse {
  asset: AssetSummary;
  upload: UploadDescriptor;
}

export interface UploadCompleteResponse {
  id: string;
  status: string;
  content_type: string;
  size_bytes: number;
}

export interface CampaignLinks {
  self: string;
  cancel: string;
}

export interface CampaignAcceptedResponse {
  id: string;
  status: CampaignStatus;
  stage: CampaignStage;
  progress_percent: number;
  created_at: string;
  updated_at: string;
  links: CampaignLinks;
}

export interface CampaignSummaryResponse extends CampaignAcceptedResponse {
  completed_stages: number;
  total_stages: number;
}

export interface CampaignListResponse {
  items: CampaignSummaryResponse[];
  next_cursor: string | null;
}

export interface CampaignInputResponse {
  product_image_asset_id: string;
  campaign_theme: string;
  target_audience: string;
  target_duration_sec: number;
  aspect_ratio: AspectRatio | (string & {});
}

export interface ProductColor {
  name?: string;
  hex?: string;
}

export interface ProductAnalysisResponse {
  product_name?: string;
  category?: string;
  primary_colors?: ProductColor;
  visible_facts?: string[];
  additional_facts?: string[];
}

export interface NarrativeStrategyResponse {
  concept?: string;
  story_premise?: string;
  hook?: string;
  conflict?: string;
  tone?: string[];
}

export interface AssetDownloadResponse {
  id: string;
  content_type: string;
  size_bytes: number;
  sha256: string | null;
  download_url: string;
  download_url_expires_at: string;
}

export interface CampaignResultsResponse {
  product_analysis: ProductAnalysisResponse | null;
  narrative_strategy: NarrativeStrategyResponse | null;
  storyboard: AssetDownloadResponse | null;
  video: AssetDownloadResponse | null;
}

export interface CampaignErrorResponse {
  code: string;
  message: string;
  retryable: boolean;
}

export interface CampaignDetailResponse extends CampaignSummaryResponse {
  input: CampaignInputResponse;
  results: CampaignResultsResponse;
  error: CampaignErrorResponse | null;
  started_at: string | null;
  completed_at: string | null;
}
