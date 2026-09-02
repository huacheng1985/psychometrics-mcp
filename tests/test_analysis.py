from __future__ import annotations

import pytest

from psychometrics_mcp.analysis import (
    correlation_matrix,
    ctt_item_analysis,
    descriptive_statistics,
    inspect_response_data,
    plan_psychometric_analysis,
)
from psychometrics_mcp.models import (
    AnalysisPlanRequest,
    CorrelationRequest,
    NumericData,
    ResponseData,
)


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
    assert result["schema_version"] == "1.0"
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
    assert result["schema_version"] == "1.0"
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
    assert result["schema_version"] == "1.0"
    assert "DIF" in sequence
    assert "longitudinal" in sequence
    assert "clustering" in sequence
    assert "leakage" in sequence


def test_response_data_rejects_ragged_rows() -> None:
    with pytest.raises(ValueError, match="same number"):
        ResponseData(responses=[[0, 1], [1]])


def test_descriptive_statistics_reports_missingness_and_quartiles() -> None:
    result = descriptive_statistics(
        NumericData(
            variable_names=["x", "y"],
            values=[[1, 10], [2, None], [3, 30], [4, 40]],
        )
    )
    assert result["schema_version"] == "1.0"
    assert result["sample_flow"]["complete_rows"] == 3
    assert result["variables"][0]["mean"] == pytest.approx(2.5)
    assert result["variables"][0]["first_quartile"] == pytest.approx(1.75)
    assert result["variables"][1]["missing_rate"] == pytest.approx(0.25)
    assert result["variables"][1]["standard_deviation"] == pytest.approx(15.2752523165)


def test_pearson_pairwise_reports_pair_specific_n() -> None:
    result = correlation_matrix(
        CorrelationRequest(
            data=NumericData(
                variable_names=["x", "y", "z"],
                values=[[1, 2, 5], [2, 4, None], [3, 6, 1], [4, None, 0]],
            ),
            method="pearson",
            missing="pairwise",
        )
    )
    assert result["correlations"][0][1] == pytest.approx(1.0)
    assert result["pairwise_n"] == [[4, 3, 3], [3, 3, 2], [3, 2, 3]]
    assert result["correlations"][1][2] is None
    assert "Pairwise deletion" in result["warnings"][0]


def test_spearman_uses_average_ranks_and_listwise_deletion() -> None:
    result = correlation_matrix(
        CorrelationRequest(
            data=NumericData(
                variable_names=["x", "y"],
                values=[[1, 4], [2, 1], [2, 2], [4, 3], [5, None]],
            ),
            method="spearman",
            missing="listwise",
        )
    )
    assert result["sample_flow"]["listwise_analyzed_rows"] == 4
    assert result["correlations"][0][1] == pytest.approx(-0.31622776601683794)
    assert result["pairwise_n"][0][1] == 4


def test_numeric_data_rejects_nonfinite_values() -> None:
    with pytest.raises(ValueError, match="finite"):
        NumericData(values=[[1, float("inf")], [2, 3]])
