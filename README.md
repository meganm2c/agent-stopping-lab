# Agent Tool-Budget Lab

## Research question

How does constraining an AI agent's tool-call budget affect diagnostic accuracy,
evidence completeness, and unnecessary investigation?

## Motivation

Agent frameworks increasingly expose controls for bounding autonomous execution.
This project tests what those limits do at the application level, including their
effect on latency and token usage.

## Why the environment is synthetic

A fixed four-component world gives us known root causes, known evidence,
reproducible tasks, objective scoring rules, and controlled budget comparisons.
The world is deterministic; model decisions are not guaranteed to be deterministic.

## Architecture

```text
User report → Microsoft Agent Framework agent → three tools → synthetic environment
                         ↓
                structured diagnosis + run metadata

Evaluation-only scenario labels → deterministic evaluations

Native framework spans → Phoenix traces → dataset → budget experiments
```

`data/scenarios.json` holds eight tasks. Each has a `runtime` section with the
report and four component states, plus separate evaluation labels. `run_agent`
accepts only runtime state and an ID used in output metadata. The model sees the
same system prompt, tool definitions, report, and retrieved observations for every
budget. It receives neither the scenario ID nor evaluation labels.

Each environment owns a deep copy of its state. Three tools return typed Pydantic
records: `check_status`, `read_logs`, and `check_recent_change`. They validate
component names and expose stable evidence IDs. IDs such as `cache_logs` identify
the observation, not its diagnosis; use `(scenario_id, evidence_id)` across tasks.

The global diagnosis vocabulary is shared across all runs so exact root-cause
matching is meaningful. It is not tailored using a scenario's hidden answer.

## Current phase

**Phase 3 is complete:** the targeted repeatability study added 50 runs; the final
fixed-6/fixed-8/adaptive comparison added 72 runs with 1,368 deterministic evaluations.
The single adaptive policy reduced calls by 32.4% versus fixed-8, but accuracy fell
from 100% to 79.2%, total tokens rose 10.4%, and latency rose 48.7%. It did not meet
the preregistered success criteria. No policy tuning followed the negative result.

- [Final results and four Phoenix demo traces](ADAPTIVE_RESULTS.md)
- [Trajectory variation](TRAJECTORY_VARIATION.md)
- [Frozen hypothesis](ADAPTIVE_HYPOTHESIS.md) and [implementation](ADAPTIVE_DESIGN.md)
- [Phoenix setup](PHOENIX.md) and [Phase 2 findings](PHOENIX_TRACE_FINDINGS.md)
- [Original pilot report](PILOT_REPORT.md), preserving the original rubric/results

Fixed-8 remains the reliability reference for this workload. Laya, another model,
dataset expansion, and the interactive demo remain unimplemented.

## Files

```text
.env.example
.gitignore
pyproject.toml
README.md
data/
  scenarios.json
  scenario_notes.md
src/agent_tool_budget_lab/
  __init__.py
  agent.py
  config.py
  environment.py
  models.py
  scenarios.py
  tools.py
scripts/
  run_agent.py
  run_budget_pilot.py
  run_smoke_tests.py
tests/
  conftest.py
  test_agent.py
  test_environment.py
  test_pilot.py
  test_scenarios.py
  test_tools.py
```

## Install and run

Use Python 3.11+ from a source checkout (tested with Python 3.12.12):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env  # only if you do not already have a .env
```

Edit the ignored `.env` file:

```dotenv
MODEL_PROVIDER=openai
MODEL_NAME=<your model with tool calling and structured-output support>
OPENAI_API_KEY=<your API key>
```

For Azure, set `MODEL_PROVIDER=azure`, use your deployment name as `MODEL_NAME`,
and supply `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, and
`AZURE_OPENAI_API_VERSION`. Existing shell variables take precedence over `.env`.
Never put secrets in result files. Azure client construction is checked locally;
a live Azure request has not been tested.

```bash
python scripts/run_smoke_tests.py
python scripts/run_agent.py --scenario diag_001 --max-tool-calls 2
python scripts/run_agent.py --scenario diag_007 --max-tool-calls 2 --output results/hard-2.json
python scripts/run_agent.py --scenario diag_007 --max-tool-calls 6 --output results/hard-6.json
python scripts/run_budget_pilot.py
```

The pilot makes **32 live agent runs**, eight tasks at budgets 2/4/6/8, using the
same model and prompt. These incur provider usage. Results are flushed after each
run to a timestamped JSONL file in ignored `results/`. A custom `--output` must not
already exist, preventing accidental overwrite. A failed run with no tool calls
halts the pilot and preserves its error record.

## Framework configuration and compatibility

Direct runtime dependencies:

| Package | Pinned version | Purpose |
|---|---|---|
| `agent-framework-core` | 1.19.0 | Agent, tools, invocation loop |
| `agent-framework-openai` | 1.14.4 | OpenAI/Azure model adapter |
| `pydantic` | 2.13.5 | Dataset, tool, and output validation |
| `python-dotenv` | 1.2.3 | Local configuration |
| `pytest` (dev) | 9.1.1 | Deterministic tests |

Core and provider releases have independent version numbers. The installed adapter
requires core >=1.19.0. The current API is `Agent` with
`OpenAIChatCompletionClient(model=...)`; this client also supports Azure endpoint
and API-version arguments. Earlier examples using `OpenAIChatClient`, `model_id`,
or a separate Azure class do not match these pinned interfaces.

The exact native controls in `agent.py` are:

