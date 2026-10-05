# OpenClaw Phoenix validation

**Stage A: PASS.** One new `diag_001`, budget-2 run; excluded from the measured study.

Experiment: [openclaw-phoenix-validation](http://127.0.0.1:6006/datasets/RGF0YXNldDoz/compare?experimentId=RXhwZXJpbWVudDoxMw==). Phoenix project: `Experiment-c5b845b49d053e279d95d959`.
Trace: [`defad300296f38df03a3a74539ab2fd0`](http://127.0.0.1:6006/projects/UHJvamVjdDoxNw==/traces/defad300296f38df03a3a74539ab2fd0); root span `a61ff2ffd6371596`.

## Gate read back from Phoenix

| Check | Result |
|---|---|
| phoenix ingestion works | PASS |
| correct tool count | PASS |
| no duplicate spans | PASS |
| token accounting trustworthy | PASS |
| latency accounting trustworthy | PASS |
| evidence ids preserved | PASS |
| exact model id preserved | PASS |
| runtime id preserved | PASS |
| blocked calls distinguishable | PASS |
| final diagnosis captured | PASS |
| no ground truth leakage | PASS |
| evaluator attachment works | PASS |

## Exact structure and accounting

8 spans: one CHAIN root, 4 LLM children, 2 executed TOOL children, and 1 blocked-request CHAIN child. Every child points to the same root. No native OpenClaw exporter ran.

Tokens: 1557 input + 133 output = 1690 total. Only LLM spans carry standard token attributes; the root carries none. The total equals the native OpenClaw result. One span per completed assistant response, not per streaming fragment.

Latency: 14.767s native run duration; 41.902s CLI wall time recorded separately. Root duration matches the former within 2ms. Tool durations are the Python recorder's invocation timings and exclude IPC. Model spans preserve hook timestamps and also store native model-call duration.

Spans are normalized after the actual run and exported via OTLP HTTP/protobuf, then fetched from Phoenix for semantic checks. Root boundaries are event-anchored using the native duration; this is transparent post-run normalization, not native OpenClaw distributed tracing. Exact intra-millisecond timing should not be inferred.

## Evaluations and finalization

All 11 existing rubric-v2 deterministic evaluations were attached both to the root span and to the experiment run, then fetched back and checked: diagnosis_correct, evidence_sufficient, evidence_completeness, premature_stop, tool_calls_used, redundant_investigation, irrelevant_calls, post_sufficiency_calls, identical_repeated_calls, token_usage, latency_seconds.

Ordered attempts: check_status(api) executed; check_recent_change(api) executed; check_status(frontend) BLOCKED.

Final diagnosis: `api_configuration_issue`; correct=True; sufficient=True; stop reason `stop`.

Tools remained visible after exhaustion. The third requested call returned a budget-exhausted observation; the final answer followed it. This differs from Microsoft’s tools-disabled finalization. A `finalization_semantics` annotation and root attributes preserve this distinction. Blocked spans are CHAIN, not TOOL, and have `executed=false`.

## Controls and evidence

Configured, internal, outbound and returned model: `gpt-4.1-mini-2025-04-14`; completed runtime `openclaw`. All submitted bodies were checked for three-tool isolation and absence of evaluation labels/project content. Ground truth was accessed for scoring only after inference. The original diagnostic prompt remains, plus OpenClaw’s model-identity line and timestamp prefix.

Machine evidence: [gate](results/openclaw-followup/stage-a-gate.json), [normalized run](results/openclaw-followup/runs/diag_001-b2-r1-ba378d4e.json), [Phoenix spans](results/openclaw-followup/traces/diag_001-b2-r1-ba378d4e.json), [fetched annotations](results/openclaw-followup/annotations/diag_001-b2-r1-ba378d4e.json), [outbound requests](results/openclaw-followup/requests/diag_001-b2-r1-ba378d4e.json).

Verification was programmatic through the Phoenix API; no screenshot is claimed. Local Phoenix links require the saved local database/server. The JSON/OTLP artifacts preserve the evidence independently of that UI.

## Scope of the pass

This PASS applies to the single saved Stage A trace and its non-recovery execution path. Stage B subsequently encountered internal connection-error recovery, an altered prompt and reused model-call IDs. Its first attempt was rejected before export, and the batch stopped. Stage A does not certify that recovery path; see [the study record](OPENCLAW_RESULTS.md).
