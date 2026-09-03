from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from psychometrics_mcp.models import (
    CategoricalCFARequest,
    FactorDefinition,
    OrdinalData,
    OrdinalEFARequest,
    OrdinalParallelAnalysisRequest,
    PolychoricCorrelationRequest,
)
from psychometrics_mcp.ordinal import (
    OrdinalAnalysisError,
    categorical_confirmatory_factor_analysis,
    ordinal_capabilities,
    ordinal_exploratory_factor_analysis,
    ordinal_parallel_analysis,
    polychoric_correlation_matrix,
)

REFERENCE_TARGETS = Path(__file__).parent / "reference" / "ordinal_expected.json"
VARIABLE_NAMES = [f"x{index}" for index in range(1, 7)]


def _ordinal_cfa_values() -> list[list[int]]:
    values = []
    cuts = [-0.65, -0.1, 0.45]
    for index in range(500):
        position = index + 1
        factor_1 = math.sin(position * 0.137) + 0.35 * math.cos(position * 0.071)
        factor_2 = 0.35 * factor_1 + math.cos(position * 0.113)
        errors = [
            0.35 * math.sin(position * (column + 2) * 0.293)
            + 0.12 * math.cos(position * (column + 3) * 0.181)
            for column in range(6)
        ]
        latent = [
            0.95 * factor_1 + errors[0],
            0.85 * factor_1 + errors[1],
            0.75 * factor_1 + errors[2],
            0.95 * factor_2 + errors[3],
            0.85 * factor_2 + errors[4],
            0.75 * factor_2 + errors[5],
        ]
        values.append([sum(value > cut for cut in cuts) + 1 for value in latent])
    return values


def _categorical_model(values: list[list[int | None]] | None = None) -> CategoricalCFARequest:
    return CategoricalCFARequest(
        data=OrdinalData(values=values or _ordinal_cfa_values(), variable_names=VARIABLE_NAMES),
        factors=[
            FactorDefinition(name="factor_a", indicators=["x1", "x2", "x3"]),
            FactorDefinition(name="factor_b", indicators=["x4", "x5", "x6"]),
        ],
    )


def test_ordinal_data_rejects_fractional_categories() -> None:
    with pytest.raises(ValidationError):
        OrdinalData(values=[[1, 1.5], [2, 2]], variable_names=["a", "b"])


def test_categorical_cfa_rejects_cross_loadings() -> None:
    with pytest.raises(ValidationError, match="does not permit cross-loadings"):
        CategoricalCFARequest(
            data=OrdinalData(values=_ordinal_cfa_values(), variable_names=VARIABLE_NAMES),
            factors=[
                FactorDefinition(name="a", indicators=["x1", "x2", "x3"]),
                FactorDefinition(name="b", indicators=["x3", "x4", "x5"]),
            ],
        )


def test_polychoric_rejects_singleton_category_before_r() -> None:
    values = [[1, 1] for _ in range(19)] + [[2, 2]]
    with pytest.raises(OrdinalAnalysisError, match="at least two complete cases"):
        polychoric_correlation_matrix(
            PolychoricCorrelationRequest(
                data=OrdinalData(values=values, variable_names=["a", "b"])
            )
        )


def test_categorical_cfa_requires_conservative_complete_sample() -> None:
    with pytest.raises(OrdinalAnalysisError, match="at least 100 complete rows"):
        categorical_confirmatory_factor_analysis(_categorical_model(_ordinal_cfa_values()[:99]))


def test_ordinal_efa_rejects_as_many_factors_as_variables() -> None:
    with pytest.raises(ValidationError, match="smaller than the number of variables"):
        OrdinalEFARequest(
            data=OrdinalData(values=_ordinal_cfa_values(), variable_names=VARIABLE_NAMES),
            factors=6,
        )


def test_ordinal_parallel_analysis_requires_three_variables() -> None:
    with pytest.raises(ValidationError, match="at least three variables"):
        OrdinalParallelAnalysisRequest(
            data=OrdinalData(values=[[1, 2], [2, 1]], variable_names=["a", "b"])
        )


