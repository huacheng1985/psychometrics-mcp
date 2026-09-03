"""Stagewise ordinal measurement invariance with isolated, fixed R adapters."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path
from typing import Any

import numpy as np

from .models import OrdinalMeasurementInvarianceRequest
from .ordinal import OrdinalAnalysisError
from .ordinal import _preflight as ordinal_preflight

STAGES = ["configural", "thresholds", "metric", "scalar", "strict"]


def ordinal_invariance_r_environment() -> dict[str, str]:
    """Use an explicit or venv-local R library only for this new engine."""
    environment = os.environ.copy()
    library = Path(environment.get("PSYCHOMETRICS_R_LIBRARY", Path(sys.prefix) / "lib/R/library"))
    if library.is_dir():
        inherited = environment.get("R_LIBS", "")
        environment["R_LIBS"] = str(library.resolve()) + (
            os.pathsep + inherited if inherited else ""
        )
    return environment


def ordinal_invariance_capabilities() -> dict[str, dict[str, Any]]:
    capability: dict[str, Any] = {
        "available": False,
        "engine": "semTools::measEq.syntax + lavaan::cfa + lavaan::lavTestLRT",
        "estimator": "WLSMV",
        "parameterization": "theta",
        "identification": "Wu.Estabrook.2016",
        "stages": STAGES,
        "categories_per_indicator": [4, 10],
        "stagewise_review_required": True,
        "automatic_decision": False,
    }
    if not shutil.which("Rscript"):
        capability["reason"] = "Rscript was not found on PATH."
    else:
        code = (
            'ok <- requireNamespace("jsonlite", quietly=TRUE) && '
            'requireNamespace("lavaan", quietly=TRUE) && '
            'requireNamespace("semTools", quietly=TRUE); '
            'cat(ok && packageVersion("lavaan") >= "0.6-21" && '
            'packageVersion("semTools") >= "0.5-9")'
        )
        try:
            check = subprocess.run(
                [shutil.which("Rscript") or "Rscript", "-e", code],
                env=ordinal_invariance_r_environment(),
                capture_output=True,
                check=False,
                text=True,
                timeout=30,
            )
            capability["available"] = check.returncode == 0 and check.stdout.strip() == "TRUE"
        except subprocess.TimeoutExpired:
            capability["reason"] = "R dependency check timed out."
        if not capability["available"]:
            capability.setdefault(
                "reason", "Requires jsonlite, lavaan >= 0.6-21, semTools >= 0.5-9."
            )
    return {"ordinal_measurement_invariance": capability}


def _preflight(
    request: OrdinalMeasurementInvarianceRequest,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    names = request.data.variable_names or [
        f"variable_{index + 1}" for index in range(len(request.data.values[0]))
    ]
    selected_names = [name for factor in request.factors for name in factor.indicators]
    indices = [names.index(name) for name in selected_names]
    complete = [all(row[index] is not None for index in indices) for row in request.data.values]
    excluded = [index + 1 for index, keep in enumerate(complete) if not keep]
    labels = list(dict.fromkeys(request.groups))
    values, groups, flow, warnings = [], [], [], []
    expected_categories = None
    for group_index, label in enumerate(labels):
        group_id = f"g{group_index + 1}"
        rows = [
            row
            for row, group, keep in zip(request.data.values, request.groups, complete, strict=True)
            if group == label and keep
        ]
        if len(rows) < 100:
            raise OrdinalAnalysisError(f"Group {label!r} requires at least 100 complete rows.")
        matrix, _, summaries, group_warnings = ordinal_preflight(
            rows, names, selected_names, minimum_rows=100
        )
        categories = [summary["categories"] for summary in summaries]
        if any(not 4 <= len(codes) <= 10 for codes in categories):
            raise OrdinalAnalysisError(
                "This threshold-first contract requires 4-10 categories per indicator in every "
                "group; binary and three-category invariance require distinct contracts."
            )
        if expected_categories is not None and categories != expected_categories:
            raise OrdinalAnalysisError(
                "Selected indicators must have identical category codes across groups."
            )
        expected_categories = categories
        if np.linalg.matrix_rank(np.corrcoef(matrix, rowvar=False)) < len(selected_names):
            raise OrdinalAnalysisError(
                f"Selected indicators are rank deficient in group {label!r}."
            )
        values.extend(matrix.astype(int).tolist())
        groups.extend([group_id] * len(rows))
        input_count = sum(group == label for group in request.groups)
        flow.append(
            {
                "group": label,
                "input_rows": input_count,
                "analyzed_rows": len(rows),
                "excluded_rows": input_count - len(rows),
                "categories": summaries,
            }
        )
        warnings.extend(f"Group {label!r}: {message}" for message in group_warnings)
    if excluded:
        warnings.append(f"Listwise deletion excluded {len(excluded)} rows on selected indicators.")
    internal = {name: f"v{index + 1}" for index, name in enumerate(selected_names)}
    payload = {
        "values": values,
        "groups": groups,
        "stage": request.stage,
        "indicators": list(internal.values()),
        "indicator_map": [{"id": internal[name], "name": name} for name in selected_names],
        "group_map": [
            {"id": f"g{index + 1}", "label": label} for index, label in enumerate(labels)
        ],
        "factors": [
            {
                "id": f"f{index + 1}",
                "name": factor.name,
                "indicators": [internal[name] for name in factor.indicators],
            }
            for index, factor in enumerate(request.factors)
        ],
    }
    return (
        payload,
        {
            "input_rows": len(request.data.values),
            "analyzed_rows": len(values),
            "excluded_rows": excluded[:100],
            "excluded_rows_truncated": len(excluded) > 100,
            "groups": flow,
        },
        warnings,
    )


def ordinal_measurement_invariance(request: OrdinalMeasurementInvarianceRequest) -> dict[str, Any]:
    """Fit a reviewed stage and, when applicable, its immediate predecessor."""
    payload, sample_flow, warnings = _preflight(request)
    capability = ordinal_invariance_capabilities()["ordinal_measurement_invariance"]
    if not capability["available"]:
        raise OrdinalAnalysisError(capability["reason"])
    script = resources.files("psychometrics_mcp").joinpath("r", "ordinal_measurement_invariance.R")
    try:
        completed = subprocess.run(
            [shutil.which("Rscript") or "Rscript", str(script)],
            input=json.dumps(payload),
            env=ordinal_invariance_r_environment(),
            capture_output=True,
            check=False,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired as exc:
        raise OrdinalAnalysisError(
            "Ordinal invariance exceeded the 300-second execution limit."
        ) from exc
    if completed.returncode != 0:
        lines = [
            line
            for line in completed.stderr.splitlines()
            if line and line != "Execution halted" and not line.startswith("Calls:")
        ]
        raise OrdinalAnalysisError(
            "Fixed ordinal invariance adapter failed: " + " ".join(lines)[-2000:]
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise OrdinalAnalysisError("Ordinal invariance adapter returned invalid JSON.") from exc
    index = STAGES.index(request.stage)
    expected = STAGES[max(0, index - 1) : index + 1]
    if [model.get("stage") for model in result.get("models", [])] != expected:
        raise OrdinalAnalysisError(
            "Ordinal invariance adapter returned an incorrect stage sequence."
        )
    result.update(
        {
            "schema_version": "1.0",
            "sample_flow": sample_flow,
            "request_sha256": hashlib.sha256(
                json.dumps(request.model_dump(), sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "review": {
                "prior_stage_reviewed": request.prior_stage_reviewed,
                "verification": "caller acknowledgement; not independent verification",
                "next_stage": STAGES[index + 1] if index < len(STAGES) - 1 else None,
                "automatic_progression": False,
            },
            "references": [
                {
                    "role": "identification",
                    "citation": "Wu & Estabrook (2016), Psychometrika, 81, 1014-1045.",
                    "doi": "10.1007/s11336-016-9506-0",
                },
                {
                    "role": "ordinal_invariance",
                    "citation": (
                        "Millsap & Yun-Tein (2004), Multivariate Behavioral Research, 39, 479-515."
                    ),
                    "doi": "10.1207/S15327906MBR3903_4",
                },
                {
                    "role": "engine",
                    "citation": "Rosseel (2012), Journal of Statistical Software, 48(2).",
                    "doi": "10.18637/jss.v048.i02",
                },
                {
                    "role": "syntax_generator",
                    "url": "https://rdrr.io/cran/semTools/man/measEq.syntax.html",
                },
            ],
            "interpretation_boundary": (
                "Prespecified ordinal CFA only. Review configural fit and each preceding stage "
                "on the same data/model before requesting a stronger stage. Statistics and fit "
                "changes are not universal pass/fail rules. No automatic partial invariance, "
                "group-mean authorization, fairness, DIF, or validity claim. Binary, "
                "three-category, mixed continuous/ordinal, and longitudinal models are unsupported."
            ),
        }
    )
    result["warnings"] = warnings + result.get("warnings", [])
    return result
