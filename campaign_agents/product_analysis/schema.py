from __future__ import annotations

from pydantic import Field

from ..schemas import StrictModel


class Color(StrictModel):
    name: str
    hex: str = Field(description="Best-effort hex color in #RRGGBB format.")

class ProductAnalysisOutput(StrictModel):
    product_name: str
    category: str
    primary_colors: Color
    visible_facts: list[str]
    additional_facts: list[str]

