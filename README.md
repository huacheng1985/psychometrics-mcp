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
| `check_computation_capabilities` | Check Python, R, `eRm`, and `jsonlite` availability |
| `inspect_response_data` | Audit dimensions, missingness, categories, ranges, and variance |
| `ctt_item_analysis` | Item summaries, item-rest correlations, raw alpha, and SEM |
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
- R with `eRm` and `jsonlite` for `rasch_model`

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
python -m build
```

The test suite includes a real `eRm` integration test and a versioned numerical
regression target for the fixed R adapter. The target is not yet independent
verification; that remains a release gate. CI separately validates Python
behavior, the R adapter, and the Docker build.

## Interpretation and safety boundaries

- Tool inputs are strict schemas; unknown fields are rejected.
- `rasch_model` calls one fixed R script and never accepts user R or shell code.
- Missingness, exclusions, methods, versions, warnings, and sample flow are
  returned with analytical results.
- Reliability is not validity, model fit is not fairness, and prediction is not
  measurement of a construct.
- Local deployment is preferred for item-response and student-level data.

See [Architecture](docs/ARCHITECTURE.md),
[Privacy and Deployment](docs/PRIVACY_AND_DEPLOYMENT.md), and the
[Development Backlog](docs/DEVELOPMENT_BACKLOG.md).

## License

MIT
