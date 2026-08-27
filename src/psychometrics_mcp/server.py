"""MCP transport and tool registration."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from .analysis import (
    ctt_item_analysis as analyze_ctt,
)
from .analysis import (
    inspect_response_data as inspect_data,
)
from .analysis import (
    plan_psychometric_analysis as make_plan,
)
from .models import AnalysisPlanRequest, ResponseData
from .rasch import computation_capabilities, run_rasch_model

mcp = MCPServer(
    "Psychometrics MCP",
    instructions=(
        "Use these tools for measurement-aware, reproducible analysis. Treat results as "
        "evidence requiring substantive review, not automatic validity claims."
    ),
)


@mcp.tool(structured_output=True)
def check_computation_capabilities() -> dict[str, Any]:
    """Report whether local Python and the fixed R/eRm Rasch engine are available."""
    return computation_capabilities()


@mcp.tool(structured_output=True)
def inspect_response_data(data: ResponseData) -> dict[str, Any]:
    """Audit response shape, missingness, categories, ranges, and zero-variance items."""
    return inspect_data(data)


@mcp.tool(structured_output=True)
def ctt_item_analysis(data: ResponseData) -> dict[str, Any]:
    """Compute item summaries, item-rest correlations, raw alpha, and SEM with warnings."""
    return analyze_ctt(data)


@mcp.tool(structured_output=True)
def plan_psychometric_analysis(request: AnalysisPlanRequest) -> dict[str, Any]:
    """Create a measurement-aware analysis sequence from the intended use and design."""
    return make_plan(request)


@mcp.tool(structured_output=True)
def rasch_model(data: ResponseData) -> dict[str, Any]:
    """Fit a fixed dichotomous Rasch model with eRm::RM; arbitrary code is never accepted."""
    return run_rasch_model(data)


def main() -> None:
    """Run the local stdio MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
