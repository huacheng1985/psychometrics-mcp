from __future__ import annotations

import json
from pathlib import Path

import pytest

from psychometrics_mcp.analysis import (
    RegressionAnalysisError,
    correlation_matrix,
    ctt_item_analysis,
    descriptive_statistics,
    inspect_response_data,
    ordinary_least_squares,
    plan_psychometric_analysis,
)
from psychometrics_mcp.models import (
    AnalysisPlanRequest,
    CorrelationRequest,
    NumericData,
    OLSRequest,
    ResponseData,
)

OLS_TARGETS = Path(__file__).parent / "reference" / "ols_numeric_expected.json"


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


def ols_reference_request() -> OLSRequest:
    x1 = list(range(1, 13))
    x2 = [0, 1] * 6
    noise = [0.2, -0.1, 0.4, -0.3, 0.1, -0.2, 0.3, -0.4, 0.0, 0.2, -0.1, -0.1]
    values = [
        [5 + 1.2 * first - 2 * second + error, first, second]
        for first, second, error in zip(x1, x2, noise, strict=True)
    ]
    return OLSRequest(
        data=NumericData(variable_names=["y", "x1", "x2"], values=values),
        outcome="y",
        predictors=["x1", "x2"],
    )


def test_ols_matches_independent_r_lm_reference() -> None:
    targets = json.loads(OLS_TARGETS.read_text(encoding="utf-8"))
    result = ordinary_least_squares(ols_reference_request())

    assert result["schema_version"] == "1.0"
    assert result["sample_flow"]["analyzed_rows"] == 12
    assert [row["term"] for row in result["coefficients"]] == ["intercept", "x1", "x2"]
    assert [row["estimate"] for row in result["coefficients"]] == pytest.approx(
        targets["coefficient_estimates"], abs=targets["absolute_tolerance"]
    )
    assert [row["standard_error"] for row in result["coefficients"]] == pytest.approx(
        targets["coefficient_standard_errors"], abs=targets["absolute_tolerance"]
    )
    assert [row["p_value"] for row in result["coefficients"]] == pytest.approx(
        targets["coefficient_p_values"], rel=1e-6, abs=1e-15
    )
    assert [row["confidence_interval_lower"] for row in result["coefficients"]] == pytest.approx(
        targets["confidence_interval_lower"], abs=targets["absolute_tolerance"]
    )
    assert [row["confidence_interval_upper"] for row in result["coefficients"]] == pytest.approx(
        targets["confidence_interval_upper"], abs=targets["absolute_tolerance"]
    )
    assert result["model_fit"]["r_squared"] == pytest.approx(
        targets["r_squared"], abs=targets["absolute_tolerance"]
    )
    assert result["model_fit"]["f_statistic"] == pytest.approx(
        targets["f_statistic"], abs=targets["absolute_tolerance"]
    )
    assert result["model_fit"]["adjusted_r_squared"] == pytest.approx(
        targets["adjusted_r_squared"], abs=targets["absolute_tolerance"]
    )
    assert result["model_fit"]["residual_standard_error"] == pytest.approx(
        targets["residual_standard_error"], abs=targets["absolute_tolerance"]
    )
    assert result["diagnostics"]["maximum_cooks_distance"] == pytest.approx(
        targets["maximum_cooks_distance"], abs=targets["absolute_tolerance"]
    )
    assert result["diagnostics"]["maximum_leverage"] == pytest.approx(
        targets["maximum_leverage"], abs=targets["absolute_tolerance"]
    )


def test_ols_reports_listwise_exclusions() -> None:
    request = ols_reference_request()
    request.data.values[2][0] = None
    request.data.values[4][2] = None
    result = ordinary_least_squares(request)

    assert result["sample_flow"] == {
        "input_rows": 12,
        "analyzed_rows": 10,
        "excluded_rows": 2,
        "excluded_input_row_numbers": [3, 5],
        "excluded_row_numbers_truncated": False,
    }
    assert "excluded listwise" in result["warnings"][0]


def test_ols_rejects_rank_deficient_design() -> None:
    request = OLSRequest(
        data=NumericData(
            variable_names=["y", "x1", "x2"],
            values=[[1, 1, 2], [2, 2, 4], [3, 3, 6], [4, 4, 8], [5, 5, 10]],
        ),
        outcome="y",
        predictors=["x1", "x2"],
    )
    with pytest.raises(RegressionAnalysisError, match="rank deficient"):
        ordinary_least_squares(request)


def test_ols_request_rejects_outcome_as_predictor() -> None:
    with pytest.raises(ValueError, match="must not also"):
        OLSRequest(
            data=NumericData(variable_names=["y", "x"], values=[[1, 2], [2, 3]]),
            outcome="y",
            predictors=["y"],
        )


def test_ols_without_intercept_labels_uncentered_r_squared() -> None:
    result = ordinary_least_squares(
        OLSRequest(
            data=NumericData(
                variable_names=["y", "x"],
                values=[[2.1, 1], [3.9, 2], [6.2, 3], [7.8, 4], [10.1, 5]],
            ),
            outcome="y",
            predictors=["x"],
            include_intercept=False,
        )
    )
    assert result["model_fit"]["r_squared_type"] == "uncentered"
    assert result["coefficients"][0]["term"] == "x"
    assert result["coefficients"][0]["estimate"] == pytest.approx(2.00363636363636)


def test_ols_ignores_missingness_in_unselected_variables() -> None:
    result = ordinary_least_squares(
        OLSRequest(
            data=NumericData(
                variable_names=["y", "x", "unused"],
                values=[[1, 1, None], [3, 2, None], [4, 3, 10], [6, 4, None]],
            ),
            outcome="y",
            predictors=["x"],
        )
    )
    assert result["sample_flow"]["analyzed_rows"] == 4
    assert result["sample_flow"]["excluded_rows"] == 0
