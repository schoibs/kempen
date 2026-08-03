# Kempen

Kempen turns a product image and campaign brief into a short-form campaign package: researched product facts, a narrative strategy, a storyboard sheet, and a finished video.
## How it works

```text
product image + campaign brief
            |
            v
Next.js workspace -> FastAPI -> PostgreSQL transactional outbox
                                      |
                                      v
                              Redis/Celery workers
                                      |
                 +--------------------+--------------------+
                 v                    v                    v
        product research      storyboard image      campaign video
        and strategy             (OpenAI)          (fal.ai Seedance)
                 |                    |                    |
                 +--------------------+--------------------+
                                      v
                              private object storage
                                      |
                                      v
                           progress and results in the UI
```

TinyFish powers web research, OpenAI powers product analysis, narrative planning, and storyboard generation, and fal.ai generates the final video.

## Prerequisites

- Docker with Compose
- OpenAI, TinyFish, and fal.ai credentials
- [Optional] Python 3.12 and Node.js 22 when running the backend or frontend outside containers

## Quick start with Docker Compose

Create the local environment file and add valid provider credentials:

```bash
cp .env.example .env
```

```dotenv
OPENAI_API_KEY=your_openai_api_key
TINYFISH_API_KEY=your_tinyfish_api_key
FAL_KEY=your_fal_api_key
```

Build and start the complete stack:

```bash
docker compose up -d --build
docker compose ps
```

Compose applies the database migrations before starting the API. It also starts separate planning and media workers, the transactional-outbox dispatcher, PostgreSQL, Redis, MinIO, and the frontend.

- Web application: `http://127.0.0.1:3000`
- API and OpenAPI documentation: `http://127.0.0.1:8000` and `http://127.0.0.1:8000/docs`
- MinIO console: `http://127.0.0.1:9001`

Starting the stack and checking health do not call the providers, but creating a campaign does incur charges.

## Local development

Create a virtual environment and install the backend dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install the frontend dependencies:

```bash
cd frontend
npm ci
cd ..
```

With `.env` configured, start only the infrastructure containers and apply the migrations:

```bash
docker compose up -d postgres redis minio
alembic upgrade head
```

Run each application process in a separate terminal from the repository root, with the virtual environment activated for Python processes:

```bash
uvicorn api.app:app --reload
```

```bash
celery -A workers.celery_app:celery_app worker --loglevel=INFO -Q planning,media
```

```bash
python -m workers.dispatcher
```

Run the frontend from `frontend/`:

```bash
npm run dev
```

The frontend defaults to proxying `/v1` and `/health` requests to `http://127.0.0.1:8000`. Set `API_INTERNAL_URL` before starting or building the frontend when the API is elsewhere.

## Health and verification

Check the running backend and its dependencies with:

```bash
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/health/ready
```

The readiness endpoint checks configuration, the database migration revision, Redis, and the object-storage bucket. For a bounded dispatcher dependency check, run:

```bash
python -m workers.dispatcher --once
```

There is currently no automated test suite. After Python changes, check that modules compile:

```bash
python -m compileall -q .
```

After frontend changes, run its production build from `frontend/`:

```bash
npm run build
```

## API workflow

The web application performs this asynchronous API flow:

1. `POST /v1/assets/upload-intents` with the image filename, content type, size, and optional SHA-256 digest.
2. Upload the exact image bytes to the returned presigned URL using the returned method and headers.
3. `POST /v1/assets/{asset_id}/complete` to verify and finalize the upload.
4. `POST /v1/campaigns` with the ready asset ID and an `Idempotency-Key` header of 16–128 characters.
5. Poll `GET /v1/campaigns/{campaign_id}` until the campaign reaches a terminal state.

Campaign endpoints also support cursor-based listing, cancellation, and retrying retryable failures:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/v1/campaigns` | List campaigns; optionally filter by status |
| `GET` | `/v1/campaigns/{campaign_id}` | Read progress, results, or error details |
| `POST` | `/v1/campaigns/{campaign_id}/cancel` | Request cancellation |
| `POST` | `/v1/campaigns/{campaign_id}/retry` | Retry a retryable failed campaign; requires `Idempotency-Key` |
| `GET` | `/v1/assets/{asset_id}/download` | Create a short-lived download URL for a ready asset |

Product images may be JPEG, PNG, or WebP and are limited to 20 MiB by default. Video duration must be a whole number of seconds from `4` through `15`. Supported aspect ratios are `auto`, `21:9`, `16:9`, `4:3`, `1:1`, `3:4`, and `9:16`.

Uploaded and generated files remain in the configured private object-storage bucket. API responses provide short-lived presigned URLs rather than server-local paths. Authentication is disabled by default, and local requests use a fixed development principal.

## Configuration

Application settings are defined in `app_config.py`, loaded from the repository-root `.env`, and generally use the `CAMPAIGN_` prefix. Start with `.env.example`, which documents the available local settings. Common overrides include:

```dotenv
CAMPAIGN_ENVIRONMENT=local
CAMPAIGN_LOG_LEVEL=INFO
CAMPAIGN_DATABASE_URL=postgresql+psycopg://campaign:campaign@localhost:5432/campaign
CAMPAIGN_REDIS_URL=redis://localhost:6379/0
CAMPAIGN_OBJECT_STORAGE_ENDPOINT=http://localhost:9000
CAMPAIGN_OBJECT_STORAGE_PUBLIC_ENDPOINT=http://localhost:9000
```

`CAMPAIGN_OBJECT_STORAGE_ENDPOINT` is used by backend processes. `CAMPAIGN_OBJECT_STORAGE_PUBLIC_ENDPOINT` must be reachable by the browser because upload and download URLs are presigned against it.

To enable authentication, set `CAMPAIGN_AUTH_ENABLED=true` and configure both `CAMPAIGN_OIDC_ISSUER` and `CAMPAIGN_OIDC_AUDIENCE`. Keep `.env` local and never commit or log credentials.
