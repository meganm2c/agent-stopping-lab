# Reproducing and reviewing this repository

The published snapshot preserves the completed research. Repository cleanup did
not rerun experiments, change the policy, rescore results, or edit observations.

## Offline review

Start with [README.md](README.md), [ADAPTIVE_RESULTS.md](ADAPTIVE_RESULTS.md), and
[the archived result inventory](results/README.md). Raw task/evaluation exports,
trace exports, summaries, and selected screenshots are included. No API key or
Phoenix database is needed to read them.

Verify the archived result bytes from the repository root:

```bash
shasum -a 256 -c results/SHA256SUMS
```

## Python environment and tests

The research used Python 3.12.12. Dependency snapshots capture the installed
versions without local paths, credentials, or private package URLs. They are
version pins, not cross-platform wheel/hash lockfiles.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-agent-lock.txt
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m pytest -q
```

The existing `pyproject.toml` also supports the smaller normal installation:
`pip install -e '.[dev,phoenix]'`. The snapshot additionally pins transitive
packages to the versions used for the completed experiments. Neither command runs
live experiments. Tests use scripted model responses and require no credentials.

## Phoenix and live execution

[PHOENIX.md](PHOENIX.md) documents server startup and experiment commands. For the
captured server environment:

```bash
python3.12 -m venv .phoenix-venv
.phoenix-venv/bin/python -m pip install -r requirements-phoenix-lock.txt
bash scripts/start_phoenix.sh
```

The local `.phoenix/` database is intentionally excluded. A new server starts
empty. The localhost trace links and IDs in historical reports refer to the
original local server; static trace exports and screenshots remain available in
the repository. Installing Phoenix does not restore that original database.

Live reruns require a private `.env` copied from `.env.example`, an OpenAI key,
and `MODEL_NAME=gpt-4.1-mini-2025-04-14` with temperature 0. They incur API usage
and may produce different trajectories. Keep the published results as the
historical reference and use a separate checkout when intentionally rerunning.

The Phase 3 runner checks the original dataset ID/version and hashes from the
archived Phase 2 manifest. On a fresh Phoenix instance, create the Phase 2 dataset
first and check the resulting IDs; historical IDs are not portable between
servers. The runner will refuse mismatches. No automatic migration or new live
run was added during repository cleanup.

See [ADAPTIVE_DESIGN.md](ADAPTIVE_DESIGN.md) for the documented Phoenix
span-annotation compatibility workaround. The original policy and criteria are
in [ADAPTIVE_HYPOTHESIS.md](ADAPTIVE_HYPOTHESIS.md).

## Publication boundaries

`.gitignore` allows only the reviewed result directories/files and screenshots.
New result directories, logs, failed-attempt exports, discovery/debug output,
removed duplicate span annotations, environments, caches, credentials, and Phoenix
state remain local. Earlier reports describe results as ignored; this publication
step adds the explicit archive allowlist without changing those historical reports.

`.env` and `.env.*` are ignored, with `.env.example` explicitly allowed. The
example contains empty credential fields. Never force-add private environment
files or the Phoenix database. At the initial publication audit, no prior Git history existed and no committed
secrets were found.

## Runtime and data boundaries

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
an error record retaining completed tool calls. No repair agent is added; experiment-level retries are disabled for Phoenix runs.
Provider transport retry behavior is inherited from the installed client. Error records intentionally omit raw provider exception
bodies; use the exception class to start troubleshooting. Usage is the framework's
aggregated token metadata when a response completes; it can be unavailable on
failed runs.

Sources: [Microsoft's tool-budget example](https://github.com/microsoft/agent-framework/blob/main/python/samples/02-agents/tools/control_total_tool_executions.py),
[Microsoft function tools](https://learn.microsoft.com/en-us/agent-framework/agents/tools/function-tools),
[OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling).
Installed package signatures and implementation were checked before integration.


## Measurement controls

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


## Additional configuration and local pilot

For Azure, set `MODEL_PROVIDER=azure`, use your deployment name as `MODEL_NAME`,
and supply `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, and
`AZURE_OPENAI_API_VERSION`. Existing shell variables take precedence over `.env`.
Never put secrets in result files. Azure client construction is checked locally;
a live Azure request has not been tested.

The source supports Python 3.11+; the dependency snapshots were captured on
Python 3.12.12. The local pilot runner is an alternative to Phoenix orchestration:

```bash
.venv/bin/python scripts/run_smoke_tests.py
.venv/bin/python scripts/run_budget_pilot.py
```

The pilot makes 32 live runs. It flushes each result to a timestamped JSONL file
and writes a summary; an explicitly supplied `--output` must not already exist.
A failed run with no tool calls halts the pilot and preserves its error record.
The single-scenario `run_agent.py --output` option does overwrite its target, so
choose a new path if saving an exploratory run.

Phase 3 writes into the archived `results/phase3-variation/` and
`results/phase3-comparison/` paths. Use a separate checkout for intentional live
reproduction. Completed matching Phoenix experiments may be reused by the runners.
Historical trace URLs are local-server references, not public hosted results.
