"""Binary/three-category contracts and adversarial execution boundaries."""

import copy
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest

from psychometrics_mcp.models import OrdinalMeasurementInvarianceRequest
from psychometrics_mcp.ordinal_invariance import (
    PROFILE_STAGES,
    OrdinalInvarianceError,
    analysis_fingerprint,
    ordinal_invariance_capabilities,
    ordinal_invariance_r_environment,
    ordinal_measurement_invariance,
)

NAMES = [f"u{i}" for i in range(1, 7)]
REFERENCE = Path(__file__).parent / "reference"


def simulated_request(profile="binary", stage="configural", seed=721, noninvariant=False):
    rng = np.random.default_rng(seed)
    factor = rng.normal(size=(2000, 1))
    response = 0.7 * factor + rng.normal(size=(2000, 6))
    offsets = np.linspace(-1, 1, 6)
    if noninvariant:
        response[1000:, 0] += 1.1 * factor[1000:, 0]
        response[1000:, 2] += 1.0
    if profile == "binary":
        values = (response > offsets).astype(int)
    else:
        values = (response > (offsets - 0.5)).astype(int) + (response > (offsets + 0.5)).astype(int)
    return OrdinalMeasurementInvarianceRequest(
        data={"values": values.tolist(), "variable_names": NAMES},
        groups=["a"] * 1000 + ["b"] * 1000,
        factors=[{"name": "f", "indicators": NAMES}],
        category_profile=profile,
        stage=stage,
        prior_stage_reviewed=stage != "configural",
    )


@pytest.fixture(scope="module")
def engine():
    if not ordinal_invariance_capabilities()["ordinal_measurement_invariance"]["available"]:
        pytest.skip("Ordinal invariance R dependencies unavailable")


def test_fingerprint_is_stage_independent_and_ignores_unselected_columns():
    request = simulated_request()
    expected = analysis_fingerprint(request)
    request.stage = "joint"
    request.prior_stage_reviewed = True
    request.reviewed_analysis_sha256 = expected
    assert analysis_fingerprint(request) == expected
    request.data.variable_names.append("unused")
    for row in request.data.values:
        row.append(42)
    assert analysis_fingerprint(request) == expected


@pytest.mark.parametrize("change", ["response", "group", "missing", "order", "factor", "profile"])
def test_fingerprint_detects_analysis_changes(change):
    request = simulated_request()
    expected = analysis_fingerprint(request)
    if change == "response":
        request.data.values[0][0] = 1 - request.data.values[0][0]
    elif change == "group":
        request.groups[0] = "b"
    elif change == "missing":
        request.data.values[0][0] = None
    elif change == "order":
        request.data.values.reverse()
    elif change == "factor":
        request.factors[0].name = "different_factor"
    else:
        request.category_profile = "three_category"
    assert analysis_fingerprint(request) != expected


def test_review_mismatch_stops_before_r(monkeypatch):
    request = simulated_request(stage="joint")
    request.reviewed_analysis_sha256 = "0" * 64
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: pytest.fail("R must not run"))
    with pytest.raises(OrdinalInvarianceError) as caught:
        ordinal_measurement_invariance(request)
    assert caught.value.code == "REVIEW_MISMATCH"


def test_binary_separate_metric_stage_rejected():
    with pytest.raises(OrdinalInvarianceError) as caught:
        ordinal_measurement_invariance(simulated_request(stage="metric"))
    assert caught.value.code == "STAGE_UNSUPPORTED"


def test_mixed_category_profiles_are_not_automatically_recoded():
    request = simulated_request()
    request.data.values[0][0] = 2
    request.data.values[1][0] = 2
    with pytest.raises(OrdinalInvarianceError) as caught:
        ordinal_measurement_invariance(request)
    assert caught.value.code == "INPUT_INVALID"


@pytest.mark.parametrize(
    "code", ["IDENTIFICATION_FAILURE", "NONCONVERGENCE", "INADMISSIBLE_SOLUTION"]
)
def test_r_failure_codes_preserved(monkeypatch, code):
    def fake_run(*args, **kwargs):
        output = (
            "TRUE"
            if "-e" in args[0]
            else json.dumps(
                {
                    "status": "error",
                    "error": {"code": code, "message": "Controlled failure", "stage": "configural"},
                }
            )
        )
        return subprocess.CompletedProcess(args[0], 0, output, "")

    monkeypatch.setattr("psychometrics_mcp.ordinal_invariance.shutil.which", lambda _: "Rscript")
    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(OrdinalInvarianceError) as caught:
        ordinal_measurement_invariance(simulated_request())
    assert caught.value.as_result()["error"]["code"] == code


