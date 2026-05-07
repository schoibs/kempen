from __future__ import annotations

from pydantic import Field

from ..schemas import StrictModel


class NarrativeStrategyOutput(StrictModel):
    concept_title: str
    hook: str
    message: str
    tone: list[str] = Field(min_length=1)
    cta: str
