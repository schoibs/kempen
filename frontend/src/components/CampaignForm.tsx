"use client";

import { useRouter } from "next/navigation";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
  type FormEvent,
} from "react";

import { completeUpload, createUploadIntent, uploadFile } from "@/lib/api/assets";
import { ApiClientError } from "@/lib/api/client";
import { createCampaign } from "@/lib/api/campaigns";
import {
  ASPECT_RATIOS,
  type AspectRatio,
  type CreateCampaignRequest,
} from "@/lib/api/types";
import { formatBytes } from "@/lib/format";

const MAX_FILE_BYTES = 20 * 1024 * 1024;
const MAX_TEXT_LENGTH = 2000;
const PENDING_STORAGE_KEY = "kempen.pendingCampaignSubmission.v1";
const PENDING_MAX_AGE_MS = 24 * 60 * 60 * 1000;
const IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"] as const;
const IMAGE_TYPE_LABELS: Record<string, string> = {
  "image/jpeg": "JPEG",
  "image/png": "PNG",
  "image/webp": "WebP",
};
const ASPECT_RATIO_OPTIONS: Array<{ value: AspectRatio; label: string }> = [
  { value: "9:16", label: "9:16 — Vertical" },
  { value: "16:9", label: "16:9 — Landscape" },
  { value: "1:1", label: "1:1 — Square" },
  { value: "4:3", label: "4:3 — Standard" },
  { value: "3:4", label: "3:4 — Portrait" },
  { value: "21:9", label: "21:9 — Cinematic" },
  { value: "auto", label: "Auto" },
];

type ImageContentType = (typeof IMAGE_TYPES)[number];
type SubmissionPhase = "preparing" | "uploading" | "verifying" | "starting";
type FieldName = "file" | "campaign_theme" | "target_audience" | "target_duration_sec" | "aspect_ratio";
type FieldErrors = Partial<Record<FieldName, string>>;
type PendingMode = "resume" | "retry";

interface PendingSubmission {
  idempotency_key: string;
  ready_asset_id: string;
  request: CreateCampaignRequest;
  created_at: string;
}

interface FormError {
  message: string;
  requestId?: string;
}

class SubmissionWorkflowError extends Error {}

const PHASE_LABELS: Record<SubmissionPhase, string> = {
  preparing: "Preparing upload",
  uploading: "Uploading image",
  verifying: "Verifying image",
  starting: "Starting campaign",
};

const FIELD_ORDER: FieldName[] = [
  "file",
  "campaign_theme",
  "target_audience",
  "target_duration_sec",
  "aspect_ratio",
];

