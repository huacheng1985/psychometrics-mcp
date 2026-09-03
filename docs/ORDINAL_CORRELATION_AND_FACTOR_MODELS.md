# Ordinal Correlation and Factor Models

Psychometrics MCP separates ordinal association, retention evidence,
exploratory structure, and confirmatory structure into four tools:

- `polychoric_correlation_matrix` estimates latent-response associations;
- `ordinal_parallel_analysis` supplies factor-retention evidence with explicit
  method sensitivity;
- `ordinal_exploratory_factor_analysis` fits a user-selected exploratory factor
  count to that association matrix;
- `categorical_confirmatory_factor_analysis` tests a prespecified
  simple-structure threshold model with WLSMV.

No result is silently promoted into the next analytical stage.

## Evidence gate

- Olsson (1979) developed maximum-likelihood and two-step maximum-likelihood
  estimation for the polychoric correlation and its thresholds.
  <https://doi.org/10.1007/BF02296207>
- Flora and Curran (2004) evaluated full and robust weighted-least-squares CFA
  for ordinal indicators. Their results support robust WLS while documenting
  the underlying continuous-response normality assumption and finite-sample
  limitations. <https://doi.org/10.1037/1082-989X.9.4.466>
- Holgado-Tello, Chacon-Moscoso, Barbero-Garcia, and Vila-Abad (2010) compared
  Pearson- and polychoric-based exploratory and confirmatory factor solutions
  for ordinal variables. <https://doi.org/10.1007/s11135-008-9190-y>
- Kampen and Weeren (2017) show why a high polychoric correlation cannot by
  itself substantiate the underlying bivariate-normal response hypothesis.
  <https://doi.org/10.1007/s11135-016-0378-2>
- Fabrigar, Wegener, MacCallum, and Strahan (1999) provide broader guidance on
  extraction, retention, rotation, and interpretation in EFA.
  <https://doi.org/10.1037/1082-989X.4.3.272>
- Horn (1965) introduced parallel analysis by comparing observed roots with
  roots from random data of the same dimensions.
  <https://doi.org/10.1007/BF02289447>
- Buja and Eyuboglu (1992) developed the permutation interpretation of parallel
  analysis and documented differences between principal-component and common-
  factor variants. <https://doi.org/10.1207/s15327906mbr2704_2>
- Garrido, Abad, and Ponsoda (2013) evaluated ordinal parallel analysis across
  data conditions and method choices, including correlation matrix, extraction
  spectrum, and eigenvalue percentile. <https://doi.org/10.1037/a0030005>
- The implementation uses the established CRAN `psych` and `lavaan` packages.
  The official lavaan categorical-data tutorial documents that `ordered=` with
  WLSMV uses DWLS estimation, robust standard errors, and a mean- and
  variance-adjusted test statistic. <https://lavaan.ugent.be/tutorial/cat.html>

The papers support the methods and limitations; package availability alone is
not treated as theoretical evidence.

## Shared ordinal-data contract

Inputs contain integer-coded ordered categories and optional missing values.
Category numbers express order, not equal spacing. Each analyzed variable must
have two to ten observed categories, and each observed category must contain at
least two complete cases. Category values need not be consecutive.

All four tools initially use listwise deletion. They return the one-based
excluded row numbers, category values and counts, sparse-category warnings, and
the number of empty bivariate contingency-table cells. The polychoric tool
requires at least 20 complete rows; ordinal parallel analysis, ordinal EFA, and
categorical CFA require at least 100 under this conservative execution contract.
Ordinal parallel analysis accepts at most 30 variables and 1,000 successful
permutations to bound local compute. These limits are software safeguards, not
claims that a design is substantively adequate.

## Unsmoothed polychoric correlation

`polychoric_correlation_matrix` calls `psych::polychoric` with two-step
estimation, pair-specific thresholds, no smoothing, and a configurable
continuity correction from 0 to 1. The default correction is 0.5. Because the
initial contract is complete-case, marginal thresholds are common across the
pairwise tables even though the engine is called with `global = FALSE` to
support variables with different category counts.

The result reports the full correlation matrix, finite marginal thresholds,
eigenvalues, positive-definiteness status, and correlations at or beyond an
absolute value of .999. A non-positive-definite result remains visible and is
never replaced with a nearby admissible matrix.

