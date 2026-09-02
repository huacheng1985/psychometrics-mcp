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

The following areas remain candidates, not accepted implementations: EFA and
parallel analysis; categorical CFA and invariance; broader IRT and polytomous
Rasch; DIF; linking and equating; CAT/MST; G-theory and rater models; DCM;
measurement-aware machine learning; validity-evidence mapping; and reproducible
report generation. Each will receive its own evidence review before coding.