export function CampaignForm() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [theme, setTheme] = useState("");
  const [audience, setAudience] = useState("");
  const [duration, setDuration] = useState("15");
  const [aspectRatio, setAspectRatio] = useState("9:16");
  const [touched, setTouched] = useState<Partial<Record<FieldName, boolean>>>({});
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<FormError | null>(null);
  const [phase, setPhase] = useState<SubmissionPhase | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [pending, setPending] = useState<PendingSubmission | null>(null);
  const [pendingMode, setPendingMode] = useState<PendingMode | null>(null);

  const submittingRef = useRef(false);
  const requestRef = useRef<AbortController | null>(null);
  const uploadedAssetIdRef = useRef<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const themeRef = useRef<HTMLTextAreaElement>(null);
  const audienceRef = useRef<HTMLTextAreaElement>(null);
  const durationRef = useRef<HTMLSelectElement>(null);
  const aspectRatioRef = useRef<HTMLSelectElement>(null);

  const draftValidation = useMemo(
    () => validateDraft(file, theme, audience, duration, aspectRatio),
    [file, theme, audience, duration, aspectRatio],
  );
  const locked = submitting || pending !== null;

  useEffect(() => {
    if (file === null) {
      setPreviewUrl(null);
      return;
    }

    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);

  useEffect(() => {
    const saved = readPendingSubmission();
    if (saved === null) {
      return;
    }

    setPending(saved);
    setPendingMode("resume");
    setTheme(saved.request.campaign_theme);
    setAudience(saved.request.target_audience);
    setDuration(String(saved.request.target_duration_sec));
    setAspectRatio(saved.request.aspect_ratio);
  }, []);

  useEffect(() => () => requestRef.current?.abort(), []);

  function selectFile(nextFile: File | null) {
    uploadedAssetIdRef.current = null;
    setFile(nextFile);
    setFormError(null);
    setPendingMode(null);
    setFieldErrors((current) => ({
      ...current,
      file: nextFile === null ? "Select a product image." : validateFile(nextFile),
    }));
    setTouched((current) => ({ ...current, file: true }));
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    selectFile(event.target.files?.[0] ?? null);
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    if (!locked) {
      selectFile(event.dataTransfer.files[0] ?? null);
    }
  }

  function removeFile() {
    selectFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  function validateBlurredField(field: FieldName) {
    setTouched((current) => ({ ...current, [field]: true }));
    setFieldErrors((current) => ({ ...current, [field]: draftValidation.errors[field] }));
  }

  function clearFieldError(field: FieldName) {
    if (fieldErrors[field]) {
      setFieldErrors((current) => ({ ...current, [field]: undefined }));
    }
  }

  function startOver() {
    clearPendingSubmission();
    setPending(null);
    setPendingMode(null);
    setFormError(null);
    setPhase(null);
    uploadedAssetIdRef.current = null;
    removeFile();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submittingRef.current) {
      return;
    }

    let activePhase: SubmissionPhase = "preparing";
    let pendingForAttempt = pending;

    if (pendingForAttempt === null && draftValidation.normalized === null) {
      setTouched(Object.fromEntries(FIELD_ORDER.map((field) => [field, true])));
      setFieldErrors(draftValidation.errors);
      focusFirstInvalidField(draftValidation.errors, {
        file: fileInputRef.current,
        campaign_theme: themeRef.current,
        target_audience: audienceRef.current,
        target_duration_sec: durationRef.current,
        aspect_ratio: aspectRatioRef.current,
      });
      return;
    }

    submittingRef.current = true;
    setSubmitting(true);
    setFormError(null);
    const controller = new AbortController();
    requestRef.current = controller;

    try {
      if (pendingForAttempt === null) {
        const normalized = draftValidation.normalized;
        if (normalized === null || file === null) {
          return;
        }

        let assetId = uploadedAssetIdRef.current;
        if (assetId === null) {
          activePhase = "preparing";
          setPhase(activePhase);
          const intent = await createUploadIntent(
            {
              filename: file.name,
              content_type: file.type as ImageContentType,
              size_bytes: file.size,
            },
            controller.signal,
          );
          if (typeof intent.asset?.id !== "string" || intent.asset.id.length === 0 || !intent.upload) {
            throw new Error("INVALID_UPLOAD_INTENT_RESPONSE");
          }

          activePhase = "uploading";
          setPhase(activePhase);
          try {
            await uploadFile(file, intent.upload, controller.signal);
          } catch (error) {
            uploadedAssetIdRef.current = null;
            throw error;
          }
          assetId = intent.asset.id;
          uploadedAssetIdRef.current = assetId;
        }

        activePhase = "verifying";
        setPhase(activePhase);
        const completed = await completeUpload(assetId, controller.signal);
        if (completed.status !== "ready" || typeof completed.id !== "string" || completed.id.length === 0) {
          throw new Error("UPLOAD_NOT_READY");
        }

        const request: CreateCampaignRequest = {
          product_image_asset_id: completed.id,
          ...normalized,
        };
        pendingForAttempt = {
          idempotency_key: `web-create-${crypto.randomUUID()}`,
          ready_asset_id: completed.id,
          request,
          created_at: new Date().toISOString(),
        };
        writePendingSubmission(pendingForAttempt);
        uploadedAssetIdRef.current = null;
        setPending(pendingForAttempt);
        setPendingMode("retry");
      }

      activePhase = "starting";
      setPhase(activePhase);
      const accepted = await createCampaign(
        pendingForAttempt.request,
        pendingForAttempt.idempotency_key,
        controller.signal,
      );
      if (typeof accepted.id !== "string" || accepted.id.length === 0) {
        throw new Error("INVALID_CAMPAIGN_RESPONSE");
      }

      clearPendingSubmission();
      setPending(null);
      router.push(`/campaigns/${encodeURIComponent(accepted.id)}`);
    } catch (error) {
      if (isAbortError(error)) {
        return;
      }

      const problemCode = error instanceof ApiClientError ? error.problem?.code : undefined;
      if (
        activePhase === "starting" &&
        (problemCode === "ASSET_NOT_READY" ||
          problemCode === "NOT_FOUND" ||
          problemCode === "INVALID_ASSET_STATE" ||
          problemCode === "IDEMPOTENCY_KEY_REUSED")
      ) {
        clearPendingSubmission();
        setPending(null);
        setPendingMode(null);
        setFieldErrors((current) => ({
          ...current,
          file: "Upload the product image again before starting a new campaign.",
        }));
        setTouched((current) => ({ ...current, file: true }));
      } else {
        setPendingMode("retry");
      }

      if (
        activePhase === "verifying" &&
        (problemCode === "ASSET_MISMATCH" ||
          problemCode === "INVALID_ASSET_STATE" ||
          problemCode === "NOT_FOUND")
      ) {
        uploadedAssetIdRef.current = null;
        setFieldErrors((current) => ({
          ...current,
          file: "The stored image did not match the selected file. Upload it again.",
        }));
        setTouched((current) => ({ ...current, file: true }));
      }

      const mappedErrors = mapApiFieldErrors(error);
      if (Object.keys(mappedErrors).length > 0) {
        setFieldErrors((current) => ({ ...current, ...mappedErrors }));
        setTouched((current) => ({
          ...current,
          ...Object.fromEntries(Object.keys(mappedErrors).map((field) => [field, true])),
        }));
      }
      setFormError(toFormError(error, activePhase));
    } finally {
      if (requestRef.current === controller) {
        requestRef.current = null;
      }
      submittingRef.current = false;
      setSubmitting(false);
      setPhase(null);
    }
  }

  return (
    <section className="create-section" aria-labelledby="create-campaign-title">
      <div className="create-heading">
        <div>
          <p className="eyebrow">New production</p>
          <h2 id="create-campaign-title">Create campaign</h2>
        </div>
        <p>Pair one product image with a focused brief. Kempen will shape the story and motion.</p>
      </div>

      {pending && (
        <div className="notice notice-warning recovery-notice" role="status">
          <div>
            <strong>{pendingMode === "resume" ? "A submission is ready to resume." : "Your campaign request is ready to retry."}</strong>
            <p>
              The image is already verified. Continuing reuses the same request so it cannot create
              a duplicate campaign.
            </p>
          </div>
          <button type="button" className="text-button" onClick={startOver} disabled={submitting}>
            Start over
          </button>
        </div>
      )}

      <form className="campaign-form" onSubmit={(event) => void handleSubmit(event)} noValidate>
        <div className="campaign-form-main">
          <fieldset className="form-fields" disabled={locked}>
            <legend className="sr-only">Campaign details</legend>

            <div className="field-group field-wide">
              <div className="field-label-row">
                <label id="product-image-label" htmlFor="product-image">Product image <span>Required</span></label>
                <span>JPEG, PNG or WebP · 20 MB max</span>
              </div>

              {pending ? (
                <div className="upload-ready" aria-labelledby="product-image-label">
                  <span className="upload-ready-mark" aria-hidden="true">✓</span>
                  <div>
                    <strong>Product image verified</strong>
                    <p>The saved submission will reuse this upload.</p>
                  </div>
                </div>
              ) : file && previewUrl ? (
                <div className="image-selection">
                  <img src={previewUrl} alt={`Preview of ${file.name}`} />
                  <div className="image-selection-copy">
                    <strong>{file.name}</strong>
                    <span>{IMAGE_TYPE_LABELS[file.type] ?? file.type} · {formatBytes(file.size)}</span>
                    <div className="image-selection-actions">
                      <label className="text-button" htmlFor="product-image">Replace image</label>
                      <button type="button" className="text-button" onClick={removeFile}>Remove</button>
                    </div>
                  </div>
                  <input
                    ref={fileInputRef}
                    className="visually-hidden-input"
                    id="product-image"
                    name="product_image"
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={handleFileChange}
                    aria-describedby={fieldErrors.file ? "product-image-error" : undefined}
                    aria-invalid={Boolean(fieldErrors.file)}
                  />
                </div>
              ) : (
                <label
                  className="image-dropzone"
                  htmlFor="product-image"
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={handleDrop}
                >
                  <input
                    ref={fileInputRef}
                    className="visually-hidden-input"
                    id="product-image"
                    name="product_image"
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={handleFileChange}
                    onBlur={() => validateBlurredField("file")}
                    aria-describedby="product-image-help product-image-error"
                    aria-invalid={Boolean(fieldErrors.file)}
                  />
                  <span className="dropzone-mark" aria-hidden="true">+</span>
                  <strong>Choose a product image</strong>
                  <span id="product-image-help">or drop one here</span>
                </label>
              )}
              {touched.file && fieldErrors.file && <p className="field-error" id="product-image-error">{fieldErrors.file}</p>}
            </div>

            <div className="field-group field-wide">
              <div className="field-label-row">
                <label htmlFor="campaign-theme">Campaign theme <span>Required</span></label>
                {theme.length >= 1800 && <span>{MAX_TEXT_LENGTH - theme.length} characters left</span>}
              </div>
              <textarea
                ref={themeRef}
                id="campaign-theme"
                name="campaign_theme"
                rows={4}
                maxLength={MAX_TEXT_LENGTH}
                value={theme}
                onChange={(event) => { setTheme(event.target.value); clearFieldError("campaign_theme"); }}
                onBlur={() => validateBlurredField("campaign_theme")}
                placeholder="Example: Bright, sunny and fun"
                aria-describedby="campaign-theme-help campaign-theme-error"
                aria-invalid={Boolean(fieldErrors.campaign_theme)}
              />
              <p className="field-help" id="campaign-theme-help">Describe the creative world, energy, or occasion.</p>
              {touched.campaign_theme && fieldErrors.campaign_theme && <p className="field-error" id="campaign-theme-error">{fieldErrors.campaign_theme}</p>}
            </div>

            <div className="field-group field-wide">
              <div className="field-label-row">
                <label htmlFor="target-audience">Target audience <span>Required</span></label>
                {audience.length >= 1800 && <span>{MAX_TEXT_LENGTH - audience.length} characters left</span>}
              </div>
              <textarea
                ref={audienceRef}
                id="target-audience"
                name="target_audience"
                rows={4}
                maxLength={MAX_TEXT_LENGTH}
                value={audience}
                onChange={(event) => { setAudience(event.target.value); clearFieldError("target_audience"); }}
                onBlur={() => validateBlurredField("target_audience")}
                placeholder="Example: Young adults who enjoy summer festivals"
                aria-describedby="target-audience-help target-audience-error"
                aria-invalid={Boolean(fieldErrors.target_audience)}
              />
              <p className="field-help" id="target-audience-help">Name the people this campaign should speak to.</p>
              {touched.target_audience && fieldErrors.target_audience && <p className="field-error" id="target-audience-error">{fieldErrors.target_audience}</p>}
            </div>

            <div className="field-group">
              <label htmlFor="campaign-duration">Duration <span>Required</span></label>
              <select
                ref={durationRef}
                id="campaign-duration"
                name="target_duration_sec"
                value={duration}
                onChange={(event) => { setDuration(event.target.value); clearFieldError("target_duration_sec"); }}
                onBlur={() => validateBlurredField("target_duration_sec")}
                aria-describedby="campaign-duration-error"
                aria-invalid={Boolean(fieldErrors.target_duration_sec)}
              >
                {Array.from({ length: 12 }, (_, index) => index + 4).map((seconds) => (
                  <option value={seconds} key={seconds}>{seconds} seconds</option>
                ))}
              </select>
              {touched.target_duration_sec && fieldErrors.target_duration_sec && <p className="field-error" id="campaign-duration-error">{fieldErrors.target_duration_sec}</p>}
            </div>

            <div className="field-group">
              <label htmlFor="aspect-ratio">Aspect ratio <span>Required</span></label>
              <select
                ref={aspectRatioRef}
                id="aspect-ratio"
                name="aspect_ratio"
                value={aspectRatio}
                onChange={(event) => { setAspectRatio(event.target.value); clearFieldError("aspect_ratio"); }}
                onBlur={() => validateBlurredField("aspect_ratio")}
                aria-describedby="aspect-ratio-error"
                aria-invalid={Boolean(fieldErrors.aspect_ratio)}
              >
                {ASPECT_RATIO_OPTIONS.map((option) => (
                  <option value={option.value} key={option.value}>{option.label}</option>
                ))}
              </select>
              {touched.aspect_ratio && fieldErrors.aspect_ratio && <p className="field-error" id="aspect-ratio-error">{fieldErrors.aspect_ratio}</p>}
            </div>
          </fieldset>
        </div>

        <div className="submission-panel">
          <div>
            <p className="eyebrow">Ready when you are</p>
            <h3>From still image to campaign story.</h3>
            <p>Your campaign begins as soon as the image is uploaded and verified.</p>
          </div>

          {formError && (
            <div className="form-error" role="alert">
              <strong>Submission paused</strong>
              <p>{formError.message}</p>
              {formError.requestId && <small>Reference: {formError.requestId}</small>}
            </div>
          )}

          <div className="submission-status" aria-live="polite">
            {phase ? <><span className="submission-pulse" aria-hidden="true" />{PHASE_LABELS[phase]}</> : <span>Four secure steps, then generation begins.</span>}
          </div>

          <button
            className="button button-primary submit-button"
            type="submit"
            disabled={submitting || (pending === null && draftValidation.normalized === null)}
          >
            {submitting && phase
              ? PHASE_LABELS[phase]
              : pendingMode === "resume"
                ? "Resume campaign submission"
                : pendingMode === "retry"
                  ? "Retry submission"
                  : "Start campaign"}
          </button>
        </div>
      </form>
    </section>
  );
}

