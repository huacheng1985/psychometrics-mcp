"""Safe adapter for a fixed eRm Rasch model script."""

from __future__ import annotations

import json
import shutil
import subprocess
from importlib import resources
from typing import Any

import numpy as np

from .models import ResponseData


class RaschModelError(RuntimeError):
    """Raised when Rasch preflight or the fixed R adapter fails."""


def computation_capabilities() -> dict[str, Any]:
    rscript = shutil.which("Rscript")
    result: dict[str, Any] = {
        "python": {"available": True},
        "r": {"available": rscript is not None, "executable": rscript},
        "rasch_rm": {"available": False, "engine": "eRm::RM", "estimator": "CML"},
    }
    if not rscript:
        result["rasch_rm"]["reason"] = "Rscript was not found on PATH."
        return result
    check = subprocess.run(
        [
            rscript,
            "-e",
            'cat(requireNamespace("jsonlite", quietly=TRUE) && '
            'requireNamespace("eRm", quietly=TRUE))',
        ],
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )
    result["rasch_rm"]["available"] = check.returncode == 0 and check.stdout == "TRUE"
    if not result["rasch_rm"]["available"]:
        result["rasch_rm"]["reason"] = "R packages eRm and jsonlite are required."
    return result


def _preflight(data: ResponseData) -> tuple[list[str], np.ndarray, list[str]]:
    matrix = np.array(
        [[np.nan if value is None else float(value) for value in row] for row in data.responses],
        dtype=float,
    )
    names = data.item_names or [f"item_{index + 1}" for index in range(matrix.shape[1])]
    observed = matrix[~np.isnan(matrix)]
    invalid = sorted(set(observed.tolist()) - {0.0, 1.0})
    if invalid:
        raise RaschModelError(f"Rasch RM accepts only 0/1 responses; found {invalid}.")
    keep = ~np.isnan(matrix).all(axis=1)
    warnings: list[str] = []
    if not keep.all():
        warnings.append(f"Excluded {int((~keep).sum())} rows with all responses missing.")
    matrix = matrix[keep]
    if matrix.shape[0] < 10:
        raise RaschModelError("At least 10 non-empty response rows are required.")
    for index, name in enumerate(names):
        values = matrix[:, index]
        values = values[~np.isnan(values)]
        if values.size < 2 or np.unique(values).size < 2:
            raise RaschModelError(f"Item {name!r} has no usable variance.")
    if matrix.shape[0] < 100:
        warnings.append("Fewer than 100 non-empty rows; item and fit estimates may be unstable.")
    if np.isnan(matrix).any():
        warnings.append("Missing item responses are retained and handled by eRm.")
    return warnings, matrix, names


def run_rasch_model(data: ResponseData) -> dict[str, Any]:
    warnings, matrix, names = _preflight(data)
    capabilities = computation_capabilities()
    if not capabilities["rasch_rm"]["available"]:
        raise RaschModelError(capabilities["rasch_rm"].get("reason", "Rasch engine unavailable."))
    payload = {
        "responses": [[None if np.isnan(value) else int(value) for value in row] for row in matrix],
        "item_names": names,
    }
    script = resources.files("psychometrics_mcp").joinpath("r", "rasch_model.R")
    completed = subprocess.run(
        [capabilities["r"]["executable"], str(script)],
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
        raise RaschModelError(f"Fixed eRm adapter failed: {detail}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RaschModelError("Fixed eRm adapter returned invalid JSON.") from exc
    result["sample_flow"] = {
        "input_rows": len(data.responses),
        "analyzed_rows": int(matrix.shape[0]),
        "items": int(matrix.shape[1]),
    }
    result["warnings"] = warnings + result.get("warnings", [])
    result["interpretation_boundary"] = (
        "Model fit does not by itself establish unidimensionality, invariance, "
        "fairness, or validity."
    )
    return result
