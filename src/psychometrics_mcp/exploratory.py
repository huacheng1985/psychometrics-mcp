"""Safe adapters for continuous-variable parallel analysis and EFA in psych."""

from __future__ import annotations

import json
import shutil
import subprocess
from importlib import resources
from typing import Any

import numpy as np

from .models import ExploratoryFactorAnalysisRequest, ParallelAnalysisRequest


class ExploratoryFactorAnalysisError(RuntimeError):
    """Raised when exploratory-factor preflight or the fixed R adapter fails."""


def exploratory_factor_capabilities() -> dict[str, dict[str, Any]]:
    """Report availability of the fixed psych parallel-analysis and EFA engines."""
    rscript = shutil.which("Rscript")
    parallel: dict[str, Any] = {
        "available": False,
        "engine": "psych::fa with simulated common-factor eigenvalues",
        "extractions": ["minres", "ml"],
    }
    efa: dict[str, Any] = {
        "available": False,
        "engine": "psych::fa",
        "extractions": ["minres", "ml"],
        "rotations": ["oblimin", "varimax", "none"],
    }
    if not rscript:
        reason = "Rscript was not found on PATH."
        parallel["reason"] = reason
        efa["reason"] = reason
        return {"parallel_analysis": parallel, "exploratory_factor_analysis": efa}

    check = subprocess.run(
        [
            rscript,
            "-e",
            'cat(requireNamespace("jsonlite", quietly=TRUE), " ", '
            'requireNamespace("psych", quietly=TRUE), " ", '
            'requireNamespace("GPArotation", quietly=TRUE), sep="")',
        ],
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )
    jsonlite_available, psych_available, rotation_available = (
        check.stdout.strip().split() if check.returncode == 0 else ["FALSE"] * 3
    )
    base_available = jsonlite_available == psych_available == "TRUE"
    parallel["available"] = base_available
    efa["available"] = base_available and rotation_available == "TRUE"
    if not parallel["available"]:
        parallel["reason"] = "R packages psych and jsonlite are required."
    if not efa["available"]:
        efa["reason"] = "R packages psych, GPArotation, and jsonlite are required."
    return {"parallel_analysis": parallel, "exploratory_factor_analysis": efa}


def _preflight(
    request: ParallelAnalysisRequest | ExploratoryFactorAnalysisRequest,
) -> tuple[np.ndarray, list[str], list[int], list[str]]:
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
    complete = ~np.isnan(matrix).any(axis=1)
    excluded_rows = (np.flatnonzero(~complete) + 1).tolist()
    matrix = matrix[complete]
    rows, variables = matrix.shape

    if rows < 20:
        raise ExploratoryFactorAnalysisError(
            "Continuous-variable factor analysis requires at least 20 complete rows under "
            f"this conservative execution contract; found {rows}."
        )
    if rows <= variables:
        raise ExploratoryFactorAnalysisError(
            "The number of complete rows must exceed the number of variables."
        )
    for index, name in enumerate(names):
        if np.var(matrix[:, index], ddof=1) <= 0:
            raise ExploratoryFactorAnalysisError(
                f"Variable {name!r} has zero variance in complete rows."
            )

    correlation = np.corrcoef(matrix, rowvar=False)
    if np.linalg.matrix_rank(correlation) < variables:
        raise ExploratoryFactorAnalysisError(
            "The complete-case correlation matrix is rank deficient."
        )
    if float(np.min(np.linalg.eigvalsh(correlation))) <= 1e-10:
        raise ExploratoryFactorAnalysisError(
            "The complete-case correlation matrix is not positive definite."
        )

    warnings: list[str] = []
    if excluded_rows:
        warnings.append(
            f"Listwise deletion excluded {len(excluded_rows)} rows with missing values."
        )
    if rows < 200:
        warnings.append(
            "Fewer than 200 complete rows; evaluate factor stability, communalities, and "
            "loading recovery for the specific design rather than treating a fixed sample-size "
            "rule as sufficient."
        )
    return matrix, names, excluded_rows, warnings


