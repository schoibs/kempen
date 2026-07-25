# Kempen

Kempen turns a product image and a campaign brief into a social-video campaign package: researched product facts, a narrative strategy, a storyboard sheet, and a finished video.

## How it works

```text
product image + campaign brief
            |
            v
product analysis and web research
            |
            v
campaign narrative strategy
            |
            v
reference-guided storyboard image
            |
            v
reference-guided campaign video
```

Kempen has two execution paths:

- `main.py` runs the pipeline synchronously and writes generated files locally.
- `api/app.py` exposes an asynchronous FastAPI API backed by PostgreSQL, Redis/Celery, and S3-compatible object storage.

## Prerequisites

- Python 3.10 or later
- Docker with Compose, for the asynchronous API
- OpenAI, TinyFish, and fal.ai credentials only when using real providers

## Python setup

Create a virtual environment and install the dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Configuration is loaded from an optional `.env` file in the repository root. The built-in local defaults enable fake providers and point infrastructure clients at the services in `compose.yaml`.

## Run the synchronous sample

The sample in [`main.py`](main.py) uses [`assets/prime.png`](assets/prime.png):

```bash
python main.py
```

In the default fake-provider mode, this produces deterministic placeholder artifacts without contacting OpenAI, TinyFish, or fal.ai. The outputs overwrite:

- `assets/generated/storyboard_sheet.png`
- `assets/generated/campaign_video.mp4`

To customize the campaign, edit the sample or import the pipeline:

```python
from domain.campaigns import CampaignInput
from main import CampaignAgentPipeline

pipeline = CampaignAgentPipeline(
    CampaignInput(
        product_image_path="assets/my-product.png",
        campaign_theme="bright, sunny, and fun",
        target_audience="young adults who love summer festivals",
        target_duration_sec=15,
        aspect_ratio="9:16",
    )
)

result = pipeline.run()
print(result["video"].video_path)
```

Video duration must be a whole number of seconds from `4` through `15`. Supported aspect ratios are `auto`, `21:9`, `16:9`, `4:3`, `1:1`, `3:4`, and `9:16`.

## Run the asynchronous API

Start PostgreSQL, Redis, and MinIO, then apply the database migrations:

```bash
docker compose up -d
alembic upgrade head
```

Run each application process in a separate terminal with the virtual environment activated:

```bash
uvicorn api.app:app --reload
```

```bash
celery -A workers.celery_app:celery_app worker --loglevel=INFO -Q planning,media
```

```bash
python -m workers.dispatcher
```

The API is available at `http://127.0.0.1:8000`, with interactive OpenAPI documentation at `http://127.0.0.1:8000/docs`. MinIO's local console is available at `http://127.0.0.1:9001` using the development credentials from `compose.yaml`.

Check process and dependency health with:

```bash
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/health/ready
```

The readiness endpoint verifies configuration, the database migration revision, Redis, and the object-storage bucket. For a bounded dispatcher dependency check, run:

```bash
python -m workers.dispatcher --once
```

## API workflow

The asynchronous flow is:

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

Uploaded and generated files remain in the configured private object-storage bucket. API responses provide short-lived presigned URLs rather than server-local paths. Authentication is currently disabled by default, and local requests use a fixed development principal.

## Configuration

Application settings live in `app_config.py`. Most environment variables use the `CAMPAIGN_` prefix. Common overrides include:

```dotenv
CAMPAIGN_ENVIRONMENT=local
CAMPAIGN_LOG_LEVEL=INFO
CAMPAIGN_FAKE_PROVIDER_MODE=true
CAMPAIGN_DATABASE_URL=postgresql+psycopg://campaign:campaign@localhost:5432/campaign
CAMPAIGN_REDIS_URL=redis://localhost:6379/0
CAMPAIGN_OBJECT_STORAGE_ENDPOINT=http://localhost:9000
```

To use real providers, explicitly disable fake mode and supply all provider credentials:

```dotenv
CAMPAIGN_FAKE_PROVIDER_MODE=false
OPENAI_API_KEY=your_openai_api_key
TINYFISH_API_KEY=your_tinyfish_api_key
FAL_KEY=your_fal_api_key
```

Real-provider runs make external requests and can incur charges. Keep `.env` local and never commit or log credentials.