function validateDraft(
  file: File | null,
  theme: string,
  audience: string,
  duration: string,
  aspectRatio: string,
): {
  errors: FieldErrors;
  normalized: Omit<CreateCampaignRequest, "product_image_asset_id"> | null;
} {
  const errors: FieldErrors = {};
  const fileError = file === null ? "Select a product image." : validateFile(file);
  if (fileError) {
    errors.file = fileError;
  }

  const normalizedTheme = theme.trim();
  if (!normalizedTheme) {
    errors.campaign_theme = "Enter a campaign theme.";
  } else if (normalizedTheme.length > MAX_TEXT_LENGTH) {
    errors.campaign_theme = `Keep the campaign theme to ${MAX_TEXT_LENGTH} characters or fewer.`;
  }

  const normalizedAudience = audience.trim();
  if (!normalizedAudience) {
    errors.target_audience = "Enter a target audience.";
  } else if (normalizedAudience.length > MAX_TEXT_LENGTH) {
    errors.target_audience = `Keep the target audience to ${MAX_TEXT_LENGTH} characters or fewer.`;
  }

  const parsedDuration = Number(duration);
  if (!Number.isInteger(parsedDuration) || parsedDuration < 4 || parsedDuration > 15) {
    errors.target_duration_sec = "Choose a whole duration from 4 through 15 seconds.";
  }

  if (!isAspectRatio(aspectRatio)) {
    errors.aspect_ratio = "Choose a supported aspect ratio.";
  }

  return {
    errors,
    normalized: Object.keys(errors).length === 0 && isAspectRatio(aspectRatio)
      ? {
          campaign_theme: normalizedTheme,
          target_audience: normalizedAudience,
          target_duration_sec: parsedDuration,
          aspect_ratio: aspectRatio,
        }
      : null,
  };
}

