"""Strict request models shared by MCP tools and tests."""

from __future__ import annotations

import math
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


class NumericData(StrictModel):
    values: list[list[float | int | None]] = Field(min_length=2)
    variable_names: list[str] | None = None

    @model_validator(mode="after")
    def rectangular_and_finite(self) -> NumericData:
        width = len(self.values[0])
        if width < 1:
            raise ValueError("At least one variable is required.")
        if any(len(row) != width for row in self.values):
            raise ValueError("Data rows must all have the same number of variables.")
        observed = (value for row in self.values for value in row if value is not None)
        if any(not math.isfinite(float(value)) for value in observed):
            raise ValueError("Observed values must be finite numbers.")
        if self.variable_names is not None:
            if len(self.variable_names) != width:
                raise ValueError("variable_names length must match the number of columns.")
            if len(set(self.variable_names)) != len(self.variable_names):
                raise ValueError("variable_names must be unique.")
            if any(not name.strip() for name in self.variable_names):
                raise ValueError("variable_names must not be blank.")
        return self


class CorrelationRequest(StrictModel):
    data: NumericData
    method: Literal["pearson", "spearman"] = "pearson"
    missing: Literal["pairwise", "listwise"] = "pairwise"

    @model_validator(mode="after")
    def at_least_two_variables(self) -> CorrelationRequest:
        if len(self.data.values[0]) < 2:
            raise ValueError("Correlation analysis requires at least two variables.")
        return self


class OLSRequest(StrictModel):
    data: NumericData
    outcome: str = Field(min_length=1)
    predictors: list[str] = Field(min_length=1)
    include_intercept: bool = True
    confidence_level: float = Field(default=0.95, gt=0.5, lt=1.0)
    missing: Literal["listwise"] = "listwise"

    @model_validator(mode="after")
    def validate_variables(self) -> OLSRequest:
        names = self.data.variable_names or [
            f"variable_{index + 1}" for index in range(len(self.data.values[0]))
        ]
        if self.outcome not in names:
            raise ValueError(f"Unknown outcome variable: {self.outcome!r}.")
        if len(set(self.predictors)) != len(self.predictors):
            raise ValueError("predictors must be unique.")
        unknown = [name for name in self.predictors if name not in names]
        if unknown:
            raise ValueError(f"Unknown predictor variables: {unknown}.")
        if self.outcome in self.predictors:
            raise ValueError("The outcome must not also be a predictor.")
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
