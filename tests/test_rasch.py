from __future__ import annotations

import pytest

from psychometrics_mcp.models import ResponseData
from psychometrics_mcp.rasch import (
    RaschModelError,
    computation_capabilities,
    run_rasch_model,
)


def reference_data(rows: int = 120) -> ResponseData:
    responses = []
    for person in range(rows):
        ability = (person % 12) - 5.5
        responses.append(
            [
                int(ability + ((person * 3 + item * 5) % 9 - 4) > difficulty)
                for item, difficulty in enumerate([-4.0, -2.0, 0.0, 2.0, 4.0])
            ]
        )
    return ResponseData(responses=responses, item_names=["i1", "i2", "i3", "i4", "i5"])


def test_rasch_rejects_nonbinary_data() -> None:
    data = reference_data(10)
    data.responses[0][0] = 2
    with pytest.raises(RaschModelError, match="only 0/1"):
        run_rasch_model(data)


@pytest.mark.integration
def test_real_erm_rasch_model() -> None:
    if not computation_capabilities()["rasch_rm"]["available"]:
        pytest.skip("R/eRm/jsonlite not installed")
    result = run_rasch_model(reference_data())
    assert result["model"]["engine"] == "eRm::RM"
    assert result["model"]["estimator"] == "conditional maximum likelihood"
    assert result["sample_flow"]["analyzed_rows"] == 120
    assert len(result["items"]) == 5
    locations = [item["location"] for item in result["items"]]
    assert locations[0] < locations[2] < locations[4]
    assert abs(sum(locations)) < 1e-8
    assert result["package_versions"]["eRm"]
