"""Exercise the installed ordinal tool through real stdio MCP using synthetic package data."""

import asyncio
import json
import os
import subprocess
import sys

import numpy as np
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from psychometrics_mcp.ordinal_invariance import PROFILE_STAGES, ordinal_invariance_r_environment


def discrete_request(profile):
    rng = np.random.default_rng(721)
    response = 0.7 * rng.normal(size=(2000, 1)) + rng.normal(size=(2000, 6))
    offsets = np.linspace(-1, 1, 6)
    if profile == "binary":
        values = (response > offsets).astype(int)
    else:
        values = (response > (offsets - 0.5)).astype(int)
        values += (response > (offsets + 0.5)).astype(int)
    names = [f"u{i}" for i in range(1, 7)]
    return {
        "category_profile": profile,
        "data": {"values": values.tolist(), "variable_names": names},
        "groups": ["a"] * 1000 + ["b"] * 1000,
        "factors": [{"name": "f", "indicators": names}],
    }


async def main():
    code = (
        "suppressPackageStartupMessages(library(semTools)); "
        "cat(jsonlite::toJSON(list(values=unname(as.matrix(datCat[1:8])), "
        "groups=as.character(datCat$g))))"
    )
    data = json.loads(
        subprocess.run(
            ["Rscript", "-e", code],
            env=ordinal_invariance_r_environment(),
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout
    )
    names = [f"u{i}" for i in range(1, 9)]
    request = {
        "data": {"values": data["values"], "variable_names": names},
        "groups": data["groups"],
        "factors": [
            {"name": "FU1", "indicators": names[:4]},
            {"name": "FU2", "indicators": names[4:]},
        ],
    }
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "psychometrics_mcp.server"],
        env={key: os.environ[key] for key in ["PSYCHOMETRICS_R_LIBRARY"] if key in os.environ},
    )
    summary = []
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            listing = await session.list_tools()
            assert "ordinal_measurement_invariance" in {tool.name for tool in listing.tools}
            for profile, payload, dfs in [
                ("polytomous", request, [38, 54, 60, 66, 74]),
                ("binary", discrete_request("binary"), [18, 22]),
                ("three_category", discrete_request("three_category"), [18, 18, 23, 28, 34]),
            ]:
                fingerprint = None
                for stage, df in zip(PROFILE_STAGES[profile], dfs, strict=True):
                    payload.update(stage=stage, prior_stage_reviewed=stage != "configural")
                    if fingerprint:
                        payload["reviewed_analysis_sha256"] = fingerprint
                    response = await session.call_tool(
                        "ordinal_measurement_invariance", {"request": payload}
                    )
                    assert not response.is_error, response.content
                    result = response.structured_content
                    assert result["status"] == "success"
                    if fingerprint:
                        assert result["analysis_sha256"] == fingerprint
                        assert result["review"]["analysis_fingerprint_checked"]
                    fingerprint = result["analysis_sha256"]
                    current = result["models"][-1]
                    assert current["fit"]["standard"]["degrees_of_freedom"] == df
                    assert current["converged"] and current["post_check"]
                    assert result["model"]["automatic_decision"] is False
                    if profile == "three_category" and stage == "thresholds":
                        comparison = result["comparisons"][0]
                        assert comparison["code"] == "NOT_INDEPENDENTLY_TESTABLE"
                        assert comparison["comparison_valid"] is False
                        assert comparison["adjusted_difference_test"]["p_value"] is None
                    else:
                        assert all(row["comparison_valid"] for row in result["comparisons"])
                    summary.append(
                        {
                            "profile": profile,
                            "stage": stage,
                            "df": df,
                            "chi_square": current["fit"]["standard"]["chi_square"],
                        }
                    )
            errors = []
            for changes, code in [
                ({"reviewed_analysis_sha256": "0" * 64}, "REVIEW_MISMATCH"),
                ({"stage": "metric"}, "STAGE_UNSUPPORTED"),
            ]:
                payload = discrete_request("binary")
                payload.update(stage="joint", prior_stage_reviewed=True)
                payload.update(changes)
                response = await session.call_tool(
                    "ordinal_measurement_invariance", {"request": payload}
                )
                assert response.is_error
                assert response.structured_content["status"] == "error"
                assert response.structured_content["error"]["code"] == code
                errors.append(code)
    print(
        json.dumps(
            {
                "tool_count": len(listing.tools),
                "stages": summary,
                "package_versions": result["package_versions"],
                "structured_errors": errors,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
