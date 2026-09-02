from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from psychometrics_mcp.factor import (
    ConfirmatoryFactorAnalysisError,
    confirmatory_factor_analysis,
    factor_capabilities,
)
from psychometrics_mcp.models import CFARequest, FactorDefinition, NumericData

REFERENCE_TARGETS = Path(__file__).parent / "reference" / "cfa_holzinger_expected.json"


def _model(values: list[list[float | None]], estimator: str = "ML") -> CFARequest:
    return CFARequest(
        data=NumericData(values=values, variable_names=[f"x{index}" for index in range(1, 10)]),
        factors=[
            FactorDefinition(name="visual", indicators=["x1", "x2", "x3"]),
            FactorDefinition(name="textual", indicators=["x4", "x5", "x6"]),
            FactorDefinition(name="speed", indicators=["x7", "x8", "x9"]),
        ],
        estimator=estimator,
    )


def _holzinger_values() -> list[list[float]]:
    code = (
        "suppressPackageStartupMessages(library(lavaan)); "
        "suppressPackageStartupMessages(library(jsonlite)); "
        "cat(toJSON(unname(as.matrix(HolzingerSwineford1939[paste0('x',1:9)])), "
        "dataframe='rows', na='null', digits=15))"
    )
    completed = subprocess.run(
        ["Rscript", "-e", code], capture_output=True, check=True, text=True, timeout=30
    )
    return json.loads(completed.stdout)


def test_cfa_rejects_cross_loadings_in_fixed_contract() -> None:
    with pytest.raises(ValidationError, match="does not permit cross-loadings"):
        CFARequest(
            data=NumericData(
                values=[[float(row + column) for column in range(5)] for row in range(20)],
                variable_names=["x1", "x2", "x3", "x4", "x5"],
            ),
            factors=[
                FactorDefinition(name="f1", indicators=["x1", "x2", "x3"]),
                FactorDefinition(name="f2", indicators=["x3", "x4", "x5"]),
            ],
        )


def test_cfa_rejects_too_few_complete_rows_before_r() -> None:
    values = [[float(row + column) for column in range(9)] for row in range(19)]
    with pytest.raises(ConfirmatoryFactorAnalysisError, match="at least 20 complete rows"):
        confirmatory_factor_analysis(_model(values))


@pytest.mark.integration
def test_lavaan_cfa_matches_published_holzinger_example() -> None:
    if not factor_capabilities()["available"]:
        pytest.skip("R/lavaan/jsonlite not installed")
    targets = json.loads(REFERENCE_TARGETS.read_text(encoding="utf-8"))
    result = confirmatory_factor_analysis(_model(_holzinger_values()))

    assert result["schema_version"] == "1.0"
    assert result["model"]["engine"] == "lavaan::cfa"
    assert result["model"]["converged"] is True
    assert result["model"]["post_check"] is True
    assert result["sample_flow"]["analyzed_rows"] == 301
    assert {reference["role"] for reference in result["references"]} == {
        "method_foundation",
        "engine",
        "interpretation_limit",
    }
    for name, expected in targets["fit"].items():
        assert result["fit"][name] == pytest.approx(expected, abs=targets["absolute_tolerance"])
    estimates = [row["estimate"] for row in result["loadings"]]
    assert estimates == pytest.approx(
        targets["unstandardized_loadings_std_lv"], abs=targets["absolute_tolerance"]
    )


@pytest.mark.integration
def test_lavaan_mlr_and_listwise_sample_flow() -> None:
    if not factor_capabilities()["available"]:
        pytest.skip("R/lavaan/jsonlite not installed")
    values = _holzinger_values()
    values[0][0] = None
    result = confirmatory_factor_analysis(_model(values, estimator="MLR"))

    assert result["sample_flow"]["analyzed_rows"] == 300
    assert result["sample_flow"]["excluded_rows"] == [1]
    assert result["fit"]["robust"]["cfi"] is not None
    assert len(result["loadings"]) == 9