function validateFile(file: File): string | undefined {
  if (!IMAGE_TYPES.includes(file.type as ImageContentType)) {
    return "Choose a JPEG, PNG, or WebP image.";
  }
  if (file.size <= 0) {
    return "The selected image is empty.";
  }
  if (file.size > MAX_FILE_BYTES) {
    return "Choose an image no larger than 20 MB.";
  }
  return undefined;
}

function mapApiFieldErrors(error: unknown): FieldErrors {
  if (!(error instanceof ApiClientError)) {
    return {};
  }

  const mapped: FieldErrors = {};
  for (const fieldError of error.problem?.errors ?? []) {
    const backendField = [...fieldError.location].reverse().find((part) => typeof part === "string");
    const field = mapBackendField(backendField);
    if (field) {
      mapped[field] = fieldError.message;
    }
  }
  return mapped;
}

function mapBackendField(field: string | undefined): FieldName | null {
  if (field === "campaign_theme" || field === "target_audience" || field === "target_duration_sec" || field === "aspect_ratio") {
    return field;
  }
  if (field === "filename" || field === "content_type" || field === "size_bytes" || field === "product_image_asset_id") {
    return "file";
  }
  return null;
}

function toFormError(error: unknown, phase: SubmissionPhase): FormError {
  const fallback: Record<SubmissionPhase, string> = {
    preparing: "The image upload could not be prepared. Try again.",
    uploading: "The image upload could not be completed. Try again.",
    verifying: "The uploaded image could not be verified. Try again.",
    starting: "The campaign could not be started. Try again.",
  };
  if (error instanceof SubmissionWorkflowError) {
    return { message: error.message };
  }
  if (!(error instanceof ApiClientError)) {
    return { message: fallback[phase] };
  }

  const retryCopy = error.retryAfterSeconds === null
    ? ""
    : ` Try again in ${error.retryAfterSeconds} seconds.`;
  return {
    message: `${error.message}${retryCopy}`,
    requestId: error.problem?.request_id,
  };
}

