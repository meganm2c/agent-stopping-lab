# OpenClaw fixed-budget follow-up

**20 accepted runs completed across 21 physical attempts.** Failed attempts: 0; user-interrupted attempts: 1; replacements launched: 1. Adaptive stopping excluded.

## Design and controls

Two scenarios (`diag_007`, `diag_008`) × budgets 6/8 × five intended repetitions. OpenClaw 2026.9.7, exact `gpt-4.1-mini-2025-04-14`, temperature 0, serial diagnostic tools. Fresh isolated state/session/workspace; original diagnostic instruction, report, three tool definitions, deterministic Python environment and rubric. Provider recovery budget zero, empty fallback chain, outbound guards and canonical invocation accounting. No execution/finalization contract changed during this study; file hashes are in the manifest.

Every run uses the validated evidence-only, tools-disabled finalizer through the pinned OpenClaw isolated runtime. It receives no prior loop answer or evaluation labels. Final JSON is validated strictly with the existing Diagnosis schema and observed-only evidence citations; no response repair. Exactly one finalizer call per accepted physical attempt.

Serial order: budget 6, then budget 8; diag_007, then diag_008; repetitions 1–5. This is a small fixed-scenario descriptive follow-up, not a randomized harness comparison. All smoke tests, original rejected attempts and finalizer validation runs are excluded.

## Aggregate results

| Budget | N | Accuracy | Completeness | Sufficient | Premature stop | Avg executed calls |
|---|---:|---:|---:|---:|---:|---:|
| 6 | 10 | 100% | 73.3% | 10% | 90% | 6.00 |
| 8 | 10 | 90% | 96.7% | 90% | 10% | 7.00 |

**Accepted means protocol-valid, not necessarily correct.** The incorrect final diagnosis is retained in the accuracy denominator; it was not replaced.

