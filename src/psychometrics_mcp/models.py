"""Strict request models shared by MCP tools and tests."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResponseData(StrictModel):
    responses: list[list[float | int | None]] = Field(min_length=2)
    item_names: list[str] | None = None

    @model_validator(mode="after")
    def rectangular(self) -> ResponseData:
        width = len(self.responses[0])
        if width < 2:
            raise ValueError("At least two items are required.")
        if any(len(row) != width for row in self.responses):
            raise ValueError("Response rows must all have the same number of items.")
        if self.item_names is not None:
            if len(self.item_names) != width:
                raise ValueError("item_names length must match the number of columns.")
            if len(set(self.item_names)) != len(self.item_names):
                raise ValueError("item_names must be unique.")
        return self


class AnalysisPlanRequest(StrictModel):
    purpose: Literal[
        "scale_development",
        "score_reporting",
        "group_comparison",
        "prediction",
        "linking_equating",
        "classification",
    ]
    item_type: Literal["dichotomous", "polytomous", "continuous", "mixed"]
    dimensionality: Literal["unknown", "unidimensional", "multidimensional"] = "unknown"
    groups: int = Field(default=1, ge=1)
    occasions: int = Field(default=1, ge=1)
    clustered: bool = False
