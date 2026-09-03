"""Exercise the installed ordinal tool through real stdio MCP using synthetic package data."""

import asyncio
import json
import os
import subprocess
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from psychometrics_mcp.ordinal_invariance import STAGES, ordinal_invariance_r_environment


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
            for stage, df in zip(STAGES, [38, 54, 60, 66, 74], strict=True):
                request.update(stage=stage, prior_stage_reviewed=stage != "configural")
                response = await session.call_tool(
                    "ordinal_measurement_invariance", {"request": request}
                )
                assert not response.is_error, response.content
                result = response.structured_content
                current = result["models"][-1]
                assert current["fit"]["standard"]["degrees_of_freedom"] == df
                assert current["converged"] and current["post_check"]
                assert result["model"]["automatic_decision"] is False
                assert all(row["comparison_valid"] for row in result["comparisons"])
                summary.append(
                    {
                        "stage": stage,
                        "df": df,
                        "chi_square": current["fit"]["standard"]["chi_square"],
                    }
                )
    print(
        json.dumps(
            {
                "tool_count": len(listing.tools),
                "stages": summary,
                "package_versions": result["package_versions"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
