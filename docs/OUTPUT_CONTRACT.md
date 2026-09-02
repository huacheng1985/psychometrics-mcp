# Output Contract

Every tool result includes a top-level `schema_version`. Version `1.0` is the
contract for the prototype's current structured JSON results.

## Compatibility policy

- Adding an optional field is backward compatible and does not change the major
  schema version.
- Renaming or removing a field, changing its type, sign convention,
  identification, estimator, or missing-data rule is breaking and requires a new
  major schema version.
- Numerical refinements that preserve the documented estimator and contract must
  be covered by regression tests and described in release notes.
- Deprecated fields must remain available for at least one minor project release
  before removal unless retaining them would create a security or correctness
  defect.

## Missing and unavailable results

JSON `null` represents a statistic that cannot be estimated under the documented
rule, such as a correlation with fewer than three paired observations or a
zero-variance variable. It does not mean zero. Sample-flow fields and warnings
explain exclusions and unavailable estimates.

## Errors

Input shape, field, and enum violations are rejected by strict Pydantic request
models before analysis. Analytical precondition failures, such as nonbinary data
for the fixed Rasch model or an unavailable R engine, fail the tool call rather
than returning a plausible-looking result. A machine-readable cross-tool error
taxonomy remains a release-gate item.

## Interpretation boundary

Statistical output is evidence for qualified review. It is not an automatic claim
of causality, construct validity, fairness, measurement invariance, or fitness
for consequential decisions.
