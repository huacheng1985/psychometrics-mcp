"""Safe adapters for ordinal correlation, EFA, and categorical CFA."""

from __future__ import annotations

import json
import shutil
import subprocess
from importlib import resources
from typing import Any

import numpy as np

from .models import CategoricalCFARequest, OrdinalEFARequest, PolychoricCorrelationRequest


class OrdinalAnalysisError(RuntimeError):
    """Raised when ordinal-data preflight or a fixed R adapter fails."""


def ordinal_capabilities() -> dict[str, dict[str, Any]]:
    """Report availability of fixed psych and lavaan ordinal-data engines."""
    rscript = shutil.which("Rscript")
    polychoric: dict[str, Any] = {
        "available": False,
        "engine": "psych::polychoric",
        "smoothing": False,
    }
    categorical_cfa: dict[str, Any] = {
        "available": False,
        "engine": "lavaan::cfa",
        "estimator": "WLSMV",
        "parameterization": "delta",
    }
    ordinal_efa: dict[str, Any] = {
        "available": False,
        "engine": "psych::polychoric + psych::fa",
        "extractions": ["minres", "ml"],
        "rotations": ["oblimin", "varimax", "none"],
        "smoothing": False,
    }
    if not rscript:
        reason = "Rscript was not found on PATH."
        polychoric["reason"] = reason
        categorical_cfa["reason"] = reason
        ordinal_efa["reason"] = reason
        return {
            "polychoric_correlation_matrix": polychoric,
            "ordinal_exploratory_factor_analysis": ordinal_efa,
            "categorical_confirmatory_factor_analysis": categorical_cfa,
        }

    check = subprocess.run(
        [
            rscript,
            "-e",
            'cat(requireNamespace("jsonlite", quietly=TRUE), " ", '
            'requireNamespace("psych", quietly=TRUE), " ", '
            'requireNamespace("lavaan", quietly=TRUE), " ", '
            'requireNamespace("GPArotation", quietly=TRUE), sep="")',
        ],
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )
    available = check.stdout.strip().split() if check.returncode == 0 else []
    jsonlite_available, psych_available, lavaan_available, rotation_available = (
        available if len(available) == 4 else ["FALSE"] * 4
    )
    polychoric["available"] = jsonlite_available == psych_available == "TRUE"
    ordinal_efa["available"] = (
        jsonlite_available == psych_available == rotation_available == "TRUE"
    )
    categorical_cfa["available"] = jsonlite_available == lavaan_available == "TRUE"
    if not polychoric["available"]:
        polychoric["reason"] = "R packages psych and jsonlite are required."
    if not categorical_cfa["available"]:
        categorical_cfa["reason"] = "R packages lavaan and jsonlite are required."
    if not ordinal_efa["available"]:
        ordinal_efa["reason"] = (
            "R packages psych, GPArotation, and jsonlite are required."
        )
    return {
        "polychoric_correlation_matrix": polychoric,
        "ordinal_exploratory_factor_analysis": ordinal_efa,
        "categorical_confirmatory_factor_analysis": categorical_cfa,
    }


