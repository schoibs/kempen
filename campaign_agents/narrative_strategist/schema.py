from __future__ import annotations

from pydantic import Field

from ..schemas import StrictModel


class NarrativeStrategyOutput(StrictModel):
    concept: str = Field(description="The main idea behind the campaign.")
    story_premise: str = Field(description="The core narrative setup: who, where, and what happens")
    hook: str = Field(description="The opening moment of the story that grabs the audience attention")
    conflict: str = Field(description="What gets in the way in the story and creates narrative momentum")
    tone: list[str] = Field(
        description="The emotional style: funny, touching, luxurious, rebellious, etc.",
        min_length=1,
        max_length=3,
    )
