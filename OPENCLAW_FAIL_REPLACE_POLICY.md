# OpenClaw fail-and-replace policy validation

## Policy

A condition is `(scenario_id, tool budget, intended repetition)`. Every physical attempt has a new run ID, isolated state/workspace and session ID, and a monotonically increasing physical attempt index. The intended repetition does not change when an attempt fails.

**ACCEPT:** one internal attempt, no provider/runtime recovery, exact pinned model/runtime, reconciled requests/usage/tools, allowed effective context, valid JSON diagnosis, and all existing Phoenix/evaluation checks.

**FAILED ATTEMPT:** preserve any transport/provider/runtime error and exclude it from scientific metrics. Preserve its usage and latency separately. An unparseable final diagnosis is also rejected; it is a model-output contract failure, not an infrastructure error, and must not be silently replaced until it produces a valid answer.

**REPLACEMENT:** only under an explicit authorized replacement policy, create a fresh isolated physical attempt for the same condition. Keep the same model, tool schemas, prompt, environment, budget and retry configuration. Never resume the failed session. Keep every failed attempt in the audit ledger. A full study must report physical attempts and exclusions alongside its accepted sample; exclusions must not be used to conceal model failures.

## Retry setting and fallback controls

The official [retry documentation](https://docs.openclaw.ai/concepts/retry) identifies `retry.provider.maxRetries` as an embedded session setting. It is not an `openclaw.json` key and does not configure all native SDK request retries.

The pinned OpenClaw 2026.9.7 runtime reads `<isolated agent directory>/settings.json`. Each attempt writes:

```json
{"retry":{"provider":{"maxRetries":0}}}
```

Installed `SettingsManager` reads this global agent setting; `createPreparedEmbeddedAgentSettingsManager` builds the in-memory session settings; the built-in runtime passes `getProviderRetrySettings().maxRetries` to the recovery controller. The small `retry_observer.mjs` wrapper logs that getter's actual return value without changing it. All observed values were zero for both attempts. The observer uses a pinned internal export, so an OpenClaw upgrade requires revalidation.

Model fallback list is empty. Only OpenAI and the exact `gpt-4.1-mini-2025-04-14` model are configured, with runtime `openclaw` explicitly pinned. Each isolated state starts without auth-profile stores; only the designated OpenAI key is supplied through the child environment. The request guard rejects a different endpoint/model or tool configuration. Fresh state and absence of auth-profile files were checked for both attempts. No fallback or rerouting was observed. Unexpected additional model attempts remain rejection conditions even if a future runtime finds another retry path.

## Test scope and outcome

Only one injected transient HTTP 503 and one fresh replacement were attempted, both for `diag_007`, budget 6, intended repetition 1. The injected response was returned before forwarding to OpenAI. The guard would flag any unexpected extra request and prevent provider contact during injection; no extra request occurred.

**Retry suppression: PASS.** One failed model invocation, one intercepted HTTP attempt, zero forwarded provider requests, no continuation instruction, no tool execution, no fallback, and zero tokens. The runtime terminated the attempt without recovery. Zero usage is established by injection placement, not inferred from a generic error response.

**Fresh-session replacement controls: PASS.** Different session/workspace/run IDs; identical fixture and scientific configuration after excluding the necessary workspace path difference; identical retry settings. No recovery occurred.

**End-to-end accepted replacement: FAIL.** The clean replacement returned YAML-like `predicted_root_cause: ...`, `explanation: ...`, and `evidence_used: ...` fields, instead of the required JSON object. Its apparent diagnosis was `database_connection_regression`, but it was not parsed/repaired or scored as a valid answer. It remains rejected. No third physical attempt was authorized or run.

| Accounting | Physical attempt 1: injected failure | Physical attempt 2: replacement |
|---|---:|---:|
| Intended repetition | 1 | 1 |
| Internal attempts | 1 | 1 |
| Model invocations | 1 | 7 |
| Observed HTTP attempts | 1 | 7 |
| Forwarded provider requests | 0 | 7 |
| Executed diagnostic calls | 0 | 6 |
| Blocked diagnostic calls | 0 | 0 |
| Input tokens | 0 | 3,315 |
| Output tokens | 0 | 179 |
| Total tokens | 0 | 3,494 |
| Accepted | No: injected infrastructure failure | No: invalid JSON diagnosis |

Failed run: `diag_007-b6-r1-54be77ad`; trace `7763d08a505a085685046b62cf168489`. The failure has a CHAIN root and one LLM child, both ERROR, and an explicit rejection annotation. It is recorded as an experiment error, outside accepted metrics.

Replacement run: `diag_007-b6-r1-24ffcdc8`. Its seven completed model responses reconcile exactly to 3,494 tokens. Canonical invocation identities, HTTP receipts, prompt hashes, and execution order are preserved. The final contract failure is distinct from transport recovery.

## Recommendation

**NOT READY FOR 20-RUN STUDY.** The tested recovery behavior is controlled, but the authorized replacement failed the existing final-output contract. Do not relax JSON validation, rewrite the saved response, or hide model-output failures through automatic replacement. Resolve final-output enforcement separately before another measured batch.

This test establishes the no-recovery behavior for one injected 503. It does not claim exhaustive coverage of DNS, streaming interruption, auth exhaustion, compaction, or every SDK retry path. All such errors remain subject to fail-closed accounting.

Evidence is in `results/openclaw-fail-replace/`: settings observations and canonical ledgers under `accounting/`, outbound requests under `requests/`, raw local state under the ignored spike directory, and policy/trace records. Historical results, README and demo remain unchanged. No adaptive stopping or full study was run.

## Phoenix records and final checks

Experiment: `openclaw-fail-replace-policy`.

Replacement trace: `b55c806340d1483d162045ea0becf7ed` (14 spans: one CHAIN root, seven LLM spans and six TOOL spans). Its root has an explicit `REJECTED_FINAL_CONTRACT` acceptance annotation, and its experiment run is recorded with an error. The first export occurred before the final-diagnosis assertion failed; Phoenix retained those original span statuses on re-export. The rejection annotation and failed experiment record are authoritative for acceptance. No duplicate model spans were created to correct the status. The publisher now rejects invalid final results before exporting an accepted-run trace.

Summary: **0 accepted physical attempts, 2 rejected**, with intended repetition 1 still unfilled. Retry suppression and fresh-session policy checks passed; successful replacement validation did not. [Machine-readable policy summary](results/openclaw-fail-replace/policy-summary.json).

58 Python tests and all four original OpenClaw Node tests passed. The injected-failure guard test confirms no provider forwarding. All 332 historical preservation hashes remained unchanged. Secret-pattern scanning found no suspected keys in new code/results. Nothing was pushed, and the existing full-study failure marker remains in place.
