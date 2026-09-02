# OLS Regression

`ordinary_least_squares` fits a fixed numeric ordinary least-squares model. It
does not accept formulas, Python, R, shell code, file paths, or arbitrary model
options.

## Request

The request contains:

- `data`: a rectangular `NumericData` object with finite observed values and
  explicit or generated unique variable names;
- `outcome`: one variable name;
- `predictors`: one or more unique numeric variable names;
- `include_intercept`: `true` by default;
- `confidence_level`: greater than 0.5 and less than 1.0; and
- `missing`: currently fixed to `listwise`.

Rows missing the outcome or any selected predictor are excluded. The result
reports their one-based input row numbers, capped at 100, plus a truncation flag.
Variables not selected for the model do not affect listwise deletion.

## Result

The version 1.0 result reports:

- coefficient estimates, classical standard errors, two-sided Student-t tests,
  and confidence intervals;
- centered R-squared with an intercept or explicitly labeled uncentered
  R-squared without one;
- adjusted R-squared, residual standard error, RMSE, MAE, and the model F test;
- rank and raw design-matrix condition number; and
- internally standardized residual, leverage, and Cook's-distance screening.

Influence details are capped at the first 25 flagged observations. Thresholds
of `2p/n` for leverage, `|3|` for internally standardized residuals, and `4/n`
for Cook's distance are screening conventions, not automatic deletion rules.
Every flagged case requires contextual review.

## Preconditions and limitations

The tool rejects a zero-variance outcome, insufficient residual degrees of
freedom, and a rank-deficient design matrix. Predictors must already be numeric;
automatic contrast coding and reference-level selection are not part of this
version.

Coefficient inference uses the classical homoskedastic covariance estimator.
It assumes an appropriate linear specification, independent errors, and
homoskedastic residuals. Robust covariance, weights, clustering, categorical
encoding, generalized linear models, and multilevel models remain explicit
future capabilities. Regression association does not establish causality,
construct validity, fairness, or measurement invariance.

## Numerical verification

The deterministic regression reference in
`tests/reference/ols_numeric_expected.json` was produced independently with R
4.5.0 `stats::lm`. Tests compare Python results with R for coefficient estimates,
standard errors, p values, confidence intervals, model fit, and influence
diagnostics.
