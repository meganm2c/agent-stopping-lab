# OpenClaw recovery/accounting validation

**Recommendation: NOT READY for the 20-run study.** All three authorized validation repetitions passed, but none exercised live recovery. Internal recovery can still introduce semantic prompt drift, which the validator rejects rather than normalizes away. No adaptive stopping or full study was run.

## Original rejection: root cause and boundaries of knowledge

Saved attempt: `diag_007-b6-r1-09e575d0`. The first native model attempt failed with `ENOTFOUND` / `Connection error.` after 30.713 seconds, before message streaming (`eventsEmitted=false`). The failure was in provider transport, before any diagnostic tool execution. The saved diagnostic does not name the failed DNS hostname or expose individual socket/SDK retries. The configured provider was OpenAI; claiming a particular DNS resolver or hostname failed would exceed the evidence.

OpenClaw then continued the same run/session from its transcript. Both startup histories were empty. It kept the model snapshot but placed the original incident under a queued-message marker and appended a continuation instruction directing the agent to preserve work and inspect interrupted actions. This changes semantics; it is not merely a timestamp.

The reused native ID was `5bf95d21-ef98-4b91-bc24-c3271a5deffc:model:1`. Native trace IDs changed from `36d95d747f394ace65641f5b4f896b5c` to `aba602854adf53d1b70fe48505a7478a`. Eight model start/end pairs were observed, but the old capture contains only seven request bodies without timestamps or HTTP receipts. Seven successful model responses followed recovery. The recovered provider inference was therefore attempted again, with a changed context; an identical HTTP request retry or its exact lower-level retry count cannot be established from that old capture.

The failed assistant reports zero usage, but that alone does not prove provider-side zero billing. Counting only the final transcript would omit the failed attempt and could omit its usage; deduplicating by native model-call ID could discard the first successful response. Six canonical tool executions were observed after recovery, with no evidence of duplicate execution. They are not promoted into an accepted measured result.

Installed runtime source: `embedded-agent-LPBaSeZ4.mjs` emits `run_status` retry information (`retryAttempt`, reason, delay and maximum attempts), then calls `continueFromCurrentTranscript` after a transient-retry decision. Its internal `retryConnectionErrors` parameter can reject connection retries, but no supported setting exposed by this spike's CLI configuration was established. `context-engine-maintenance-BmtwKjvy.mjs` supplies the queued-message marker. No runtime patch was made.

## Available identifiers and new ledger

| Signal | Availability / use |
|---|---|
| Native run/session IDs | Captured from model hooks; can span recovery |
| Native model-call ID | Retained for diagnosis; not a unique key |
| Internal attempt index | Derived from ordered `before_agent_run` events |
| Invocation ordinal | Monotonic in the saved event stream, including failed invocations |
| HTTP request ordinal | Recorded before each guarded fetch, with timestamp |
| Provider request ID | Allowlisted `x-request-id` response header; captured for all 24 successful invocations in the mini-batch |
| Provider response ID | Assistant `responseId` retained separately from HTTP request ID |
| Retry metadata | Runtime source exposes retry status; the plugin ledger derives attempt boundaries and preserves model outcomes/errors, without claiming all status events were subscribed |

Canonical identity is **native run ID + internal attempt index + global invocation ordinal**. Each HTTP request has a subordinate ordinal identity. Provider IDs are attributes, not required identity components, because failures may have none. Canonical IDs remain unique even when the native call ID repeats. No failed attempt is collapsed into its successful successor.

The transport observer preserves outbound bodies and records only status, request ID, timestamp and error name/code. It does not record credentials, authorization headers, or consume/modify response streams.

## Acceptance policy and prompt drift

The ledger pairs serial start/end boundaries, assigns timestamped HTTP attempts and assistant usage once, reconciles canonical tool order against assistant tool requests, and rejects missing, overlapping, conflicting or multiply attributed records. Successful token totals must also reconcile against the native result through the existing normalizer. The Phoenix readback verifies canonical identities and complete ledger attributes on model spans.

For every observed HTTP invocation, the ledger stores:

- effective system/user context hash;
- semantic context hash after removing only the recognized leading timestamp format;
- full message-history hash, which may legitimately change as tool observations accumulate.

The semantic context must exactly equal the original diagnostic system instruction plus the already documented model-identity line, and the original incident report. Continuation instructions, altered system text or additional user instructions reject the run. Missing HTTP evidence yields an explicit accounting error, never a fabricated prompt hash. The legacy rejected run also has per-attempt hook prompt hashes saved separately.

Multiple HTTP attempts within one model invocation are preserved but rejected until their individual usage can be established. Error outcomes are rejected rather than assumed to consume zero tokens. This is observable, fail-closed recovery handling; it is not acceptance of arbitrary retries. Live semantic drift is detected after execution, so a rejected run can still incur provider cost.

## Three-run mini-batch

All runs: `diag_007`, budget 6, exact model `gpt-4.1-mini-2025-04-14`, runtime `openclaw`, temperature 0, no parallel tools, fresh isolated state. Separate Phoenix experiment: `openclaw-recovery-validation-budget-6`. These are validation runs, not part of the 20-run study.

| Repetition | Decision | Tokens | Trace ID |
|---|---|---:|---|
| 1 | ACCEPT | 4,187 | `e56cc2aaf88ffe2e4b5fa02172f552d2` |
| 2 | ACCEPT | 4,190 | `29de26d241a11fc8e29374db4342b3ee` |
| 3 | ACCEPT | 4,184 | `97c5ca3d2c6a97f30b8290580312137e` |

**Accepted 3; rejected 0.** Each had one internal attempt, eight model invocations and eight matched HTTP receipts. No recovery occurred. All 11 existing deterministic evaluations attached and were read back, alongside the trace validation checks. The original rejected attempt remains rejected and is outside these counts.

Machine evidence: [summary with clickable trace URLs](results/openclaw-recovery-validation/summary.json), [original rejection audit](results/openclaw-recovery-validation/original-rejection-audit.json), and per-run `accounting/`, `requests/`, `runs/`, `traces/` and `annotations/` under `results/openclaw-recovery-validation/`. Results retain the existing ignored-directory policy.

## Remaining blocker and next step

Model identity accounting is now robust to reused native IDs. Successful-run token attribution is verified; failed/ambiguous retry usage remains explicitly untrusted. Prompt invariants are enforced, but semantic-changing runtime recovery is not controlled or accepted. Three clean runs do not demonstrate a safe recovered run.

Before a full study, establish a supported no-continuation retry control, or explicitly design a failure/replacement policy and validate it with an injected transport failure. Keep all rejected attempts and their costs in that protocol. Do not remove the full-study failure marker or silently replace rejected runs. Historical Microsoft results, README and demo were not modified.

## Verification

56 Python tests passed (41 existing plus 15 follow-up/recovery tests), along with all four original OpenClaw Node contract tests. Tests cover reused IDs, missing requests, multiple HTTP attempts, prompt drift, failed usage and credential-free transport receipts. All three saved Phoenix traces were revalidated against the final validator: 16 spans each. All 332 historical preservation hashes remained unchanged; the new-code/result secret-pattern scan found no suspected keys.
