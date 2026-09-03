"""Safe adapter for fixed continuous-indicator multi-group invariance models."""

from __future__ import annotations

import json
import shutil
import subprocess
from importlib import resources
from typing import Any

import numpy as np

from .models import ContinuousMeasurementInvarianceRequest


class MeasurementInvarianceError(RuntimeError):
    """Raised when invariance preflight or the fixed lavaan adapter fails."""


def measurement_invariance_capabilities() -> dict[str, dict[str, Any]]:
    """Report availability of the admitted multi-group invariance engine."""
    capability: dict[str, Any] = {
        "available": False,
        "engine": "lavaan::cfa + lavaan::lavTestLRT",
        "indicator_scale": "continuous",
        "estimators": ["ML", "MLR"],
        "stages": ["configural", "metric", "scalar", "strict"],
        "automatic_decision": False,
        "partial_invariance_search": False,
    }
    rscript = shutil.which("Rscript")
    if not rscript:
        capability["reason"] = "Rscript was not found on PATH."
        return {"continuous_measurement_invariance": capability}
    check = subprocess.run(
        [
            rscript,
            "-e",
            'cat(requireNamespace("jsonlite", quietly=TRUE) && '
            'requireNamespace("lavaan", quietly=TRUE))',
        ],
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )
    capability["available"] = check.returncode == 0 and check.stdout == "TRUE"
    if not capability["available"]:
        capability["reason"] = "R packages lavaan and jsonlite are required."
    return {"continuous_measurement_invariance": capability}


def _preflight(
    request: ContinuousMeasurementInvarianceRequest,
) -> tuple[np.ndarray, list[str], list[str], list[Any], list[int], list[dict[str, Any]], list[str]]:
    matrix = np.array(
        [
            [np.nan if value is None else float(value) for value in row]
            for row in request.data.values
        ],
        dtype=float,
    )
    names = request.data.variable_names or [
        f"variable_{index + 1}" for index in range(matrix.shape[1])
    ]
    indicators = [indicator for factor in request.factors for indicator in factor.indicators]
    name_to_index = {name: index for index, name in enumerate(names)}
    selected = matrix[:, [name_to_index[indicator] for indicator in indicators]]
    complete = ~np.isnan(selected).any(axis=1)
    excluded_rows = (np.flatnonzero(~complete) + 1).tolist()
    selected = selected[complete]
    analyzed_groups = [group for group, keep in zip(request.groups, complete, strict=True) if keep]

    unique_groups = list(dict.fromkeys(request.groups))
    group_ids = [f"g{index + 1}" for index in range(len(unique_groups))]
    group_to_id = dict(zip(unique_groups, group_ids, strict=True))
    encoded_groups = [group_to_id[group] for group in analyzed_groups]
    group_flow: list[dict[str, Any]] = []
    warnings: list[str] = []

    for group, group_id in zip(unique_groups, group_ids, strict=True):
        group_mask = np.array([value == group for value in analyzed_groups], dtype=bool)
        group_matrix = selected[group_mask]
        input_rows = sum(value == group for value in request.groups)
        analyzed_rows = int(group_matrix.shape[0])
        if analyzed_rows < 100:
            raise MeasurementInvarianceError(
                f"Group {group!r} requires at least 100 complete rows under this conservative "
                f"execution contract; found {analyzed_rows}."
            )
        if analyzed_rows <= len(indicators):
            raise MeasurementInvarianceError(
                f"Group {group!r} must have more complete rows than indicators."
            )
        for index, indicator in enumerate(indicators):
            if np.var(group_matrix[:, index], ddof=1) <= 0:
                raise MeasurementInvarianceError(
                    f"Indicator {indicator!r} has zero variance in group {group!r}."
                )
        correlation = np.corrcoef(group_matrix, rowvar=False)
        if np.linalg.matrix_rank(correlation) < len(indicators):
            raise MeasurementInvarianceError(
                f"The indicator correlation matrix is rank deficient in group {group!r}."
            )
        if float(np.min(np.linalg.eigvalsh(correlation))) <= 1e-10:
            raise MeasurementInvarianceError(
                f"The indicator correlation matrix is not positive definite in group {group!r}."
            )
        if analyzed_rows < 200:
            warnings.append(
                f"Group {group!r} has fewer than 200 complete rows; evaluate parameter and "
                "fit-index stability for the specific model and group distributions."
            )
        group_flow.append(
            {
                "group": group,
                "internal_group_id": group_id,
                "input_rows": input_rows,
                "analyzed_rows": analyzed_rows,
                "excluded_rows": input_rows - analyzed_rows,
            }
        )

    if excluded_rows:
        warnings.insert(
            0,
            f"Listwise deletion excluded {len(excluded_rows)} rows with missing selected "
            "indicators.",
        )
    if len(request.factors) == 1 and len(indicators) == 3:
        warnings.append(
            "Each group's configural one-factor, three-indicator model is just-identified; "
            "its global fit cannot test the group-specific measurement structure."
        )
    return (
        selected,
        indicators,
        encoded_groups,
        unique_groups,
        excluded_rows,
        group_flow,
        warnings,
    )


