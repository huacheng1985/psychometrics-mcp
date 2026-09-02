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
- Reproducible tables, plots, citations, seeds, exclusions, and package versions

## Priority 1: Everyday analytical foundation

- Data import, dictionaries, recoding, reverse scoring, weights, and missingness
- Descriptive statistics with missingness and quartiles (implemented);
  distributions, cross-tabs, and visual diagnostics (remaining)
- Pearson and Spearman matrices with pairwise/listwise deletion (implemented);
  polychoric and partial correlation plus uncertainty intervals (remaining)
- t tests, ANOVA/ANCOVA, chi-square, effect sizes, and multiplicity controls
- OLS, logistic, ordinal, count, robust, and multilevel regression

## Priority 2: Measurement core

- CTT scale diagnostics, reliability intervals, omega, and score precision
- EFA, parallel analysis, CFA, SEM, categorical estimators, and local dependence
- Rasch extensions: PCM, RSM, person/item fit, Wright maps, targeting, and DIF
- 1PL/2PL/3PL and polytomous IRT with model comparison and information functions
- Generalizability theory, rater models, many-facet models, and DCM

## Priority 3: Measurement decisions

- Multi-group and longitudinal invariance
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
