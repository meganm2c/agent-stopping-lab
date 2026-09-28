# Rubric version 2

The original live pilot report and JSONL scores remain unchanged. For comparisons,
rescore those saved outputs under this rubric; do not attribute rubric improvements
to tracing. Runtime observations, reports, tools, and the system prompt are unchanged.

- **diag_006:** canonical cause remains `api_dependency_issue`. Explicitly accept
  `api_configuration_issue` for this scenario only: the API's wrong cache port is
  both a dependency-routing problem and an API configuration error. There is no
  global alias between these categories. All other scenarios still require their
  canonical label unless they explicitly list alternatives.
- **diag_005:** move `api_logs` from required to supporting. Database logs establish
  failed new API connections with TLS handshake errors; the database change names
  the incompatible TLS versions. Together these establish the mechanism without
  needing a second report of API write failures.
- **diag_007:** move `database_logs` from required to supporting. Database status
  establishes available server capacity; API logs localize delay to acquiring a
  connection; the API pool change establishes the client-side limit. The database
  logs corroborate server health already observed through status.
- **diag_001–004, diag_006, diag_008:** reviewed with no evidence changes. Their
  declared sets retain incident impact, localization, or causal linkage. A plausible
  guess from fewer observations is not sufficient reason to weaken the rubric.

Diagnosis correctness, evidence completeness, and evidence sufficiency are scored
independently. Exact label matching (including explicit aliases) uses no LLM judge.
Difficulty labels retain their pilot provenance; moving confirmation evidence does
not imply a measured difficulty ranking. Required counts are now 1, 2, 2, 4, 2, 3,
4, 6. Alternate evidence paths remain a limitation to review before scaling.
