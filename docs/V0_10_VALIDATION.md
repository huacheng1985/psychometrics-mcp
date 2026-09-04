# v0.10 Development Validation

Date: 2026-09-03. Scope: an extension of `ordinal_measurement_invariance`,
not a new tool. The server still exposes 17 tools. This document records local
development evidence, not a release approval or certification.

## Admitted scope and evidence

- Binary configural and joint threshold/loading/intercept constraints.
- Three-category stagewise models, with threshold equality explicitly marked
  not independently testable.
- Existing 4-10-category behavior retained as the default profile.
- Stage-independent analysis fingerprints, optional reviewed-fingerprint match,
  and controlled adapter errors transported as MCP errors.

The identification framework is Wu and Estabrook (2016),
<https://doi.org/10.1007/s11336-016-9506-0>. The implementation follows
[`semTools::measEq.syntax`](https://rdrr.io/cran/semTools/man/measEq.syntax.html)
and uses `lavaan::cfa`, not a newly implemented estimator. See the
[full contract](ORDINAL_MEASUREMENT_INVARIANCE.md) for assumptions and limits.

## Local checks

- Ruff: passed.
- Pytest: 85 passed, including actual R integration tests.
- Normal wheel installation and wheel/sdist build: passed; the wheel contains
  the current fixed R adapter.
- Dependency audit: no known vulnerabilities reported for auditable Python
  dependencies. The unpublished project itself is not audited by PyPI lookup.
- Real macOS stdio MCP: 12 admitted profile/stage calls succeeded, and two
  negative calls returned `REVIEW_MISMATCH` and `STAGE_UNSUPPORTED` with MCP
  error status and structured payloads.
- Docker image `psychometrics-mcp:0.10.0`: built and passed the same 12 stage
  calls and two error calls. Linux arm64 used R 4.2.2, lavaan 0.7-2, semTools
  0.5-9, and jsonlite 1.8.4. New binary/three-category standard chi-square values
  differed from macOS by less than 3e-6. This is cross-environment regression
  evidence, not independent estimation.
- Global lavaan remains 0.6-19. This adapter uses isolated lavaan 0.7-2 and
  semTools 0.5-9, with R 4.5.0 and jsonlite 2.0.0 on the Mac Mini.

Fixed targets cover standard/scaled chi-square, degrees of freedom, and valid
adjusted difference statistics and p values. Hand-specified models independently
encode the identification constraints but still use the same lavaan estimator.
They are not independent-solver validation. Mocked failure tests verify error
transport; they do not establish the statistical detection rate of bad models.

## Small deterministic simulation diagnostic

Each sample has two groups of 1,000 respondents and six indicators. A standard
normal common factor has loading 0.7 and independent standard normal errors.
Item locations range from -1 to 1. Binary responses use one threshold at each
location; three-category responses use thresholds at location minus/plus 0.5.
The alternative increases group 2's first loading by 1.1 and shifts its third
underlying response by 1.0. All 12 requested comparisons below converged and
passed the implemented admissibility checks.

| Seed | Binary joint, invariant parameters | Binary joint, alternative | Three-category scalar, invariant parameters | Three-category scalar, alternative |
| --- | ---: | ---: | ---: | ---: |
| 721 | .07882 | 2.77e-16 | .90243 | 1.15e-51 |
| 722 | .51650 | 1.17e-26 | .16413 | 6.09e-60 |
| 723 | .41828 | 2.73e-28 | .99072 | 6.48e-58 |

Entries are Satorra (2000) scaled-shifted difference-test p values. Binary joint
comparisons use 4 difference degrees of freedom; three-category scalar versus
metric uses 5. The alternative also violates loading invariance: requesting
scalar here is a software diagnostic, not endorsement of progressing after a
failed metric model. Review flags in these automated fixtures are synthetic.

These three seeds do not estimate power or Type I error. Not all tests from
invariant-parameter samples are nonsignificant: seed 721's three-category metric
comparison has p = .02266. That realized sample is retained without selection
or tuning. No automatic accept/reject decision is made by the tool.

Reproduce the diagnostic from the checkout with development dependencies and
the isolated R library installed:

```sh
.venv/bin/python - <<'PY'
import runpy
from psychometrics_mcp.ordinal_invariance import ordinal_measurement_invariance

make = runpy.run_path('tests/test_discrete_invariance.py')['simulated_request']
for seed in (721, 722, 723):
    for profile, stage in [('binary', 'joint'), ('three_category', 'scalar')]:
        for alternative in (False, True):
            result = ordinal_measurement_invariance(make(profile, stage, seed, alternative))
            print(seed, profile, alternative,
                  result['comparisons'][0]['adjusted_difference_test'])
PY
```

## Remaining boundaries

Mixed-category/scale profiles, binary strict/mean extensions, longitudinal
models, automatic partial invariance, empirical instrument validation, and a
cross-tool error taxonomy remain outside this slice. A fingerprint is not a
signed review record. Parameter-covariance checks are not a proof of global
identification. Publication, merging main, and release tagging require a separate
approval step.
