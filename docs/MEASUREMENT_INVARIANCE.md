# Continuous-Indicator Measurement Invariance

`continuous_measurement_invariance` evaluates whether a prespecified
continuous-indicator CFA retains the same measurement parameters across two to
ten observed groups. The group vector is supplied separately from the numeric
data, so it cannot be mistaken for an indicator.

The tool reports a fixed nested sequence and never converts the evidence into
an automatic invariance decision or group-comparison authorization.

## Evidence gate

- Meredith (1993) formally distinguishes weak, strong, and strict factorial
  invariance and connects these constraints to measurement invariance.
  <https://doi.org/10.1007/BF02294825>
- Cheung and Rensvold (2002) evaluate changes in fit indices under cross-group
  equality constraints and show why model comparison should not rely only on
  raw chi-square differences.
  <https://doi.org/10.1207/S15328007SEM0902_5>
- Chen (2007) studies the sensitivity of CFI, RMSEA, and SRMR changes to loading,
  intercept, and residual noninvariance across design conditions.
  <https://doi.org/10.1080/10705510701301834>
- Rosseel (2012) documents the `lavaan` structural-equation-modeling engine used
  by the fixed adapter. <https://doi.org/10.18637/jss.v048.i02>
- The official lavaan multi-group tutorial documents `group.equal`, the
  configural/weak/strong sequence, and `lavTestLRT` model comparisons.
  <https://lavaan.ugent.be/tutorial/groups.html>

The simulation-derived fit-index recommendations are evidence about particular
conditions, not context-free golden rules. The tool therefore returns signed
changes without classifying them against a universal cutoff.

## Fixed model sequence

All groups share the same user-specified simple structure. Indicators cannot
cross-load, and every factor has at least three indicators.

1. `configural`: the same loading pattern, with parameters estimated by group;
2. `metric`: all factor loadings constrained equal across groups;
3. `scalar`: loadings and observed-variable intercepts constrained equal;
4. `strict`: loadings, intercepts, and residual variances constrained equal.

The adapter calls `lavaan::cfa` with `std.lv = TRUE`, an explicit mean
structure, and either ML or MLR. For MLR, adjacent comparisons use lavaan's
Satorra-Bentler scaled difference test. For ML, they use the standard chi-square
difference test.

Each model returns standard fit statistics. MLR additionally returns scaled
test statistics and robust CFI, TLI, and RMSEA. Each adjacent comparison returns
the likelihood-ratio statistic, degrees-of-freedom difference, p value, and
signed changes computed as constrained minus less-constrained fit:

- a negative delta CFI indicates lower CFI in the constrained model;
- a positive delta RMSEA indicates higher RMSEA;
- a positive delta SRMR indicates higher SRMR.

The direction is explicit so downstream clients do not need to infer a sign
convention. The result also contains group-specific configural loadings,
indicator intercepts, and residual variances.

## Input and failure contract

The tool initially uses listwise deletion across selected indicators. Every
group must retain at least 100 rows, more rows than indicators, nonzero variance
for every indicator, and a full-rank positive-definite indicator correlation
matrix. The 100-row threshold is a conservative software safeguard, not a claim
of sufficient power or parameter stability.

Every stage must converge, pass lavaan's post-estimation admissibility check,
retain nonnegative residual variances, and have positive-definite latent
covariance matrices. Convergence or post-check failure stops the tool call;
residual and latent-covariance diagnostics remain explicit in successful
results.

The result reports overall and per-group sample flow, one-based excluded row
numbers, estimator and package versions, model constraints, warnings, and the
absence of any automatic decision.

## Deliberate boundaries

The tool does not:

- repair a poorly fitting configural model;
- use modification indices to release equality constraints;
- conduct an automatic partial-invariance search;
- compare observed or latent group means;
- handle sampling weights, clusters, complex survey designs, or longitudinal
  dependence;
- establish construct validity, fairness, absence of DIF, or substantive group
  equivalence.

Ordered-categorical invariance is not routed through this tool. Thresholds,
latent-response intercepts, and residual variances require a distinct
identification sequence. The separate [ordinal tool](ORDINAL_MEASUREMENT_INVARIANCE.md)
follows Wu and Estabrook (2016) through a fixed, reviewed-stage
`semTools::measEq.syntax` contract for indicators with 4-10 categories.
<https://doi.org/10.1007/s11336-016-9506-0>

## Validation

The integration test uses the published two-school
`lavaan::HolzingerSwineford1939` example. The official tutorial supplies the
configural, metric, and scalar model sequence and rounded fit results. The
versioned test stores higher-precision lavaan values and adds a strict model.
Thus, the first three models are tied to a published package example, while the
strict model and decimal-level values remain engine-based regression evidence,
not an independent SEM implementation.
