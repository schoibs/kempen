# Campaign Generator

A Python pipeline that turns a subject image and campaign brief into a short social video campaign.

The pipeline analyzes the supplied subject image, builds a campaign narrative, creates a scene-by-scene storyboard, then generates prompt payloads for image start frames and image-to-video generation.

## Pipeline Flow

1. `ProductAnalysisAgent` reads the product image and extracts conservative visible facts.
2. `NarrativeStrategistAgent` combines product analysis with the campaign theme, audience, and target duration.
3. `StoryboardAgent` converts the strategy into timed 9:16 video scenes.
4. `ImagePromptGeneratorService` creates one image edit prompt per scene for `gpt-image-2`.
5. `VideoPromptGeneratorService` creates one Kling image-to-video prompt per scene for `fal-ai/kling-video/v3/standard/image-to-video`.

## Requirements

- Python 3.10 or newer.
- An OpenAI API key for the OpenAI Agents SDK.
- An OpenAI-compatible Chat Completions endpoint for the prompt services.
- A TinyFish API key if you want the agents to use web search or web fetch.

Install dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Environment

Create a local `.env` file:

```bash
cp .env.sample .env
```

Set these values:

```dotenv
OPENAI_API_KEY=your_openai_api_key

TINYFISH_API_KEY=your_tinyfish_api_key

LLM_BASE_URL=https://api.openai.com/v1/chat/completions
LLM_API_KEY=your_openai_or_compatible_api_key
```

Notes:

- `OPENAI_API_KEY` is used by the campaign agents built with the OpenAI Agents SDK.
- `LLM_BASE_URL` and `LLM_API_KEY` are used by `clients/llm.py` for the image and video prompt generation services.
- `TINYFISH_API_KEY` is only needed when an agent invokes the `tinyfish_web_search` or `web_fetch` tool.

## Usage

Use the pipeline from Python:

```python
import json

from main import CampaignAgentPipeline, CampaignInput

pipeline = CampaignAgentPipeline(
    campaign_input=CampaignInput(
        product_image_path="assets/prime.png",
        campaign_theme="High-energy summer launch",
        target_audience="Gen Z gym-goers and student athletes",
        target_duration_sec=15,
        aspect_ratio="9:16",
    )
)

result = pipeline.run()

print(json.dumps(result, indent=2))
```

You can also run `main.py` directly:

```bash
python main.py
```
