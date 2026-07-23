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

`CampaignAgentPipeline.run()` returns the inputs, the two structured planning outputs, and paths/metadata for the generated storyboard and video.

## Prerequisites

- Python 3.10 or later
- API credentials for OpenAI, TinyFish, and fal.ai

All stages make external API requests and may incur provider charges.

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the repository root:

```dotenv
OPENAI_API_KEY=your_openai_api_key
TINYFISH_API_KEY=your_tinyfish_api_key
FAL_KEY=your_fal_api_key
```

## Run the sample campaign

The sample in [`main.py`](main.py) uses [`assets/prime.png`](assets/prime.png):

```bash
python main.py
```

On success, the default generated assets are written to:

- `assets/generated/storyboard_sheet.png`
- `assets/generated/campaign_video.mp4`

The video stage also returns the hosted video URL, generation seed (when provided), and fal request ID.

## Customize a campaign

Edit the `CampaignInput` in `main.py`, or import the pipeline into your own script:

```python
from main import CampaignAgentPipeline, CampaignInput

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

Video durations must be whole seconds from `4` through `15`. Supported aspect ratios are:

```text
auto, 21:9, 16:9, 4:3, 1:1, 3:4, 9:16
```