def _run_adapter(payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    script = resources.files("psychometrics_mcp").joinpath("r", "exploratory_factor.R")
    completed = subprocess.run(
        [shutil.which("Rscript") or "Rscript", str(script)],
        input=json.dumps(payload),
        capture_output=True,
        check=False,
        text=True,
        timeout=timeout,
    )
    if completed.returncode != 0:
        error_lines = [
            line
            for line in completed.stderr.strip().splitlines()
            if line and line != "Execution halted"
        ]
        detail = error_lines[-1] if error_lines else "unknown R error"
        raise ExploratoryFactorAnalysisError(f"Fixed psych adapter failed: {detail}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ExploratoryFactorAnalysisError(
            "Fixed psych adapter returned invalid JSON."
        ) from exc


def _finalize(
    result: dict[str, Any],
    request: ParallelAnalysisRequest | ExploratoryFactorAnalysisRequest,
    matrix: np.ndarray,
    excluded_rows: list[int],
    warnings: list[str],
) -> dict[str, Any]:
    result["schema_version"] = "1.0"
    result["sample_flow"] = {
        "input_rows": len(request.data.values),
        "analyzed_rows": int(matrix.shape[0]),
        "excluded_rows": excluded_rows[:100],
        "excluded_rows_truncated": len(excluded_rows) > 100,
        "variables": int(matrix.shape[1]),
    }
    result["warnings"] = warnings + result.get("warnings", [])
    result["interpretation_boundary"] = (
        "Exploratory factor results are model-dependent evidence about covariance structure. "
        "They do not name constructs, confirm a measurement model, establish score validity, "
        "invariance, fairness, causal meaning, or fitness for consequential decisions. Factor "
        "retention and interpretation require substantive judgment and sensitivity analyses."
    )
    return result


def parallel_analysis(request: ParallelAnalysisRequest) -> dict[str, Any]:
    """Run Horn-style common-factor parallel analysis with a recorded random seed."""
    matrix, names, excluded_rows, warnings = _preflight(request)
    capability = exploratory_factor_capabilities()["parallel_analysis"]
    if not capability["available"]:
        raise ExploratoryFactorAnalysisError(
            capability.get("reason", "The psych parallel-analysis engine is unavailable.")
        )
    result = _run_adapter(
        {
            "action": "parallel_analysis",
            "values": matrix.tolist(),
            "variable_names": names,
            "extraction": request.extraction,
            "iterations": request.iterations,
            "percentile": request.percentile,
            "seed": request.seed,
        },
        timeout=300,
    )
    result["references"] = [
        {
            "role": "method_foundation",
            "citation": (
                "Horn, J. L. (1965). A rationale and test for the number of factors in "
                "factor analysis. Psychometrika, 30, 179-185."
            ),
            "doi": "10.1007/BF02289447",
        },
        {
            "role": "method_evaluation",
            "citation": (
                "Hayton, J. C., Allen, D. G., & Scarpello, V. (2004). Factor retention "
                "decisions in exploratory factor analysis: A tutorial on parallel analysis. "
                "Organizational Research Methods, 7(2), 191-205."
            ),
            "doi": "10.1177/1094428104263675",
        },
        {
            "role": "engine",
            "citation": "Revelle, W. psych: Procedures for Psychological Research.",
            "url": "https://CRAN.R-project.org/package=psych",
        },
    ]
    return _finalize(result, request, matrix, excluded_rows, warnings)


def exploratory_factor_analysis(
    request: ExploratoryFactorAnalysisRequest,
) -> dict[str, Any]:
    """Fit a constrained continuous-variable EFA through psych::fa."""
    matrix, names, excluded_rows, warnings = _preflight(request)
    capability = exploratory_factor_capabilities()["exploratory_factor_analysis"]
    if not capability["available"]:
        raise ExploratoryFactorAnalysisError(
            capability.get("reason", "The psych EFA engine is unavailable.")
        )
    result = _run_adapter(
        {
            "action": "exploratory_factor_analysis",
            "values": matrix.tolist(),
            "variable_names": names,
            "factors": request.factors,
            "extraction": request.extraction,
            "rotation": request.rotation,
        },
        timeout=180,
    )
    result["references"] = [
        {
            "role": "method_guidance",
            "citation": (
                "Fabrigar, L. R., Wegener, D. T., MacCallum, R. C., & Strahan, E. J. "
                "(1999). Evaluating the use of exploratory factor analysis in psychological "
                "research. Psychological Methods, 4(3), 272-299."
            ),
            "doi": "10.1037/1082-989X.4.3.272",
        },
        {
            "role": "rotation_foundation",
            "citation": (
                "Browne, M. W. (2001). An overview of analytic rotation in exploratory "
                "factor analysis. Multivariate Behavioral Research, 36(1), 111-150."
            ),
            "doi": "10.1207/S15327906MBR3601_05",
        },
        {
            "role": "engine",
            "citation": "Revelle, W. psych: Procedures for Psychological Research.",
            "url": "https://CRAN.R-project.org/package=psych",
        },
    ]
    return _finalize(result, request, matrix, excluded_rows, warnings)
