# Psychometrics MCP Development Backlog

The backlog deliberately treats Rasch as one small vertical slice of a broader
measurement-aware environment. Every new model must include validation data,
diagnostics, provenance, interpretation boundaries, and regression tests.

## Priority 0: Foundation and release gates

- Schema version on every current output and documented compatibility policy
  (implemented); typed output models, machine-readable error taxonomy, and
  deprecation telemetry (remaining)
- Versioned eRm implementation-regression target (implemented); independently
  verified numerical targets from a separate implementation or hand-audited
  published reference (release gate)
- Cross-platform Docker builds and MCP client compatibility tests
- CI dependency scanning with pip-audit and local no-persistence policy
  (implemented); repository vulnerability alerts, formal security review,
  retention enforcement for future hosted modes, and audit events (remaining)
- Evidence-gated tool admission policy with method and package citations
  (implemented); reproducible tables, plots, machine-readable citations, seeds,
  exclusions, and package versions (remaining)

## Priority 1: Everyday analytical foundation

- Data import, dictionaries, recoding, reverse scoring, weights, and missingness
- Descriptive statistics with missingness and quartiles (implemented);
  distributions, cross-tabs, and visual diagnostics (remaining)
- Pearson and Spearman matrices with pairwise/listwise deletion (implemented);
  unsmoothed listwise polychoric matrices (implemented); partial correlation,
  pairwise ordinal missingness, goodness-of-fit checks for latent bivariate
  normality, and uncertainty intervals (remaining)
- t tests, ANOVA/ANCOVA, chi-square, effect sizes, and multiplicity controls
- Numeric OLS with classical inference and influence screening (implemented);
  categorical encoding, robust covariance, weighted least squares, logistic,
  ordinal, count, and multilevel regression (remaining)

## Priority 2: Measurement core

- CTT scale diagnostics, reliability intervals, omega, and score precision
- Continuous-indicator simple-structure CFA with lavaan ML/MLR (implemented);
  continuous-variable EFA and seeded common-factor parallel analysis with psych
  (implemented); ordinal EFA from unsmoothed polychoric matrices and categorical
  CFA with lavaan WLSMV (implemented); seeded ordinal permutation parallel
  analysis with correlation, extraction-spectrum, and cutoff sensitivity
  (implemented); SEM, additional retention rules, resampling stability, and
  local dependence (remaining)
- Rasch extensions: PCM, RSM, person/item fit, Wright maps, targeting, and DIF
- 1PL/2PL/3PL and polytomous IRT with model comparison and information functions
- Generalizability theory, rater models, many-facet models, and DCM

## Priority 3: Measurement decisions

- Continuous multi-group configural, metric, scalar, and strict invariance with
  ML/MLR (implemented); ordinal multi-group invariance under Wu-Estabrook
  identification and longitudinal invariance (remaining)
- DIF detection with effect sizes, purification, sensitivity, and fairness review
- Linking, equating, vertical scaling, anchor drift, and uncertainty propagation
- CAT/MST simulation, exposure, routing, stopping, and ETIF evaluation
- Standard setting, classification consistency/accuracy, and cut-score uncertainty

## Priority 4: Measurement-aware machine learning

- Regularized regression, trees, random forests, boosting, and model comparison
- Cluster/time-aware cross-validation, leakage checks, calibration, and uncertainty
- Subgroup stability and fairness diagnostics
- Explainability with an explicit boundary between prediction and construct meaning
- Reliability and construct relevance checks for labels and predictors

## Priority 5: Evidence, ecosystem, and hosted service

- Validity-evidence maps and reproducible psychometric reports
- Publication-ready tables, plots, accessible exports, and audit trails
- Plugin/adaptor registry, contribution templates, benchmarks, and documentation
- Free open-source local server as the primary product
- Quota-limited community endpoint for teaching and public demonstration
- Optional institutional deployments with private infrastructure and support
