---
title: When Should an Agent Stop?
emoji: 🔎
colorFrom: blue
colorTo: gray
sdk: static
app_file: index.html
pinned: false
---

# Agent Tool-Budget Lab

## Cross-Harness Evaluation of Agent Stopping with OpenClaw, Microsoft Agent Framework, and Phoenix

This project studies when tool-using agents should stop investigating. It began
as a controlled Microsoft Agent Framework experiment and was later replicated on
OpenClaw to test whether evidence-quality and trajectory-instability findings
generalized across harnesses. Phoenix organized trace inspection, experiment
comparison and deterministic evaluation.

**Cross-harness conclusion: YES, PARTIALLY GENERALIZED**

### OpenClaw follow-up

Two scenarios × budgets 6/8 × five repetitions: **20 accepted runs** from
21 physical attempts, including one preserved user interruption and a fresh
replacement. Exact model: `gpt-4.1-mini-2025-04-14`. Same tools, deterministic
environment and evidence rubric; fixed budgets only, no adaptive OpenClaw study.

| Tool budget | Accuracy | Evidence completeness | Evidence sufficient | Premature stop | Avg calls |
|---|---:|---:|---:|---:|---:|
| 6 | 100% | 73.3% | 10% | 90% | 6.0 |
| 8 | 90% | 96.7% | 90% | 10% | 7.0 |

**At budget 6, accuracy was 100%, but only 10% of runs had sufficient evidence.**
Trajectories/evidence sets varied in 4/4 groups; diagnoses were stable in 3/4.
Ten of twenty runs were correct but evidence-insufficient. One budget-8 run was
incorrect despite complete evidence; it remains in the accuracy denominator.
Premature stop means incomplete required evidence, including forced budget stops.

Correct-but-insufficient answers, stable outcomes with varying paths, and greater
evidence retrieval at higher budgets were **REPRODUCED**. Execution-limit effects
were **PARTIALLY REPRODUCED**. This is a robustness replication, not a causal
framework comparison or a claim of latency superiority.

OpenClaw required an explicit adapter-level tools-disabled finalizer. Effective
prompts, stopping semantics and runtime overhead differ from Microsoft. The
finalizer adds inference cost and can change the final label. See
[OpenClaw results and trace examples](OPENCLAW_RESULTS.md),
[cross-harness comparison](OPENCLAW_COMPARISON.md), and
[offline tests / live reproduction](spikes/openclaw-followup/TESTING.md).

## Static demo

**When Should an Agent Stop? — Cross-Harness Evaluation with OpenClaw + Phoenix**

The page leads with OpenClaw, compares the findings across harnesses, and replays
three report-derived OpenClaw examples. The original Microsoft results, 88-run
replay and Phoenix screenshots remain in a separate baseline section.

No API key, Python backend, Gradio server or running Phoenix is required.
Only same-origin static assets are loaded. A service worker enables offline reload
after the first successful load on a supporting browser/host.

```sh
bash scripts/start_static_demo.sh
```

Open `http://127.0.0.1:8000/`. See [static deployment instructions](STATIC_DEMO.md).
GitHub contains the site; uploading to a Hugging Face Static Space is a separate
step. The [original Gradio app](DEMO.md) remains available for the Microsoft replay.

## Original Microsoft baseline

The sections below describe the original Microsoft study and its separate phases.
Its final repeated comparison (24 runs per strategy) found:

- Fixed-8: 100% accuracy, 5.79 calls, 3,698 tokens/run, 4.85s/run.
- Adaptive: 79.2% accuracy, 3.92 calls, 4,083 tokens/run, 7.20s/run.
- Adaptive reduced calls by 32.4% but increased tokens by 10.4% and latency by 48.7%.

## Why this project

A tool budget changes what an agent can learn: small budgets can force unsupported
answers, while larger budgets can allow unnecessary investigation. This project
asks whether adaptive stopping can improve that tradeoff. Final-answer accuracy
alone cannot show whether an agent collected enough evidence or wasted work.

## System design

