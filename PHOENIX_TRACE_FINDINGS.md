# Phoenix trace findings

## Outcome

Local Phoenix stores the eight-example dataset, four budget experiments, 32 successful tasks, and 352 deterministic evaluation results. All persisted scores were checked against local Python calculations. Tool/model spans, tool evidence, and treatment fingerprints were also checked. There were no budget violations, task failures, malformed tool arguments, or structured-output failures in the final four experiments.

## Where to inspect

- [Eight-example dataset](http://localhost:6006/datasets/RGF0YXNldDox/examples)
- [Four experiments](http://localhost:6006/datasets/RGF0YXNldDox/experiments)
- [Compare budgets](http://localhost:6006/datasets/RGF0YXNldDox/compare?experimentId=RXhwZXJpbWVudDox&experimentId=RXhwZXJpbWVudDoy&experimentId=RXhwZXJpbWVudDoz&experimentId=RXhwZXJpbWVudDo0)
- [Setup, tracing configuration, evaluator definitions, and commands](PHOENIX.md)
- [Documented rubric adjustments](data/RUBRIC_CHANGES.md)

Experiment names: `tool-budget-2`, `tool-budget-4`, `tool-budget-6`, `tool-budget-8`. The dataset contains only scenario ID/report in input, canonical/accepted causes in reference output, and difficulty/category/version in metadata. Only input is bound to the agent task.

## Results under rubric v2

| Budget | Accuracy | Completeness | Calls | Premature | Redundant | Seconds | Tokens |
|---|---|---|---|---|---|---|---|
| 2 | 50.0% | 25.0% | 1.88 | 87.5% | 1.25 | 2.29 | 1206 |
| 4 | 62.5% | 64.6% | 3.75 | 62.5% | 2.00 | 3.68 | 2228 |
| 6 | 87.5% | 82.3% | 5.12 | 50.0% | 2.62 | 4.36 | 3148 |
| 8 | 100.0% | 96.9% | 5.75 | 12.5% | 2.75 | 5.11 | 3649 |

There were zero identical repeat calls. Redundancy is the union of calls outside required/supporting evidence, repeated identical calls, and calls after sufficiency. Its subcomponents remain separate Phoenix evaluations.

### Comparison with the same original outputs rescored under v2

| Budget | Old / new accuracy | Old / new completeness | Old / new calls | Old / new premature | Old / new redundant | Old / new seconds | Old / new tokens |
|---|---|---|---|---|---|---|---|
| 2 | 50.0% / 50.0% | 25.0% / 25.0% | 2.00 / 1.88 | 87.5% / 87.5% | 1.38 / 1.25 | 2.29 / 2.29 | 1267 / 1206 |
| 4 | 62.5% / 62.5% | 70.8% / 64.6% | 3.75 / 3.75 | 50.0% / 62.5% | 1.88 / 2.00 | 3.52 / 3.68 | 2233 / 2228 |
| 6 | 87.5% / 87.5% | 76.0% / 82.3% | 5.25 / 5.12 | 62.5% / 50.0% | 2.75 / 2.62 | 4.30 / 4.36 | 3230 / 3148 |
| 8 | 100.0% / 100.0% | 96.9% / 96.9% | 5.62 / 5.75 | 12.5% / 12.5% | 2.62 / 2.75 | 4.50 / 5.11 | 3552 / 3649 |

The original published v1 budget-8 accuracy was 87.5%; its saved outputs score 100% under the explicit diag_006 alias. The new Phoenix accuracy curve exactly matches the **rescored** baseline. This improvement is not attributed to tracing. Completeness and premature-stop changes likewise combine rubric revisions and new model trajectories.

All prompt hashes, runtime-world hashes, model names, and model settings match the original pilot. Tool code gained attributes only; the tools, descriptions, observations, and output schema did not change. Runs are sequential, temperature is 0, reasoning effort remains unset, max iterations remains 20, and parallel calls remain disabled. Small trajectory differences remain; temperature 0 is not a determinism guarantee. Latency includes execution/instrumentation overhead but excludes much of asynchronous export and all evaluation work, so it does not isolate telemetry overhead.

## Representative traces

The step tables below are reconstructed from tool spans fetched back from Phoenix. They show observations delivered to the agent; model tool choices and final explanation are visible in adjacent model spans. No internal reasoning is inferred.

### Low-budget incorrect: diag_007, budget 2

[Open Phoenix trace](http://localhost:6006/projects/UHJvamVjdDo1/traces/f43f839349da8a36f3a1874a368f6b34)

Prediction: `api_dependency_issue`; correct: False; stop: `tool_budget`.

| Step | Tool/component | Evidence delivered | Role | Sufficient afterward? |
|---|---|---|---|---|
| 1 | `check_status(frontend)` | `frontend_status`: CPU is 78%; rendering itself remains under 20 ms. | distractor | False |
| 2 | `check_status(api)` | `api_status`: Request handlers wait for a downstream resource; API CPU is normal. | required | False |

Final missing required evidence: api_change, api_logs, database_status.
First rubric sufficiency: not reached.

The frontend distractor was observed, but no trace evidence proves it caused the error. The API wait observation identifies a downstream problem without establishing the pool regression.

### Low-budget correct by symptom-based inference: diag_008, budget 2

[Open Phoenix trace](http://localhost:6006/projects/UHJvamVjdDo1/traces/8075d33936651437da7c48f9a21a909d)

Prediction: `cache_configuration_regression`; correct: True; stop: `tool_budget`.

| Step | Tool/component | Evidence delivered | Role | Sufficient afterward? |
|---|---|---|---|---|
| 1 | `check_status(frontend)` | `frontend_status`: Availability and latency are within baseline. | outside rubric | False |
| 2 | `check_status(api)` | `api_status`: Availability and latency are within baseline. | outside rubric | False |

Final missing required evidence: api_logs, cache_change, cache_logs, cache_status, database_status, frontend_logs.
First rubric sufficiency: not reached.

The correct cache category is inferred from stale-value symptoms and two healthy status checks. None of the six required observations was retrieved; exact correctness alone overstates support.

### Medium-budget improvement: diag_006, budget 6

[Open Phoenix trace](http://localhost:6006/projects/UHJvamVjdDo3/traces/312e78acb04b35bfef86bf8b497d8945)

Prediction: `api_dependency_issue`; correct: True; stop: `tool_budget`.

| Step | Tool/component | Evidence delivered | Role | Sufficient afterward? |
|---|---|---|---|---|
| 1 | `check_status(frontend)` | `frontend_status`: Availability and latency are within baseline. | outside rubric | False |
| 2 | `check_status(api)` | `api_status`: Availability and latency are within baseline. | outside rubric | False |
| 3 | `check_status(database)` | `database_status`: Availability and latency are within baseline. | outside rubric | False |
| 4 | `check_status(cache)` | `cache_status`: Cache responds to health probes with normal latency. | required | False |
| 5 | `read_logs(api)` | `api_logs`: Search requests time out fetching cached search indexes. No database request is issued on the failing path. | required | False |
| 6 | `check_recent_change(cache)` | `cache_change`: No configuration or deployment changes in the incident window. | outside rubric | False |

Final missing required evidence: api_change.
First rubric sufficiency: not reached.

At budget 4 the same scenario answered unknown. API logs at the higher budget localize the cache access failure. The port-change evidence is still missing, so category correctness precedes mechanism confirmation. No distractor-caused effect is established.

### High-budget investigation after sufficiency: diag_003, budget 8

[Open Phoenix trace](http://localhost:6006/projects/UHJvamVjdDo4/traces/d9102f52a1e78ef66a6c6cc3538aaec4)

Prediction: `database_saturation`; correct: True; stop: `agent_answered`.

| Step | Tool/component | Evidence delivered | Role | Sufficient afterward? |
|---|---|---|---|---|
| 1 | `check_status(frontend)` | `frontend_status`: Availability and latency are within baseline. | outside rubric | False |
| 2 | `check_status(api)` | `api_status`: Availability and latency are within baseline. | outside rubric | False |
| 3 | `check_status(database)` | `database_status`: CPU is 100%; active queries are 240 against capacity of 40. | required | False |
| 4 | `read_logs(database)` | `database_logs`: Query execution queues are growing; CPU time is dominated by full-table scans, with no connection or lock errors. | required | True |
| 5 | `check_recent_change(database)` | `database_change`: No configuration or deployment changes in the incident window. | outside rubric | True |
| 6 | `check_status(cache)` | `cache_status`: Availability and latency are within baseline. | outside rubric | True |
| 7 | `read_logs(api)` | `api_logs`: No errors or unusual traffic in the incident window. | outside rubric | True |

Final missing required evidence: none.
First rubric sufficiency: call 4.

Database status plus logs make the diagnosis supportable under the rubric. Later calls collect normal change/cache/API observations and do not change the final category. They are post-sufficiency confirmation/exploration, not identical repeats.

### Voluntary stop before the cap: diag_007, budget 8

[Open Phoenix trace](http://localhost:6006/projects/UHJvamVjdDo4/traces/fbd6d0436926c03267dfb0d9a5351001)

Prediction: `database_connection_regression`; correct: True; stop: `agent_answered`.

| Step | Tool/component | Evidence delivered | Role | Sufficient afterward? |
|---|---|---|---|---|
| 1 | `check_status(frontend)` | `frontend_status`: CPU is 78%; rendering itself remains under 20 ms. | distractor | False |
| 2 | `check_status(api)` | `api_status`: Request handlers wait for a downstream resource; API CPU is normal. | required | False |
| 3 | `check_status(database)` | `database_status`: Query CPU is 20%, storage latency is normal, and only 2 connections are active. | required | False |
| 4 | `check_status(cache)` | `cache_status`: Availability and latency are within baseline. | outside rubric | False |
| 5 | `read_logs(api)` | `api_logs`: Handlers spend 2 seconds waiting for database connection acquisition; cache requests finish within baseline. | required | False |
| 6 | `check_recent_change(api)` | `api_change`: API database pool maximum changed from 40 to 2 during the last configuration rollout. | required | True |

Final missing required evidence: none.
First rubric sufficiency: call 6.

API logs and the pool change, together with server health and API degradation, establish the client connection bottleneck. The agent answers voluntarily before using all eight calls. The frontend distractor was encountered but did not prevent a correct supported diagnosis.

### Budget-forced final answer with sufficient evidence: diag_008, budget 8

[Open Phoenix trace](http://localhost:6006/projects/UHJvamVjdDo4/traces/1c360d72c814804f27b74b7bac652e6e)

Prediction: `cache_configuration_regression`; correct: True; stop: `tool_budget`.

| Step | Tool/component | Evidence delivered | Role | Sufficient afterward? |
|---|---|---|---|---|
| 1 | `check_status(frontend)` | `frontend_status`: Availability and latency are within baseline. | outside rubric | False |
| 2 | `check_status(api)` | `api_status`: Availability and latency are within baseline. | outside rubric | False |
| 3 | `check_status(cache)` | `cache_status`: Hit rate is 98%, memory is 45%, and network round trips are within baseline. | required | False |
| 4 | `check_status(database)` | `database_status`: Primary and read replica are current; replication lag is zero and queries complete normally. | required | False |
| 5 | `read_logs(frontend)` | `frontend_logs`: Affected browsers receive old values from API GET responses after successful saves; no local caching is enabled. | required | False |
| 6 | `read_logs(api)` | `api_logs`: Writes commit to the database and publish invalidations to namespace records-v2. Subsequent reads sometimes return old cache entries. | required | False |
| 7 | `read_logs(cache)` | `cache_logs`: Read entries are served from records-v1; invalidations arrive on records-v2 and match no entries. | required | False |
| 8 | `check_recent_change(cache)` | `cache_change`: Cache read namespace reverted to records-v1 during a configuration rollout. API invalidation namespace remains records-v2. | required | True |

Final missing required evidence: none.
First rubric sufficiency: call 8.

The final cache change completes the required chain. The framework then requests a tool-disabled final answer. Hitting the cap here is not premature under the evidence rubric; there are no post-sufficiency calls.

## What Phoenix added

Phoenix makes the four configurations comparable against one dataset and links each result to the exact sequence of model requests, tool results, and final answer. The evidence and post-sufficiency evaluations separate a lucky category match from a supported diagnosis. Native token counters and experiment annotations expose the cost of extra exploration. This materially improves diagnosis of failures over aggregate JSON tables; it does not make the agent more accurate or prove causal model reasoning.

## Artifacts and scope

- `results/phoenix-20260928T011340Z/`: authoritative experiment exports, comparison, and fetched spans.
- `results/screenshots/`: UI captures.
- `PILOT_REPORT.md`: original pilot, preserved unchanged.
- No new scenarios, model comparisons, dynamic stopping, LLM judges, or deployment UI were implemented.

## Repeatability check

The optional check used four existing scenarios, three repeats per cell, budgets 4/6/8, and the same snapshot at temperature 0. All 36 tasks and 396 persisted evaluations passed verification. No run exceeded its budget; prompt, runtime, model, and settings matched the original pilot.

| Scenario | Budget | Diagnoses (three runs) | Distinct trajectories | Stop reasons | Completeness range |
|---|---:|---|---:|---|---|
| diag_004 | 4 | api_dependency_issue, api_dependency_issue, api_dependency_issue | 1 | tool_budget | 50%–50% |
| diag_006 | 4 | unknown, unknown, unknown | 1 | tool_budget | 33%–33% |
| diag_007 | 4 | api_dependency_issue, api_dependency_issue, api_dependency_issue | 1 | tool_budget | 50%–50% |
| diag_008 | 4 | cache_configuration_regression, cache_configuration_regression, cache_configuration_regression | 2 | tool_budget | 33%–33% |
| diag_004 | 6 | api_dependency_issue, api_dependency_issue, api_dependency_issue | 1 | tool_budget | 50%–50% |
| diag_006 | 6 | api_dependency_issue, api_dependency_issue, api_dependency_issue | 1 | tool_budget | 67%–67% |
| diag_007 | 6 | database_connection_regression, database_connection_regression, database_connection_regression | 2 | tool_budget | 75%–100% |
| diag_008 | 6 | cache_configuration_regression, cache_configuration_regression, cache_configuration_regression | 1 | tool_budget | 67%–67% |
| diag_004 | 8 | cache_configuration_regression, cache_configuration_regression, cache_configuration_regression | 2 | agent_answered, tool_budget | 75%–75% |
| diag_006 | 8 | api_configuration_issue, api_configuration_issue, api_configuration_issue | 2 | agent_answered | 100%–100% |
| diag_007 | 8 | database_connection_regression, database_connection_regression, database_connection_regression | 2 | agent_answered | 100%–100% |
| diag_008 | 8 | cache_configuration_regression, cache_configuration_regression, cache_configuration_regression | 2 | tool_budget | 100%–100% |

Diagnoses were unchanged within all 12 cells. Tool sequences varied in 6/12 cells;
stop reason varied in 1/12 (`diag_004`, budget 8). Required evidence completeness
varied in 1/12 (`diag_007`, budget 6: 75–100%). This small sample supports the
accuracy pattern, while showing that one trajectory or stop reason per cell can
be misleading even at temperature 0. It does not establish population accuracy.
The repeat subset is a separate four-example Phoenix dataset containing existing
worlds; the main eight-example dataset is unchanged. Exports and the machine-readable
summary are in `results/phoenix-repeatability/`.

## Views to inspect

Open the dataset comparison linked above and select **Metrics** for budget-level
evaluations, tokens, and latency; select **List** for individual outputs and scores.
Both views were inspected in a browser. The default Grid view displayed headers
but a blank body during inspection; List is the verified workaround. Phoenix's
built-in performance latency includes experiment wrapping; our `latency_seconds`
evaluator measures agent execution, so these numbers need not match.

- [Metrics screenshot](results/screenshots/experiment-metrics.png)
- [Example list screenshot](results/screenshots/experiment-list.png)
- [Dataset examples screenshot](results/screenshots/dataset-examples.png)
- [Hard trace screenshot](results/screenshots/hard-trace.png)

Expand native LLM spans for messages and tool spans for arguments/results. Root
attributes show stop reason and post-run evaluation metadata. These are observable
requests and outputs, not access to hidden model reasoning.

## Recommended next experiment

Before changing the stopping policy, randomize the order of a larger repeat check
on the same four scenarios at budgets 6 and 8 (for example, ten runs per cell).
Predeclare evidence sufficiency, calls, and stop reason as primary outcomes and
report per-scenario variation. This targets the observed trajectory instability
and the gap between correct labels and complete evidence. It also avoids
confounding a new stopping policy with an uncertain fixed-budget baseline.
This is a recommendation only; no additional experiment or stopping policy was added.