def _preflight(
    values: list[list[int | None]],
    all_names: list[str],
    selected_names: list[str],
    minimum_rows: int,
) -> tuple[np.ndarray, list[int], list[dict[str, Any]], list[str]]:
    matrix = np.array(
        [[np.nan if value is None else int(value) for value in row] for row in values],
        dtype=float,
    )
    name_to_index = {name: index for index, name in enumerate(all_names)}
    selected = matrix[:, [name_to_index[name] for name in selected_names]]
    complete = ~np.isnan(selected).any(axis=1)
    excluded_rows = (np.flatnonzero(~complete) + 1).tolist()
    selected = selected[complete]

    if selected.shape[0] < minimum_rows:
        raise OrdinalAnalysisError(
            f"Ordinal analysis requires at least {minimum_rows} complete rows under this "
            f"execution contract; found {selected.shape[0]}."
        )

    category_summaries: list[dict[str, Any]] = []
    sparse_categories: list[str] = []
    for index, name in enumerate(selected_names):
        categories, counts = np.unique(selected[:, index].astype(int), return_counts=True)
        if len(categories) < 2:
            raise OrdinalAnalysisError(
                f"Variable {name!r} must contain at least two observed categories."
            )
        if len(categories) > 10:
            raise OrdinalAnalysisError(
                f"Variable {name!r} has {len(categories)} categories; the fixed contract "
                "permits at most 10."
            )
        if int(np.min(counts)) < 2:
            raise OrdinalAnalysisError(
                f"Every observed category of variable {name!r} must contain at least two "
                "complete cases."
            )
        if int(np.min(counts)) < 5:
            sparse_categories.append(name)
        category_summaries.append(
            {
                "variable": name,
                "categories": categories.tolist(),
                "counts": counts.tolist(),
            }
        )

    zero_cells = 0
    total_pair_cells = 0
    selected_int = selected.astype(int)
    for first in range(selected.shape[1]):
        first_categories = category_summaries[first]["categories"]
        first_map = {value: index for index, value in enumerate(first_categories)}
        for second in range(first + 1, selected.shape[1]):
            second_categories = category_summaries[second]["categories"]
            second_map = {value: index for index, value in enumerate(second_categories)}
            table = np.zeros((len(first_categories), len(second_categories)), dtype=int)
            for row in selected_int:
                table[first_map[int(row[first])], second_map[int(row[second])]] += 1
            zero_cells += int(np.sum(table == 0))
            total_pair_cells += int(table.size)

    warnings: list[str] = []
    if excluded_rows:
        warnings.append(
            f"Listwise deletion excluded {len(excluded_rows)} rows with missing selected "
            "variables."
        )
    if selected.shape[0] < 200:
        warnings.append(
            "Fewer than 200 complete rows; threshold, polychoric-correlation, and WLSMV "
            "stability must be evaluated for the observed category distributions and model."
        )
    if sparse_categories:
        warnings.append(
            "At least one observed category has fewer than five complete cases for: "
            + ", ".join(sparse_categories)
            + "."
        )
    if zero_cells:
        warnings.append(
            f"Observed {zero_cells} empty cells across {total_pair_cells} bivariate ordinal "
            "table cells; inspect boundary estimates and sensitivity to sparse categories."
        )
    return selected, excluded_rows, category_summaries, warnings


