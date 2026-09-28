# Adaptive stopping results

The final comparison uses the unchanged eight-example Phoenix dataset, three runs per example and configuration: 72 agent runs with deterministic post-run evaluations. The 50-run targeted study is reported separately in [TRAJECTORY_VARIATION.md](TRAJECTORY_VARIATION.md). The single policy was frozen before these runs; it was not tuned against the outcomes.

[Phoenix comparison](http://localhost:6006/datasets/RGF0YXNldDox/compare?experimentId=RXhwZXJpbWVudDoxMA==&experimentId=RXhwZXJpbWVudDoxMQ==&experimentId=RXhwZXJpbWVudDoxMg==) — use **Metrics** and **List**. The Phase 2 Grid view was blank; no cosmetic debugging was required.

## Aggregate comparison

| Metric | fixed-budget-6 | fixed-budget-8 | adaptive-stopping |
|---|---:|---:|---:|
| Diagnosis accuracy | 87.5% | 100.0% | 79.2% |
| Evidence completeness | 83.3% | 97.9% | 70.1% |
| Evidence sufficiency | 54.2% | 91.7% | 33.3% |
| Premature-stop rate | 45.8% | 8.3% | 66.7% |
| Average tool calls | 4.96 | 5.79 | 3.92 |
| Post-sufficiency calls | 0.46 | 0.54 | 0.00 |
| Irrelevant calls | 2.46 | 2.71 | 1.67 |
| End-to-end seconds | 4.31 | 4.85 | 7.20 |
| Agent tokens | 3046.58 | 3698.38 | 2435.75 |
| Stopper tokens | 0.00 | 0.00 | 1646.83 |
| Total tokens | 3046.58 | 3698.38 | 4082.58 |
| Stopper seconds | 0.00 | 0.00 | 3.61 |

Each mean uses all 24 runs in that configuration. Agent tokens exclude stopping requests; total tokens include them. Latency covers the complete agent execution, including all checks and the final answer.

### Stop reasons

- `fixed-budget-6`: {'tool_budget': 15, 'agent_answered': 9}
- `fixed-budget-8`: {'tool_budget': 7, 'agent_answered': 17}
- `adaptive-stopping`: {'adaptive_stop': 24}

## Adaptive outcomes

- Effective stop rate: 100.0% (24/24).
- False early-stop rate: 66.7% (16/24).
- False early-stop rate among effective stops: 66.7%.
- Mean call index among effective stops: 3.92.
- Mean ceiling slack (`8 - calls`): 4.08; this is not a counterfactual saving.
- Actual mean call saving vs fixed-8: 1.88 (32.4%).
- Actual mean total-token saving vs fixed-8: -384.21 (-10.4%); negative means added cost.
- Actual mean latency saving vs fixed-8: -2.36 seconds (-48.7%); negative means slower.
- Stopper errors: 0.

These are differences of observed configuration means. Repetition indices do not create identical counterfactual trajectories, and serial configuration order/network conditions limit interpretation of latency differences.

## Preregistered criteria

| Criterion | Observed result | Passed |
|---|---|---|
| Accuracy within one correct run of fixed-8 | 79.2% vs 100.0% | False |
| At least 10% fewer calls | 32.4% | True |
| At least 5% lower total tokens or latency | tokens -10.4%; latency -48.7% | False |
| At most one false early stop | 16 | False |
| No execution/parse failures or budget violations | Verified runs; stopper errors 0 | True |

**Hypothesis supported:** False. No threshold or prompt was changed after results.

## Per-scenario comparison

| Scenario | Strategy | Correct / 3 | Completeness | Calls | Agent tokens | Stopper tokens | Seconds |
|---|---|---:|---:|---:|---:|---:|---:|
| diag_001 | fixed-budget-6 | 3 | 100.0% | 2.67 | 1614 | 0 | 2.97 |
| diag_001 | fixed-budget-8 | 3 | 100.0% | 2.33 | 1452 | 0 | 2.44 |
| diag_001 | adaptive-stopping | 3 | 100.0% | 1.00 | 789 | 293 | 2.66 |
| diag_002 | fixed-budget-6 | 3 | 100.0% | 3.00 | 1798 | 0 | 3.19 |
| diag_002 | fixed-budget-8 | 3 | 100.0% | 3.00 | 1798 | 0 | 2.82 |
| diag_002 | adaptive-stopping | 3 | 50.0% | 2.00 | 1271 | 635 | 4.16 |
| diag_003 | fixed-budget-6 | 3 | 100.0% | 6.00 | 3711 | 0 | 4.78 |
| diag_003 | fixed-budget-8 | 3 | 100.0% | 7.00 | 4486 | 0 | 5.53 |
| diag_003 | adaptive-stopping | 3 | 50.0% | 3.00 | 1754 | 1035 | 5.72 |
| diag_004 | fixed-budget-6 | 0 | 50.0% | 6.00 | 3734 | 0 | 4.87 |
| diag_004 | fixed-budget-8 | 3 | 83.3% | 8.00 | 5282 | 0 | 6.45 |
| diag_004 | adaptive-stopping | 0 | 33.3% | 2.33 | 1455 | 798 | 4.43 |
| diag_005 | fixed-budget-6 | 3 | 100.0% | 4.00 | 2356 | 0 | 3.76 |
| diag_005 | fixed-budget-8 | 3 | 100.0% | 4.67 | 2789 | 0 | 3.85 |
| diag_005 | adaptive-stopping | 3 | 100.0% | 5.00 | 2998 | 2098 | 8.92 |
| diag_006 | fixed-budget-6 | 3 | 66.7% | 6.00 | 3651 | 0 | 4.85 |
| diag_006 | fixed-budget-8 | 3 | 100.0% | 7.00 | 4405 | 0 | 6.00 |
| diag_006 | adaptive-stopping | 1 | 77.8% | 5.67 | 3450 | 2517 | 9.94 |
| diag_007 | fixed-budget-6 | 3 | 83.3% | 6.00 | 3752 | 0 | 5.04 |
| diag_007 | fixed-budget-8 | 3 | 100.0% | 6.33 | 4009 | 0 | 4.88 |
| diag_007 | adaptive-stopping | 3 | 83.3% | 6.33 | 4008 | 3026 | 11.67 |
| diag_008 | fixed-budget-6 | 3 | 66.7% | 6.00 | 3756 | 0 | 5.06 |
| diag_008 | fixed-budget-8 | 3 | 100.0% | 8.00 | 5366 | 0 | 6.79 |
| diag_008 | adaptive-stopping | 3 | 66.7% | 6.00 | 3760 | 2772 | 10.15 |

## Demo traces

### Fixed-6 premature stop

[diag_004, repetition 3](http://localhost:6006/projects/UHJvamVjdDoxNA==/traces/4e99700a30d1dfba4ebf0fab79de23ad) — `api_dependency_issue`, correct=False, sufficiency=False, stop=`tool_budget`.

| Step | Tool | Observed output | Stopping decision |
|---:|---|---|---|
| 1 | check_status(frontend) | {"component": "frontend", "status": "healthy", "detail": "CPU is 58% versus usual 50%; rendering latency remains normal.", "evidence_id": "frontend_status"} | — |
| 2 | check_status(api) | {"component": "api", "status": "degraded", "detail": "Read latency is 1.8 seconds; time is spent on repeated backend reads.", "evidence_id": "api_status"} | — |
| 3 | check_status(database) | {"component": "database", "status": "healthy", "detail": "Availability and latency are within baseline.", "evidence_id": "database_status"} | — |
| 4 | check_status(cache) | {"component": "cache", "status": "healthy", "detail": "Availability and latency are within baseline.", "evidence_id": "cache_status"} | — |
| 5 | read_logs(api) | {"component": "api", "log_summary": "No errors or unusual traffic in the incident window.", "evidence_id": "api_logs"} | — |
| 6 | check_recent_change(api) | {"component": "api", "changed": false, "description": "No configuration or deployment changes in the incident window.", "evidence_id": "api_change"} | — |

Missing required evidence after execution: cache_change, cache_logs. Post-sufficiency calls: 0. Agent explanation: The API is experiencing degraded performance with high read latency due to repeated backend reads, while the database and cache are healthy and show no signs of saturation or issues. There are no recent changes in the API configuration or deployment, and logs show no errors or unusual traffic. This suggests the root cause is likely an issue with an external dependency the API relies on, causing slow responses.

### Fixed-8 successful but inefficient

[diag_003, repetition 1](http://localhost:6006/projects/UHJvamVjdDoxNQ==/traces/361c347abe399281c863be871a56d5a0) — `database_saturation`, correct=True, sufficiency=True, stop=`tool_budget`.

| Step | Tool | Observed output | Stopping decision |
|---:|---|---|---|
| 1 | check_status(frontend) | {"component": "frontend", "status": "healthy", "detail": "Availability and latency are within baseline.", "evidence_id": "frontend_status"} | — |
| 2 | check_status(api) | {"component": "api", "status": "healthy", "detail": "Availability and latency are within baseline.", "evidence_id": "api_status"} | — |
| 3 | check_status(database) | {"component": "database", "status": "degraded", "detail": "CPU is 100%; active queries are 240 against capacity of 40.", "evidence_id": "database_status"} | — |
| 4 | read_logs(database) | {"component": "database", "log_summary": "Query execution queues are growing; CPU time is dominated by full-table scans, with no connection or lock errors.", "evidence_id": "database_logs"} | — |
| 5 | check_recent_change(database) | {"component": "database", "changed": false, "description": "No configuration or deployment changes in the incident window.", "evidence_id": "database_change"} | — |
| 6 | check_status(cache) | {"component": "cache", "status": "healthy", "detail": "Availability and latency are within baseline.", "evidence_id": "cache_status"} | — |
| 7 | check_recent_change(api) | {"component": "api", "changed": false, "description": "No configuration or deployment changes in the incident window.", "evidence_id": "api_change"} | — |
| 8 | check_recent_change(frontend) | {"component": "frontend", "changed": false, "description": "No configuration or deployment changes in the incident window.", "evidence_id": "frontend_change"} | — |

Missing required evidence after execution: none. Post-sufficiency calls: 4. Agent explanation: The database is saturated with CPU at 100% and active queries far exceeding capacity, causing delays in query execution and slow appearance of saved records in search. There are no recent changes in database configuration or deployment, and other components are healthy, indicating the root cause is database saturation.

### Adaptive supported early stop

[diag_001, repetition 3](http://localhost:6006/projects/UHJvamVjdDoxNg==/traces/3f35a3762237ca33283dbc9048ef64a6) — `api_configuration_issue`, correct=True, sufficiency=True, stop=`adaptive_stop`.

| Step | Tool | Observed output | Stopping decision |
|---:|---|---|---|
| 1 | check_status(api) | {"component": "api", "status": "unavailable", "detail": "Startup validation failed: configured request limit is zero; all requests are rejected.", "evidence_id": "api_status"} | STOP: The API component is confirmed unavailable due to a configuration error where the request limit is set to zero, causing all requests to be rejected. This explains the user report fully, so further investigation is unlikely to add value. |

Missing required evidence after execution: none. Post-sufficiency calls: 0. Agent explanation: The API is rejecting all requests because its startup validation failed due to a configured request limit set to zero, causing all requests to be rejected.

### Adaptive failure or edge case

[diag_004, repetition 3](http://localhost:6006/projects/UHJvamVjdDoxNg==/traces/36feb4505b0fbe1b65eb5cfa51ca14a5) — `database_saturation`, correct=False, sufficiency=False, stop=`adaptive_stop`.

| Step | Tool | Observed output | Stopping decision |
|---:|---|---|---|
| 1 | check_status(frontend) | {"component": "frontend", "status": "healthy", "detail": "CPU is 58% versus usual 50%; rendering latency remains normal.", "evidence_id": "frontend_status"} | CONTINUE: The frontend component is healthy with only a slight increase in CPU usage and normal rendering latency, which does not fully explain the reported slowness. Further investigation is needed to check other components or system metrics to identify the cause of the performance issue. |
| 2 | check_status(api) | {"component": "api", "status": "degraded", "detail": "Read latency is 1.8 seconds; time is spent on repeated backend reads.", "evidence_id": "api_status"} | STOP: The frontend is healthy with normal rendering latency, but the API is degraded due to high read latency caused by repeated backend reads. This explains the application's slowness reported by users, providing a coherent diagnosis. |

Missing required evidence after execution: cache_change, cache_logs, database_status. Post-sufficiency calls: 0. Agent explanation: The API is experiencing degraded status with high read latency due to repeated backend reads, indicating the database is likely saturated and causing the overall application slowness. The frontend is healthy with normal rendering latency, so the issue is not in the frontend.


## Interpretation and failures

The frozen hypothesis was not supported. The controller recognized an obvious
fault cheaply on `diag_001`, but often treated a plausible explanation of symptoms
as a sufficiently resolved root cause. It reduced diagnostic calls while losing
both accuracy and evidence support, and its own requests outweighed token and
latency savings.

Specific observed failures:

- **`diag_004`:** the stopper ended investigation after two or three calls. It
  treated degraded API reads as a coherent explanation of slowness before
  inspecting healthy database status or cache evidence. The diagnostic agent
  then attributed the incident to the wrong component/category. All three
  adaptive runs were incorrect, while all fixed-8 runs were correct.
- **`diag_006`:** two adaptive runs stopped after five calls with cache-retrieval
  timeouts but without the API destination change. They incorrectly named a
  cache configuration regression. One run continued to seven and diagnosed
  the accepted API configuration cause correctly. A healthy cache plus a timeout
  does not resolve which side of the connection is misconfigured.
- **`diag_008`:** all three adaptive runs had the correct broad cache label but
  stopped at six calls, missing cache logs/change that identify the namespace
  mismatch. Accuracy alone would hide this incomplete support.
- **`diag_003`:** stopping after database status produced the correct saturation
  label in all three runs, but omitted logs required to establish the mechanism
  and distinguish connection/lock problems. This is a rubric-defined false early
  stop, distinct from a demonstrably wrong diagnosis.

All 24 adaptive runs triggered STOP before the ceiling. That fact is not evidence
that all 24 saved useful work: the fixed-8 agent already stops voluntarily often,
and some adaptive routes took more calls than their fixed counterparts. Ceiling
slack and differences of observed configuration means are reported separately.

The stopper reasons are observable justifications, not access to hidden model
reasoning. They support the specific finding that the controller accepted a
coherent symptom explanation despite unresolved causal ambiguity. No claim about
attention to distractors or internal confidence is needed.

## Best observed tradeoff and developer takeaway

Fixed-8 is the reliability reference on this workload. Fixed-6 is the simpler
lower-cost option, with a measured loss of accuracy and evidence completeness.
The tested adaptive policy is not a better replacement: it has lower accuracy
than fixed-6 as well as higher total token usage and latency. Its one advantage is
fewer diagnostic-tool executions. These synthetic tools have negligible runtime
cost, so saving calls is not equivalent to saving elapsed time or model tokens.

The strongest lesson is to measure the controller as part of the system. A
plausible STOP explanation and fewer tool calls can coexist with worse answers,
less supporting evidence, and greater overall cost. Phoenix made that visible by
joining each decision to the exact observed prefix, final diagnosis, deterministic
evaluations, and separate model usage.

## Laya and demo decision

**Laya is not justified by this result yet.** Stopping quality failed alongside
overhead; making the same signal cheaper would not repair false early stops or
lost accuracy. First establish a reliable stopping signal on reviewed held-out
cases before testing whether a smaller decision model can reproduce it cheaply.
No alternate prompt, policy, model, or scenario was tried in this phase.

**The project is ready for a final educational demo**, provided it presents this
negative result honestly and keeps fixed-8 as the reference. The demo can show an
obvious successful early stop alongside an ambiguous failure and the complete
cost comparison. It should not advertise adaptive stopping as an optimization
that worked. No interactive UI, Laya integration, or deployment was implemented.

## Validity and limits

The original dataset ID/version, synthetic observations, tool schemas, diagnostic
prompt, output schema, model snapshot, temperature, and original evaluator
functions were preserved. The stopper sees only observed input/output prefixes;
fetched native LLM inputs were checked for hidden evaluation fields. Tool and
stopping traces, native token counters, persisted scores, and original run
fingerprints were independently checked against exported results.

This is eight synthetic scenarios with three final repetitions per configuration,
not 24 independent incident types. The study establishes a result for this
controlled workload, not general reliability or statistical noninferiority.
Serial configuration order and live API variation affect latency. The
post-sufficiency rubric measures missing/extra checklist evidence rather than
proving the agent could not know a diagnosis sooner. All original scoring remains
unchanged, including scenario-specific aliases.

## Artifacts and Phoenix views

- [Frozen hypothesis and exact prompt](ADAPTIVE_HYPOTHESIS.md)
- [Runtime implementation and evaluator definitions](ADAPTIVE_DESIGN.md)
- [Targeted repeatability study](TRAJECTORY_VARIATION.md)
- [Stopping-check screenshot](results/screenshots/adaptive-stopping-check.png)
- [Final Metrics comparison](results/screenshots/adaptive-comparison-metrics.png)
- [Final List comparison](results/screenshots/adaptive-comparison-list.png)
- `results/phase3-variation/`: 50 tasks, 550 evaluations, fetched traces and summaries.
- `results/phase3-comparison/`: 72 tasks, 1,368 evaluations, fetched traces, summaries,
  and four selected demo links in `demo-traces.json`.
- `results/phase3-frozen-policy.json`: prompt, schemas, and hypothesis fingerprint.

Open each selected trace above, then select the `stopping_check` span to see the
observed prefix and decision/reason. Its native LLM child exposes the actual prompt,
structured output, and usage. The comparison's Metrics/List views are sufficient;
there is no need to repair the cosmetic Grid issue for this phase.

A final UI check also found a server GraphQL integer-serialization error when
optional root annotations were present. Their duplicate records were archived and
removed; experiment evaluations and root attributes are preserved. See the
[implementation note](ADAPTIVE_DESIGN.md#phoenix-trace-page-workaround). The trace
pages were rechecked after this workaround.

