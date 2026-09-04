# Rasch Numerical Regression Reference

`rasch_binary_expected.json` records fixed numerical targets for the deterministic
120-person, five-item response generator in `tests/test_rasch.py`. The targets
were produced on macOS with R 4.5.0, eRm 1.0-10, and jsonlite 2.0.0. The
same item locations and conditional log likelihood were reproduced within the
recorded tolerance in the Linux arm64 Docker image with R 4.2.2, eRm 1.0-2,
and jsonlite 1.8.4.

This artifact is an implementation regression target. It detects changes in the
Python-to-R adapter, parameter sign convention, identification, and numerical
results. It is not an independent validation because the targets and the tested
implementation use the same eRm engine. The Docker result establishes
cross-environment regression stability, not independent algorithmic validation.
Independent verification against a separate implementation or a published
hand-audited reference remains a release gate.

## OLS numerical reference

`ols_numeric_expected.json` records targets produced independently with R 4.5.0
`stats::lm` for the deterministic model `y ~ x1 + x2` defined in
`tests/test_analysis.py`. The Python OLS implementation is checked against R for
coefficient estimates, classical standard errors, model fit, and influence
diagnostics. This reference validates numerical agreement for the documented
small model; it is not evidence that regression assumptions hold for new data.

## CFA numerical reference

`cfa_holzinger_expected.json` records the published three-factor
`lavaan::HolzingerSwineford1939` example and additional high-precision targets
for the same model under `std.lv = TRUE`. The integration test verifies model
mapping, extraction, and numerical stability through the fixed adapter. Because
the reference and runtime both use lavaan, this remains engine-based numerical
validation rather than an independent CFA implementation.

## Parallel-analysis numerical reference

`parallel_synthetic_expected.json` records common-factor eigenvalues and
seeded 95th-percentile simulation thresholds for the deterministic two-factor
generator in `tests/test_exploratory.py`. It catches changes in the fixed
parallel-analysis adapter, R random-number stream, or `psych` engine. Because
the reference and runtime both use `psych`, it is engine-based regression
validation rather than an independent confirmation of Horn's method.

## Ordinal numerical references

`ordinal_expected.json` contains four targets. The symmetric binary-table
polychoric target is independent and analytic: when both thresholds equal zero,
the quadrant probability identity gives the stated tetrachoric correlation.
The ordinal EFA, seeded permutation parallel-analysis, and categorical CFA
targets use the deterministic 500-row, six-indicator generator in
`tests/test_ordinal.py`. They detect adapter and engine drift but remain
engine-based because the targets and runtime use `psych` or `lavaan`,
respectively. The ordinal parallel-analysis observed and seeded reference
eigenvalues reproduced within `4.5e-13` across macOS R 4.5.0 with `psych`
2.5.6 and the Linux arm64 container's R 4.2.2 with `psych` 2.2.9. This is
cross-version regression evidence, not independent algorithmic validation.

## Measurement-invariance numerical reference

`invariance_expected.json` uses the `lavaan::HolzingerSwineford1939` two-school
example documented in the official lavaan multi-group tutorial. Configural,
metric, and scalar chi-square values and the first two nested-model differences
are published tutorial targets. The strict-invariance model and stored
high-precision values are engine-based regression targets. The test therefore
checks the fixed sequence, constraints, extraction, and numerical stability; it
does not independently validate lavaan or establish invariance in the example.
All four standard chi-square values reproduced within `5e-13` across macOS R
4.5.0 with lavaan 0.6-19 and the Linux arm64 container's R 4.2.2 with lavaan
0.6-14. This is cross-version regression evidence, not an independent
implementation check.

## Ordinal measurement-invariance reference

`ordinal_invariance_expected.json` stores five stagewise targets for
`semTools::datCat`, with two correlated factors and no longitudinal constraints.
The dataset is a synthetic package example. Targets use R 4.5.0, lavaan 0.7-2,
and semTools 0.5-9; they are engine-based regression checks, not published
empirical findings or independent algorithmic validation.

`ordinal_invariance_manual.R` constructs the configural and threshold-equality
models explicitly without calling `measEq.syntax`. Agreement verifies the
syntax generator's release of group-2 intercept and residual identification
restrictions when thresholds are equated. It remains a same-estimator check
because the manual models also use lavaan.

All five standard chi-square values agreed within `3e-7` between macOS R 4.5.0
and the Linux arm64 image's R 4.2.2, both with isolated lavaan 0.7-2 and semTools
0.5-9. Real stdio MCP calls exercised every stage in both environments. This is
cross-environment regression evidence, not a separate estimation algorithm.

`discrete_invariance_expected.json` adds fixed-seed binary and three-category
targets for every admitted stage. `discrete_invariance_manual.R` hand-specifies
configural, binary joint, and three-category threshold models, without semTools
syntax generation. All loadings are explicitly freed before assigning equality
labels to avoid lavaan's automatic marker constraint. Both routes use lavaan:
agreement checks the adapter and identification mapping, not solver independence.

The invariant-parameter three-category fixture has a metric comparison p value
of about .0227. This is retained as sampled, not tuned to meet a cutoff. Separate
fixed alternatives perturb one loading and one response location. These checks
establish numerical behavior only, not calibrated power or Type I error rates.
