# Campaign Generator

Campaign Generator is a Python pipeline that turns a product image and campaign brief into a story-driven social ad.

## What It Does

1. Analyzes the supplied product image.
2. Researches current public context for the product.
3. Builds a creative campaign narrative strategy from the brief.
4. Generates a cinematic storyboard sheet.
5. Generates a short campaign video.

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Create a `.env` file in the project root. You can start from `.env.sample`:

```bash
cp .env.sample .env
```

Then fill in the required API keys:

```bash
OPENAI_API_KEY=your_openai_api_key
FAL_KEY=your_fal_api_key
TINYFISH_API_KEY=your_tinyfish_api_key
```

The pipeline calls live OpenAI, fal.ai, and TinyFish APIs.

## Run The Pipeline

The sample entrypoint in `main.py` uses `assets/prime.png` and a short campaign brief:

```bash
python3 main.py
```

## Customize The Campaign

Edit the `CampaignInput` in `main.py`:

```python
pipeline = CampaignAgentPipeline(
    campaign_input=CampaignInput(
        product_image_path="assets/prime.png",
        campaign_theme="bright, sunny and fun",
        target_audience="young adults who love summer festivals, beach parties and clubs",
        target_duration_sec=15,
        aspect_ratio="9:16",
    )
)
pipeline.run()
```

Supported video durations are integer seconds from `4` through `15`.

Supported aspect ratios are:

```text
auto, 21:9, 16:9, 4:3, 1:1, 3:4, 9:16
```

## Pipeline Outputs

`CampaignAgentPipeline.run()` returns a dictionary with:

- `input`: the campaign input values
- `product_analysis`: structured product facts and researched context
- `narrative_strategy`: campaign concept, premise, hook, conflict, and tone
- `storyboard`: the generated storyboard image path
- `video`: the generated video path

By default, generated media is written to `assets/generated/storyboard_sheet.png` and `assets/generated/campaign_video.mp4`.
