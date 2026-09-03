from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from psychometrics_mcp.models import OrdinalMeasurementInvarianceRequest
from psychometrics_mcp.ordinal import OrdinalAnalysisError
from psychometrics_mcp.ordinal_invariance import (
    STAGES,
    _preflight,
    ordinal_invariance_capabilities,
    ordinal_invariance_r_environment,
    ordinal_measurement_invariance,
)

REFERENCE = Path(__file__).parent / "reference"
NAMES = [f"u{i}" for i in range(1, 9)]
FACTORS = [{"name": "FU1", "indicators": NAMES[:4]}, {"name": "FU2", "indicators": NAMES[4:]}]


def _request(values=None, groups=None, **kwargs):
    if values is None:
        values = np.random.default_rng(1729).integers(1, 6, size=(400, 8)).tolist()
    return OrdinalMeasurementInvarianceRequest(
        data={"values": values, "variable_names": NAMES},
        groups=groups if groups is not None else ["a"] * 200 + ["b"] * 200,
        factors=FACTORS,
        **kwargs,
    )


@pytest.fixture(scope="module")
def datcat():
    if not ordinal_invariance_capabilities()["ordinal_measurement_invariance"]["available"]:
        pytest.skip("R/lavaan/semTools/jsonlite unavailable")
    code = (
        "suppressPackageStartupMessages(library(semTools)); "
        "cat(jsonlite::toJSON(list(values=unname(as.matrix(datCat[1:8])), "
        "groups=as.character(datCat$g))))"
    )
    result = subprocess.run(
        ["Rscript", "-e", code],
        env=ordinal_invariance_r_environment(),
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return json.loads(result.stdout)


def test_later_stage_requires_review():
    with pytest.raises(ValidationError, match="prior_stage_reviewed"):
        _request(stage="thresholds")


def test_group_labels_are_strict_and_match_rows():
    with pytest.raises(ValidationError):
        _request(groups=[True] * 200 + [False] * 200)
    with pytest.raises(ValidationError, match="groups length"):
        _request(groups=["a", "b"])


@pytest.mark.parametrize("categories", [2, 3])
def test_binary_and_three_category_contracts_not_silently_used(categories):
    values = np.random.default_rng(11).integers(1, categories + 1, size=(400, 8)).tolist()
    with pytest.raises(OrdinalAnalysisError, match="4-10 categories"):
        _preflight(_request(values=values))


def test_different_category_codes_rejected():
    request = _request()
    for row in request.data.values[200:]:
        row[0] += 10
    with pytest.raises(OrdinalAnalysisError, match="identical category codes"):
        _preflight(request)


def test_small_group_rejected_before_engine():
    with pytest.raises(OrdinalAnalysisError, match="at least 100 complete rows"):
        _preflight(_request(values=[[1] * 8] * 198, groups=["a"] * 99 + ["b"] * 99))


def test_singleton_category_is_not_merged_automatically():
    request = _request()
    request.data.values[0][0] = 6
    with pytest.raises(OrdinalAnalysisError, match="at least two"):
        _preflight(request)


def test_listwise_flow_and_category_order_are_preserved():
    request = _request()
    request.data.values[0][0] = None
    payload, flow, warnings = _preflight(request)
    assert flow["excluded_rows"] == [1]
    assert flow["analyzed_rows"] == 399
    assert [row["analyzed_rows"] for row in flow["groups"]] == [199, 200]
    assert flow["groups"][0]["categories"][0]["categories"] == [1, 2, 3, 4, 5]
    assert len(payload["groups"]) == len(payload["values"]) == 399
    assert any("Listwise" in warning for warning in warnings)


@pytest.mark.integration
@pytest.mark.parametrize("stage", STAGES)
def test_stagewise_datcat_regression_and_identification(datcat, stage):
    targets = json.loads((REFERENCE / "ordinal_invariance_expected.json").read_text())
    index = STAGES.index(stage)
    result = ordinal_measurement_invariance(
        _request(**datcat, stage=stage, prior_stage_reviewed=index > 0)
    )
    assert [row["stage"] for row in result["models"]] == STAGES[max(0, index - 1) : index + 1]
    current = result["models"][-1]
    assert current["fit"]["standard"]["degrees_of_freedom"] == targets["degrees_of_freedom"][index]
    for kind, key in [("standard", "standard_chi_square"), ("scaled", "scaled_chi_square")]:
        assert current["fit"][kind]["chi_square"] == pytest.approx(
            targets[key][index], abs=targets["absolute_tolerance"], rel=0
        )
    assert len(result["comparisons"]) == int(index > 0)
    if index:
        comparison = result["comparisons"][0]
        assert comparison["comparison_valid"] is True
        assert comparison["adjusted_difference_test"]["chi_square_difference"] == pytest.approx(
            targets["adjusted_chi_square_difference"][index - 1], abs=1e-5, rel=0
        )
        assert comparison["automatic_decision"] is None
    assert result["model"]["automatic_decision"] is False
    assert result["review"]["automatic_progression"] is False
    assert len(result["request_sha256"]) == 64
    assert result["sample_flow"]["analyzed_rows"] == 200
    assert current["diagnostics"]["thresholds_increasing"] is True
    assert "v1" in current["generated_syntax"]
    audit = current["parameter_audit"]
    intercept = next(p for p in audit if p["lhs"] == "v1" and p["op"] == "~1" and p["group"] == 2)
    residual = next(
        p
        for p in audit
        if p["lhs"] == "v1" and p["rhs"] == "v1" and p["op"] == "~~" and p["group"] == 2
    )
    assert (intercept["free"] == 0) is (stage in ["configural", "scalar", "strict"])
    assert (residual["free"] == 0) is (stage in ["configural", "strict"])


@pytest.mark.integration
def test_generated_identification_matches_hand_specified_constraints(datcat):
    completed = subprocess.run(
        ["Rscript", str(REFERENCE / "ordinal_invariance_manual.R")],
        env=ordinal_invariance_r_environment(),
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    manual = json.loads(completed.stdout)
    result = ordinal_measurement_invariance(
        _request(**datcat, stage="thresholds", prior_stage_reviewed=True)
    )
    for model in result["models"]:
        expected = manual[model["stage"]]
        assert model["fit"]["standard"]["chi_square"] == pytest.approx(
            expected["chisq"], abs=1e-5, rel=0
        )
        assert model["fit"]["scaled"]["chi_square"] == pytest.approx(
            expected["chisq.scaled"], abs=1e-5, rel=0
        )
        assert model["fit"]["standard"]["degrees_of_freedom"] == expected["df"]


@pytest.mark.integration
def test_four_category_threshold_stage_has_independent_restrictions(datcat):
    values = [[min(int(value), 4) for value in row] for row in datcat["values"]]
    result = ordinal_measurement_invariance(
        _request(
            values=values, groups=datcat["groups"], stage="thresholds", prior_stage_reviewed=True
        )
    )
    test = result["comparisons"][0]
    assert test["comparison_valid"] is True
    # Three thresholds per item, less two released location/scale restrictions.
    assert test["adjusted_difference_test"]["degrees_of_freedom_difference"] == 8
