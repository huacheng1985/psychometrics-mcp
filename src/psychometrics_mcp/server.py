"""MCP transport and tool registration."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from .analysis import (
    correlation_matrix as analyze_correlations,
)
from .analysis import (
    ctt_item_analysis as analyze_ctt,
)
from .analysis import (
    descriptive_statistics as describe_data,
)
from .analysis import (
    inspect_response_data as inspect_data,
)
from .analysis import (
    ordinary_least_squares as fit_ols,
)
from .analysis import (
    plan_psychometric_analysis as make_plan,
)
from .factor import confirmatory_factor_analysis as fit_cfa
from .factor import factor_capabilities
from .models import (
    AnalysisPlanRequest,
    CFARequest,
    CorrelationRequest,
    NumericData,
    OLSRequest,
    ResponseData,
)
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
    """Report whether local Python and the fixed R analysis engines are available."""
    result = computation_capabilities()
    result["confirmatory_factor_analysis"] = factor_capabilities()
    return result


@mcp.tool(structured_output=True)
def inspect_response_data(data: ResponseData) -> dict[str, Any]:
    """Audit response shape, missingness, categories, ranges, and zero-variance items."""
    return inspect_data(data)


@mcp.tool(structured_output=True)
def ctt_item_analysis(data: ResponseData) -> dict[str, Any]:
    """Compute item summaries, item-rest correlations, raw alpha, and SEM with warnings."""
    return analyze_ctt(data)


@mcp.tool(structured_output=True)
def descriptive_statistics(data: NumericData) -> dict[str, Any]:
    """Summarize numeric variables with sample flow, missingness, and robust boundaries."""
    return describe_data(data)


@mcp.tool(structured_output=True)
def correlation_matrix(request: CorrelationRequest) -> dict[str, Any]:
    """Compute Pearson or Spearman correlations with explicit missing-data handling."""
    return analyze_correlations(request)


@mcp.tool(structured_output=True)
def ordinary_least_squares(request: OLSRequest) -> dict[str, Any]:
    """Fit a fixed numeric OLS model with classical inference and influence diagnostics."""
    return fit_ols(request)


@mcp.tool(structured_output=True)
def confirmatory_factor_analysis(request: CFARequest) -> dict[str, Any]:
    """Fit a fixed continuous-indicator simple-structure CFA with lavaan::cfa."""
    return fit_cfa(request)


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