def test_ordinal_parallel_analysis_limits_computational_width() -> None:
    values = [[1] * 31, [2] * 31]
    with pytest.raises(ValidationError, match="limited to 30 variables"):
        OrdinalParallelAnalysisRequest(data=OrdinalData(values=values))


def test_ordinal_parallel_analysis_requires_conservative_complete_sample() -> None:
    with pytest.raises(OrdinalAnalysisError, match="at least 100 complete rows"):
        ordinal_parallel_analysis(
            OrdinalParallelAnalysisRequest(
                data=OrdinalData(
                    values=_ordinal_cfa_values()[:99], variable_names=VARIABLE_NAMES
                ),
                iterations=100,
            )
        )


@pytest.mark.integration
def test_polychoric_matches_independent_symmetric_binary_reference() -> None:
    if not ordinal_capabilities()["polychoric_correlation_matrix"]["available"]:
        pytest.skip("R/psych/jsonlite not installed")
    targets = json.loads(REFERENCE_TARGETS.read_text(encoding="utf-8"))["polychoric"]
    values: list[list[int | None]] = (
        [[0, 0]] * 350 + [[0, 1]] * 150 + [[1, 0]] * 150 + [[1, 1]] * 350
    )
    values.append([None, 1])
    result = polychoric_correlation_matrix(
        PolychoricCorrelationRequest(
            data=OrdinalData(values=values, variable_names=["a", "b"]),
            continuity_correction=0,
        )
    )

    assert result["schema_version"] == "1.0"
    assert result["method"]["smoothing"] is False
    assert result["correlations"][0]["b"] == pytest.approx(
        targets["analytic_tetrachoric_correlation"], abs=targets["absolute_tolerance"]
    )
    assert result["thresholds"][0]["thresholds"][0]["estimate"] == pytest.approx(0)
    assert result["diagnostics"]["positive_definite"] is True
    assert result["sample_flow"]["analyzed_rows"] == 1000
    assert result["sample_flow"]["excluded_rows"] == [1001]


@pytest.mark.integration
def test_wlsmv_categorical_cfa_matches_versioned_target() -> None:
    if not ordinal_capabilities()["categorical_confirmatory_factor_analysis"]["available"]:
        pytest.skip("R/lavaan/jsonlite not installed")
    targets = json.loads(REFERENCE_TARGETS.read_text(encoding="utf-8"))["categorical_cfa"]
    result = categorical_confirmatory_factor_analysis(_categorical_model())

    assert result["schema_version"] == "1.0"
    assert result["model"]["requested_estimator"] == "WLSMV"
    assert result["model"]["estimation"] == "diagonally weighted least squares"
    assert result["model"]["converged"] is True
    assert result["model"]["post_check"] is True
    assert result["fit"]["robust_scaled"]["chi_square"] == pytest.approx(
        targets["robust_scaled_chi_square"], abs=targets["absolute_tolerance"]
    )
    assert result["fit"]["srmr"] == pytest.approx(
        targets["srmr"], abs=targets["absolute_tolerance"]
    )
    assert [row["standardized_estimate"] for row in result["loadings"]] == pytest.approx(
        targets["standardized_loadings"], abs=targets["absolute_tolerance"]
    )
    assert result["factor_covariances"][0]["standardized_estimate"] == pytest.approx(
        targets["standardized_factor_correlation"], abs=targets["absolute_tolerance"]
    )
    assert len(result["thresholds"]) == 18
    assert result["thresholds"][0]["lower_category"] == 1
    assert result["thresholds"][0]["upper_category"] == 2
    assert result["diagnostics"]["latent_covariance_positive_definite"] is True
    assert {reference["role"] for reference in result["references"]} == {
        "ordinal_estimation_evaluation",
        "engine",
        "engine_contract",
    }


