"""Pydantic models and enums for tool parameters and responses.

Typed parameters give MCP clients a precise schema, which helps the LLM call
your tools correctly. Prefer enums for closed sets of values and Pydantic
models for structured inputs/outputs.

These are illustrative — replace them with models for your own service.
"""

from __future__ import annotations

import math
import re
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ResponseFormat(str, Enum):
    """How a tool should shape its return value.

    - JSON     → machine-readable dict/list (best for chaining tool calls)
    - MARKDOWN → human-readable text (best for direct display)
    """

    JSON = "json"
    MARKDOWN = "markdown"


class PaginationParams(BaseModel):
    """Reusable pagination inputs for list-style tools.

    Federal APIs almost always paginate. Expose these to the caller (or handle
    paging internally) and return `has_more` / `next_offset` in your response.
    """

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of items to return (1–100).",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of items to skip from the start of the result set.",
    )


LayerId = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")]
LayerIds = Annotated[list[LayerId], Field(min_length=1, max_length=20)]
ModuleId = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")]
ModuleIds = Annotated[list[ModuleId], Field(min_length=1, max_length=20)]
Resolution = (
    Literal["auto", "native"]
    | Annotated[float, Field(gt=0, le=100000, allow_inf_nan=False)]
)


class Geometry(BaseModel):
    """Bounded two-dimensional WGS84 GeoJSON geometry (longitude, latitude)."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["Point", "Polygon", "MultiPolygon"]
    coordinates: list[Any]

    @model_validator(mode="after")
    def validate_coordinates(self) -> Geometry:
        count = 0

        def position(value: Any) -> None:
            nonlocal count
            count += 1
            if count > 10000:
                raise ValueError("Geometry exceeds 10000 positions; simplify it.")
            if not isinstance(value, list) or len(value) != 2:
                raise ValueError("Each position must contain longitude and latitude.")
            for coordinate, bound in zip(value, (180, 90), strict=True):
                if (
                    isinstance(coordinate, bool)
                    or not isinstance(coordinate, (int, float))
                    or not math.isfinite(coordinate)
                    or abs(coordinate) > bound
                ):
                    raise ValueError("Coordinates must be finite WGS84 numbers.")

        def polygon(rings: Any) -> None:
            if not isinstance(rings, list) or not rings:
                raise ValueError("Polygon must contain at least one ring.")
            for ring in rings:
                if not isinstance(ring, list) or len(ring) < 4:
                    raise ValueError("Polygon rings require at least four positions.")
                for point in ring:
                    position(point)
                if ring[0] != ring[-1]:
                    raise ValueError("Polygon rings must be closed.")
                if len({tuple(point) for point in ring[:-1]}) < 3:
                    raise ValueError("Polygon rings require three distinct vertices.")

        if self.type == "Point":
            position(self.coordinates)
        elif self.type == "Polygon":
            polygon(self.coordinates)
        else:
            if not self.coordinates:
                raise ValueError("MultiPolygon must contain at least one polygon.")
            for rings in self.coordinates:
                polygon(rings)
        return self


class ToolResult(BaseModel):
    """Preserves upstream fields and per-layer failures without invented metadata."""

    source: Literal["catalog", "analysis"]
    retrieved_at: str
    data: dict[str, Any] | list[Any]
    warnings: list[str] = Field(default_factory=list)


def validate_fields(value: str) -> str:
    """Allow '*' or a bounded comma-separated list of field identifiers."""
    if value != "*" and not re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_]*(?:,[A-Za-z_][A-Za-z0-9_]*){0,49}", value
    ):
        raise ValueError("Use '*' or comma-separated field identifiers without spaces.")
    return value
