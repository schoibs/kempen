import { apiRequest } from "./client";
import type {
  UploadCompleteResponse,
  UploadDescriptor,
  UploadIntentRequest,
  UploadIntentResponse,
} from "./types";

export class StorageUploadError extends Error {
  constructor() {
    super("The image could not be uploaded to storage.");
    this.name = "StorageUploadError";
  }
}

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

export async function uploadFile(
  file: File,
  upload: UploadDescriptor,
  signal?: AbortSignal,
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(upload.url, {
      method: upload.method,
      headers: upload.headers,
      body: file,
      credentials: "omit",
      signal,
    });
  } catch (error) {
    if (isAbortError(error)) {
      throw error;
    }
    throw new StorageUploadError();
  }

  if (!response.ok) {
    throw new StorageUploadError();
  }
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}
