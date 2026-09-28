# Live tool-budget pilot report

## Model and setup

Authentication succeeded and the model-list API returned 132 models. Selected **gpt-4.1-mini-2025-04-14**, an accessible snapshot with tool calling and structured output. It is a small, low-latency model without a separate reasoning step, appropriate for this diagnostic baseline. The snapshot avoids alias changes. [Official model documentation](https://developers.openai.com/api/docs/models/gpt-4.1-mini).

Updated only `MODEL_NAME` in the ignored `.env`; credentials were never printed. `MODEL_TEMPERATURE` defaults to 0. No reasoning-effort parameter is sent. Added deterministic metrics, stop-control observation, fixed-setting metadata, and prompt/runtime fingerprints. No dataset or prompt edits, new model comparisons, Phoenix, or OpenTelemetry changes.

A simple generation check returned “OK.” (13 tokens). The separate easy test succeeded: `diag_001`, budget 2, `check_status(api) → check_recent_change(api)`, correct `api_configuration_issue`, valid structured diagnosis, 2 executed calls, 4.17 seconds, 1,263 tokens. The framework forced the final answer after budget exhaustion. The second tool was after checklist completion.

## Separate hard-case comparison: diag_007

True category: `database_connection_regression`. These four runs precede and are separate from the 32-run pilot; they are not included in aggregate results.

| Budget | Prediction | Correct | Calls | Required evidence | Repeats | Outside rubric | Seconds | Tokens | Stop |
|---|---|---|---|---|---|---|---|---|---|
| 2 | api_dependency_issue | False | 2 | 1/5 | 0 | 1 | 2.98 | 1297 | tool_budget |
| 4 | api_dependency_issue | False | 4 | 2/5 | 0 | 2 | 4.70 | 2402 | tool_budget |
| 6 | database_connection_regression | True | 6 | 4/5 | 0 | 2 | 5.98 | 3755 | tool_budget |
| 8 | database_connection_regression | True | 6 | 4/5 | 0 | 2 | 4.95 | 3760 | agent_answered |

### Budget 2

Trajectory: `check_status(frontend)` → `check_status(api)`

Retrieved: `frontend_status`, `api_status`

Missing required: `api_change`, `api_logs`, `database_logs`, `database_status`

Premature under checklist: True; calls after full evidence: 0.

### Budget 4

Trajectory: `check_status(frontend)` → `check_status(api)` → `check_status(database)` → `check_status(cache)`

Retrieved: `frontend_status`, `api_status`, `database_status`, `cache_status`

Missing required: `api_change`, `api_logs`, `database_logs`

Premature under checklist: True; calls after full evidence: 0.

### Budget 6

Trajectory: `check_status(frontend)` → `check_status(api)` → `check_status(database)` → `check_status(cache)` → `read_logs(api)` → `check_recent_change(api)`

Retrieved: `frontend_status`, `api_status`, `database_status`, `cache_status`, `api_logs`, `api_change`

Missing required: `database_logs`

Premature under checklist: True; calls after full evidence: 0.

### Budget 8

Trajectory: `check_status(frontend)` → `check_status(api)` → `check_status(database)` → `check_status(cache)` → `read_logs(api)` → `check_recent_change(api)`

Retrieved: `frontend_status`, `api_status`, `database_status`, `cache_status`, `api_logs`, `api_change`

Missing required: `database_logs`

Premature under checklist: True; calls after full evidence: 0.

## Full pilot aggregates

One live run per scenario/budget cell; 32 total. Only the configured budget changes across treatments. Temperature 0 does not guarantee identical model responses. Runs execute sequentially in budget order, so latency can also reflect service conditions and caching.

“Redundant” below is the union of repeated calls, calls returning evidence outside the required/supporting set, and calls after collecting the complete required set. It is a rubric-based count, not a claim that every exploratory call was avoidable. Premature means incomplete checklist at termination.

### All

| Budget | n | Accuracy | Evidence | Calls | Premature | Redundant | Seconds | Tokens |
|---|---|---|---|---|---|---|---|---|
| 2 | 8 | 50.0% | 24.4% | 2.00 | 87.5% | 1.38 | 2.29 | 1267.4 |
| 4 | 8 | 62.5% | 65.4% | 3.75 | 62.5% | 1.88 | 3.52 | 2232.8 |
| 6 | 8 | 87.5% | 78.8% | 5.25 | 62.5% | 2.75 | 4.30 | 3229.6 |
| 8 | 8 | 87.5% | 90.2% | 5.62 | 37.5% | 2.62 | 4.50 | 3552.4 |

### Easy

| Budget | n | Accuracy | Evidence | Calls | Premature | Redundant | Seconds | Tokens |
|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 100.0% | 50.0% | 2.00 | 66.7% | 1.00 | 2.45 | 1269.0 |
| 4 | 3 | 100.0% | 100.0% | 3.33 | 0.0% | 1.33 | 3.36 | 1985.3 |
| 6 | 3 | 100.0% | 100.0% | 4.00 | 0.0% | 2.00 | 3.48 | 2435.3 |
| 8 | 3 | 100.0% | 100.0% | 4.33 | 0.0% | 2.33 | 3.90 | 2680.7 |

### Medium

| Budget | n | Accuracy | Evidence | Calls | Premature | Redundant | Seconds | Tokens |
|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 0.0% | 8.3% | 2.00 | 100.0% | 1.67 | 2.21 | 1259.3 |
| 4 | 3 | 33.3% | 50.0% | 4.00 | 100.0% | 2.33 | 3.60 | 2364.7 |
| 6 | 3 | 66.7% | 61.1% | 6.00 | 100.0% | 4.00 | 4.75 | 3675.7 |
| 8 | 3 | 66.7% | 80.6% | 6.00 | 66.7% | 3.33 | 4.70 | 3751.3 |

### Hard

| Budget | n | Accuracy | Evidence | Calls | Premature | Redundant | Seconds | Tokens |
|---|---|---|---|---|---|---|---|---|
| 2 | 2 | 50.0% | 10.0% | 2.00 | 100.0% | 1.50 | 2.17 | 1277.0 |
| 4 | 2 | 50.0% | 36.7% | 4.00 | 100.0% | 2.00 | 3.64 | 2406.0 |
| 6 | 2 | 100.0% | 73.3% | 6.00 | 100.0% | 2.00 | 4.85 | 3752.0 |
| 8 | 2 | 100.0% | 90.0% | 7.00 | 50.0% | 2.00 | 5.09 | 4561.5 |

### Investigation measures, separated

| Budget | Avg identical repeats | Avg outside required/supporting | Avg calls after completion |
|---|---|---|---|
| 2 | 0.00 | 1.38 | 0.12 |
| 4 | 0.00 | 1.88 | 0.25 |
| 6 | 0.00 | 2.75 | 0.50 |
| 8 | 0.00 | 2.62 | 0.62 |

## Validity and framework audit

- All 32 runs completed with valid diagnoses and no tool errors, malformed arguments, or unobserved evidence citations.
- Every run stayed within its budget. Every observed model round requested at most one function. The exact guard remains enabled; no live request needed blocking.
- Model, temperature, prompt fingerprint, reasoning configuration, and iteration ceiling matched across budgets. Runtime fingerprints matched for each scenario.
- Every run builds a fresh environment, tools, and agent. Tests cover deep-copy isolation and exclusion of evaluation labels from runtime/model messages. The shared category vocabulary includes all possible causes, but never identifies the current scenario answer.
- Stop reason uses observed model-request controls. `tool_budget` means a final request with `tool_choice=none` at the cap; `agent_answered` means a free answer. It does not reveal whether a capped agent would have continued voluntarily.
- Framework `finish_reason=stop` alone cannot distinguish these cases. Token metadata was available for all runs and exactly matched the sum of per-round totals.
- Stop counts: {'tool_budget': 21, 'agent_answered': 11}. No other framework limit or timeout occurred.
- Native `max_function_calls` remains a best-effort batch limit; disabling parallel requests and the exact guard preserve the treatment. The final model answer consumes tokens but no tool budget.
- Core 1.19.0 and provider adapter 1.14.4 use independent package version numbers. No integration fix was needed after valid authentication.
- Deterministic validation: 23 tests passed before live execution; no runtime implementation changes were made during the live runs.

## Signal assessment and recommendation

**Classification: STRONG SIGNAL within this small pilot, with a scoring caveat.**
Budget materially changes both exact-match success and investigation trajectories:
accuracy rises from 50% to 87.5%, evidence completeness from 24.4% to 90.2%, and
average calls from 2.00 to 5.62. Average tokens rise from 1,267 to 3,552 and latency
from 2.29 to 4.50 seconds. These are exploratory observations from one run per
cell, not a reliable population estimate or proof of an optimal budget.

Accuracy is unchanged between budgets 6 and 8, but the underlying outcomes differ:
`diag_004` becomes correct while `diag_006` changes to a defensible category that
exact matching rejects. Therefore the apparent accuracy plateau is partly a
labeling artifact, not established reasoning deterioration. Evidence completeness
continues improving. Redundancy is not monotonic: 2.75 rubric-redundant calls at
budget 6 versus 2.62 at budget 8. There were **zero identical repeated calls**.

### Observed behaviors

- **Budget exhaustion before mechanism evidence:** `diag_007` spends four calls
  checking statuses. At budget 4 it predicts an API dependency issue; with six
  calls it reaches database-connection evidence and predicts the correct category.
- **Correct guesses without required support:** at budget 2, `diag_003` and
  `diag_008` inspect only healthy frontend/API statuses, collect 0 required items,
  and infer the correct category from the symptom. No hidden labels were leaked;
  their explanations explicitly rely on symptom-based expectations.
- **Broad exploration:** `diag_006` uses its first four calls on component statuses
  even though useful evidence lives in API logs and the API change record. This is
  exploration outside the checklist, not repeated status checks.
- **Post-sufficiency investigation:** `diag_001` has sufficient evidence after its
  first API status call but makes two additional calls at budgets 4/6/8.
  `diag_003` completes its checklist at call 4, then makes three more calls at
  budget 8. This is concrete excess investigation under the declared rubric.
- **Voluntary answers before the cap:** `diag_002` answers after three calls at
  budgets 4/6/8. `diag_007` answers after six at budget 8, although its checklist
  still lacks `database_logs`.
- **Exact-label ambiguity:** `diag_006` at budget 8 retrieves all required evidence
  and correctly explains that the API's cache destination changed to port 6380
  while the cache listens on 6379. Its category `api_configuration_issue` is
  semantically reasonable but differs from `api_dependency_issue`. The budget-6
  explanation is less specific yet gets full exact-match credit. Do not count
  this example as demonstrated reasoning drift.
- No malformed tool arguments, structured-output failures, repeated identical
  queries, fabricated evidence citations, or established distractor-caused changes
  were observed. Retrieving a distractor is not proof that it caused an error.

### Smallest revisions to consider

Do not regenerate the dataset or change this run's scores retrospectively.

1. Clarify the category boundary for `diag_006`. A wrong API endpoint/port naturally
   fits `api_configuration_issue`; reserve dependency issues for a distinct
   downstream failure, or define the global categories unambiguously before the
   next run. Record any change as a new dataset version.
2. Review whether `database_logs` in `diag_007` and `api_logs` in `diag_005` are truly
   mandatory. Plausible alternative paths already establish the mechanism. Move
   confirmatory items to supporting evidence or declare alternative sufficient
   sets after human review. Avoid equating every checklist omission with a bad
   diagnosis.
3. Retain correctness and completeness as separate metrics. Before expanding,
   consider a symptom-matched contrasting case for the stale-data and slow-search
   tasks, so symptom-only guessing is less reliable. No new cases were added here.
4. Difficulty currently describes an intended evidence path, not observed model
   difficulty: the hard tasks reach 100% exact accuracy at budget 6, while medium
   tasks reach only 66.7%. Treat that as a useful pilot finding.

**Recommendation: proceed toward Phoenix instrumentation for these eight tasks;
the budget effect is large enough to justify tracing.** First resolve the small
category/rubric issues above before interpreting Phoenix accuracy and premature-
stopping evaluations as authoritative. Do not expand to 30 tasks yet.

**Exact next step:** review `diag_006`'s category and `diag_005`/`diag_007`'s required
sets, save a versioned scoring decision, then authorize the next phase to add
Phoenix spans at the existing run/model/tool boundaries. This phase stops with
this report; no Phoenix or scenario revision was implemented.

## Per-run trajectories

### diag_001, budget 2

Prediction: `api_configuration_issue`; correct: True; required evidence: 1/1; stop: `tool_budget`.

`check_status(api)` → `check_recent_change(api)`

Missing: none.

Repeats: 0; outside rubric: 1; after completion: 1.

### diag_002, budget 2

Prediction: `frontend_deployment_regression`; correct: True; required evidence: 1/2; stop: `tool_budget`.

`check_status(frontend)` → `read_logs(frontend)`

Missing: frontend_change.

Repeats: 0; outside rubric: 0; after completion: 0.

### diag_003, budget 2

Prediction: `database_saturation`; correct: True; required evidence: 0/2; stop: `tool_budget`.

`check_status(frontend)` → `check_status(api)`

Missing: database_logs, database_status.

Repeats: 0; outside rubric: 2; after completion: 0.

### diag_004, budget 2

Prediction: `database_saturation`; correct: False; required evidence: 1/4; stop: `tool_budget`.

`check_status(frontend)` → `check_status(api)`

Missing: cache_change, cache_logs, database_status.

Repeats: 0; outside rubric: 1; after completion: 0.

### diag_005, budget 2

Prediction: `unknown`; correct: False; required evidence: 0/3; stop: `tool_budget`.

`check_status(api)` → `check_status(database)`

Missing: api_logs, database_change, database_logs.

Repeats: 0; outside rubric: 2; after completion: 0.

### diag_006, budget 2

Prediction: `unknown`; correct: False; required evidence: 0/3; stop: `tool_budget`.

`check_status(frontend)` → `check_status(api)`

Missing: api_change, api_logs, cache_status.

Repeats: 0; outside rubric: 2; after completion: 0.

### diag_007, budget 2

Prediction: `unknown`; correct: False; required evidence: 1/5; stop: `tool_budget`.

`check_status(frontend)` → `check_status(api)`

Missing: api_change, api_logs, database_logs, database_status.

Repeats: 0; outside rubric: 1; after completion: 0.

### diag_008, budget 2

Prediction: `cache_configuration_regression`; correct: True; required evidence: 0/6; stop: `tool_budget`.

`check_status(frontend)` → `check_status(api)`

Missing: api_logs, cache_change, cache_logs, cache_status, database_status, frontend_logs.

Repeats: 0; outside rubric: 2; after completion: 0.

### diag_001, budget 4

Prediction: `api_configuration_issue`; correct: True; required evidence: 1/1; stop: `agent_answered`.

`check_status(api)` → `check_recent_change(api)` → `read_logs(api)`

Missing: none.

Repeats: 0; outside rubric: 2; after completion: 2.

### diag_002, budget 4

Prediction: `frontend_deployment_regression`; correct: True; required evidence: 2/2; stop: `agent_answered`.

`check_status(frontend)` → `read_logs(frontend)` → `check_recent_change(frontend)`

Missing: none.

Repeats: 0; outside rubric: 0; after completion: 0.

### diag_003, budget 4

Prediction: `database_saturation`; correct: True; required evidence: 2/2; stop: `tool_budget`.

`check_status(frontend)` → `check_status(api)` → `check_status(database)` → `read_logs(database)`

Missing: none.

Repeats: 0; outside rubric: 2; after completion: 0.

### diag_004, budget 4

Prediction: `api_dependency_issue`; correct: False; required evidence: 2/4; stop: `tool_budget`.

`check_status(frontend)` → `check_status(api)` → `check_status(database)` → `check_status(cache)`

Missing: cache_change, cache_logs.

Repeats: 0; outside rubric: 2; after completion: 0.

### diag_005, budget 4

Prediction: `database_connection_regression`; correct: True; required evidence: 2/3; stop: `tool_budget`.

`check_status(api)` → `check_status(database)` → `read_logs(database)` → `check_recent_change(database)`

Missing: api_logs.

Repeats: 0; outside rubric: 2; after completion: 0.

### diag_006, budget 4

Prediction: `unknown`; correct: False; required evidence: 1/3; stop: `tool_budget`.

`check_status(frontend)` → `check_status(api)` → `check_status(database)` → `check_status(cache)`

Missing: api_change, api_logs.

Repeats: 0; outside rubric: 3; after completion: 0.

### diag_007, budget 4

Prediction: `api_dependency_issue`; correct: False; required evidence: 2/5; stop: `tool_budget`.

`check_status(frontend)` → `check_status(api)` → `check_status(database)` → `check_status(cache)`

Missing: api_change, api_logs, database_logs.

Repeats: 0; outside rubric: 2; after completion: 0.

### diag_008, budget 4

Prediction: `cache_configuration_regression`; correct: True; required evidence: 2/6; stop: `tool_budget`.

`check_status(frontend)` → `check_status(api)` → `check_status(cache)` → `check_status(database)`

Missing: api_logs, cache_change, cache_logs, frontend_logs.

Repeats: 0; outside rubric: 2; after completion: 0.

### diag_001, budget 6

Prediction: `api_configuration_issue`; correct: True; required evidence: 1/1; stop: `agent_answered`.

`check_status(api)` → `check_recent_change(api)` → `read_logs(api)`

Missing: none.

Repeats: 0; outside rubric: 2; after completion: 2.

### diag_002, budget 6

Prediction: `frontend_deployment_regression`; correct: True; required evidence: 2/2; stop: `agent_answered`.

`check_status(frontend)` → `read_logs(frontend)` → `check_recent_change(frontend)`

Missing: none.

Repeats: 0; outside rubric: 0; after completion: 0.

### diag_003, budget 6

Prediction: `database_saturation`; correct: True; required evidence: 2/2; stop: `tool_budget`.

`check_status(frontend)` → `check_status(api)` → `check_status(database)` → `read_logs(database)` → `check_recent_change(database)` → `check_status(cache)`

Missing: none.

Repeats: 0; outside rubric: 4; after completion: 2.

### diag_004, budget 6

Prediction: `api_dependency_issue`; correct: False; required evidence: 2/4; stop: `tool_budget`.

`check_status(frontend)` → `check_status(api)` → `read_logs(api)` → `check_status(database)` → `check_status(cache)` → `check_recent_change(api)`

Missing: cache_change, cache_logs.

Repeats: 0; outside rubric: 4; after completion: 0.

### diag_005, budget 6

Prediction: `database_connection_regression`; correct: True; required evidence: 2/3; stop: `tool_budget`.

`check_status(api)` → `check_status(database)` → `check_status(cache)` → `read_logs(api)` → `check_recent_change(api)` → `check_recent_change(database)`

Missing: database_logs.

Repeats: 0; outside rubric: 4; after completion: 0.

### diag_006, budget 6

Prediction: `api_dependency_issue`; correct: True; required evidence: 2/3; stop: `tool_budget`.

`check_status(frontend)` → `check_status(api)` → `check_status(database)` → `check_status(cache)` → `read_logs(api)` → `check_recent_change(cache)`

Missing: api_change.

Repeats: 0; outside rubric: 4; after completion: 0.

### diag_007, budget 6

Prediction: `database_connection_regression`; correct: True; required evidence: 4/5; stop: `tool_budget`.

`check_status(frontend)` → `check_status(api)` → `check_status(database)` → `check_status(cache)` → `read_logs(api)` → `read_logs(database)`

Missing: api_change.

Repeats: 0; outside rubric: 2; after completion: 0.

### diag_008, budget 6

Prediction: `cache_configuration_regression`; correct: True; required evidence: 4/6; stop: `tool_budget`.

`check_status(frontend)` → `check_status(api)` → `check_status(cache)` → `check_status(database)` → `read_logs(frontend)` → `read_logs(api)`

Missing: cache_change, cache_logs.

Repeats: 0; outside rubric: 2; after completion: 0.

### diag_001, budget 8

Prediction: `api_configuration_issue`; correct: True; required evidence: 1/1; stop: `agent_answered`.

`check_status(api)` → `check_recent_change(api)` → `read_logs(api)`

Missing: none.

Repeats: 0; outside rubric: 2; after completion: 2.

### diag_002, budget 8

Prediction: `frontend_deployment_regression`; correct: True; required evidence: 2/2; stop: `agent_answered`.

`check_status(frontend)` → `read_logs(frontend)` → `check_recent_change(frontend)`

Missing: none.

Repeats: 0; outside rubric: 0; after completion: 0.

### diag_003, budget 8

Prediction: `database_saturation`; correct: True; required evidence: 2/2; stop: `agent_answered`.

`check_status(frontend)` → `check_status(api)` → `check_status(database)` → `read_logs(database)` → `check_recent_change(database)` → `check_status(cache)` → `read_logs(api)`

Missing: none.

Repeats: 0; outside rubric: 5; after completion: 3.

### diag_004, budget 8

Prediction: `cache_configuration_regression`; correct: True; required evidence: 3/4; stop: `agent_answered`.

`check_status(frontend)` → `check_status(api)` → `check_status(database)` → `check_status(cache)` → `read_logs(api)` → `check_recent_change(api)` → `check_recent_change(cache)`

Missing: cache_logs.

Repeats: 0; outside rubric: 4; after completion: 0.

### diag_005, budget 8

Prediction: `database_connection_regression`; correct: True; required evidence: 2/3; stop: `agent_answered`.

`check_status(api)` → `check_status(database)` → `read_logs(database)` → `check_recent_change(database)`

Missing: api_logs.

Repeats: 0; outside rubric: 2; after completion: 0.

### diag_006, budget 8

Prediction: `api_configuration_issue`; correct: False; required evidence: 3/3; stop: `agent_answered`.

`check_status(frontend)` → `check_status(api)` → `check_status(database)` → `check_status(cache)` → `read_logs(api)` → `check_recent_change(cache)` → `check_recent_change(api)`

Missing: none.

Repeats: 0; outside rubric: 4; after completion: 0.

### diag_007, budget 8

Prediction: `database_connection_regression`; correct: True; required evidence: 4/5; stop: `agent_answered`.

`check_status(frontend)` → `check_status(api)` → `check_status(database)` → `check_status(cache)` → `read_logs(api)` → `check_recent_change(api)`

Missing: database_logs.

Repeats: 0; outside rubric: 2; after completion: 0.

### diag_008, budget 8

Prediction: `cache_configuration_regression`; correct: True; required evidence: 6/6; stop: `tool_budget`.

`check_status(frontend)` → `check_status(api)` → `check_status(cache)` → `check_status(database)` → `read_logs(frontend)` → `read_logs(api)` → `read_logs(cache)` → `check_recent_change(cache)`

Missing: none.

Repeats: 0; outside rubric: 2; after completion: 0.

## Local artifacts

- [Full pilot JSONL](results/live-pilot.jsonl)
- [Aggregate JSON](results/live-pilot.summary.json)
- [Separate hard comparison](results/hard-comparison.jsonl)
- [Easy live test](results/easy-live.json)
- [Experiment manifest](results/experiment-manifest.json)

`results/` remains gitignored. The report contains the aggregate measurements; raw local files retain tool arguments, outputs, evidence, diagnoses, latency, and usage.