def continuous_measurement_invariance(
    request: ContinuousMeasurementInvarianceRequest,
) -> dict[str, Any]:
    """Fit configural, metric, scalar, and strict continuous-indicator models."""
    (
        selected,
        indicators,
        encoded_groups,
        group_labels,
        excluded_rows,
        group_flow,
        warnings,
    ) = _preflight(request)
    capability = measurement_invariance_capabilities()["continuous_measurement_invariance"]
    if not capability["available"]:
        raise MeasurementInvarianceError(
            capability.get("reason", "The lavaan invariance engine is unavailable.")
        )

    internal_indicators = [f"v{index + 1}" for index in range(len(indicators))]
    indicator_to_internal = dict(zip(indicators, internal_indicators, strict=True))
    factor_payload = [
        {
            "id": f"f{index + 1}",
            "name": factor.name,
            "indicators": [indicator_to_internal[name] for name in factor.indicators],
        }
        for index, factor in enumerate(request.factors)
    ]
    group_payload = [
        {"id": f"g{index + 1}", "label": label} for index, label in enumerate(group_labels)
    ]
    script = resources.files("psychometrics_mcp").joinpath(
        "r", "continuous_measurement_invariance.R"
    )
    completed = subprocess.run(
        [shutil.which("Rscript") or "Rscript", str(script)],
        input=json.dumps(
            {
                "values": selected.tolist(),
                "indicator_ids": internal_indicators,
                "indicator_names": indicators,
                "groups": encoded_groups,
                "group_map": group_payload,
                "factors": factor_payload,
                "estimator": request.estimator,
            }
        ),
        capture_output=True,
        check=False,
        text=True,
        timeout=300,
    )
    if completed.returncode != 0:
        error_lines = [
            line
            for line in completed.stderr.strip().splitlines()
            if line and line != "Execution halted"
        ]
        detail = next(
            (line for line in reversed(error_lines) if line.startswith("Error")),
            error_lines[-1] if error_lines else "unknown R error",
        )
        raise MeasurementInvarianceError(f"Fixed lavaan invariance adapter failed: {detail}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise MeasurementInvarianceError(
            "Fixed lavaan invariance adapter returned invalid JSON."
        ) from exc

    models = result.get("models", [])
    comparisons = result.get("comparisons", [])
    if len(models) != 4 or len(comparisons) != 3:
        raise MeasurementInvarianceError(
            "Fixed lavaan invariance adapter returned an incomplete model sequence."
        )
    failed_stages = [
        model["stage"]
        for model in models
        if (
            not model.get("converged", False)
            or not model.get("post_check", False)
            or not model.get("diagnostics", {}).get("residual_variances_nonnegative", False)
            or not model.get("diagnostics", {}).get("latent_covariances_positive_definite", False)
        )
    ]
    if failed_stages:
        raise MeasurementInvarianceError(
            "lavaan convergence or admissibility checks failed for stages: "
            + ", ".join(failed_stages)
            + "."
        )

    result["schema_version"] = "1.0"
    result["sample_flow"] = {
        "input_rows": len(request.data.values),
        "analyzed_rows": int(selected.shape[0]),
        "excluded_rows": excluded_rows[:100],
        "excluded_rows_truncated": len(excluded_rows) > 100,
        "indicators": len(indicators),
        "factors": len(request.factors),
        "groups": group_flow,
    }
    result["warnings"] = warnings + result.get("warnings", [])
    result["references"] = [
        {
            "role": "method_framework",
            "citation": (
                "Meredith, W. (1993). Measurement invariance, factor analysis and "
                "factorial invariance. Psychometrika, 58, 525-543."
            ),
            "doi": "10.1007/BF02294825",
        },
        {
            "role": "fit_change_evaluation",
            "citation": (
                "Cheung, G. W., & Rensvold, R. B. (2002). Evaluating goodness-of-fit "
                "indexes for testing measurement invariance. Structural Equation Modeling, "
                "9(2), 233-255."
            ),
            "doi": "10.1207/S15328007SEM0902_5",
        },
        {
            "role": "fit_change_sensitivity",
            "citation": (
                "Chen, F. F. (2007). Sensitivity of goodness of fit indexes to lack of "
                "measurement invariance. Structural Equation Modeling, 14(3), 464-504."
            ),
            "doi": "10.1080/10705510701301834",
        },
        {
            "role": "engine",
            "citation": (
                "Rosseel, Y. (2012). lavaan: An R package for structural equation "
                "modeling. Journal of Statistical Software, 48(2), 1-36."
            ),
            "doi": "10.18637/jss.v048.i02",
        },
    ]
    result["interpretation_boundary"] = (
        "The sequence evaluates increasingly restrictive equality constraints in a "
        "prespecified continuous-indicator CFA. Chi-square differences and changes in CFI, "
        "RMSEA, and SRMR are evidence, not universal pass/fail rules. Meaningful comparison "
        "also requires adequate configural fit, identification, representative groups, "
        "substantive review, and attention to power and approximation error. The tool does not "
        "search for partial invariance, authorize observed or latent mean comparisons, establish "
        "fairness or validity, or prove that groups interpret scores identically."
    )
    return result
