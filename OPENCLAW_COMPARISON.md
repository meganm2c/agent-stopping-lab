# Microsoft–OpenClaw follow-up comparison

## Conclusion: YES, PARTIALLY GENERALIZED

Across the matched 20-run subsets, Microsoft had 6/20 correct-but-insufficient diagnoses and trajectory variation in 3/4 groups. OpenClaw had 10/20 and variation in 4/4 groups. These are observed patterns under different runtime/finalization implementations, not causal framework effects.

Microsoft source: [actual targeted-repeatability artifacts](results/phase3-variation/runs.jsonl), filtered to diag_007/diag_008, budgets 6/8, five repetitions each. The full Microsoft study had 50 runs; its 6/10 variation claim is not substituted for this matched four-group comparison.

## Findings

| Microsoft finding | Classification | OpenClaw evidence |
|---|---|---|
| Correct diagnosis can still have insufficient evidence | REPRODUCED | 10/20 correct-but-insufficient runs in 3/4 groups. |
| Stable outcomes can hide trajectory instability | REPRODUCED | 3/4 groups had stable labels across all five repetitions and varying ordered paths. |
| Larger budgets expose more discriminating evidence | REPRODUCED | Completeness 73.3% → 96.7%; sufficiency 10% → 90%. |
| Tool-budget semantics materially affect investigation quality | PARTIALLY REPRODUCED | 7/20 runs reached a blocked diagnostic request. Budget effects are observed descriptively; the causal effect of blocked-call versus tools-disabled semantics was not isolated. |

**Outcome variation also occurred:** 1 accepted final diagnosis was incorrect despite complete evidence. In diag_007/budget-8/repetition-5, the diagnostic-loop text named `database_connection_regression`, while the separate finalizer returned `api_configuration_issue`; the unchanged rubric scores the final label as incorrect. The finalizer did not receive that earlier answer. This observed label change makes finalization a material comparability caveat, not grounds to relabel the result or blame the harness.

The fourth classification separates evidence that budget constraints affect investigation from any claim about why the two harnesses differ. The finalizer cannot retrieve missing evidence; correctness after finalization still does not certify a sufficient diagnostic trajectory.

## Historical Microsoft matched subset

| Budget | N | Accuracy | Completeness | Sufficient | Premature stop | Avg executed calls |
|---|---:|---:|---:|---:|---:|---:|
| 6 | 10 | 100% | 80.8% | 40% | 60% | 6.00 |
| 8 | 10 | 100% | 100.0% | 100% | 0% | 7.40 |

## OpenClaw with explicit finalization adapter

| Budget | N | Accuracy | Completeness | Sufficient | Premature stop | Avg executed calls |
|---|---:|---:|---:|---:|---:|---:|
| 6 | 10 | 100% | 73.3% | 10% | 90% | 6.00 |
| 8 | 10 | 90% | 96.7% | 90% | 10% | 7.00 |

## What was held constant

- Exact model snapshot and temperature 0.
- Original diagnostic instruction and incident report text.
- Three diagnostic tool names/definitions backed by the same deterministic Python environment.
- Same executed-call budgets, scenario ground truth and evidence rubric.
- Fresh session/state; no memory, project context, adaptive controller or evaluation labels in model input.

## What differed

- Microsoft finalizes within its conversation with tools disabled at the framework cap and its response-format control. OpenClaw retains diagnostic tools until loop termination, may return blocked-call observations, then makes a separate fresh, zero-tool completion over frozen evidence.
- The adapter adds one model call and its full cost. It validates final JSON strictly but does not use provider-constrained JSON-schema decoding. OpenClaw’s isolated runtime does not expose that control.
- Effective diagnostic prompts include OpenClaw model identity and timestamp context. The finalizer receives a separate instruction/schema and observed evidence instead of Microsoft’s full conversation.
- Runtime versions, execution dates/provider conditions, process startup, bridge and finalization overhead differ. Budget/scenario order was serial, not randomized.
- Blocked calls are recorded separately and cannot execute additional tools. Their observations can affect loop stopping, unlike immediate tools-disabled finalization. The finalizer does not receive blocked calls as evidence.

Do not claim framework superiority, causality, or direct latency superiority. OpenClaw’s token/latency split is in [the results report](OPENCLAW_RESULTS.md); even its trace duration excludes some CLI startup that is included in full wall time.

The specific diag_007 budget-6 API-change versus database-log sufficiency branch did not recur. Lack of recurrence in five repetitions is not proof of impossibility. The diag_008 required-cache-evidence counts and exact examples are in the results report.

## Packaging recommendation

Package this as a bounded cross-harness follow-up for Aparna, with the failed-attempt ledger, exact trace exemplars and finalization caveat visible. It is sufficient to discuss evaluation engineering and whether patterns recur; it is not a framework leaderboard or a statistical population claim. Further model calls are not needed for that presentation. A fresh Microsoft subset using a matched evidence-only finalizer would be the next step if stronger causal comparability is required. Do not add adaptive stopping merely to strengthen the story.

**YES, PARTIALLY GENERALIZED**
