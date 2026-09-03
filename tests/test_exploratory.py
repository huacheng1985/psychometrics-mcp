from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from psychometrics_mcp.exploratory import (
    ExploratoryFactorAnalysisError,
    exploratory_factor_analysis,
    exploratory_factor_capabilities,
    parallel_analysis,
)
from psychometrics_mcp.models import (
    ExploratoryFactorAnalysisRequest,
    NumericData,
    ParallelAnalysisRequest,
)

REFERENCE_TARGETS = Path(__file__).parent / "reference" / "parallel_synthetic_expected.json"
VARIABLE_NAMES = [f"x{index}" for index in range(1, 7)]


def _synthetic_values() -> list[list[float]]:
    values = []
    for index in range(240):
        position = index + 1
        factor_1 = math.sin(position * 0.17) + 0.35 * math.cos(position * 0.07)
        factor_2 = 0.35 * factor_1 + math.cos(position * 0.11)
        errors = [
            0.22 * math.sin(position * (column + 2) * 0.31)
            + 0.08 * math.cos(position * (column + 3) * 0.19)
            for column in range(6)
        ]
        values.append(
            [
                0.9 * factor_1 + errors[0],
                0.8 * factor_1 + errors[1],
                0.7 * factor_1 + errors[2],
                0.9 * factor_2 + errors[3],
                0.8 * factor_2 + errors[4],
                0.7 * factor_2 + errors[5],
            ]
        )
    return values


def _data(values: list[list[float | None]] | None = None) -> NumericData:
    return NumericData(values=values or _synthetic_values(), variable_names=VARIABLE_NAMES)


def test_parallel_analysis_requires_three_variables() -> None:
    with pytest.raises(ValidationError, match="at least three variables"):
        ParallelAnalysisRequest(data=NumericData(values=[[1.0, 2.0], [2.0, 1.0]]))


def test_efa_rejects_as_many_factors_as_variables() -> None:
    with pytest.raises(ValidationError, match="smaller than the number of variables"):
        ExploratoryFactorAnalysisRequest(data=_data(), factors=6)


def test_exploratory_preflight_rejects_zero_variance_before_r() -> None:
    values = _synthetic_values()
    for row in values:
        row[0] = 1.0
    with pytest.raises(ExploratoryFactorAnalysisError, match="zero variance"):
        parallel_analysis(ParallelAnalysisRequest(data=_data(values)))


@pytest.mark.integration
def test_parallel_analysis_matches_versioned_synthetic_target_and_seed() -> None:
    if not exploratory_factor_capabilities()["parallel_analysis"]["available"]:
        pytest.skip("R/psych/jsonlite not installed")
    request = ParallelAnalysisRequest(data=_data(), iterations=100, seed=123)
    first = parallel_analysis(request)
    second = parallel_analysis(request)
    targets = json.loads(REFERENCE_TARGETS.read_text(encoding="utf-8"))

    assert first["schema_version"] == "1.0"
    assert first["suggested_factors"] == targets["suggested_factors"] == 2
    assert first["eigenvalues"] == second["eigenvalues"]
    assert [row["observed_common_factor_eigenvalue"] for row in first["eigenvalues"]] == (
        pytest.approx(targets["observed_common_factor_eigenvalues"], abs=1e-8)
    )
    assert [row["simulated_percentile"] for row in first["eigenvalues"]] == pytest.approx(
        targets["simulated_percentiles"], abs=1e-6
    )
    assert {reference["role"] for reference in first["references"]} == {
        "method_foundation",
        "method_evaluation",
        "engine",
    }


@pytest.mark.integration
def test_oblimin_efa_recovers_two_groups_and_reports_listwise_flow() -> None:
    if not exploratory_factor_capabilities()["exploratory_factor_analysis"]["available"]:
        pytest.skip("R/psych/GPArotation/jsonlite not installed")
    values: list[list[float | None]] = _synthetic_values()
    values[0][0] = None
    result = exploratory_factor_analysis(
        ExploratoryFactorAnalysisRequest(data=_data(values), factors=2)
    )

    assert result["schema_version"] == "1.0"
    assert result["model"]["engine"] == "psych::fa"
    assert result["model"]["solution_available"] is True
    assert result["sample_flow"]["analyzed_rows"] == 239
    assert result["sample_flow"]["excluded_rows"] == [1]
    dominant = []
    for row in result["loadings"]:
        loadings = row["pattern_loadings"]
        dominant.append(max(loadings, key=lambda factor: abs(loadings[factor])))
    assert len(set(dominant[:3])) == 1
    assert len(set(dominant[3:])) == 1
    assert dominant[0] != dominant[3]
    assert all(
        max(abs(value) for value in row["pattern_loadings"].values()) > 0.85
        for row in result["loadings"]
    )
    for factor in ("factor_1", "factor_2"):
        anchor = max(
            (row["pattern_loadings"][factor] for row in result["loadings"]),
            key=abs,
        )
        assert anchor > 0
    assert result["diagnostics"]["heywood_case_detected"] is False
    assert len(result["largest_residual_correlations"]) == 15
    assert "Listwise deletion excluded 1 rows" in result["warnings"][0]


@pytest.mark.integration
def test_one_factor_efa_records_effective_no_rotation() -> None:
    if not exploratory_factor_capabilities()["exploratory_factor_analysis"]["available"]:
        pytest.skip("R/psych/GPArotation/jsonlite not installed")
    result = exploratory_factor_analysis(
        ExploratoryFactorAnalysisRequest(data=_data(), factors=1, rotation="oblimin")
    )
    assert result["model"]["requested_rotation"] == "oblimin"
    assert result["model"]["effective_rotation"] == "none"
    assert any("one-factor solution" in warning for warning in result["warnings"])
