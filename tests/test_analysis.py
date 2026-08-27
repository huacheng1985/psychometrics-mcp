from __future__ import annotations

import pytest

from psychometrics_mcp.analysis import (
    ctt_item_analysis,
    inspect_response_data,
    plan_psychometric_analysis,
)
from psychometrics_mcp.models import AnalysisPlanRequest, ResponseData


@pytest.fixture
def responses() -> ResponseData:
    return ResponseData(
        item_names=["a", "b", "c", "d"],
        responses=[
            [0, 0, 0, 0],
            [0, 0, 1, 0],
            [0, 1, 0, 1],
            [1, 0, 1, 1],
            [1, 1, 0, 1],
            [1, 1, 1, 1],
        ],
    )


def test_inspection_reports_shape_and_categories(responses: ResponseData) -> None:
    result = inspect_response_data(responses)
    assert result["sample"] == {
        "rows": 6,
        "items": 4,
        "complete_rows": 6,
        "incomplete_rows": 0,
    }
    assert result["items"][0]["categories"] == [
        {"value": 0.0, "count": 3},
        {"value": 1.0, "count": 3},
    ]


def test_ctt_returns_alpha_and_item_rest(responses: ResponseData) -> None:
    result = ctt_item_analysis(responses)
    assert result["scale"]["coefficient_alpha"] == pytest.approx(0.6153846153846154)
    assert len(result["items"]) == 4
    assert all("item_rest_correlation" in item for item in result["items"])


def test_plan_adds_design_specific_checks() -> None:
    result = plan_psychometric_analysis(
        AnalysisPlanRequest(
            purpose="prediction",
            item_type="dichotomous",
            groups=2,
            occasions=2,
            clustered=True,
        )
    )
    sequence = " ".join(result["recommended_sequence"])
    assert "DIF" in sequence
    assert "longitudinal" in sequence
    assert "clustering" in sequence
    assert "leakage" in sequence


def test_response_data_rejects_ragged_rows() -> None:
    with pytest.raises(ValueError, match="same number"):
        ResponseData(responses=[[0, 1], [1]])
