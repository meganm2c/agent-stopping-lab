# Adaptive stopping hypothesis

## Preregistered before adaptive runs

The design and criteria below were written before any adaptive model call or final
comparison. Implementation is conditional on a trace-based opportunity review
in `TRAJECTORY_VARIATION.md`. A negative result will be retained without prompt
search, dataset changes, or repeated tuning.

Hypothesis: a model checking the observed evidence after each diagnostic tool can
preserve nearly all fixed-8 accuracy while reducing investigation enough to offset
its own token or latency overhead.

## Success criteria

For the planned 24 runs per configuration (8 scenarios × 3 repetitions), require:

1. Adaptive accuracy is no more than one correct run below fixed-8 (4.17 percentage
   points), with all failures included in the denominator.
2. Average executed diagnostic calls fall by at least 10% relative to fixed-8.
3. Mean total tokens **or** mean end-to-end agent latency falls by at least 5%,
   including all stopping checks and the final diagnostic answer.
4. False early stops occur in at most 1/24 adaptive runs. Also report the rate
   conditional on the stopper triggering, with its denominator.
5. No budget violations or execution/parse failures.

These are descriptive acceptance thresholds for this small workload, not a
statistical noninferiority claim. Evidence completeness and sufficiency remain
separate from diagnosis accuracy. Report per-scenario results so repeated easy
cases cannot hide failures on hard cases. Compare fixed-6 as the simpler option.

## Single candidate policy

Use `gpt-4.1-mini-2025-04-14`, temperature 0, as a separate structured decision
request after each completed tool. Supply only the user report and observed
ordered tool names, arguments, outputs, and evidence IDs. Do not supply scenario
ID, difficulty, reference answer, evaluation labels, future world state, or the
required/supporting/distractor rubric. No tentative diagnosis is fabricated when
the diagnostic agent has not emitted one.

Proposed exact system prompt:

```text
You decide whether a diagnostic agent should continue investigating a software incident.
Use only the user report and observed tool results supplied below.
Return STOP only when the observed evidence supports a coherent diagnosis and another
call is unlikely to materially improve confidence or resolve an important ambiguity.
Return CONTINUE when important uncertainty remains. Do not assume unobserved facts.
Return a decision (STOP or CONTINUE) and a short reason grounded in observed evidence.
```

Schema: `{decision: Literal["STOP", "CONTINUE"], reason: str}`; no extra fields.
The decision/reason is logged, but not fed back as diagnostic evidence. STOP
requests a final structured diagnosis with tools disabled, using the unchanged
agent prompt and observed tool results. Hard ceiling remains eight executions.
A check at the ceiling is logged but cannot claim an effective adaptive stop;
the hard ceiling already requires the final answer. Check failures fall back to
CONTINUE and remain visible. No retry or revised policy is selected based on scores.

## Measurement and controls

- Keep the original Phoenix dataset/version, worlds, prompt, three tools, output
  schema, model snapshot, temperature, and framework settings.
- Run `fixed-budget-6`, `fixed-budget-8`, `adaptive-stopping`, three repetitions
  per existing example, serial execution. Repetition IDs identify comparable
  cells, but no shared stochastic seed creates identical counterfactuals.
- Existing `token_usage` retains diagnostic-agent tokens. Add explicit stopper
  and total tokens; never silently redefine the old evaluator.
- End-to-end latency includes stopping checks; report check latency separately.
- `avoided_calls_vs_budget8 = max(0, 8 - calls)` is ceiling slack, not a causal
  saving. Separately compare means against actual fixed-8 executions.
- Outcomes and token costs may vary even at temperature 0. Latency is affected
  by request order and network conditions; avoid causal overhead claims from
  differences between independent runs.

If stopping works but overhead prevents savings, a smaller decision model is a
reasonable follow-up. If the stopping signal itself is unreliable, cost reduction
alone does not justify Laya. No demo or Laya implementation is part of this phase.