@pytest.mark.integration
@pytest.mark.parametrize("profile", ["binary", "three_category"])
def test_profiles_match_numeric_references(engine, profile):
    targets = json.loads((REFERENCE / "discrete_invariance_expected.json").read_text())[profile]
    fingerprint = analysis_fingerprint(simulated_request(profile))
    for index, stage in enumerate(PROFILE_STAGES[profile]):
        request = simulated_request(profile, stage)
        if index:
            request.reviewed_analysis_sha256 = fingerprint
        result = ordinal_measurement_invariance(request)
        assert result["schema_version"] == "1.1"
        assert result["analysis_sha256"] == fingerprint
        assert result["review"]["analysis_fingerprint_checked"] == (index > 0)
        model = result["models"][-1]
        assert model["fit"]["standard"]["degrees_of_freedom"] == targets["df"][index]
        assert model["fit"]["standard"]["chi_square"] == pytest.approx(
            targets["chi_square"][index], abs=1e-5, rel=0
        )
        assert model["fit"]["scaled"]["chi_square"] == pytest.approx(
            targets["scaled_chi_square"][index], abs=1e-5, rel=0
        )
        if profile == "three_category" and stage == "thresholds":
            comparison = result["comparisons"][0]
            assert comparison["comparison_valid"] is False
            assert comparison["code"] == "NOT_INDEPENDENTLY_TESTABLE"
            assert comparison["adjusted_difference_test"]["p_value"] is None
            assert comparison["adjusted_difference_test"]["chi_square_difference"] is None
            assert comparison["adjusted_difference_test"]["degrees_of_freedom_difference"] == 0
        elif index:
            assert result["comparisons"][0]["comparison_valid"] is True
            test = result["comparisons"][0]["adjusted_difference_test"]
            assert test["chi_square_difference"] == pytest.approx(
                targets["adjusted_difference"][index - 1], abs=1e-5, rel=0
            )
            assert test["p_value"] == pytest.approx(targets["p"][index - 1], abs=1e-5, rel=0)


@pytest.mark.integration
@pytest.mark.parametrize("profile,stage", [("binary", "joint"), ("three_category", "scalar")])
def test_known_noninvariance_is_visible_in_this_fixed_simulation(engine, profile, stage):
    request = simulated_request(profile, stage, noninvariant=True)
    result = ordinal_measurement_invariance(request)
    comparison = result["comparisons"][0]
    assert comparison["comparison_valid"] is True
    assert comparison["adjusted_difference_test"]["p_value"] < 0.01
    assert comparison["automatic_decision"] is None


@pytest.mark.integration
@pytest.mark.parametrize("profile,stage", [("binary", "joint"), ("three_category", "thresholds")])
def test_hand_specified_models_match_generator(engine, profile, stage):
    request = simulated_request(profile, stage)
    result = ordinal_measurement_invariance(request)
    completed = subprocess.run(
        ["Rscript", str(REFERENCE / "discrete_invariance_manual.R")],
        input=json.dumps(
            {"values": request.data.values, "groups": request.groups, "profile": profile}
        ),
        env=ordinal_invariance_r_environment(),
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    manual = json.loads(completed.stdout)
    for model in result["models"]:
        target = manual[model["stage"]]
        assert model["fit"]["standard"]["chi_square"] == pytest.approx(
            target["chisq"], abs=1e-5, rel=0
        )
        assert model["fit"]["standard"]["degrees_of_freedom"] == target["df"]


def test_dependency_and_timeout_errors(monkeypatch):
    monkeypatch.setattr("psychometrics_mcp.ordinal_invariance.shutil.which", lambda _: None)
    with pytest.raises(OrdinalInvarianceError) as caught:
        ordinal_measurement_invariance(simulated_request())
    assert caught.value.code == "DEPENDENCY_UNAVAILABLE"
    monkeypatch.setattr("psychometrics_mcp.ordinal_invariance.shutil.which", lambda _: "Rscript")

    def fake_run(*args, **kwargs):
        if "-e" in args[0]:
            return subprocess.CompletedProcess(args[0], 0, "TRUE", "")
        raise subprocess.TimeoutExpired("Rscript", 300)

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(OrdinalInvarianceError) as caught:
        ordinal_measurement_invariance(copy.deepcopy(simulated_request()))
    assert caught.value.code == "EXECUTION_TIMEOUT"


@pytest.mark.parametrize(
    "output,returncode,code",
    [
        ("not json", 0, "INVALID_ENGINE_OUTPUT"),
        ("[]", 0, "INVALID_ENGINE_OUTPUT"),
        ('{"status":"error"}', 0, "INVALID_ENGINE_OUTPUT"),
        ('{"status":"success","models":[null]}', 0, "INVALID_ENGINE_OUTPUT"),
        ("", 1, "ENGINE_FAILURE"),
    ],
)
def test_malformed_engine_output_is_a_controlled_error(monkeypatch, output, returncode, code):
    monkeypatch.setattr("psychometrics_mcp.ordinal_invariance.shutil.which", lambda _: "Rscript")

    def fake_run(*args, **kwargs):
        if "-e" in args[0]:
            return subprocess.CompletedProcess(args[0], 0, "TRUE", "")
        return subprocess.CompletedProcess(args[0], returncode, output, "private raw data")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(OrdinalInvarianceError) as caught:
        ordinal_measurement_invariance(simulated_request())
    assert caught.value.code == code
    assert "private raw data" not in str(caught.value)
