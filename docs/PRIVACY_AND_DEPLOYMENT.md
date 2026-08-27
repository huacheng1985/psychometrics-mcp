# Privacy and Deployment Boundary

The local stdio server is the recommended mode for real assessment data.
Response data is passed in memory to deterministic functions and the fixed R
adapter. This repository does not persist input data or send it to an LLM or a
remote analytics service.

Container users should mount only the narrow files they need, read-only. Do not
mount a home directory or shared research drive. Direct identifiers and
regulated student records should be removed or replaced before analysis.

A future hosted service is not authorized to accept sensitive data by default.
Before launch it requires authentication, quotas, documented retention and
deletion, encryption, incident response, auditability, abuse controls, and a
formal decision about FERPA/HIPAA/institutional agreements. Public demo data
must be synthetic or openly licensed.

