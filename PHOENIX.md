# Local Phoenix workflow

## Install and start

The agent retains its original model/framework dependencies. Install the optional
Phoenix client packages into the agent environment, and the server separately:

```bash
.venv/bin/python -m pip install -e '.[dev,phoenix]'
python3 -m venv .phoenix-venv
.phoenix-venv/bin/python -m pip install -r requirements-phoenix-server.txt
bash scripts/start_phoenix.sh
```

Open http://localhost:6006. The server stores its database under ignored `.phoenix/`;
restarting it preserves datasets, experiments, and traces. The launch script binds
to loopback and disables Phoenix's assistant, MCP server, and external resources.
Those product features are outside this experiment. Keep this terminal running.

Agent-side defaults (also in `.env.example`):

```dotenv
PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006
PHOENIX_API_KEY=
PHOENIX_PROJECT=agent-tool-budget-lab
```

The endpoint is the server base URL; the exporter appends `/v1/traces` and uses
OTLP over HTTP/protobuf. Cloud later can use a different base URL and API key.
Credentials remain in `.env` and are never printed or stored in traces. Model names and nonsecret experiment settings are recorded for reproducibility.

## Compatibility gate, experiments, and inspection

```bash
.venv/bin/python scripts/run_phoenix_gate.py
.venv/bin/python scripts/run_phoenix_experiments.py
# Use the directory printed by the experiment runner:
.venv/bin/python scripts/summarize_phoenix.py --manifest results/phoenix-TIMESTAMP/manifest.json
.venv/bin/python scripts/run_smoke_tests.py
```

The gate traces `diag_001` at budget 2 and `diag_007` at budget 8. Inspect their
model/tool sequence before interpreting experiments. The experiment runner uses
`AsyncClient.experiments.run_experiment`, concurrency 1, retries 0, and one
repetition. It reuses matching *completed* experiments to resume after a local
reporting failure. Matching requires dataset version, budget, model, temperature,
prompt hash, and dataset hash. Failed task batches stop before evaluations or the
next budget. Do not interpret partial experiment records as results.

The eight-example dataset name includes a hash of the local JSON. Inputs contain
only scenario ID and user report. References contain canonical/accepted labels;
metadata contains difficulty, category, rubric version, and dataset hash. The task
binds only `input` and checks it against local JSON. The model receives only the
runtime report and tool observations. The canonical world remains
`data/scenarios.json`.

Each budget produces eight tasks and 88 evaluation results (11 evaluators per
task). The summary script reads persisted Phoenix outputs and evaluations,
verifies scores against Python calculations, checks native tool/model spans and
experimental controls, adds three visible CODE annotations to diagnostic root
spans, and compares against the original pilot rescored with rubric v2.

## Tracing design

Microsoft emits the native agent, model, and tool spans. Sensitive-data capture
is enabled to include this synthetic environment's messages and tool results.
No SDK/provider auto-instrumentor is enabled, avoiding duplicate model spans.

Two small custom span boundaries are added: `diagnostic_run` holds input, final
output, scenario, budget, model, stop reason, and post-run evaluation attributes;
`final_diagnosis` marks the answer. Existing tool spans get tool index, component,
evidence ID, execution status, and structured input/output attributes.

`NativeSpanPresentation` translates native `gen_ai.*` fields into OpenInference
display attributes at export time. Span IDs, parents, timing, events, and original
attributes are preserved. This gives Phoenix LLM/AGENT/TOOL kinds, visible model
messages, and token counters without a second tracing stack. Hidden evaluation
fields are attached only after execution and never enter model messages.

Pinned packages:

- Agent environment: `arize-phoenix-client==3.5.0`, `arize-phoenix-otel==0.17.1`,
  `opentelemetry-sdk==1.45.0`.
- Separate server: `arize-phoenix==20.16.0`. Its dependencies include
  `arize-phoenix-evals==3.9.0`; our application neither installs that package
  directly nor uses its LLM evaluators.

Compatibility findings:

- `phoenix.otel.register()` 0.17.1 reads the removed exporter `_headers` attribute
  with OTel 1.45, even with verbose output disabled. We use the public Phoenix
  `TracerProvider` with the standard HTTP exporter instead.
- Attributes are not writable at the SDK's span-ending callback. Display mapping
  therefore copies completed spans at export, using the public `ReadableSpan` API.
- The synchronous experiment implementation rejects async tasks despite its broad
  type signature. The async client with explicit concurrency 1 is used.
- Evaluation runs are dataclasses, not dictionaries. Saved experiment artifacts
  serialize them structurally rather than converting them to opaque strings.

## Deterministic scoring

See [rubric changes](data/RUBRIC_CHANGES.md). `diagnosis_correct` is exact canonical
or scenario-specific alias membership. It is independent of evidence sufficiency.

| Evaluation | Definition |
|---|---|
| diagnosis_correct | Canonical/accepted label match |
| evidence_completeness | Retrieved required IDs / required ID count |
| evidence_sufficient | All required IDs retrieved |
| premature_stop | Required set incomplete at termination |
| tool_calls_used | Actual executions, including invalid/repeated attempts |
| irrelevant_calls | Returned evidence outside required/supporting sets |
| post_sufficiency_calls | Calls after first full required set |
| identical_repeated_calls | Same tool plus component repeated |
| redundant_investigation | Union of the preceding three call-index sets |
| latency_seconds | Timed agent execution |
| token_usage | Framework total tokens; unavailable stays null |

These are rubric-based diagnostics. An exploratory call can be useful even if it
is labeled irrelevant. Budget exhaustion and voluntary answers are distinguished
by recorded framework stop controls. No LLM judge is involved.

Official references: [Phoenix Python SDK](https://arize.com/docs/phoenix/resources/python-api),
[experiment API](https://arize-phoenix.readthedocs.io/projects/client/api/experiments.html),
[OpenTelemetry setup](https://arize.com/docs/phoenix/tracing/how-to-tracing/setup-tracing/custom-spans).
Installed interfaces were inspected and integration-tested.

## Optional repeatability

```bash
.venv/bin/python scripts/run_phoenix_repeatability.py
```

This makes 36 live runs on four existing scenarios with three repetitions at
budgets 4/6/8. Unlike the main runner it creates fresh experiments each invocation;
do not rerun it just to view results. Completed results and UI links are documented
in [trace findings](PHOENIX_TRACE_FINDINGS.md).