## Ordinal parallel analysis

`ordinal_parallel_analysis` independently permutes every variable without
replacement. Each reference data set therefore preserves every observed
univariate category count exactly while breaking cross-variable association.
The adapter obtains both an unsmoothed, pair-specific-threshold
`psych::polychoric` matrix and a Pearson matrix for the observed and permuted
data. It rejects, rather than repairs, invalid polychoric reference matrices and
attempts at most three times the requested number of successful permutations.
The successful, attempted, and rejected counts and rejection reasons are
returned.

The tool compares eight retention variants formed by crossing:

- polychoric and Pearson correlation matrices;
- principal-component roots and common-factor roots from the selected MINRES or
  ML method; and
- the mean and a requested percentile of the permutation roots.

The primary variant is polychoric correlation, principal-component roots, and
the mean permutation root. This configuration follows the broad recommendation
reported by Garrido et al. (2013), but the tool labels it as a primary
suggestion rather than a confirmed count. Every variant uses the first-crossing
rule: it retains consecutive leading observed roots only until the first root
that does not exceed its matched reference. Disagreement across variants is a
warning and remains visible in the structured result. The random seed and all
per-root observed and reference values are returned. No suggested count is
automatically fitted by the EFA tool.

The permutation generator is fixed in the current contract. Thresholded-normal
simulation, alternative ordinal null models, MAP, comparison-data methods, and
bootstrap stability are not silently substituted and remain future sensitivity
extensions.

## Ordinal EFA

`ordinal_exploratory_factor_analysis` first estimates the same unsmoothed
polychoric matrix and then passes it to `psych::fa` with the complete-case
sample size. It supports MINRES or ML extraction and oblimin, varimax, or no
rotation. A non-positive-definite polychoric matrix stops the analysis rather
than triggering automatic smoothing.

Outputs include pattern loadings, structure coefficients, communalities,
uniquenesses, factor correlations, variance-accounted summaries, fit
information supplied by `psych`, and the largest residual correlations. The
adapter normalizes factor signs by making the largest absolute pattern loading
on each factor positive and transforms the factor-correlation matrix
consistently. Factor order remains engine-dependent. Heywood cases and the
minimum polychoric eigenvalue are explicit diagnostics.

The factor count is supplied by the caller. Even when an ordinal parallel-
analysis result is available, choosing and fitting that count is a separate
human-reviewed action. Garrido, Abad, and Ponsoda (2013) show that parallel
analysis with ordinal variables is sensitive to sample size, loadings, factor
count and correlations, number of response categories, and skewness.
<https://doi.org/10.1037/a0030005>

## Categorical CFA

`categorical_confirmatory_factor_analysis` uses a fixed
`lavaan::cfa` WLSMV workflow. Indicators are converted to ordered factors using
their observed category order. The model uses a probit latent-response link,
delta parameterization, latent variances fixed to one, freely correlated
factors, and listwise deletion. Each indicator belongs to exactly one factor,
and each factor requires at least three indicators.

The result distinguishes conventional fit statistics from robust/scaled
statistics. It returns loadings, adjacent-category threshold mappings, factor
covariances, residual variances, convergence, lavaan post-check status, latent
covariance admissibility, package versions, and engine warnings. WLSMV does not
provide likelihood-based AIC or BIC, so those values are not fabricated.

## Validation and interpretation limits

The polychoric integration test uses an independent analytic tetrachoric
reference. For a symmetric binary table with both thresholds at zero,
`rho = sin(2*pi*(P11 - 1/4))`; the fixed table gives
`rho = 0.5877852523`.

The ordinal parallel-analysis, EFA, and categorical CFA tests use a
deterministic 500-row, six-indicator, two-factor generator. They verify seeded
retention recovery and all eight sensitivity variants, loading recovery,
threshold mapping, correlation-matrix admissibility, WLSMV convergence and
post-check, and versioned numerical targets. Those parallel and factor-model
targets are engine-based, not independent implementations. Cross-version and
independent validation remain distinct claims.

All four tools depend on the hypothesis that ordered observations arise by
thresholding latent continuous responses, with bivariate-normal assumptions
for each polychoric association. High correlations or good fit cannot establish
that data-generating story. Results do not establish dimensionality, construct
meaning, validity, invariance, fairness, causality, or fitness for consequential
decisions.
