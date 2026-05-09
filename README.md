# Campaign Generator

A Python pipeline that turns a subject image and campaign brief into a short social video campaign.

The pipeline analyzes the supplied subject image, builds a campaign narrative, creates a scene-by-scene storyboard, then generates prompt payloads for image start frames and image-to-video generation.

## Pipeline

1. `ProductAnalysisAgent` reads the product image and extracts conservative
   product facts, visible constraints, and supporting research notes.
2. `NarrativeStrategistAgent` combines the product analysis with the campaign
   theme, target audience, and target duration.
3. `StoryboardAgent` turns the strategy into a timed vertical storyboard with
   subjects, scenes, shot sequences, audio direction, and text overlay guidance.
4. `VideoPromptGeneratorService` converts storyboard scenes into validated Kling
   v3 image-to-video prompt payloads.
  
## Requirements

- Python 3.10 or newer
- OpenAI API access for the OpenAI Agents SDK
- An OpenAI-compatible Chat Completions endpoint for `clients/llm.py`
- TinyFish API access if live agents use web search or fetch tools

Install dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Environment

Create a local `.env` file from the sample:

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

- `OPENAI_API_KEY` is used by agents built on the OpenAI Agents SDK.
- `LLM_BASE_URL` and `LLM_API_KEY` are used by `clients/llm.py`. The client
  accepts either a base URL or a `/chat/completions` URL and normalizes it.
- `TINYFISH_API_KEY` is required only when an agent invokes
  `tinyfish_web_search` or `web_fetch`.

## Usage

Run the sample pipeline:

```bash
python main.py
```

Use the pipeline from Python:

```python
import json

from main import CampaignAgentPipeline, CampaignInput

pipeline = CampaignAgentPipeline(
    campaign_input=CampaignInput(
        product_image_path="assets/prime.png",
        campaign_theme="bright, sunny and fun",
        target_audience="young adults who love summer festivals, beach parties and clubs",
        target_duration_sec=15,
        aspect_ratio="9:16",
    )
)

result = pipeline.run()
print(json.dumps(result, indent=2))
```
