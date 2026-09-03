# Tool Admission Policy

Psychometrics MCP admits analytical tools one constrained contract at a time.
The presence of an R function is not sufficient.

## Required evidence gate

Each candidate must document:

1. A clearly defined statistical or psychometric estimand and intended use.
2. Peer-reviewed theoretical or methodological support, preferably including
   the foundational method paper and relevant limitations research.
3. A maintained, commonly used R implementation with an official manual and a
   stable extraction interface. A peer-reviewed package paper is preferred.
4. Identification, estimator, missing-data, and input-scale assumptions.
5. Preflight checks, convergence or failure checks, and diagnostics appropriate
   to the method.
6. A fixed structured schema that cannot execute arbitrary code.
7. Versioned numerical references, cross-environment integration tests, and an
   explicit statement of whether validation is independent or engine-based.
8. Sample flow, exclusions, package versions, warnings, and an interpretation
   boundary in every result.

No tool may automatically claim validity, fairness, invariance, causal meaning,
or fitness for a consequential decision. Exploratory suggestions and confirmed
results must remain distinct.

## Admission sequence

The next candidate is chosen by dependency value, evidence strength, package
maturity, and ability to define a safe fixed contract. The first newly admitted
measurement-core tool is continuous-indicator CFA through `lavaan::cfa`.

The next accepted measurement-core slice is continuous-variable EFA and
Horn-style common-factor parallel analysis through fixed `psych::fa` adapters.
Their candidate-versus-fitted outputs remain separate, and neither may name or
confirm a construct automatically.

The next accepted dependency slice comprises unsmoothed two-step polychoric
correlations, ordinal EFA through `psych`, and categorical CFA through lavaan
WLSMV. Association, exploration, and confirmation remain separate outputs.

The next accepted retention slice is seeded permutation parallel analysis for
ordinal data. It preserves exact univariate category margins, never smooths a
polychoric matrix, and exposes sensitivity across polychoric versus Pearson
correlations, principal-component versus common-factor spectra, and mean versus
requested-percentile cutoffs. Its primary recommendation remains exploratory
evidence and is never passed automatically to EFA.

The following areas remain candidates, not accepted implementations:
continuous and ordinal invariance; broader IRT and polytomous Rasch; DIF; linking
and equating; CAT/MST; G-theory and rater models; DCM; measurement-aware machine
learning; validity-evidence mapping; and reproducible report generation. Each
will receive its own evidence review before coding.
