# OpenClaw finalization validation

**READY FOR 20-RUN STUDY with the explicit finalization adapter.** Both fresh `diag_007`, budget-6 validation attempts passed. No 20-run study or adaptive stopping was run. This is a newly defined adapter condition, not evidence of identical Microsoft/OpenClaw behavior.

## Native structured-output investigation

GPT-4.1 mini supports Structured Outputs and the exact snapshot `gpt-4.1-mini-2025-04-14` remains available in the [official model documentation](https://developers.openai.com/api/docs/models/gpt-4.1-mini). The provider supports strict JSON-schema output, but the selected runtime must expose that control.

OpenClaw documents `responseFormat` for direct-provider completions. Its `isolated-agent-runtime` mode instead guarantees a fresh, tools-disabled completion and rejects direct-provider response-format controls. See [OpenClaw model helpers](https://docs.openclaw.ai/plugins/sdk-runtime/models). The installed 2026.9.7 implementation makes the same distinction.

An actual no-inference probe through the documented plugin API supplied `responseFormat` with isolated execution. It returned `LLM_ISOLATED_INPUT_REJECTED`: isolated completion does not support `responseFormat`. **Zero HTTP requests** were issued. [Probe evidence](results/openclaw-finalization-validation/finalization/native-schema-probe.json).

A tool-schema final answer would require exposing a tool, contrary to this phase's zero-tool requirement. Switching to direct-provider mode would change the pinned runtime route. Neither was used. Native constrained decoding is therefore unavailable through the selected isolated runtime interface; this does not mean OpenClaw or the model lack all structured-output support.

## Chosen boundary

Every new adapter run follows:

1. Complete the original OpenClaw diagnostic loop with its unchanged prompt, three tools, deterministic environment and execution cap.
2. Verify diagnostic accounting, exact model/runtime and absence of recovery. Freeze ordered executed tool outputs.
3. Make exactly one additional call through `api.runtime.llm.complete`, with `execution.mode="isolated-agent-runtime"`, exact model and temperature 0.
4. Validate the untouched response with the existing `Diagnosis.model_validate_json(..., strict=True)` and check that every cited evidence ID was observed.
5. Attach evaluations only after the full final diagnosis passes.

This is an **adapter-level finalization step**, applied to every run regardless of whether the loop's earlier answer was valid JSON. It does not repair or selectively retry malformed answers. The diagnostic-loop answer is preserved as intermediate output and is never supplied to the finalizer.

The finalizer receives only:

- original incident report;
- ordered executed tool names, arguments and original output objects, with canonical indices;
- the six shared root-cause labels plus `unknown`, extracted from the original Microsoft system instruction;
- the existing Diagnosis JSON schema and fixed finalization instructions.

Its schema has exactly `predicted_root_cause: string`, `explanation: string`, and `evidence_used: string[]`, with additional properties forbidden. No scenario answer, required-evidence set, difficulty, sufficiency score, eval, previous answer or repository content enters the finalizer input. Typed tool-output validation rejects unexpected hidden fields. The outgoing request guard checks exact equality with the frozen system/user messages, zero tools, exact endpoint/model, temperature 0 and exactly one request. The runtime reports execution owner `{kind: "harness", id: "openclaw"}` and returns provider/model attribution from its assistant result.

The diagnostic runtime reads `retry.provider.maxRetries=0`. The isolated finalizer has no diagnostic-loop continuation state; its guard rejects a second outgoing request, and accounting rejects additional attempts. Neither live finalizer retried.

**Deterministic boundary means deterministic acceptance and evidence freezing, not guaranteed model behavior.** This route requests JSON in the prompt and validates it strictly; it does not claim provider-enforced JSON-schema decoding. Refusals, malformed JSON, extra fields, wrong types or unobserved evidence citations fail the physical attempt without repair.

## Validation results

| Check | Repetition 1 | Repetition 2 |
|---|---|---|
| Exact model / OpenClaw owner | PASS | PASS |
| Executed diagnostic calls / budget | 6 / 6 | 6 / 6 |
| Blocked calls | 0 | 0 |
| Diagnostic internal attempts | 1 | 1 |
| Finalization HTTP calls | 1 | 1 |
| No recovery or semantic drift | PASS | PASS |
| Frozen, permitted evidence only | PASS | PASS |
| Strict JSON and observed-only citations | PASS | PASS |
| Phoenix structure / token reconciliation | PASS | PASS |
| Existing deterministic evaluations | 11 verified | 11 verified |
| Overall | **PASS** | **PASS** |

Both final diagnoses: **`database_connection_regression`**, correct and evidence-sufficient under the existing rubric. Those evaluations were computed after finalization, never provided to it.

Both diagnostic paths were:
`check_status(frontend)` → `check_status(api)` → `check_status(database)` → `check_status(cache)` → `read_logs(api)` → `check_recent_change(api)`.

Retrieved IDs: `frontend_status`, `api_status`, `database_status`, `cache_status`, `api_logs`, `api_change`. Repetition 1 cited `api_status`, `api_logs`, `api_change`, `database_status`, `cache_status`; repetition 2 cited the same set without `cache_status`. All citations were observed.

## Tokens and latency

All diagnostic-loop tokens, including its intermediate answer, remain included.

| Tokens | Repetition 1 | Repetition 2 |
|---|---:|---:|
| Diagnostic loop | 3,472 | 3,501 |
| Finalization | 724 | 721 |
| Total | **4,196** | **4,222** |

| Seconds | Repetition 1 | Repetition 2 |
|---|---:|---:|
| Diagnostic native run duration | 26.562 | 20.094 |
| Finalization phase after diagnostic end | 18.467 | 15.174 |
| Combined trace duration | **45.029** | **35.268** |
| Isolated completion operation, within finalization phase | 8.025 | 6.051 |
| Full end-to-end wall time, including both CLI invocations | **80.775** | **72.693** |

The finalization phase includes adapter/CLI preparation after the diagnostic event boundary. The completion span covers the actual plugin completion operation, including model preparation. Root duration uses the native diagnostic duration plus the subsequent finalization phase. Full wall time also captures diagnostic CLI startup and process shutdown, which are outside that event-anchored root. All are saved separately; the shorter trace duration is not claimed as whole-process latency. Do not compare these CLI timings directly with Microsoft latency as a harness advantage.

## Phoenix

Experiment: `openclaw-finalization-validation-budget-6`.

- Repetition 1: run `diag_007-b6-r1-96134b71`; [trace ec6395ee6c1788b5066cfe621dca6308](http://127.0.0.1:6006/projects/UHJvamVjdDoyMQ==/traces/ec6395ee6c1788b5066cfe621dca6308).
- Repetition 2: run `diag_007-b6-r2-28e26580`; [trace 0049cdd740ddb86faab18170743ec1a7](http://127.0.0.1:6006/projects/UHJvamVjdDoyMQ==/traces/0049cdd740ddb86faab18170743ec1a7).

Each trace has **15 spans**: one root, seven diagnostic LLM spans, six executed tool spans, and one finalization LLM span. The finalization span carries `phase="finalization"`, `tools_enabled=false`, and `finalization_adapter=true`. Canonical identities, request receipts, input hashes and usage are retained. The finalizer span boundaries are explicit adapter operation timestamps, not fabricated diagnostic-runtime hooks. All children share the run root. The root holds the final validated diagnosis and no standard LLM token attributes; summing model spans equals the recorded run total.

The existing finalization-semantics annotation describes tools remaining visible during the diagnostic loop. The new finalization span separately establishes that tools were unavailable in the explicit finalizer.

## Scientific comparability

Microsoft: diagnostic loop → framework budget boundary → tools disabled → final answer, with its existing conversation and response-format control. A voluntary answer can also precede the cap.

OpenClaw adapter: diagnostic loop → budget boundary / agent stop → evidence frozen → separate fresh tools-disabled completion → validated final answer.

Task, snapshot, vocabulary, tool behavior, cap, ground truth and rubric remain constant. Finalization context, prompts, execution semantics, schema enforcement mechanism and overhead differ. The new condition can test whether evidence gaps and trajectory variation recur across harnesses; it cannot isolate the causal effect of the harness or support a direct latency ranking. A fresh Microsoft subset using the same evidence-only finalizer would be needed for tighter finalization control. Record both diagnostic trajectory and finalizer costs in any future study.

## Failure and replacement policy

Any diagnostic accounting/recovery failure, finalizer transport failure, invalid final JSON or unobserved citation rejects the physical attempt. Preserve both phases and do not score it as an accepted run. A replacement must use a fresh entire diagnostic session and finalizer, the same intended repetition and condition, and a new physical attempt index/run ID. Do not rerun only the finalizer against a failed attempt until it passes. Record every failure and replacement; distinguish infrastructure failures from model-output failures.

`finalized_attempt.py` provides this reusable two-phase adapter and preserves rejection records; it never resumes or retries internally. `publish_finalization.py` publishes saved validation artifacts without inference. The legacy study launcher remains blocked by its existing failure marker and must use this new adapter before a future authorized study. No historical attempt has been retroactively accepted under the new contract.

Machine-readable evidence: [repetition 1](results/openclaw-finalization-validation/repetition-1.json), [repetition 2](results/openclaw-finalization-validation/repetition-2.json), plus diagnostic records, frozen fixtures, request bodies, completions, Phoenix spans and evaluations under `results/openclaw-finalization-validation/`. Results retain the repository's existing ignore policy.

## Development checks

71 Python tests and all four original OpenClaw Node contract tests passed. New tests reject YAML/markdown, extra fields, type coercion, unobserved citations, hidden tool-output fields, modified frozen evidence, extra tools, prior-answer context and model substitution. Both saved Phoenix traces were revalidated against the final validator. All 332 historical preservation hashes remained unchanged; new-code/result scans found no suspected credential values. README and demo were not modified.
