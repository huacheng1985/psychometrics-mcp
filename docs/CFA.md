# Confirmatory Factor Analysis

`confirmatory_factor_analysis` fits a prespecified, simple-structure CFA for
continuous indicators through a fixed `lavaan::cfa` adapter. It never accepts
arbitrary lavaan, R, or shell syntax.

## Admission evidence

- Method foundation: Jöreskog (1969) developed the general confirmatory
  maximum-likelihood factor-analysis framework, including identification,
  likelihood-ratio testing, and parameter uncertainty.
  <https://doi.org/10.1007/BF02289343>
- Engine evidence: Rosseel (2012) describes and evaluates `lavaan` as an open
  source latent-variable modeling system in the peer-reviewed *Journal of
  Statistical Software*. <https://doi.org/10.18637/jss.v048.i02>
- Engine status: CRAN places `lavaan` in its Psychometrics task view and records
  its current package metadata. <https://CRAN.R-project.org/package=lavaan>
- Interpretation safeguard: fit-index thresholds are not universal decision
  rules. Marsh, Hau, and Wen (2004) document the danger of generalizing fixed
  cutoffs beyond the conditions under which they were studied.
  <https://doi.org/10.1207/S15328007SEM1103_2>

These sources support admitting the constrained tool. They do not establish
that a particular user's factor model is substantively correct.

## Fixed contract

- Indicators are numeric and treated as continuous.
- Every factor has at least three indicators.
- Factor names are unique and indicators cannot cross-load.
- Latent variances are fixed to one (`std.lv = TRUE`).
- Exogenous factors correlate freely under `lavaan::cfa` defaults.
- Estimation is `ML` or robust `MLR`; `MLR` is the default.
- Missing selected indicators use listwise deletion, with one-based excluded
  row numbers returned for audit.
- The adapter returns convergence and post-estimation checks, global fit,
  loadings with uncertainty, standardized estimates, factor covariances,
  residual variances, package versions, and warnings.

The tool deliberately does not accept correlated residuals, cross-loadings,
regressions, arbitrary constraints, ordinal indicators, modification indices,
or factor scores. Those require separate reviewed contracts.

## Fit interpretation

The result reports chi-square, CFI, TLI, RMSEA with its confidence interval,
SRMR, AIC, and BIC. For `MLR`, robust CFI, TLI, and RMSEA are also returned.
No automatic pass/fail label is produced. Fit must be evaluated together with
theory, residual diagnostics, parameter plausibility, sample properties, and
comparison to defensible alternative models.

## Numerical verification

The integration test reconstructs the three-factor model for the 301-row
`lavaan::HolzingerSwineford1939` example and checks the adapter against the
published lavaan tutorial results and versioned numerical targets. This verifies
the fixed model mapping, identification, transport, and extracted results. It is
not independent reimplementation of CFA and is not validity evidence for other
data.