diag_007, budget 8, repetition 5: final label `api_configuration_issue`, with 100% evidence completeness. [Trace `199b9e00b809344ad0ad62477e09843a`](http://127.0.0.1:6006/projects/UHJvamVjdDoyMw==/traces/199b9e00b809344ad0ad62477e09843a).


Premature stop uses the unchanged rubric definition: required evidence is incomplete. It includes forced budget exhaustion and is not a claim that every such stop was voluntary.

| Budget | Diagnostic tokens | Finalizer tokens | Total tokens | Diagnostic s | Finalization s | Trace total s | Full wall s |
|---|---:|---:|---:|---:|---:|---:|---:|
| 6 | 3977.9 | 754.8 | 4732.7 | 18.634 | 16.093 | 34.727 | 65.537 |
| 8 | 4224.2 | 829.0 | 5053.2 | 16.842 | 13.617 | 30.459 | 56.330 |

All cost columns are means over accepted runs. Diagnostic tokens include the loop’s intermediate answer; finalizer cost is additional and separately counted. Finalization phase time includes setup after the diagnostic event boundary; total trace duration is diagnostic native duration plus that phase. Full wall time additionally includes CLI startup/shutdown. No direct cross-harness latency superiority is claimed. Failed attempts are excluded from these scientific means and retained separately.

## Repeatability

| Scenario / budget | Stable diagnosis | Ordered paths | Evidence sets | Sufficiency varies | Tool counts | Token range | Trace seconds range |
|---|---|---:|---:|---|---|---|---|
| diag_007/budget-6 | True | 2 | 2 | True | [6] | 4217–4950 | 30.092–37.571 |
| diag_008/budget-6 | True | 2 | 2 | False | [6] | 4204–5001 | 30.596–41.150 |
| diag_007/budget-8 | False | 2 | 2 | False | [6, 7] | 4192–5047 | 27.241–28.914 |
| diag_008/budget-8 | True | 2 | 2 | True | [6, 8] | 4216–5905 | 29.905–34.640 |

Of four scenario/budget groups: **3** had stable diagnosis labels, **4** had varying ordered trajectories, **2** had a same-label pair with different evidence sufficiency, and **3** contained correct-but-insufficient runs (10/20 runs). Stable labels and varying paths coexisted throughout 3/4 groups.

Computed directly from saved ordered executed calls: trajectory signature is `(tool_name, component)` in invocation order; evidence-set signature is sorted unique retrieved IDs; diagnosis stability compares exact final labels. Blocked calls are excluded from trajectory/execution counts and reported separately. Token/latency ranges above show their variation; five repetitions do not establish deterministic behavior.

## Trace exemplars

### A. Same scenario, budget and diagnosis; different trajectory

**diag_008, budget 8, repetition 1, physical attempt 1** — [trace `1d469ed64ab9c1a6295ca6d04368175b`](http://127.0.0.1:6006/projects/UHJvamVjdDoyMw==/traces/1d469ed64ab9c1a6295ca6d04368175b).

- Diagnosis: `cache_configuration_regression`; correct=True.
- Exact path: check_status(frontend) → check_status(api) → check_status(database) → check_status(cache) → read_logs(frontend) → read_logs(api) → read_logs(cache) → check_recent_change(cache).
- Evidence set: api_logs, api_status, cache_change, cache_logs, cache_status, database_status, frontend_logs, frontend_status.
- Completeness: 100.0%; sufficient=True; missing: none.
- Tokens: 4961 diagnostic + 924 finalizer = 5885 total.
- Latency: 17.340s diagnostic + 15.738s finalization phase = 33.078s trace; 56.977s full wall time.
- Executed calls: 8; blocked requests: 0.

**diag_008, budget 8, repetition 3, physical attempt 1** — [trace `abc189c7ef7b27b34851d00c328eda85`](http://127.0.0.1:6006/projects/UHJvamVjdDoyMw==/traces/abc189c7ef7b27b34851d00c328eda85).

- Diagnosis: `cache_configuration_regression`; correct=True.
- Exact path: check_status(frontend) → check_status(api) → check_status(database) → check_status(cache) → read_logs(cache) → check_recent_change(cache).
- Evidence set: api_status, cache_change, cache_logs, cache_status, database_status, frontend_status.
- Completeness: 66.7%; sufficient=False; missing: api_logs, frontend_logs.
- Tokens: 3472 diagnostic + 744 finalizer = 4216 total.
- Latency: 20.177s diagnostic + 14.124s finalization phase = 34.301s trace; 66.712s full wall time.
- Executed calls: 6; blocked requests: 0.

Pair selected within one exact scenario/budget group, prioritizing a sufficiency difference and correct diagnoses.

### B. Correct diagnosis with insufficient evidence

**diag_008, budget 8, repetition 3, physical attempt 1** — [trace `abc189c7ef7b27b34851d00c328eda85`](http://127.0.0.1:6006/projects/UHJvamVjdDoyMw==/traces/abc189c7ef7b27b34851d00c328eda85).

- Diagnosis: `cache_configuration_regression`; correct=True.
- Exact path: check_status(frontend) → check_status(api) → check_status(database) → check_status(cache) → read_logs(cache) → check_recent_change(cache).
- Evidence set: api_status, cache_change, cache_logs, cache_status, database_status, frontend_status.
- Completeness: 66.7%; sufficient=False; missing: api_logs, frontend_logs.
- Tokens: 3472 diagnostic + 744 finalizer = 4216 total.
- Latency: 20.177s diagnostic + 14.124s finalization phase = 34.301s trace; 66.712s full wall time.
- Executed calls: 6; blocked requests: 0.

### C. Budget 6 versus 8: additional discriminating evidence

**diag_008, budget 6, repetition 1, physical attempt 1** — [trace `d844fa49a87054cf06c58b1d5d584b17`](http://127.0.0.1:6006/projects/UHJvamVjdDoyMg==/traces/d844fa49a87054cf06c58b1d5d584b17).

- Diagnosis: `cache_configuration_regression`; correct=True.
- Exact path: check_status(frontend) → check_status(api) → check_status(database) → check_status(cache) → read_logs(frontend) → read_logs(api).
- Evidence set: api_logs, api_status, cache_status, database_status, frontend_logs, frontend_status.
- Completeness: 66.7%; sufficient=False; missing: cache_change, cache_logs.
- Tokens: 4179 diagnostic + 786 finalizer = 4965 total.
- Latency: 22.238s diagnostic + 16.919s finalization phase = 39.157s trace; 66.559s full wall time.
- Executed calls: 6; blocked requests: 1.

**diag_008, budget 8, repetition 1, physical attempt 1** — [trace `1d469ed64ab9c1a6295ca6d04368175b`](http://127.0.0.1:6006/projects/UHJvamVjdDoyMw==/traces/1d469ed64ab9c1a6295ca6d04368175b).

- Diagnosis: `cache_configuration_regression`; correct=True.
- Exact path: check_status(frontend) → check_status(api) → check_status(database) → check_status(cache) → read_logs(frontend) → read_logs(api) → read_logs(cache) → check_recent_change(cache).
- Evidence set: api_logs, api_status, cache_change, cache_logs, cache_status, database_status, frontend_logs, frontend_status.
- Completeness: 100.0%; sufficient=True; missing: none.
- Tokens: 4961 diagnostic + 924 finalizer = 5885 total.
- Latency: 17.340s diagnostic + 15.738s finalization phase = 33.078s trace; 56.977s full wall time.
- Executed calls: 8; blocked requests: 0.

This compares independent repetitions across budgets, not a replayed counterfactual.

## Scenario-specific checks

The specific Microsoft `diag_007` budget-6 branch (`check_recent_change(api)` versus `read_logs(database)`, same correct diagnosis but different sufficiency) **did not recur**. This was verified from raw trajectories, not inferred from aggregate accuracy.

| Scenario / discriminating evidence | Budget 6 retrieval | Budget 8 retrieval |
|---|---:|---:|
| diag_007: api_status | 5/5 | 5/5 |
| diag_007: api_logs | 5/5 | 5/5 |
| diag_007: database_status | 5/5 | 5/5 |
| diag_007: api_change | 1/5 | 5/5 |
| diag_008: frontend_logs | 3/5 | 4/5 |
| diag_008: api_logs | 3/5 | 4/5 |
| diag_008: database_status | 5/5 | 5/5 |
| diag_008: cache_status | 5/5 | 5/5 |
| diag_008: cache_logs | 2/5 | 5/5 |
| diag_008: cache_change | 2/5 | 5/5 |

## Phoenix and finalization

Blocked diagnostic requests: 7 across 7/20 runs. These are never counted as executed tools. Diagnostic tools remain visible until the loop ends; only the explicit finalizer is tools-disabled. All accepted final stop reasons are `adapter_finalization`.

Each accepted trace contains one root, diagnostic model/tool spans, any blocked-request CHAIN spans, and exactly one model span with `phase=finalization`, `tools_enabled=false`, `finalization_adapter=true`. Only model spans carry standard token attributes. Every accepted trace passed the 12 readback gates, and all 11 deterministic evaluations were attached and verified at root/experiment level.

Experiments: `openclaw-repeatability-budget-6-finalized-v1` and `openclaw-repeatability-budget-8-finalized-v1`, on a separate dataset. The suffix distinguishes this validated finalizer study from the earlier halted experiment.

## Failures and saved evidence

Physical attempts: 21; failed: 0; user-interrupted: 1; replacement attempts: 1. Intended repetition and physical attempt indices are distinct in the manifest and per-run records. No failed native session was resumed.

The user-interrupted physical attempt was preserved separately. No model/tool events or request capture were saved for that interrupted attempt; its cost is not assumed to be zero. It is excluded from accepted-run means. The subsequent replacement used new isolated state and a new run ID.

| Condition | Attempt | Run ID | Failure kind |
|---|---:|---|---|
| diag_008/budget-8/repetition-4 | 1 | diag_008-b8-r4-6e684718 | user interruption |

[Summary](results/openclaw-followup/study-v1/summary.json), [20 accepted rows](results/openclaw-followup/study-v1/runs.jsonl), [manifest and physical-attempt ledger](results/openclaw-followup/study-v1/manifest.json), [trace exemplars](results/openclaw-followup/study-v1/exemplars.json). Per-run diagnostic artifacts, finalizer inputs/outputs, requests, OTLP bytes, fetched spans and annotations are in the same directory. Full native local state remains in the ignored spike directory. Results follow the repository’s existing ignore policy and must be included explicitly when packaging.

The validated adapter files were used unchanged. The new runner is `spikes/openclaw-followup/run_validated_study.py`; it resumes saved publication work without silently rerunning inference. Analysis is `spikes/openclaw-followup/analyze_validated_study.py` and performs no model calls. Do not use the older pre-finalization analyzer to regenerate these reports.

All four prerequisite validation reports remain unchanged. Earlier OpenClaw result/comparison drafts are archived under `study-v1/prior_reports/`. Historical Microsoft results/reports, README and demo were preserved. See [cross-harness interpretation](OPENCLAW_COMPARISON.md).

## Completion verification

[Independent verification](results/openclaw-followup/study-v1/verification.json) confirms exactly five accepted repetitions in every scenario/budget cell, 20 unique intended slots, and 220 verified evaluator results at each of the root-span and experiment levels. Native diagnostic usage reconciled for all 20 runs; accepted diagnostic-plus-finalizer usage totals 97,859 tokens. All 18 previously accepted records and the interrupted attempt remained byte-for-byte unchanged. All configured model fallbacks were empty and isolated auth-profile stores were absent.

75 Python tests and all four original OpenClaw Node contract tests passed. The four analysis tests passed again after report updates. Preserved historical files and all four prerequisite reports remained unchanged. Local report links were checked; no suspected credential values were found in new code/results. Inference stopped after the two missing intended slots were accepted. No adaptive experiment was started.