function focusFirstInvalidField(
  errors: FieldErrors,
  elements: Record<FieldName, HTMLElement | null>,
) {
  const firstInvalid = FIELD_ORDER.find((field) => errors[field]);
  if (firstInvalid) {
    elements[firstInvalid]?.focus();
  }
}

function writePendingSubmission(pending: PendingSubmission) {
  try {
    sessionStorage.setItem(PENDING_STORAGE_KEY, JSON.stringify(pending));
  } catch {
    throw new SubmissionWorkflowError(
      "This browser cannot save the recovery record needed to submit safely. Enable session storage and try again.",
    );
  }
}

function readPendingSubmission(): PendingSubmission | null {
  let raw: string | null;
  try {
    raw = sessionStorage.getItem(PENDING_STORAGE_KEY);
  } catch {
    return null;
  }
  if (raw === null) {
    return null;
  }

  try {
    const value: unknown = JSON.parse(raw);
    if (!isPendingSubmission(value)) {
      clearPendingSubmission();
      return null;
    }
    const createdAt = Date.parse(value.created_at);
    if (Number.isNaN(createdAt) || Date.now() - createdAt >= PENDING_MAX_AGE_MS || createdAt > Date.now()) {
      clearPendingSubmission();
      return null;
    }
    return value;
  } catch {
    clearPendingSubmission();
    return null;
  }
}

