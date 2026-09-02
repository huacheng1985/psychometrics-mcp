# Architecture

Psychometrics MCP is a measurement-centered analytical environment, not an
arbitrary R execution server and not only a Rasch wrapper.

The current local-first vertical slice has four boundaries:

1. MCP schemas accept only explicitly modeled fields.
2. Deterministic Python functions perform inspection, descriptive statistics,
   correlation, CTT, and planning.
3. A fixed R adapter invokes only `eRm::RM`; user-provided R and shell code are
   never accepted.
4. Results carry a schema version and return applicable sample flow, methods,
   package versions, warnings, and explicit interpretation limits.

The default transport is stdio. This keeps assessment data on the user's
machine and lets the MCP host own model access. A future hosted Streamable HTTP
service should be a separate deployment profile with authentication, quotas,
short retention, audit logging, and strict data-classification controls.

Cloudflare may provide DNS, TLS, access control, and rate limiting. The Python
and R computation layer belongs in a container runtime that supports longer
statistical jobs; it should not be implemented as arbitrary code in an edge
worker.
