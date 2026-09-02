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