The environment has four components: `frontend`, `api`, `database`, and `cache`.
Three tools expose their state:

- `check_status(component)`
- `read_logs(component)`
- `check_recent_change(component)`

The [eight scenarios](data/scenarios.json) define root causes, required/supporting
evidence, and distractors. These evaluation fields stay hidden from the agent
and controller. Each run starts fresh and retrieves observations with stable IDs.

Synthetic incidents give reproducible tool outputs, objective ground truth, and
controlled difficulty. Model decisions and live inference latency can still vary.

```text
User report → Microsoft Agent Framework → Diagnostic tools → Synthetic environment
                       │                       │
                       └── model/tool spans ───┘
                                  ↓
                             Arize Phoenix
                    traces · dataset · evals · experiments
```

## How to read the results

| Study | Purpose and scope |
|---|---|
| [Original pilot](PILOT_REPORT.md) | Initial 32 runs; historical scoring rubric |
| [Phoenix fixed-budget sweep](PHOENIX_TRACE_FINDINGS.md) | 32 fresh runs at budgets 2/4/6/8, using the reviewed rubric |
| [Targeted repeatability](TRAJECTORY_VARIATION.md) | 50 runs across five scenarios at budgets 6/8 |
| [Final adaptive comparison](ADAPTIVE_RESULTS.md) | 72 runs: all eight scenarios, three configurations, three repetitions |

The tables below belong to separate run batches. Original pilot scores remain in
their report; [rubric corrections](data/RUBRIC_CHANGES.md) explain scoring changes.

## Experiment 1: Fixed tool budgets

The independent variable was maximum tool/function calls: **2 / 4 / 6 / 8**.
The Phoenix sweep ran each scenario once at each budget, for 32 runs.

Everything else stayed fixed: `gpt-4.1-mini-2025-04-14`, temperature 0, system
prompt, tools, scenarios, structured diagnosis schema, and framework configuration.
Parallel tool calls were disabled. An exact execution guard supplements the
framework limit because a batch can otherwise overshoot the cap.

| Tool budget | Accuracy | Evidence completeness | Avg. calls | Premature stops |
|---|---:|---:|---:|---:|
| 2 | 50.0% | 25.0% | 1.88 | 87.5% |
| 4 | 62.5% | 64.6% | 3.75 | 62.5% |
| 6 | 87.5% | 82.3% | 5.13 | 50.0% |
| 8 | 100% | 96.9% | 5.75 | 12.5% |

Higher budgets substantially improved accuracy and evidence collection. Eight
was the best observed fixed-budget configuration in this sweep.

## What Phoenix revealed

Ordered model/tool spans exposed what each tool returned, which evidence remained
missing, and whether the agent answered voluntarily or was forced to stop by its
budget. Traces distinguished correct guesses from supported diagnoses and showed
calls made after sufficient evidence was already available.

In the targeted study, each medium/hard scenario ran five times at each budget.
Diagnoses stayed stable within all **10 scenario/budget groups**, but **6 of 10**
had varying tool trajectories.

**Outcome stability can hide trajectory instability:** identical diagnoses can
come from different evidence paths, call counts, latency, tokens, and stop reasons.
The medium/hard study found no post-sufficiency calls. Recurring opportunities to
stop sooner appeared in earlier easy-case traces, limiting the expected benefit.

## Experiment 2: Adaptive stopping

The hypothesis was that a model-based controller could inspect observed evidence
after each tool result and return structured `STOP` or `CONTINUE` decisions.
The same model snapshot served as the controller, with a hard ceiling of eight
diagnostic tool calls.

The controller received only the user report and observed tool names, arguments,
outputs, and evidence IDs. It could not see the root cause, required/supporting
evidence labels, distractor labels, difficulty, or evaluation metadata. Every
check was traced in Phoenix. The [prompt and success criteria](ADAPTIVE_HYPOTHESIS.md)
were frozen before the final comparison and were not tuned afterward.

The final experiments—`fixed-budget-6`, `fixed-budget-8`, and
`adaptive-stopping`—used the same dataset, with three repetitions per scenario.
Their repeated measurements are distinct from Experiment 1.

