import type { ApiFieldError, ApiProblem } from "./types";

type RequestOptions = Omit<RequestInit, "body"> & {
  json?: unknown;
};

export class ApiClientError extends Error {
  readonly status: number;
  readonly problem: ApiProblem | null;

  constructor(status: number, problem: ApiProblem | null, fallbackMessage: string) {
    super(problem?.detail ?? fallbackMessage);
    this.name = "ApiClientError";
    this.status = status;
    this.problem = problem;
  }
}

export async function apiRequest<T extends object>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  if (!path.startsWith("/")) {
    throw new Error("API paths must be same-origin relative paths.");
  }

  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.json !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, {
    ...options,
    headers,
    body: options.json === undefined ? undefined : JSON.stringify(options.json),
  });
  const payload = await readJsonObject(response);

  if (!response.ok) {
    const problem = toApiProblem(payload, response.status);
    throw new ApiClientError(
      response.status,
      problem,
      `The request could not be completed (HTTP ${response.status}).`,
    );
  }

  if (payload === null) {
    throw new ApiClientError(
      response.status,
      null,
      "The server returned an unreadable response.",
    );
  }

  return payload as T;
}

async function readJsonObject(response: Response): Promise<Record<string, unknown> | null> {
  const body = await response.text();
  if (!body.trim()) {
    return null;
  }

  const contentType = response.headers.get("content-type")?.toLowerCase() ?? "";
  const looksLikeJson = contentType.includes("json") || /^[\s]*[{[]/.test(body);
  if (!looksLikeJson) {
    return null;
  }

  try {
    const parsed: unknown = JSON.parse(body);
    return isRecord(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function toApiProblem(
  value: Record<string, unknown> | null,
  responseStatus: number,
): ApiProblem | null {
  if (
    value === null ||
    typeof value.title !== "string" ||
    typeof value.code !== "string" ||
    typeof value.detail !== "string"
  ) {
    return null;
  }

  return {
    type: typeof value.type === "string" ? value.type : undefined,
    title: value.title,
    status: typeof value.status === "number" ? value.status : responseStatus,
    code: value.code,
    detail: value.detail,
    request_id: typeof value.request_id === "string" ? value.request_id : undefined,
    errors: Array.isArray(value.errors) ? value.errors.flatMap(toFieldError) : [],
  };
}

function toFieldError(value: unknown): ApiFieldError[] {
  if (
    !isRecord(value) ||
    !Array.isArray(value.location) ||
    typeof value.message !== "string"
  ) {
    return [];
  }

  const location = value.location.filter(
    (part): part is string | number => typeof part === "string" || typeof part === "number",
  );
  return [{ location, message: value.message }];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
