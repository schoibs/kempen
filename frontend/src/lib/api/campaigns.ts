import { apiRequest } from "./client";
import type {
  CampaignDetailResponse,
  CampaignListResponse,
  CampaignStatus,
} from "./types";

interface ListCampaignsOptions {
  status?: CampaignStatus;
  cursor?: string;
  limit?: number;
  signal?: AbortSignal;
}

export async function listCampaigns({
  status,
  cursor,
  limit = 20,
  signal,
}: ListCampaignsOptions = {}): Promise<CampaignListResponse> {
  const query = new URLSearchParams({ limit: String(limit) });
  if (status) {
    query.set("status", status);
  }
  if (cursor) {
    query.set("cursor", cursor);
  }

  const response = await apiRequest<CampaignListResponse>(`/v1/campaigns?${query}`, { signal });
  return {
    items: Array.isArray(response.items) ? response.items : [],
    next_cursor: typeof response.next_cursor === "string" ? response.next_cursor : null,
  };
}

export function getCampaign(
  campaignId: string,
  signal?: AbortSignal,
): Promise<CampaignDetailResponse> {
  return apiRequest<CampaignDetailResponse>(
    `/v1/campaigns/${encodeURIComponent(campaignId)}`,
    { signal },
  );
}