function clearPendingSubmission() {
  try {
    sessionStorage.removeItem(PENDING_STORAGE_KEY);
  } catch {
    // Storage may be unavailable; there is nothing else for the UI to clear.
  }
}

function isPendingSubmission(value: unknown): value is PendingSubmission {
  if (!isRecord(value) || !isRecord(value.request)) {
    return false;
  }

  const request = value.request;
  return (
    typeof value.idempotency_key === "string" &&
    value.idempotency_key.length >= 16 &&
    value.idempotency_key.length <= 128 &&
    typeof value.ready_asset_id === "string" &&
    value.ready_asset_id.length >= 1 &&
    typeof value.created_at === "string" &&
    request.product_image_asset_id === value.ready_asset_id &&
    typeof request.campaign_theme === "string" &&
    request.campaign_theme.length >= 1 &&
    request.campaign_theme.length <= MAX_TEXT_LENGTH &&
    typeof request.target_audience === "string" &&
    request.target_audience.length >= 1 &&
    request.target_audience.length <= MAX_TEXT_LENGTH &&
    typeof request.target_duration_sec === "number" &&
    Number.isInteger(request.target_duration_sec) &&
    request.target_duration_sec >= 4 &&
    request.target_duration_sec <= 15 &&
    isAspectRatio(request.aspect_ratio)
  );
}

function isAspectRatio(value: unknown): value is AspectRatio {
  return typeof value === "string" && ASPECT_RATIOS.includes(value as AspectRatio);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}
