"""Safe adapter for fixed continuous-indicator CFA models in lavaan."""

from __future__ import annotations

import json
import shutil
import subprocess
from importlib import resources
from typing import Any

import numpy as np

from .models import CFARequest


class ConfirmatoryFactorAnalysisError(RuntimeError):
    """Raised when CFA preflight or the fixed lavaan adapter fails."""


def factor_capabilities() -> dict[str, Any]:
    """Report availability of the fixed lavaan CFA engine."""
    rscript = shutil.which("Rscript")
    result: dict[str, Any] = {
        "available": False,
        "engine": "lavaan::cfa",
        "estimators": ["ML", "MLR"],
    }
    if not rscript:
        result["reason"] = "Rscript was not found on PATH."
        return result
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
    result["available"] = check.returncode == 0 and check.stdout == "TRUE"
    if not result["available"]:
        result["reason"] = "R packages lavaan and jsonlite are required."
    return result


def _preflight(request: CFARequest) -> tuple[np.ndarray, list[str], list[int], list[str]]:
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
    name_to_index = {name: index for index, name in enumerate(names)}
    indicators = [indicator for factor in request.factors for indicator in factor.indicators]
    selected = matrix[:, [name_to_index[indicator] for indicator in indicators]]
    complete = ~np.isnan(selected).any(axis=1)
    excluded_rows = (np.flatnonzero(~complete) + 1).tolist()
    selected = selected[complete]

    if selected.shape[0] < 20:
        raise ConfirmatoryFactorAnalysisError(
            "Continuous-indicator CFA requires at least 20 complete rows under this "
            f"conservative execution contract; found {selected.shape[0]}."
        )
    for index, indicator in enumerate(indicators):
        if np.var(selected[:, index], ddof=1) <= 0:
            raise ConfirmatoryFactorAnalysisError(
                f"Indicator {indicator!r} has zero variance in complete rows."
            )
    correlation = np.corrcoef(selected, rowvar=False)
    if np.linalg.matrix_rank(correlation) < len(indicators):
        raise ConfirmatoryFactorAnalysisError(
            "The complete-case indicator correlation matrix is rank deficient."
        )

    warnings: list[str] = []
    if excluded_rows:
        warnings.append(
            f"Listwise deletion excluded {len(excluded_rows)} rows with missing selected "
            "indicators."
        )
    if selected.shape[0] < 200:
        warnings.append(
            "Fewer than 200 complete rows; evaluate estimate and fit-index stability for the "
            "specific model rather than treating a sample-size rule as sufficient."
        )
    if len(request.factors) == 1 and len(indicators) == 3:
        warnings.append(
            "A one-factor, three-indicator model is typically just-identified; global fit "
            "indices cannot test the measurement structure."
        )
    return selected, indicators, excluded_rows, warnings


def confirmatory_factor_analysis(request: CFARequest) -> dict[str, Any]:
    """Fit a fixed, simple-structure continuous CFA through lavaan::cfa."""
    selected, indicators, excluded_rows, warnings = _preflight(request)
    capability = factor_capabilities()
    if not capability["available"]:
        raise ConfirmatoryFactorAnalysisError(
            capability.get("reason", "The lavaan CFA engine is unavailable.")
        )

    internal_indicators = [f"v{index + 1}" for index in range(len(indicators))]
    indicator_to_internal = dict(zip(indicators, internal_indicators, strict=True))
    factor_payload = []
    for index, factor in enumerate(request.factors):
        factor_payload.append(
            {
                "id": f"f{index + 1}",
                "name": factor.name,
                "indicators": [indicator_to_internal[name] for name in factor.indicators],
            }
        )
    payload = {
        "values": selected.tolist(),
        "indicator_ids": internal_indicators,
        "indicator_names": indicators,
        "factors": factor_payload,
        "estimator": request.estimator,
        "confidence_level": request.confidence_level,
    }
    script = resources.files("psychometrics_mcp").joinpath("r", "cfa_model.R")
    completed = subprocess.run(
        [shutil.which("Rscript") or "Rscript", str(script)],
        input=json.dumps(payload),
        capture_output=True,
        check=False,
        text=True,
        timeout=120,
    )
    if completed.returncode != 0:
        detail = (
            completed.stderr.strip().splitlines()[-1]
            if completed.stderr.strip()
            else "unknown R error"
        )
        raise ConfirmatoryFactorAnalysisError(f"Fixed lavaan adapter failed: {detail}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ConfirmatoryFactorAnalysisError(
            "Fixed lavaan adapter returned invalid JSON."
        ) from exc
    if not result.get("model", {}).get("converged", False):
        raise ConfirmatoryFactorAnalysisError("lavaan did not converge for the requested CFA.")

    result["schema_version"] = "1.0"
    result["sample_flow"] = {
        "input_rows": len(request.data.values),
        "analyzed_rows": int(selected.shape[0]),
        "excluded_rows": excluded_rows[:100],
        "excluded_rows_truncated": len(excluded_rows) > 100,
        "indicators": len(indicators),
        "factors": len(request.factors),
    }
    result["warnings"] = warnings + result.get("warnings", [])
    result["references"] = [
        {
            "role": "method_foundation",
            "citation": (
                "Joreskog, K. G. (1969). A general approach to confirmatory maximum "
                "likelihood factor analysis. Psychometrika, 34, 183-202."
            ),
            "doi": "10.1007/BF02289343",
        },
        {
            "role": "engine",
            "citation": (
                "Rosseel, Y. (2012). lavaan: An R package for structural equation "
                "modeling. Journal of Statistical Software, 48(2), 1-36."
            ),
            "doi": "10.18637/jss.v048.i02",
        },
        {
            "role": "interpretation_limit",
            "citation": (
                "Marsh, H. W., Hau, K. T., & Wen, Z. (2004). In search of golden "
                "rules. Structural Equation Modeling, 11(3), 320-341."
            ),
            "doi": "10.1207/S15328007SEM1103_2",
        },
    ]
    result["interpretation_boundary"] = (
        "CFA fit and parameter estimates are evidence about a prespecified covariance model. "
        "They do not by themselves establish construct validity, score comparability, causal "
        "meaning, fairness, or measurement invariance."
    )
    return result
