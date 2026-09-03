# Exploratory Factor Analysis and Parallel Analysis

Psychometrics MCP admits factor retention and exploratory factor estimation as
two separate tools. `parallel_analysis` proposes a candidate factor count;
`exploratory_factor_analysis` estimates a user-selected factor count. A
parallel-analysis suggestion is never silently promoted into a fitted or
confirmed measurement model.

## Evidence gate

- Horn (1965) introduced parallel analysis by comparing observed roots with
  roots from random data. <https://doi.org/10.1007/BF02289447>
- Hayton, Allen, and Scarpello (2004) reviewed factor-retention errors and
  provided a practical parallel-analysis tutorial.
  <https://doi.org/10.1177/1094428104263675>
- Fabrigar, Wegener, MacCallum, and Strahan (1999) examined consequential EFA
  decisions, including extraction, retention, and rotation.
  <https://doi.org/10.1037/1082-989X.4.3.272>
- Browne (2001) reviewed analytic rotation and the interpretation of rotated
  exploratory solutions. <https://doi.org/10.1207/S15327906MBR3601_05>
- The fixed implementation uses `psych::fa`. CRAN describes `psych` as a
  general-purpose psychometric package, lists it in the Psychometrics task
  view, and records `GPArotation` as an imported rotation dependency.
  <https://CRAN.R-project.org/package=psych>

The method papers support the statistical procedures; the CRAN record supports
the selected implementation. Package availability alone is not treated as
theoretical evidence.

## Fixed parallel-analysis contract

The version 1.0 request accepts continuous numeric data, `minres` or `ml`
extraction, 100 to 2,000 simulations, a percentile strictly between .50 and
1.00, a recorded nonnegative integer seed, and listwise deletion. The default
is 500 simulations at the 95th percentile using MINRES.

The adapter computes observed common-factor eigenvalues with `psych::fa`,
generates independent standard-normal datasets with the same row and column
counts, and applies the same extraction to every simulated correlation matrix.
It retains the contiguous leading observed eigenvalues that are strictly above
their simulated percentile thresholds. Negative later common-factor
eigenvalues are possible and are not silently replaced by zero.

The result reports every observed root, simulated mean, simulated percentile,
retention decision, seed, random generator, method, package versions, warnings,
and sample flow. It is a retention aid, not a uniquely correct dimensionality
decision.

## Fixed EFA contract

The version 1.0 request accepts a factor count smaller than the number of
continuous variables, MINRES or maximum-likelihood extraction, and one of three
rotations:

- `oblimin`, the default, permits correlated factors and requires
  `GPArotation`;
- `varimax` imposes an orthogonal rotated solution;
- `none` returns an unrotated solution.

A one-factor solution is necessarily returned without rotation, and the result
records both the requested and effective rotation. Inputs are screened for at
least three variables, at least 20 complete rows, more rows than variables,
zero variance, rank deficiency, and a non-positive-definite Pearson correlation
matrix.

The result contains pattern loadings, structure coefficients, communalities,
uniquenesses, factor correlations, variance-accounted summaries, fit indices
when `psych` supplies them, and up to 25 largest residual correlations. A
Heywood diagnostic identifies negative uniqueness or communality above one.
Warnings are captured rather than printed to the MCP transport.

Factor signs are indeterminate. For reproducible serialization, each factor is
reoriented so its largest absolute pattern loading is positive, and the factor
correlation matrix is transformed consistently. Factor order remains the
engine's order and must not be interpreted as substantive rank. Pattern and
structure coefficients are both returned because they differ under oblique
rotation.

`psych::fa` does not expose one universal convergence flag across both admitted
extraction methods. The adapter therefore reports only that a finite solution
was returned, captures engine warnings, and exposes Heywood and residual
diagnostics; it does not fabricate a stronger convergence claim.

## Validation status and limits

The integration tests use a deterministic 240-row, six-variable generator with
two correlated factors. They verify recovery of the two loading groups,
listwise sample flow, factor-sign normalization, seeded repeatability, and a
versioned numerical target. This target is engine-based regression validation
because both its recorded values and runtime values use `psych`; independent
numerical verification remains a later release gate.

Current exclusions are deliberate: ordinal/polychoric input, bootstrap
stability, resampled-data parallel analysis, MAP and other retention rules,
factor scores, bifactor rotations, target rotation, and automatic construct
naming are not implemented. EFA results do not establish validity, invariance,
fairness, causal meaning, or suitability for consequential score use.
