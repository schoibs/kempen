from __future__ import annotations

from pydantic import Field

from ..schemas import StrictModel


class Color(StrictModel):
    name: str
    hex: str = Field(description="Best-effort hex color in #RRGGBB format.")


class PreservationConstraints(StrictModel):
    must_preserve: list[str]
    must_not_introduce: list[str]


class ProductAnalysisOutput(StrictModel):
    product_name: str
    category: str
    primary_colors: Color
    visible_text: list[str]
    preservation_constraints: PreservationConstraints