def _run_adapter(script_name: str, payload: dict[str, Any], timeout: int = 180) -> dict[str, Any]:
    script = resources.files("psychometrics_mcp").joinpath("r", script_name)
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
        raise OrdinalAnalysisError(f"Fixed ordinal R adapter failed: {detail}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise OrdinalAnalysisError("Fixed ordinal R adapter returned invalid JSON.") from exc


def polychoric_correlation_matrix(request: PolychoricCorrelationRequest) -> dict[str, Any]:
    """Estimate an unsmoothed polychoric correlation matrix with psych."""
    names = request.data.variable_names or [
        f"variable_{index + 1}" for index in range(len(request.data.values[0]))
    ]
    matrix, excluded_rows, categories, warnings = _preflight(
        request.data.values, names, names, minimum_rows=20
    )
    capability = ordinal_capabilities()["polychoric_correlation_matrix"]
    if not capability["available"]:
        raise OrdinalAnalysisError(
            capability.get("reason", "The psych polychoric engine is unavailable.")
        )
    result = _run_adapter(
        "polychoric_correlation.R",
        {
            "values": matrix.astype(int).tolist(),
            "variable_names": names,
            "continuity_correction": request.continuity_correction,
        },
    )
    result["schema_version"] = "1.0"
    result["sample_flow"] = {
        "input_rows": len(request.data.values),
        "analyzed_rows": int(matrix.shape[0]),
        "excluded_rows": excluded_rows[:100],
        "excluded_rows_truncated": len(excluded_rows) > 100,
        "variables": len(names),
    }
    result["category_distributions"] = categories
    result["warnings"] = warnings + result.get("warnings", [])
    result["references"] = [
        {
            "role": "method_foundation",
            "citation": (
                "Olsson, U. (1979). Maximum likelihood estimation of the polychoric "
                "correlation coefficient. Psychometrika, 44(4), 443-460."
            ),
            "doi": "10.1007/BF02296207",
        },
        {
            "role": "method_evaluation",
            "citation": (
                "Flora, D. B., & Curran, P. J. (2004). An empirical evaluation of "
                "alternative methods of estimation for confirmatory factor analysis with "
                "ordinal data. Psychological Methods, 9(4), 466-491."
            ),
            "doi": "10.1037/1082-989X.9.4.466",
        },
        {
            "role": "assumption_limit",
            "citation": (
                "Kampen, J. K., & Weeren, A. (2017). A recommendation for applied "
                "researchers to substantiate the claim that ordinal variables are the "
                "product of underlying bivariate normal distributions. Quality & Quantity, "
                "51, 2163-2170."
            ),
            "doi": "10.1007/s11135-016-0378-2",
        },
        {
            "role": "engine",
            "citation": "Revelle, W. psych: Procedures for Psychological Research.",
            "url": "https://CRAN.R-project.org/package=psych",
        },
    ]
    result["interpretation_boundary"] = (
        "Polychoric correlations estimate association between hypothesized latent continuous "
        "responses under threshold and bivariate-normal assumptions. They do not establish "
        "dimensionality, construct validity, invariance, fairness, or causal relationships."
    )
    return result


def categorical_confirmatory_factor_analysis(request: CategoricalCFARequest) -> dict[str, Any]:
    """Fit a fixed simple-structure ordinal CFA with lavaan WLSMV."""
    names = request.data.variable_names or [
        f"variable_{index + 1}" for index in range(len(request.data.values[0]))
    ]
    indicators = [indicator for factor in request.factors for indicator in factor.indicators]
    matrix, excluded_rows, categories, warnings = _preflight(
        request.data.values, names, indicators, minimum_rows=100
    )
    capability = ordinal_capabilities()["categorical_confirmatory_factor_analysis"]
    if not capability["available"]:
        raise OrdinalAnalysisError(
            capability.get("reason", "The lavaan categorical CFA engine is unavailable.")
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
    result = _run_adapter(
        "categorical_cfa.R",
        {
            "values": matrix.astype(int).tolist(),
            "indicator_ids": internal_indicators,
            "indicator_names": indicators,
            "category_values": [summary["categories"] for summary in categories],
            "factors": factor_payload,
            "estimator": request.estimator,
            "confidence_level": request.confidence_level,
        },
        timeout=240,
    )
    if not result.get("model", {}).get("converged", False):
        raise OrdinalAnalysisError("lavaan did not converge for the requested categorical CFA.")
    result["schema_version"] = "1.0"
    result["sample_flow"] = {
        "input_rows": len(request.data.values),
        "analyzed_rows": int(matrix.shape[0]),
        "excluded_rows": excluded_rows[:100],
        "excluded_rows_truncated": len(excluded_rows) > 100,
        "indicators": len(indicators),
        "factors": len(request.factors),
    }
    result["category_distributions"] = categories
    result["warnings"] = warnings + result.get("warnings", [])
    result["references"] = [
        {
            "role": "ordinal_estimation_evaluation",
            "citation": (
                "Flora, D. B., & Curran, P. J. (2004). An empirical evaluation of "
                "alternative methods of estimation for confirmatory factor analysis with "
                "ordinal data. Psychological Methods, 9(4), 466-491."
            ),
            "doi": "10.1037/1082-989X.9.4.466",
        },
        {
            "role": "engine",
            "citation": (
                "Rosseel, Y. (2012). lavaan: An R package for structural equation modeling. "
                "Journal of Statistical Software, 48(2), 1-36."
            ),
            "doi": "10.18637/jss.v048.i02",
        },
        {
            "role": "engine_contract",
            "citation": "lavaan categorical data tutorial.",
            "url": "https://lavaan.ugent.be/tutorial/cat.html",
        },
    ]
    result["interpretation_boundary"] = (
        "Categorical CFA tests a prespecified latent-response threshold model. Fit, loadings, "
        "and thresholds do not by themselves establish construct validity, score comparability, "
        "measurement invariance, fairness, causal meaning, or consequential-use fitness."
    )
    return result


def ordinal_exploratory_factor_analysis(request: OrdinalEFARequest) -> dict[str, Any]:
    """Fit EFA to an unsmoothed polychoric matrix with psych."""
    names = request.data.variable_names or [
        f"variable_{index + 1}" for index in range(len(request.data.values[0]))
    ]
    matrix, excluded_rows, categories, warnings = _preflight(
        request.data.values, names, names, minimum_rows=100
    )
    capability = ordinal_capabilities()["ordinal_exploratory_factor_analysis"]
    if not capability["available"]:
        raise OrdinalAnalysisError(
            capability.get("reason", "The psych ordinal EFA engine is unavailable.")
        )
    result = _run_adapter(
        "ordinal_efa.R",
        {
            "values": matrix.astype(int).tolist(),
            "variable_names": names,
            "factors": request.factors,
            "extraction": request.extraction,
            "rotation": request.rotation,
            "continuity_correction": request.continuity_correction,
        },
        timeout=240,
    )
    result["schema_version"] = "1.0"
    result["sample_flow"] = {
        "input_rows": len(request.data.values),
        "analyzed_rows": int(matrix.shape[0]),
        "excluded_rows": excluded_rows[:100],
        "excluded_rows_truncated": len(excluded_rows) > 100,
        "variables": len(names),
        "factors": request.factors,
    }
    result["category_distributions"] = categories
    result["warnings"] = warnings + result.get("warnings", [])
    result["references"] = [
        {
            "role": "correlation_foundation",
            "citation": (
                "Olsson, U. (1979). Maximum likelihood estimation of the polychoric "
                "correlation coefficient. Psychometrika, 44(4), 443-460."
            ),
            "doi": "10.1007/BF02296207",
        },
        {
            "role": "ordinal_factor_evaluation",
            "citation": (
                "Holgado-Tello, F. P., Chacon-Moscoso, S., Barbero-Garcia, I., & "
                "Vila-Abad, E. (2010). Polychoric versus Pearson correlations in "
                "exploratory and confirmatory factor analysis of ordinal variables. "
                "Quality & Quantity, 44, 153-166."
            ),
            "doi": "10.1007/s11135-008-9190-y",
        },
        {
            "role": "exploratory_method_guidance",
            "citation": (
                "Fabrigar, L. R., Wegener, D. T., MacCallum, R. C., & Strahan, E. J. "
                "(1999). Evaluating the use of exploratory factor analysis in psychological "
                "research. Psychological Methods, 4(3), 272-299."
            ),
            "doi": "10.1037/1082-989X.4.3.272",
        },
        {
            "role": "assumption_limit",
            "citation": (
                "Kampen, J. K., & Weeren, A. (2017). A recommendation for applied "
                "researchers to substantiate the claim that ordinal variables are the "
                "product of underlying bivariate normal distributions. Quality & Quantity, "
                "51, 2163-2170."
            ),
            "doi": "10.1007/s11135-016-0378-2",
        },
        {
            "role": "engine",
            "citation": "Revelle, W. psych: Procedures for Psychological Research.",
            "url": "https://CRAN.R-project.org/package=psych",
        },
    ]
    result["interpretation_boundary"] = (
        "Ordinal EFA is exploratory evidence under latent-response and threshold assumptions. "
        "It does not determine a uniquely correct factor count, name constructs, confirm a "
        "measurement model, or establish validity, invariance, fairness, or causal meaning."
    )
    return result
