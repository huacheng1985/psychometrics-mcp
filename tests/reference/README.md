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

`ordinal_expected.json` contains three targets. The symmetric binary-table
polychoric target is independent and analytic: when both thresholds equal zero,
the quadrant probability identity gives the stated tetrachoric correlation.
The ordinal EFA and categorical CFA targets use the deterministic 500-row,
six-indicator generator in `tests/test_ordinal.py`. They detect adapter and
engine drift but remain engine-based because the targets and runtime use
`psych` or `lavaan`, respectively.