| Metric | Fixed-6 | Fixed-8 | Adaptive |
|---|---:|---:|---:|
| Accuracy | 87.5% | 100% | 79.2% |
| Evidence completeness | 83.3% | 97.9% | 70.1% |
| Evidence sufficiency | 54.2% | 91.7% | 33.3% |
| Avg. tool calls | 4.96 | 5.79 | 3.92 |
| Total tokens/run | 3,047 | 3,698 | 4,083 |
| Seconds/run | 4.31 | 4.85 | 7.20 |

**The hypothesis was not supported.** Fewer tool calls did not lower system cost:
controller overhead increased total tokens and latency. **16 of 24 adaptive runs
stopped without sufficient evidence.**

The controller sometimes accepted a plausible explanation before resolving the
cause. In one [failure trace](ADAPTIVE_RESULTS.md#adaptive-failure-or-edge-case),
it stopped after slow API reads, before database health and cache evidence were
checked; the agent then attributed the incident to the wrong cause.

## Main developer learnings

- Tool budgets affect reliability.
- Accuracy can hide missing evidence and unnecessary investigation.
- Stable outputs can hide unstable tool trajectories.
- Fewer tool calls do not guarantee lower total inference cost.
- Control models add cost and failure modes; evaluate the whole system.

## Why Phoenix mattered

Phoenix connected deterministic scores to the executions that produced them:

- **Experiment comparison:** configurations shared a dataset and evaluator definitions.
- **Evidence-gap analysis:** model/tool spans showed each observation and forced
  versus voluntary stopping, including correct answers with incomplete evidence.
- **Controller diagnosis:** `stopping_check` spans exposed the observed input,
  STOP/CONTINUE reason, and model usage behind premature decisions and added cost.

The working **Metrics**, **List**, and trace views support comparison and diagnosis.
[Integration notes](ADAPTIVE_DESIGN.md#phoenix-trace-page-workaround) document the
local server's annotation workaround; experiment evaluations were preserved.

![Phoenix comparison of fixed budgets and adaptive stopping](results/screenshots/adaptive-comparison-metrics.png)

The screenshot uses Fixed-6 as its comparison baseline; the headline percentage
changes compare Adaptive with Fixed-8.

## Evaluation design

Objective ground truth supports deterministic Python evaluators. **No LLM-as-a-judge
was used for the core metrics**; the stopping model was an online controller.

| Metric | Definition |
|---|---|
| Diagnosis correctness | Canonical or explicitly accepted scenario-specific label |
| Evidence completeness / sufficiency | Fraction of required IDs retrieved / all required IDs retrieved |
| Premature stop | Run ended with incomplete required evidence |
| Tool calls used | Executed attempts, including invalid or repeated attempts |
| Irrelevant calls | Evidence outside the required/supporting rubric |
| Post-sufficiency calls | Calls after the required set was complete |
| Identical repeated calls | Repeated tool/component pair |
| Latency / token usage | Agent execution time and reported model usage |
| Adaptive metadata | Effective STOP, stopping index, false early stop, controller overhead, total tokens |

Missing checklist evidence does not prove a diagnosis was impossible; exploratory
calls may still be useful. False early stops are scored **after execution** using
hidden labels. [Evaluator details](ADAPTIVE_DESIGN.md#metric-definitions) explain
the accounting and denominators.

## Repository structure

```text
src/agent_tool_budget_lab/  Agent, environment, tools, stopper, tracing, evaluators
scripts/                   Run experiments and analyze/export results
data/                      Scenarios, evidence rubric, documented corrections
results/                   Reviewed outputs, trace exports, screenshots, checksums
tests/                     Offline tests using scripted model responses
spikes/openclaw-followup/   Validated OpenClaw adapter, offline tests and fixtures
static/                    Static replay assets and curated OpenClaw report extract
OPENCLAW_RESULTS.md        OpenClaw measurements and trace examples
OPENCLAW_COMPARISON.md     Cross-harness interpretation and caveats
PHOENIX_TRACE_FINDINGS.md   Fixed-budget trace analysis
TRAJECTORY_VARIATION.md     Targeted repeatability study
ADAPTIVE_HYPOTHESIS.md      Frozen policy and acceptance criteria
ADAPTIVE_RESULTS.md         Final comparison and failure analysis
REPRODUCIBILITY.md          Detailed setup and measurement controls
```

## Reproducing the original Microsoft study

**Review the included results without rerunning models.** For intentional live
reproduction, use a separate checkout: Phase 3 writes to the archived result paths.
Commands below incur API usage when they run agents or experiments.

```bash
git clone https://github.com/meganm2c/agent-stopping-lab.git
cd agent-stopping-lab
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-agent-lock.txt
.venv/bin/python -m pip install --no-deps -e .
test -f .env || cp .env.example .env
```

Set `OPENAI_API_KEY` privately in `.env`, plus:

```dotenv
MODEL_PROVIDER=openai
MODEL_NAME=gpt-4.1-mini-2025-04-14
MODEL_TEMPERATURE=0
```

Keep `.env` ignored and never commit it. From the repository root in a separate
terminal, install and start the local Phoenix server:

```bash
python3.12 -m venv .phoenix-venv
.phoenix-venv/bin/python -m pip install -r requirements-phoenix-lock.txt
bash scripts/start_phoenix.sh
```

Open `http://localhost:6006`. Local Phoenix state under `.phoenix/` is not version
controlled. Back in the project terminal:

```bash
# Offline tests; no API credentials needed
.venv/bin/python -m pytest -q

# One diagnostic run, then an easy/hard Phoenix trace check
.venv/bin/python scripts/run_agent.py --scenario diag_001 --max-tool-calls 2
.venv/bin/python scripts/run_phoenix_gate.py

# Fixed-budget Phoenix dataset and experiments
.venv/bin/python scripts/run_phoenix_experiments.py

# Phase 3: targeted repeatability, then fixed-6/fixed-8/adaptive comparison
.venv/bin/python scripts/run_phase3.py variation
.venv/bin/python scripts/run_phase3.py comparison
```

**Phase 3 prerequisite:** the runner requires the archived Phase 2 dataset
ID/version and hashes. Create the fixed-budget dataset first and verify IDs match;
historical IDs and trace URLs are not portable between Phoenix servers.
[Reproducibility details](REPRODUCIBILITY.md) cover this limitation and configuration;
[Phoenix setup](PHOENIX.md) includes analysis commands.

## Results and reports

- [OpenClaw results](OPENCLAW_RESULTS.md) — 20-run follow-up and curated trace examples
- [Cross-harness comparison](OPENCLAW_COMPARISON.md) — controls, differences and classifications
- [OpenClaw tests and reproduction](spikes/openclaw-followup/TESTING.md) — offline fixtures and separate live setup

- [Original pilot](PILOT_REPORT.md) — historical rubric and initial measurements
- [Phoenix setup](PHOENIX.md) and [trace findings](PHOENIX_TRACE_FINDINGS.md)
- [Trajectory variation](TRAJECTORY_VARIATION.md) — repeated scenario/budget groups
- [Adaptive hypothesis](ADAPTIVE_HYPOTHESIS.md) — frozen prompt and success criteria
- [Adaptive design](ADAPTIVE_DESIGN.md) — implementation, schema, tracing, evaluators
- [Adaptive results](ADAPTIVE_RESULTS.md) — full metrics and four representative traces
- [Reproducibility](REPRODUCIBILITY.md) and [archived artifacts](results/README.md)

## Limitations

Eight synthetic scenarios, one model snapshot, and narrow diagnostic tools limit
generalization: there is no universal best tool budget here. Repetitions are not
independent incident types, and experiment order/API variation affect latency.
The adaptive controller was intentionally not tuned after the final results.

## Future work

Improve representations of unresolved uncertainty and test broader scenarios,
frameworks, and models. Cheaper controllers or learned System-1 decision models
become useful cost-reduction experiments only after stopping reliability improves.
This result does not yet justify Laya.
