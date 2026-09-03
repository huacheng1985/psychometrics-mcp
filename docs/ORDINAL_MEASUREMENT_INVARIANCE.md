# Stagewise Ordinal Measurement Invariance

`ordinal_measurement_invariance` uses `semTools::measEq.syntax` to generate a
fixed simple-structure multi-group CFA, then fits it with `lavaan::cfa` using
WLSMV, theta parameterization, and Wu-Estabrook identification. It accepts
ordinal data only; continuous data must use the separate continuous tool.

## Admission evidence

- Wu, H., & Estabrook, R. (2016). Identification of confirmatory factor analysis
  models of different levels of invariance for ordered categorical outcomes.
  *Psychometrika, 81*, 1014-1045. <https://doi.org/10.1007/s11336-016-9506-0>
  supplies the identification framework: equality constraints can release
  location/scale identification restrictions, so adding constraints naively to
  a continuous-indicator sequence is not sufficient.
- Millsap, R. E., & Yun-Tein, J. (2004). Assessing factorial invariance in ordered-
  categorical measures. *Multivariate Behavioral Research, 39*, 479-515.
  <https://doi.org/10.1207/S15327906MBR3903_4> provides foundational treatment of
  ordinal factorial invariance. Its identification strategy is background,
  not the strategy selected by this adapter.
- Rosseel, Y. (2012). lavaan: An R package for structural equation modeling.
  *Journal of Statistical Software, 48*(2). <https://doi.org/10.18637/jss.v048.i02>
  documents the estimation engine.
- The maintained [semTools documentation](https://rdrr.io/cran/semTools/man/measEq.syntax.html)
  documents `ID.cat="Wu.Estabrook.2016"`, threshold-first tests, and the
  recommendation to inspect and fit one invariance stage at a time.
- [lavaan's comparison documentation](https://rdrr.io/cran/lavaan/man/lavTestLRT.html)
  documents the Satorra (2000) scaled-shifted difference test and `A.method="delta"`
  for models nested in their implied moments under different parameterizations.

Package documentation supports the implementation contract; it is not treated
as a substitute for the peer-reviewed methodological evidence above.

## Reviewed progression

| Requested stage | Cumulative equality constraints | Models fitted in this call |
| --- | --- | --- |
| `configural` (default) | Same loading pattern only | Configural |
| `thresholds` | Thresholds | Configural and thresholds |
| `metric` | Thresholds, loadings | Thresholds and metric |
| `scalar` | Thresholds, loadings, latent-response intercepts | Metric and scalar |
| `strict` | Thresholds, loadings, intercepts, residual variances | Scalar and strict |

The first call requires no review flag. Every stronger stage requires
`prior_stage_reviewed=true`: a caller acknowledgement that the preceding stage
on the same data and model has been examined. This flag is not independently
verified and does not constitute a statistical decision or an enforced human
approval system. The tool never sets it automatically. Each call refits only
the immediate predecessor for comparison; it does not establish the validity
of earlier stages. The request hash makes changes to the submitted specification
auditable, but does not contain or save the original data.

Do not progress after unacceptable fit merely because estimation converged.
The tool does not release constraints, select anchors, or search for partial
invariance. All substantive decisions remain outside its execution contract.

## Input safeguards

- Two to ten groups, matched to input rows, with nonblank string or strict integer
  labels; numeric-looking strings remain distinct from integers.
- At most 20,000 rows and 30 selected indicators; at least three indicators per
  factor, no cross-loadings, no arbitrary model or shell syntax.
- Every selected indicator has 4-10 categories in every group, with identical
  numeric category codes across groups. Numeric order specifies category order;
  callers must verify that codes have the same substantive meaning.
- Listwise deletion uses only selected indicators. Every group retains at least
  100 complete cases, each category has at least two cases, and the selected
  indicator matrix must have full rank. These are execution safeguards, not
  claims of adequate sample size. Sparse marginal categories and bivariate cells
  are reported as warnings.
- The R adapter checks convergence before extraction and stops on inadmissible
  solutions, nonpositive residual variances, nonpositive-definite latent or sample
  polychoric covariance matrices, or non-increasing thresholds. It does not
  smooth the polychoric matrix to force acceptance.

Binary and three-category indicators are deliberately excluded: a separate
threshold-equality test is not available in the same way under Wu-Estabrook
identification. Mixed-scale, longitudinal, complex-survey, and clustered models
also remain unimplemented.

## Output and interpretation

Every fit reports its generated syntax, parameter audit (including fixed/free
status and equality labels), identifier mappings, standard/scaled/robust fit
statistics, sample flow, diagnostics, package versions, and warnings. Intercepts
and residual variances refer to underlying continuous responses, not the observed
integer category codes.

Adjacent comparisons call `lavTestLRT(method="satorra.2000", A.method="delta",
scaled.shifted=TRUE)`. They do **not** subtract scaled model chi-square values.
All fit-index deltas are constrained minus preceding fit. Standard, scaled, and
robust indices remain separate. Unavailable robust indices stay `null` with a
warning, rather than being silently replaced by standard indices. An invalid
adjusted comparison has `comparison_valid=false` and no interpretable p value.

No universal cutoff or automatic invariance decision is returned. This tool
does not authorize observed/latent mean comparisons or establish fairness,
absence of DIF, or construct validity.

## Isolated dependencies and validation

The adapter requires lavaan >= 0.6-21 and semTools >= 0.5-9 plus jsonlite. The
reproducible local/container installer pins lavaan 0.7-2 and semTools 0.5-9.
Prerequisite numerical dependencies and jsonlite must already be installed.

For the project virtual environment:

```sh
Rscript scripts/install_ordinal_invariance_dependencies.R .venv/lib/R/library
```

Only this adapter prepends that virtual environment's R library. An explicit
`PSYCHOMETRICS_R_LIBRARY` directory can override it. The Docker image uses
`/opt/psychometrics-r`. Existing tools continue to use their previous R library;
the system installation is not overwritten. CI also tests against the current
packages resolved by its R setup and exercises real MCP calls inside Docker.
When using a custom library, explicitly pass `PSYCHOMETRICS_R_LIBRARY` in the
MCP host's server environment; stdio clients may filter inherited variables.

The regression fixture uses `semTools::datCat`, a documented synthetic
two-factor, two-group dataset. All five stages have engine-based numerical
targets. A second test hand-specifies configural and threshold models without
calling the syntax generator, checking identification mapping. Both still use
lavaan for estimation: neither is independent algorithmic validation. The
example is not evidence of invariance in a real instrument.
