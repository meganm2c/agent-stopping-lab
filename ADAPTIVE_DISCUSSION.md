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
