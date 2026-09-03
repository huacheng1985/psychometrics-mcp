# Psychometrics MCP

Psychometrics MCP is a local-first, measurement-aware MCP server for
reproducible statistical and psychometric analysis. It is designed to help an
AI host use constrained analytical tools without exposing arbitrary R or shell
execution.

The project is an early prototype. Current results require qualified human
review and must not be used as automatic evidence of score validity, fairness,
or fitness for consequential decisions.

## Current tools

| Tool | Purpose |
|---|---|
| `check_computation_capabilities` | Check Python and fixed R engine availability |
| `inspect_response_data` | Audit dimensions, missingness, categories, ranges, and variance |
| `ctt_item_analysis` | Item summaries, item-rest correlations, raw alpha, and SEM |
| `descriptive_statistics` | Available-case numeric summaries, quartiles, and missingness |
| `correlation_matrix` | Pearson or Spearman matrices with pairwise/listwise deletion and pair-specific n |
| `polychoric_correlation_matrix` | Unsmoothed two-step polychoric matrix for ordered categorical variables |
| `ordinary_least_squares` | Numeric OLS with classical inference, fit, sample flow, and influence diagnostics |
| `confirmatory_factor_analysis` | Continuous-indicator simple-structure CFA with fixed `lavaan::cfa` ML/MLR estimation |
| `categorical_confirmatory_factor_analysis` | Ordered-indicator simple-structure CFA with fixed `lavaan::cfa` WLSMV estimation |
| `continuous_measurement_invariance` | Configural, metric, scalar, and strict multi-group CFA comparisons without automatic pass/fail rules |
| `parallel_analysis` | Seeded Horn-style common-factor retention evidence with MINRES or ML |
| `ordinal_parallel_analysis` | Seeded permutation PA with polychoric/Pearson, PCA/common-factor, and cutoff sensitivity |
| `exploratory_factor_analysis` | Fixed-factor continuous EFA with MINRES/ML and oblimin/varimax/no rotation |
| `ordinal_exploratory_factor_analysis` | Fixed-factor EFA from an unsmoothed polychoric matrix |
| `plan_psychometric_analysis` | Build a purpose- and design-aware analysis sequence |
| `rasch_model` | Fit a fixed dichotomous `eRm::RM` model with CML |

Rasch is the first end-to-end numerical validation slice, not the product
boundary. The development plan includes descriptive statistics, correlations,
regression, measurement-aware machine learning, factor models, broader
IRT/Rasch, DIF and invariance, linking/equating, CAT/MST, G-theory, rater
models, DCM, validity evidence, and reproducible reporting.

## Local installation

Requirements:

- Python 3.11+
- R with `eRm`, `lavaan`, `psych`, `GPArotation`, and `jsonlite` for the fixed
  Rasch, CFA, parallel-analysis, and EFA adapters

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install '.[dev]'
psychometrics-mcp
```

The command starts a stdio MCP server. Configure an MCP host to launch the
absolute path to `.venv/bin/psychometrics-mcp`.

## Docker

```bash
docker build -t psychometrics-mcp:local .
docker run --rm -i psychometrics-mcp:local
```

The server communicates over stdin/stdout, so `-i` is required. It runs as a
non-root user and does not need a data volume because tools accept structured
inputs. If future file-based tools are enabled, mount only a narrow directory
read-only.

## Verification

```bash
ruff check .
pytest
pip-audit
python -m build
```

All tool results carry `schema_version: "1.0"`. The test suite includes real
`eRm`, `lavaan`, and `psych` integration tests and versioned numerical
regression targets.
Each reference states whether it is independent or engine-based validation. CI
separately validates Python behavior, the R adapters, and the Docker build.

## Interpretation and safety boundaries

- Tool inputs are strict schemas; unknown fields are rejected.
- R-backed tools call fixed scripts and never accept user R or shell code.
- Missingness, exclusions, methods, versions, warnings, and sample flow are
  returned with analytical results.
- Reliability is not validity, model fit is not fairness, and prediction is not
  measurement of a construct.
- Local deployment is preferred for item-response and student-level data.

See [Architecture](docs/ARCHITECTURE.md), [Tool Admission
Policy](docs/TOOL_ADMISSION_POLICY.md), [OLS Regression](docs/OLS_REGRESSION.md),
[Confirmatory Factor Analysis](docs/CFA.md),
[Measurement Invariance](docs/MEASUREMENT_INVARIANCE.md),
[EFA and Parallel Analysis](docs/EFA_AND_PARALLEL_ANALYSIS.md),
[Ordinal Correlation and Factor Models](docs/ORDINAL_CORRELATION_AND_FACTOR_MODELS.md),
[Privacy and Deployment](docs/PRIVACY_AND_DEPLOYMENT.md), the [Output
Contract](docs/OUTPUT_CONTRACT.md), and the [Development
Backlog](docs/DEVELOPMENT_BACKLOG.md).

## License

MIT
