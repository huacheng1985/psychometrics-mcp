"""Deterministic, measurement-aware analysis functions."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

import numpy as np

from .models import AnalysisPlanRequest, CorrelationRequest, NumericData, ResponseData


def _matrix(data: ResponseData) -> tuple[np.ndarray, list[str]]:
    matrix = np.array(
        [[np.nan if value is None else float(value) for value in row] for row in data.responses],
        dtype=float,
    )
    names = data.item_names or [f"item_{index + 1}" for index in range(matrix.shape[1])]
    return matrix, names


def _numeric_matrix(data: NumericData) -> tuple[np.ndarray, list[str]]:
    matrix = np.array(
        [[np.nan if value is None else float(value) for value in row] for row in data.values],
        dtype=float,
    )
    names = data.variable_names or [
        f"variable_{index + 1}" for index in range(matrix.shape[1])
    ]
    return matrix, names


def descriptive_statistics(data: NumericData) -> dict[str, Any]:
    matrix, names = _numeric_matrix(data)
    variables: list[dict[str, Any]] = []
    for index, name in enumerate(names):
        column = matrix[:, index]
        observed = column[~np.isnan(column)]
        variables.append(
            {
                "variable": name,
                "observed_n": int(observed.size),
                "missing_n": int(np.isnan(column).sum()),
                "missing_rate": float(np.isnan(column).mean()),
                "mean": None if not observed.size else float(np.mean(observed)),
                "standard_deviation": (
                    None if observed.size < 2 else float(np.std(observed, ddof=1))
                ),
                "minimum": None if not observed.size else float(np.min(observed)),
                "first_quartile": (
                    None if not observed.size else float(np.percentile(observed, 25))
                ),
                "median": None if not observed.size else float(np.median(observed)),
                "third_quartile": (
                    None if not observed.size else float(np.percentile(observed, 75))
                ),
                "maximum": None if not observed.size else float(np.max(observed)),
                "zero_variance": bool(observed.size > 0 and np.all(observed == observed[0])),
            }
        )
    complete = ~np.isnan(matrix).any(axis=1)
    warnings: list[str] = []
    if np.isnan(matrix).any():
        warnings.append("Statistics use all observed values separately for each variable.")
    if any(variable["observed_n"] < 2 for variable in variables):
        warnings.append(
            "Standard deviation is unavailable for variables with fewer than two values."
        )
    if any(variable["zero_variance"] for variable in variables):
        warnings.append("One or more variables have zero observed variance.")
    return {
        "schema_version": "1.0",
        "sample_flow": {
            "input_rows": int(matrix.shape[0]),
            "variables": int(matrix.shape[1]),
            "complete_rows": int(complete.sum()),
            "incomplete_rows": int((~complete).sum()),
        },
        "variables": variables,
        "method": {
            "standard_deviation": "Sample standard deviation with denominator n - 1",
            "quartiles": "Linear interpolation (NumPy default)",
            "missing": "Available-case statistics computed separately by variable",
        },
        "warnings": warnings,
        "interpretation_boundary": (
            "Descriptive statistics summarize this sample; they do not establish population "
            "effects, measurement quality, fairness, or validity."
        ),
    }


def _average_ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    ranks = np.empty(values.size, dtype=float)
    start = 0
    while start < values.size:
        stop = start + 1
        while stop < values.size and sorted_values[stop] == sorted_values[start]:
            stop += 1
        ranks[order[start:stop]] = (start + 1 + stop) / 2
        start = stop
    return ranks


def correlation_matrix(request: CorrelationRequest) -> dict[str, Any]:
    matrix, names = _numeric_matrix(request.data)
    input_rows = int(matrix.shape[0])
    if request.missing == "listwise":
        matrix = matrix[~np.isnan(matrix).any(axis=1)]

    estimates: list[list[float | None]] = []
    pairwise_n: list[list[int]] = []
    unavailable_pairs: list[str] = []
    for x_index, x_name in enumerate(names):
        estimate_row: list[float | None] = []
        n_row: list[int] = []
        for y_index, y_name in enumerate(names):
            x = matrix[:, x_index]
            y = matrix[:, y_index]
            keep = ~np.isnan(x) & ~np.isnan(y)
            x_keep, y_keep = x[keep], y[keep]
            n = int(keep.sum())
            estimate: float | None = None
            if n >= 3 and np.std(x_keep, ddof=1) > 0 and np.std(y_keep, ddof=1) > 0:
                if request.method == "spearman":
                    x_keep = _average_ranks(x_keep)
                    y_keep = _average_ranks(y_keep)
                estimate = float(np.corrcoef(x_keep, y_keep)[0, 1])
                if abs(estimate) < 1e-15:
                    estimate = 0.0
                estimate = max(-1.0, min(1.0, estimate))
            elif y_index >= x_index:
                unavailable_pairs.append(f"{x_name} × {y_name}")
            estimate_row.append(estimate)
            n_row.append(n)
        estimates.append(estimate_row)
        pairwise_n.append(n_row)

    warnings: list[str] = []
    if np.isnan(_numeric_matrix(request.data)[0]).any():
        if request.missing == "pairwise":
            warnings.append(
                "Pairwise deletion can use different rows for different correlations and may "
                "produce a non-positive-semidefinite matrix."
            )
        else:
            warnings.append("Listwise deletion excludes every row with any missing value.")
    if unavailable_pairs:
        warnings.append(
            "Correlations unavailable because n < 3 or a variable has zero variance: "
            + ", ".join(unavailable_pairs)
            + "."
        )
    warnings.append(
        "Correlation does not establish causation, construct validity, or measurement invariance."
    )
    return {
        "schema_version": "1.0",
        "method": request.method,
        "missing": request.missing,
        "variables": names,
        "correlations": estimates,
        "pairwise_n": pairwise_n,
        "sample_flow": {
            "input_rows": input_rows,
            "listwise_analyzed_rows": (
                int(matrix.shape[0]) if request.missing == "listwise" else None
            ),
        },
        "warnings": warnings,
        "interpretation_boundary": (
            "Correlations describe bivariate association in the analyzed observations; "
            "substantive and measurement conclusions require additional evidence."
        ),
    }


def inspect_response_data(data: ResponseData) -> dict[str, Any]:
    matrix, names = _matrix(data)
    items: list[dict[str, Any]] = []
    for index, name in enumerate(names):
        column = matrix[:, index]
        observed = column[~np.isnan(column)]
        counts = Counter(float(value) for value in observed)
        items.append(
            {
                "item": name,
                "observed_n": int(observed.size),
                "missing_n": int(np.isnan(column).sum()),
                "missing_rate": round(float(np.isnan(column).mean()), 6),
                "categories": [
                    {"value": value, "count": count} for value, count in sorted(counts.items())
                ],
                "minimum": None if not observed.size else float(np.min(observed)),
                "maximum": None if not observed.size else float(np.max(observed)),
                "zero_variance": bool(observed.size > 0 and np.all(observed == observed[0])),
            }
        )
    complete = ~np.isnan(matrix).any(axis=1)
    return {
        "schema_version": "1.0",
        "sample": {
            "rows": int(matrix.shape[0]),
            "items": int(matrix.shape[1]),
            "complete_rows": int(complete.sum()),
            "incomplete_rows": int((~complete).sum()),
        },
        "items": items,
        "warnings": [
            warning
            for warning, condition in (
                (
                    "One or more items have zero observed variance.",
                    any(i["zero_variance"] for i in items),
                ),
                (
                    "Missing responses are present; CTT uses pairwise item-rest correlations.",
                    np.isnan(matrix).any(),
                ),
            )
            if condition
        ],
    }


def _correlation(x: np.ndarray, y: np.ndarray) -> float | None:
    keep = ~np.isnan(x) & ~np.isnan(y)
    if keep.sum() < 3:
        return None
    x_keep, y_keep = x[keep], y[keep]
    if np.std(x_keep, ddof=1) == 0 or np.std(y_keep, ddof=1) == 0:
        return None
    return float(np.corrcoef(x_keep, y_keep)[0, 1])


def ctt_item_analysis(data: ResponseData) -> dict[str, Any]:
    matrix, names = _matrix(data)
    item_results: list[dict[str, Any]] = []
    for index, name in enumerate(names):
        column = matrix[:, index]
        other_score = np.nansum(np.delete(matrix, index, axis=1), axis=1)
        all_other_missing = np.isnan(np.delete(matrix, index, axis=1)).all(axis=1)
        other_score[all_other_missing] = np.nan
        observed = column[~np.isnan(column)]
        item_results.append(
            {
                "item": name,
                "n": int(observed.size),
                "mean": None if not observed.size else float(np.mean(observed)),
                "sd": None if observed.size < 2 else float(np.std(observed, ddof=1)),
                "item_rest_correlation": _correlation(column, other_score),
            }
        )

    complete = matrix[~np.isnan(matrix).any(axis=1)]
    alpha: float | None = None
    sem: float | None = None
    if complete.shape[0] >= 2:
        item_variances = np.var(complete, axis=0, ddof=1)
        total_scores = np.sum(complete, axis=1)
        total_variance = float(np.var(total_scores, ddof=1))
        if total_variance > 0:
            k = complete.shape[1]
            alpha = float((k / (k - 1)) * (1 - float(np.sum(item_variances)) / total_variance))
            sem = float(np.std(total_scores, ddof=1) * math.sqrt(max(0.0, 1 - alpha)))

    warnings: list[str] = []
    if complete.shape[0] < matrix.shape[0]:
        warnings.append("Coefficient alpha and SEM use complete cases only.")
    if complete.shape[0] < 30:
        warnings.append("Fewer than 30 complete cases; estimates may be unstable.")
    if alpha is not None and (alpha < 0 or alpha > 1):
        warnings.append("Alpha is outside [0, 1]; inspect item coding and covariance structure.")
    warnings.append(
        "Reliability is sample- and use-dependent; alpha alone is not validity evidence."
    )
    return {
        "schema_version": "1.0",
        "sample_flow": {
            "input_rows": int(matrix.shape[0]),
            "complete_rows_for_scale_statistics": int(complete.shape[0]),
        },
        "scale": {"coefficient_alpha": alpha, "sem_total_score_units": sem},
        "items": item_results,
        "warnings": warnings,
        "method": {
            "item_rest_correlation": "Pearson correlation with the sum of all other observed items",
            "alpha": "Raw coefficient alpha on complete cases",
        },
    }


def plan_psychometric_analysis(request: AnalysisPlanRequest) -> dict[str, Any]:
    steps = [
        "Audit data provenance, coding, missingness, distributions, and sample flow.",
        "Define the construct, score interpretation, intended use, and decision consequences.",
    ]
    if request.dimensionality == "unknown":
        steps.append(
            "Evaluate dimensionality with theory, parallel analysis, "
            "and an appropriate factor model."
        )
    if request.item_type == "dichotomous":
        steps.append("Compare CTT diagnostics with Rasch or IRT item and person fit.")
    elif request.item_type == "polytomous":
        steps.append(
            "Inspect category functioning before fitting PCM/RSM or polytomous IRT models."
        )
    elif request.item_type == "continuous":
        steps.append(
            "Use covariance-based reliability and factor models appropriate "
            "to continuous indicators."
        )
    else:
        steps.append(
            "Model mixed indicator types with estimators that respect each response distribution."
        )
    if request.groups > 1:
        steps.append("Evaluate measurement invariance and DIF before comparing group scores.")
    if request.occasions > 1:
        steps.append("Evaluate longitudinal invariance, linking, and dependence across occasions.")
    if request.clustered:
        steps.append(
            "Account for clustering in standard errors, validation, and cross-validation splits."
        )
    if request.purpose == "prediction":
        steps.append(
            "Use measurement-aware validation: target reliability, leakage, "
            "calibration, subgroup stability, and uncertainty."
        )
    elif request.purpose == "linking_equating":
        steps.append(
            "Document anchor quality, population assumptions, linking design, "
            "and sensitivity to drift."
        )
    elif request.purpose == "classification":
        steps.append(
            "Quantify classification consistency, accuracy, uncertainty near "
            "cut scores, and subgroup impact."
        )
    steps.append(
        "Report estimates, uncertainty, exclusions, software versions, "
        "diagnostics, and sensitivity analyses."
    )
    return {
        "schema_version": "1.0",
        "recommended_sequence": steps,
        "interpretation_boundary": (
            "This plan supports analysis design; it does not establish validity "
            "without substantive evidence and human review."
        ),
    }