```python
client.function_invocation_configuration.update({
    "max_function_calls": max_tool_calls,
    "max_iterations": 20,
    "allow_concurrent_invocation": False,
})
response = await agent.run(report, options={
    "response_format": Diagnosis,
    "allow_multiple_tool_calls": False,
})
```

`max_function_calls` counts individual calls across model rounds; `max_iterations`
bounds model round trips. Twenty rounds is a fixed safety ceiling above the pilot's
largest budget. A final model response is requested with tools disabled once the
native call limit is reached. The final answer does not consume a tool call.

**Native call limits are best effort:** they are checked between batches. To keep
the experimental treatment exact, parallel model tool requests are disabled and
`ToolRecorder.invoke` also gates every execution. Oversized batches yield explicit
`tool_budget_exhausted` outputs for blocked requests. Records distinguish executed
calls from blocked requests. Invalid component attempts consume budget; repeated
calls also consume budget. The recorder runs synchronously with framework
concurrent invocation disabled, so checking and incrementing cannot interleave.

The final response uses a Pydantic structured-output schema and is validated again
locally. A refusal, invalid output, provider error, or 180-second timeout produces
an error record retaining completed tool calls. No hidden retry or repair agent
alters the experiment. Error records intentionally omit raw provider exception
bodies; use the exception class to start troubleshooting. Usage is the framework's
aggregated token metadata when a response completes; it can be unavailable on
failed runs.

Sources: [Microsoft's tool-budget example](https://github.com/microsoft/agent-framework/blob/main/python/samples/02-agents/tools/control_total_tool_executions.py),
[Microsoft function tools](https://learn.microsoft.com/en-us/agent-framework/agents/tools/function-tools),
[OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling).
Installed package signatures and implementation were checked before integration.

## Pilot interpretation

| Tasks | Difficulty | Required observations |
|---|---|---|
| diag_001–003 | easy | 1–2 |
| diag_004–006 | medium | 2–4 |
| diag_007–008 | hard | 4–6, with distractors |

The JSONL includes accuracy, evidence completeness, stopping before the required
set, calls after first collecting that set, exact repeated calls, and citations
not actually retrieved. Evaluation happens after the run; it never guides the
agent. `required_evidence` is the predeclared sufficient-evidence rubric. A model
may guess correctly or form a reasonable inference with a subset. Missing checklist
items therefore measure incomplete support under the rubric, not proof the model
could not know the answer. See [scenario notes](data/scenario_notes.md).

The console compares correct diagnoses, average calls, evidence completeness,
repetition, latency, and errors by budget. Tokens and full trajectories are in the
JSONL. Identical outcomes are explicitly flagged as a design issue. Small or noisy
differences also require inspection; a single run per cell cannot establish a
causal effect or reliable accuracy curve.

**Original pilot (rubric v1):** accuracy was 50%, 62.5%, 87.5%, and 87.5% at budgets 2/4/6/8.
Mean evidence completeness was 24.4%, 65.4%, 78.8%, and 90.2%; average tokens rose
from 1,267 to 3,552. The pilot shows a strong preliminary budget effect, but
`diag_006` exposes an overlapping-category scoring problem and some required sets
appear stricter than necessary. No repeated identical calls occurred. See the
[pilot report](PILOT_REPORT.md) before interpreting the plateau or expanding the
dataset. [Rubric v2](data/RUBRIC_CHANGES.md) documents the reviewed alias and evidence changes.

## Phoenix experiments

See [PHOENIX.md](PHOENIX.md) for installation, local server startup, tracing,
dataset creation, experiment commands, and evaluator definitions. Open the running
server at http://localhost:6006. The experiment names are `tool-budget-2`,
`tool-budget-4`, `tool-budget-6`, and `tool-budget-8`.

[PHOENIX_TRACE_FINDINGS.md](PHOENIX_TRACE_FINDINGS.md) contains direct trace links,
comparisons with the rescored pilot, representative failures, and repeatability
results. Model settings, runtime observations, and prompt remain unchanged.

### Live pilot measurement controls

`MODEL_TEMPERATURE` defaults to `0` and is applied identically across budgets.
No reasoning-effort option is sent. Use a model supporting temperature and the
existing tool/structured-output schema. The selected model is
`gpt-4.1-mini-2025-04-14`, verified through model discovery, a generation check,
and the live tool-calling pilot. It remains configurable through `MODEL_NAME`.

Run records now include prompt/runtime SHA-256 fingerprints, fixed model settings,
and per-model-round stop controls and usage. `tool_budget` means the framework
sent the final request with `tool_choice=none` after consuming the budget;
`agent_answered` means it answered without that forced stop. The former does not
prove it would have chosen to continue if given more budget. Other forced stops
and failed/timed-out runs are distinguished.

The pilot also writes a `.summary.json` file with budget and difficulty aggregates.
It reports required-evidence counts/IDs, missing evidence, and three separate
investigation measures: identical repeat calls, calls returning evidence outside
the required/supporting set, and calls after obtaining the full required set.
`redundant_calls` is the union of those call indices, so overlaps count once.
These are rubric-based measures: exploratory calls may be useful to an agent even
if they are outside the predeclared checklist. `premature_stop` means the final
retrieved evidence is incomplete, including failed runs; inspect the separate
error count before interpreting it as a model behavior. Missing token totals are
reported as unavailable, never as zero.

## Repository snapshot and reproducibility

See [REPRODUCIBILITY.md](REPRODUCIBILITY.md) for the captured dependency versions,
offline tests, archive checksums, local Phoenix limitations, and publication
boundaries. [Reviewed results](results/README.md) are included through an explicit
allowlist; new runs and local debug output remain ignored. Historical experiment
code and results are preserved unchanged.
