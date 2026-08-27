# Psychometrics MCP: Measurement-Aware Tools for AI-Assisted Analysis

**Submission category:** Innovation Demonstration  
**Modality:** In-person only  
**Format:** 60-minute individual eBoard demonstration  
**Review:** Blind; no author names appear in the proposal text

## Abstract

Psychometrics MCP is an open-source, local-first server that lets AI assistants invoke constrained psychometric analyses with explicit diagnostics, provenance, and interpretation limits. This demonstration shows data inspection, classical item analysis, and Rasch estimation, then teaches attendees how measurement-aware tool design can improve reproducibility without surrendering expert judgment or sensitive data.

## Demonstration Summary

AI assistants can generate plausible statistical advice, but general-purpose tool access can also enable inappropriate models, hidden data handling, irreproducible commands, and interpretations that outrun evidence. Psychometrics MCP helps measurement researchers, practitioners, and instructors conduct reproducible, measurement-aware analysis by giving AI hosts a constrained set of validated tools with strict inputs, explicit diagnostics, provenance, and interpretation limits. The server is free, open-source, and local-first; its core analyses do not require the project to receive users' response data or pay for their language-model use.

The working prototype implements five Model Context Protocol tools. It checks computation capabilities; audits response dimensions, missingness, category use, ranges, and zero variance; calculates classical item summaries, item-rest correlations, coefficient alpha, and standard error of measurement; generates purpose- and design-aware analysis plans; and fits a dichotomous Rasch model through a fixed `eRm::RM` adapter using conditional maximum likelihood. The server rejects unknown input fields and invalid response codes, returns sample flow and software versions, and never accepts arbitrary R or shell commands. Rasch is the first numerical validation slice, not the project boundary.

During the eBoard demonstration, attendees will follow a synthetic item-response dataset through three views. First, a schema and data audit will show how the server identifies missingness, invalid categories, and unstable conditions before estimation. Second, classical and Rasch outputs will illustrate the difference between obtaining a number and obtaining an auditable result with assumptions, exclusions, diagnostics, and interpretation boundaries. Third, a live tool call from an AI host will show that the host can request an analysis while the fixed analytical engine, rather than model-generated code, controls what executes. A local Docker deployment will demonstrate that protected response data can remain on the user's computer.

After the demonstration, attendees will be able to: distinguish constrained analytical tools from unrestricted code execution; identify the provenance and diagnostic fields needed to audit AI-assisted psychometric results; run the open-source server locally; and adapt the design pattern to additional methods without treating model fit, reliability, or prediction as automatic validity evidence. Attendees will also receive a development map covering descriptive statistics, correlation, regression, factor models, broader Rasch/IRT, DIF and invariance, linking and equating, CAT/MST, rater and generalizability models, measurement-aware machine learning, and reproducible reporting.

The innovation addresses the 2027 meeting theme by connecting measurement expertise with AI infrastructure while preserving human oversight. The repository already includes MCP client regression tests, a real R/`eRm` numerical integration test, container deployment, privacy boundaries, and continuous-integration workflows. Before the Annual Meeting, independently verified reference datasets, additional numerical benchmarks, user documentation, and a reusable demonstration dataset will be released. The result will be a practical community resource rather than a commercial product or a claim that AI can replace psychometric judgment.

## Software Requirements

- Presenter: laptop with Docker, a local MCP-compatible AI host, internet access for fallback only, and an eBoard connection.
- Attendees: no software installation, account, or API key is required to follow the demonstration.
- Distribution: public source repository, container instructions, synthetic example data, and verification notes.
- Privacy: demonstration data will be synthetic or openly licensed; no student or examinee records will be uploaded.

## Development Commitments Before April 2027

1. Publish the open-source repository and tagged container release.
2. Add independently verified reference datasets and numerical tolerances.
3. Document local setup for major MCP hosts and a no-sensitive-data demonstration path.
4. Complete a security and dependency review and publish the data-handling boundary.
5. Prepare an accessible eBoard walkthrough and a downloadable quick-start guide.

## References

Mair, P., & Hatzinger, R. (2007). Extended Rasch modeling: The eRm package for the application of IRT models in R. *Journal of Statistical Software, 20*(9), 1–20.

Model Context Protocol. (2026). *Model Context Protocol specification*. https://modelcontextprotocol.io/

National Council on Measurement in Education. (2026). *2027 NCME Annual Meeting call for proposals*. https://ncme.org/wp-content/uploads/2026/08/NCME_cfp_2027_final_r1.pdf

## Submission Check

- Title: no more than 12 words.
- Abstract: no more than 50 words.
- Demonstration summary: no more than 500 words.
- Proposal text is blinded.
- Deadline: September 13, 2026, 11:59 PM PDT.