@pytest.mark.integration
def test_ordinal_efa_recovers_groups_with_unsmoothed_polychorics() -> None:
    if not ordinal_capabilities()["ordinal_exploratory_factor_analysis"]["available"]:
        pytest.skip("R/psych/GPArotation/jsonlite not installed")
    targets = json.loads(REFERENCE_TARGETS.read_text(encoding="utf-8"))["ordinal_efa"]
    result = ordinal_exploratory_factor_analysis(
        OrdinalEFARequest(
            data=OrdinalData(values=_ordinal_cfa_values(), variable_names=VARIABLE_NAMES),
            factors=2,
        )
    )

    assert result["model"]["correlation"] == "unsmoothed two-step polychoric"
    assert result["diagnostics"]["polychoric_matrix_positive_definite"] is True
    assert result["diagnostics"]["heywood_case_detected"] is False
    loadings = [
        [row["pattern_loadings"]["factor_1"], row["pattern_loadings"]["factor_2"]]
        for row in result["loadings"]
    ]
    assert [value for row in loadings for value in row] == pytest.approx(
        [value for row in targets["pattern_loadings"] for value in row],
        abs=targets["absolute_tolerance"],
    )
    assert all(abs(row[0]) > 0.9 and abs(row[1]) < 0.02 for row in loadings[:3])
    assert all(abs(row[1]) > 0.9 and abs(row[0]) < 0.02 for row in loadings[3:])
    assert {reference["role"] for reference in result["references"]} == {
        "correlation_foundation",
        "ordinal_factor_evaluation",
        "exploratory_method_guidance",
        "assumption_limit",
        "engine",
    }


@pytest.mark.integration
def test_ordinal_parallel_analysis_is_seeded_and_reports_sensitivity() -> None:
    if not ordinal_capabilities()["ordinal_parallel_analysis"]["available"]:
        pytest.skip("R/psych/jsonlite not installed")
    targets = json.loads(REFERENCE_TARGETS.read_text(encoding="utf-8"))[
        "ordinal_parallel_analysis"
    ]
    request = OrdinalParallelAnalysisRequest(
        data=OrdinalData(values=_ordinal_cfa_values(), variable_names=VARIABLE_NAMES),
        iterations=100,
        seed=123,
    )
    first = ordinal_parallel_analysis(request)
    second = ordinal_parallel_analysis(request)

    assert first["schema_version"] == "1.0"
    assert first["method"]["smoothing"] is False
    assert first["method"]["reference_generation"].startswith(
        "independent within-column permutation"
    )
    assert first["method"]["exact_univariate_margins_preserved"] is True
    assert first["diagnostics"]["permutation_margins_preserved_by_construction"] is True
    assert first["suggested_factors"] == targets["suggested_factors"] == 2
    assert first["eigenvalues"] == second["eigenvalues"]
    assert first["simulation"] == second["simulation"]
    assert first["simulation"]["successful_iterations"] == 100
    assert len(first["sensitivity_results"]) == 8
    variants = {
        (row["correlation"], row["spectrum"], row["cutoff"])
        for row in first["sensitivity_results"]
    }
    assert variants == {
        (correlation, spectrum, cutoff)
        for correlation in ("polychoric", "pearson")
        for spectrum in ("principal_components", "common_factor_minres")
        for cutoff in ("mean", "percentile")
    }
    observed = [
        row["observed"]["polychoric_principal_components"]
        for row in first["eigenvalues"]
    ]
    reference_means = [
        row["permutation_mean"]["polychoric_principal_components"]
        for row in first["eigenvalues"]
    ]
    assert observed == pytest.approx(
        targets["observed_polychoric_principal_component_eigenvalues"], abs=1e-8
    )
    assert reference_means == pytest.approx(
        targets["permutation_mean_polychoric_principal_component_eigenvalues"], abs=1e-6
    )
    assert {reference["role"] for reference in first["references"]} == {
        "method_foundation",
        "permutation_foundation",
        "ordinal_method_evaluation",
        "engine",
    }
