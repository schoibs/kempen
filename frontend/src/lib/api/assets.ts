import { apiRequest } from "./client";
import type {
  UploadCompleteResponse,
  UploadIntentRequest,
  UploadIntentResponse,
} from "./types";

export function createUploadIntent(
  request: UploadIntentRequest,
  signal?: AbortSignal,
): Promise<UploadIntentResponse> {
  return apiRequest<UploadIntentResponse>("/v1/assets/upload-intents", {
    method: "POST",
    json: request,
    signal,
  });
}

export function completeUpload(
  assetId: string,
  signal?: AbortSignal,
): Promise<UploadCompleteResponse> {
  return apiRequest<UploadCompleteResponse>(
    `/v1/assets/${encodeURIComponent(assetId)}/complete`,
    { method: "POST", signal },
  );
}
