from __future__ import annotations

import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.mark.asyncio
async def test_stdio_client_discovers_expected_tools() -> None:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "psychometrics_mcp.server"],
    )
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = await session.list_tools()
            capabilities = await session.call_tool("check_computation_capabilities", {})
    names = {tool.name for tool in tools.tools}
    assert names == {
        "check_computation_capabilities",
        "inspect_response_data",
        "ctt_item_analysis",
        "descriptive_statistics",
        "correlation_matrix",
        "polychoric_correlation_matrix",
        "ordinary_least_squares",
        "confirmatory_factor_analysis",
        "categorical_confirmatory_factor_analysis",
        "continuous_measurement_invariance",
        "ordinal_measurement_invariance",
        "parallel_analysis",
        "exploratory_factor_analysis",
        "ordinal_exploratory_factor_analysis",
        "ordinal_parallel_analysis",
        "plan_psychometric_analysis",
        "rasch_model",
    }
    assert capabilities.is_error is False
    assert capabilities.structured_content["schema_version"] == "1.0"
    assert capabilities.structured_content["python"]["available"] is True
