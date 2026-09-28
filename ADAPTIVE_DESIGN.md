# Adaptive stopping implementation

## Policy and boundaries

The exact frozen prompt and acceptance criteria are in
[ADAPTIVE_HYPOTHESIS.md](ADAPTIVE_HYPOTHESIS.md). `StopDecision` is a Pydantic
record with `decision: Literal['STOP', 'CONTINUE']` and `reason: str`; extra fields
are forbidden. The same pinned OpenAI model and temperature are used for both
roles. The stopper has no tools and receives a fresh request containing the user
report and the full observed diagnostic-tool prefix. It is an online controller,
not an LLM evaluator. All outcome evaluators remain deterministic Python.

`observed_payload` explicitly selects tool name, arguments, output, and observed
evidence IDs. It never receives `Scenario`, `RuntimeState`, hidden component
states, evaluation labels, or difficulty. Scenario ID is supplied only to trace
attributes. There is no per-scenario stopping rule or minimum-evidence checklist.

The unchanged diagnostic agent does not emit a tentative diagnosis at every step.
The controller therefore infers sufficiency from observed reports/results without
pretending an intermediate diagnosis is available. Its short reason is visible in
Phoenix but is not fed back to the diagnostic model as evidence.

## Framework control

`CheckAfterTool` is function middleware. After the tool completes, it awaits one
stopping request, including after the eighth call. When STOP occurs before eight,
`FinalizeAfterStop` sets `tool_choice=none` on the next diagnostic model request.
The system prompt, diagnostic output schema, tools, tool descriptions, and message
history are retained. The final diagnosis comes from the diagnostic agent.

The native `max_function_calls` remains eight in the adaptive strategy. A recorder
guard also prevents further execution if an unexpected multi-call batch arrives
after STOP. Parallel calls remain disabled. Checks at call eight are measured but
cannot trigger an effective adaptive stop because the hard ceiling already applies.
This conservative accounting includes their overhead rather than claiming a saving.
A malformed/failed check falls back to CONTINUE, retains any returned usage, and
records the error class without a provider error body. The unchanged overall run
timeout is 180 seconds; each check has a 30-second timeout.

## Trace visibility

Existing native model/tool spans remain. A `stopping_check` CHAIN span contains:

- scenario ID, call index, model name, and observed input JSON;
- STOP/CONTINUE, reason, effective-stop flag, elapsed time, and output JSON;
- one native LLM child with stopping prompt, structured response, and token counts.

The CHAIN records stopper tokens under a custom attribute; the native LLM owns
the standard token counters, avoiding double counting in Phoenix. The root records
strategy and final stop reason. Post-run root attributes show correctness and evidence sufficiency. Experiment
evaluations show adaptive trigger and false early stop.

## Metric definitions

The original eleven evaluators are unchanged. In particular, `token_usage` remains
**diagnostic-agent** token usage. End-to-end `latency_seconds` includes stopper time
because it times the entire execution. Eight additional evaluators are:

| Metric | Definition |
|---|---|
| adaptive_stop_triggered | STOP effectively disabled tools before the hard ceiling |
| stop_call_index | Executed calls at effective STOP; null if it did not trigger |
| false_early_stop | Effective STOP with incomplete required evidence, computed after execution |
| avoided_calls_vs_budget8 | max(0, 8 − actual calls); ceiling slack only |
| stopper_overhead_tokens | Sum of all check tokens; null if any check usage is unavailable |
| stopper_overhead_latency | Sum of elapsed check times |
| total_tokens | Diagnostic-agent plus stopper tokens |
| stopper_errors | Number of checks that failed or returned invalid structured output |

A correct diagnosis may still count as a false early stop when support is incomplete
under the fixed rubric. Aggregate false-early-stop rates use all adaptive runs;
the report also shows the rate among effective stops. Savings compare actual
fixed-8 means, not ceiling slack or an assumed matched counterfactual.

## Reproduce

Keep local Phoenix running with `bash scripts/start_phoenix.sh`, then:

```bash
.venv/bin/python scripts/run_phase3.py variation
.venv/bin/python scripts/analyze_phase3.py variation
.venv/bin/python scripts/report_trajectory_variation.py
# Review the opportunity and freeze the hypothesis before proceeding:
.venv/bin/python scripts/run_phase3.py comparison
.venv/bin/python scripts/analyze_phase3.py comparison
.venv/bin/python scripts/report_adaptive_results.py
```

The runner checks the original dataset version, prompt/data hashes, model snapshot,
and temperature. It reuses matching completed experiments rather than purchasing
another copy after a local reporting failure. Concurrency is one and experiment
retries are zero. SDK transport behavior remains inherited from the original
client. The targeted study uses a local subset of original example IDs; the final
comparison uses all eight original examples. Both retain the same dataset/version.

Results remain under ignored `results/phase3-*`; reports preserve conclusions and
local Phoenix links. No dependencies, synthetic observations, rubric definitions,
or model snapshots changed in this phase.

Structured decisions use the existing framework's Pydantic response-format support,
consistent with [OpenAI's structured output documentation](https://developers.openai.com/api/docs/guides/structured-outputs).

## Validation outcome

32 deterministic tests pass, including STOP finalization, hard-ceiling precedence,
malformed-check fallback, unexpected batch guarding, separate token accounting,
runtime payload isolation, and unchanged diagnostic requests when every check
returns CONTINUE. The 50 targeted and 72 final runs completed without budget
violations, run errors, or stopper errors. All 1,918 new evaluation records were
verified against local Python calculations. Every final trace's native LLM token
sum matched agent-plus-stopper usage, and all 94 stopping checks matched their
observed tool prefixes and recorded decisions.

## Phoenix trace-page workaround

The final browser pass found a GraphQL error (`Int cannot represent non-integer
value: <int64 instance>`) in span-annotation summaries. Optional duplicate root
annotations triggered it. The 288 Phase 3 duplicates were archived locally and
removed through Phoenix's filtered annotation API; all 1,368 experiment evaluations,
traces, original root attributes, and decisions remain intact. The verification
script no longer adds those duplicate annotations. This avoids changing server
packages or experiment outcomes. Metrics/List comparison views remain usable.
