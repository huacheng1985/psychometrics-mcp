from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from psychometrics_mcp.invariance import (
    MeasurementInvarianceError,
    continuous_measurement_invariance,
    measurement_invariance_capabilities,
)
from psychometrics_mcp.models import (
    ContinuousMeasurementInvarianceRequest,
    FactorDefinition,
    NumericData,
)

REFERENCE_TARGETS = Path(__file__).parent / "reference" / "invariance_expected.json"
VARIABLE_NAMES = [f"x{index}" for index in range(1, 10)]
FACTORS = [
    FactorDefinition(name="visual", indicators=["x1", "x2", "x3"]),
    FactorDefinition(name="textual", indicators=["x4", "x5", "x6"]),
    FactorDefinition(name="speed", indicators=["x7", "x8", "x9"]),
]


def _holzinger_data() -> tuple[list[list[float]], list[str]]:
    code = (
        "suppressPackageStartupMessages(library(lavaan)); "
        "suppressPackageStartupMessages(library(jsonlite)); "
        "result <- list(values=unname(as.matrix(HolzingerSwineford1939[paste0('x',1:9)])), "
        "groups=as.character(HolzingerSwineford1939$school)); "
        "cat(toJSON(result, dataframe='rows', na='null', digits=15))"
    )
    completed = subprocess.run(
        ["Rscript", "-e", code], capture_output=True, check=True, text=True, timeout=30
    )
    result = json.loads(completed.stdout)
    return result["values"], result["groups"]


def _request(estimator: str = "ML") -> ContinuousMeasurementInvarianceRequest:
    values, groups = _holzinger_data()
    return ContinuousMeasurementInvarianceRequest(
        data=NumericData(values=values, variable_names=VARIABLE_NAMES),
        groups=groups,
        factors=FACTORS,
        estimator=estimator,
    )


def test_invariance_requires_matching_group_vector() -> None:
    with pytest.raises(ValidationError, match="groups length must match"):
        ContinuousMeasurementInvarianceRequest(
            data=NumericData(values=[[1.0] * 9, [2.0] * 9], variable_names=VARIABLE_NAMES),
            groups=["a", "b", "b"],
            factors=FACTORS,
        )


def test_invariance_requires_two_groups() -> None:
    with pytest.raises(ValidationError, match="at least two groups"):
        ContinuousMeasurementInvarianceRequest(
            data=NumericData(values=[[1.0] * 9, [2.0] * 9], variable_names=VARIABLE_NAMES),
            groups=["a", "a"],
            factors=FACTORS,
        )


def test_invariance_requires_conservative_sample_per_group() -> None:
    values = [[float((row + 1) * (column + 2) % 101) for column in range(9)] for row in range(198)]
    request = ContinuousMeasurementInvarianceRequest(
        data=NumericData(values=values, variable_names=VARIABLE_NAMES),
        groups=["a"] * 99 + ["b"] * 99,
        factors=FACTORS,
    )
    with pytest.raises(MeasurementInvarianceError, match="at least 100 complete rows"):
        continuous_measurement_invariance(request)


@pytest.mark.integration
def test_continuous_invariance_matches_published_holzinger_sequence() -> None:
    if not measurement_invariance_capabilities()["continuous_measurement_invariance"]["available"]:
        pytest.skip("R/lavaan/jsonlite not installed")
    targets = json.loads(REFERENCE_TARGETS.read_text(encoding="utf-8"))
    result = continuous_measurement_invariance(_request("ML"))

    assert result["schema_version"] == "1.0"
    assert result["model"]["sequence"] == ["configural", "metric", "scalar", "strict"]
    assert result["model"]["automatic_decision"] is False
    assert result["model"]["partial_invariance_search"] is False
    assert result["sample_flow"]["analyzed_rows"] == 301
    assert [group["analyzed_rows"] for group in result["sample_flow"]["groups"]] == [156, 145]
    assert all(model["converged"] and model["post_check"] for model in result["models"])
    assert len(result["comparisons"]) == 3
    assert all(comparison["comparison_valid"] is True for comparison in result["comparisons"])
    assert all(comparison["automatic_decision"] is None for comparison in result["comparisons"])

    assert [model["fit"]["standard"]["chi_square"] for model in result["models"]] == (
        pytest.approx(targets["ml_standard_chi_square"], abs=targets["absolute_tolerance"])
    )
    assert [model["fit"]["standard"]["degrees_of_freedom"] for model in result["models"]] == (
        targets["degrees_of_freedom"]
    )
    assert [
        comparison["likelihood_ratio_test"]["chi_square_difference"]
        for comparison in result["comparisons"]
    ] == pytest.approx(targets["ml_chi_square_differences"], abs=targets["absolute_tolerance"])
    assert len(result["configural_parameters"]["loadings"]) == 18
    assert {reference["role"] for reference in result["references"]} == {
        "method_framework",
        "fit_change_evaluation",
        "fit_change_sensitivity",
        "engine",
    }


@pytest.mark.integration
def test_continuous_invariance_mlr_reports_robust_changes() -> None:
    if not measurement_invariance_capabilities()["continuous_measurement_invariance"]["available"]:
        pytest.skip("R/lavaan/jsonlite not installed")
    result = continuous_measurement_invariance(_request("MLR"))

    assert all(model["fit"]["robust"]["cfi"] is not None for model in result["models"])
    assert all(
        comparison["fit_change"]["robust_delta_cfi"] is not None
        for comparison in result["comparisons"]
    )
    assert all(
        "Satorra-Bentler" in comparison["likelihood_ratio_test"]["method"]
        for comparison in result["comparisons"]
    )
