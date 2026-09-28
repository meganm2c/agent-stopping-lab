# Trajectory variation study

50 fresh runs: all three medium and both hard scenarios, budgets 6/8, five repetitions per cell. The same eight-example Phoenix dataset/version was used through a local five-example view; no dataset rows were added or changed. Original prompt/runtime/model/settings fingerprints, deterministic evaluations, and fetched tool spans were verified. Execution was serial, with budget 6 before budget 8; latency comparisons may include order/network effects.

| Scenario | Budget | Modal diagnosis fraction | Calls mean (min–max; SD) | Sequences | Evidence sets | Stops | Post-sufficiency | Irrelevant | Tokens | Seconds |
|---|---:|---:|---|---:|---:|---|---:|---:|---:|---:|
| diag_004 | 6 | 100% | 6.00 (6–6; 0.00) | 1 | 1 | {'tool_budget': 5} | 0.00 | 4.00 | 3737 | 5.58 |
| diag_005 | 6 | 100% | 4.00 (4–4; 0.00) | 1 | 1 | {'agent_answered': 5} | 0.00 | 2.00 | 2356 | 3.54 |
| diag_006 | 6 | 100% | 6.00 (6–6; 0.00) | 2 | 2 | {'tool_budget': 5} | 0.00 | 4.00 | 3648 | 4.85 |
| diag_007 | 6 | 100% | 6.00 (6–6; 0.00) | 2 | 2 | {'tool_budget': 5} | 0.00 | 2.00 | 3754 | 4.81 |
| diag_008 | 6 | 100% | 6.00 (6–6; 0.00) | 2 | 2 | {'tool_budget': 5} | 0.00 | 2.00 | 3758 | 4.93 |
| diag_004 | 8 | 100% | 7.80 (7–8; 0.40) | 3 | 3 | {'agent_answered': 1, 'tool_budget': 4} | 0.00 | 4.40 | 5120 | 5.94 |
| diag_005 | 8 | 100% | 4.00 (4–4; 0.00) | 1 | 1 | {'agent_answered': 5} | 0.00 | 2.00 | 2359 | 3.86 |
| diag_006 | 8 | 100% | 7.00 (7–7; 0.00) | 2 | 2 | {'agent_answered': 5} | 0.00 | 4.00 | 4389 | 5.60 |
| diag_007 | 8 | 100% | 6.80 (6–7; 0.40) | 2 | 2 | {'agent_answered': 5} | 0.00 | 2.00 | 4374 | 5.46 |
| diag_008 | 8 | 100% | 8.00 (8–8; 0.00) | 1 | 1 | {'tool_budget': 5} | 0.00 | 2.00 | 5364 | 6.00 |

Diagnoses were stable in 10/10 groups; trajectories varied in 6/10 groups. Consistency uses exact predicted labels (modal-label count / runs); scoring still accepts scenario-specific aliases. Standard deviation is descriptive population SD across the five observed runs, not uncertainty over independent scenarios.

## Representative sequences

### diag_004

- [Budget 6, repetition 5](http://localhost:6006/projects/UHJvamVjdDoxMg==/traces/4a9217d4db6d2dede2f6ed5f4a9851b9): check_status(frontend) → check_status(api) → check_status(database) → check_status(cache) → read_logs(api) → check_recent_change(api). Diagnosis `api_dependency_issue`; complete=False; post-sufficiency=0; stop=`tool_budget`.
- [Budget 8, repetition 5](http://localhost:6006/projects/UHJvamVjdDoxMw==/traces/f20f8deec6923abb3a33c788dbf554f8): check_status(frontend) → check_status(api) → check_status(database) → check_status(cache) → read_logs(api) → check_recent_change(api) → check_recent_change(cache). Diagnosis `cache_configuration_regression`; complete=False; post-sufficiency=0; stop=`agent_answered`.
- [Budget 8, repetition 4](http://localhost:6006/projects/UHJvamVjdDoxMw==/traces/bf251b839ace81f415c60ac62d3d2bfb): check_status(frontend) → check_status(api) → check_status(database) → check_status(cache) → read_logs(api) → check_recent_change(api) → read_logs(database) → read_logs(cache). Diagnosis `cache_configuration_regression`; complete=False; post-sufficiency=0; stop=`tool_budget`.
- [Budget 8, repetition 2](http://localhost:6006/projects/UHJvamVjdDoxMw==/traces/17dac184ec307577718e8ac620b48b9e): check_status(frontend) → check_status(api) → check_status(database) → check_status(cache) → read_logs(api) → check_recent_change(api) → check_recent_change(cache) → read_logs(cache). Diagnosis `cache_configuration_regression`; complete=True; post-sufficiency=0; stop=`tool_budget`.

### diag_005

- [Budget 6, repetition 5](http://localhost:6006/projects/UHJvamVjdDoxMg==/traces/8a5ac1464664be1043e1f463c4d5f919): check_status(api) → check_status(database) → read_logs(database) → check_recent_change(database). Diagnosis `database_connection_regression`; complete=True; post-sufficiency=0; stop=`agent_answered`.
- [Budget 8, repetition 5](http://localhost:6006/projects/UHJvamVjdDoxMw==/traces/cb82dc2c950067c297850d3bc1e639a9): check_status(api) → check_status(database) → read_logs(database) → check_recent_change(database). Diagnosis `database_connection_regression`; complete=True; post-sufficiency=0; stop=`agent_answered`.

### diag_006

- [Budget 6, repetition 5](http://localhost:6006/projects/UHJvamVjdDoxMg==/traces/31d48e78ce0276b24796eed78f1686a5): check_status(frontend) → check_status(api) → check_status(database) → check_status(cache) → read_logs(api) → check_recent_change(cache). Diagnosis `api_dependency_issue`; complete=False; post-sufficiency=0; stop=`tool_budget`.
- [Budget 6, repetition 1](http://localhost:6006/projects/UHJvamVjdDoxMg==/traces/dfaa7a9b0c0341983e563f915e7c154a): check_status(frontend) → check_status(api) → check_status(database) → check_status(cache) → read_logs(api) → read_logs(cache). Diagnosis `api_dependency_issue`; complete=False; post-sufficiency=0; stop=`tool_budget`.
- [Budget 8, repetition 5](http://localhost:6006/projects/UHJvamVjdDoxMw==/traces/f8cf3a7ea2aff0cf83c00536fbff6b1a): check_status(frontend) → check_status(api) → check_status(database) → check_status(cache) → read_logs(api) → check_recent_change(cache) → check_recent_change(api). Diagnosis `api_configuration_issue`; complete=True; post-sufficiency=0; stop=`agent_answered`.
- [Budget 8, repetition 1](http://localhost:6006/projects/UHJvamVjdDoxMw==/traces/f59afad651bb23268f858383c7babdce): check_status(frontend) → check_status(api) → check_status(database) → check_status(cache) → read_logs(api) → read_logs(cache) → check_recent_change(api). Diagnosis `api_configuration_issue`; complete=True; post-sufficiency=0; stop=`agent_answered`.

### diag_007

- [Budget 6, repetition 5](http://localhost:6006/projects/UHJvamVjdDoxMg==/traces/b45e487e5702a37f06a7aa4840a40c2d): check_status(frontend) → check_status(api) → check_status(database) → check_status(cache) → read_logs(api) → check_recent_change(api). Diagnosis `database_connection_regression`; complete=True; post-sufficiency=0; stop=`tool_budget`.
- [Budget 6, repetition 4](http://localhost:6006/projects/UHJvamVjdDoxMg==/traces/8f616bfc517841cb34eb408023a3846b): check_status(frontend) → check_status(api) → check_status(database) → check_status(cache) → read_logs(api) → read_logs(database). Diagnosis `database_connection_regression`; complete=False; post-sufficiency=0; stop=`tool_budget`.
- [Budget 8, repetition 4](http://localhost:6006/projects/UHJvamVjdDoxMw==/traces/2ffb9f066c688aead3e290dd70828cbd): check_status(frontend) → check_status(api) → check_status(database) → check_status(cache) → read_logs(api) → check_recent_change(api). Diagnosis `database_connection_regression`; complete=True; post-sufficiency=0; stop=`agent_answered`.
- [Budget 8, repetition 5](http://localhost:6006/projects/UHJvamVjdDoxMw==/traces/d9a82f34cdc0c44466e6117fecedc6c3): check_status(frontend) → check_status(api) → check_status(database) → check_status(cache) → read_logs(api) → read_logs(database) → check_recent_change(api). Diagnosis `database_connection_regression`; complete=True; post-sufficiency=0; stop=`agent_answered`.

### diag_008

- [Budget 6, repetition 5](http://localhost:6006/projects/UHJvamVjdDoxMg==/traces/055e7668a504954ec0c0699c53eedf01): check_status(frontend) → check_status(api) → check_status(cache) → check_status(database) → read_logs(frontend) → read_logs(api). Diagnosis `cache_configuration_regression`; complete=False; post-sufficiency=0; stop=`tool_budget`.
- [Budget 6, repetition 4](http://localhost:6006/projects/UHJvamVjdDoxMg==/traces/915de43ed5cf8b864672e2645ea0f4e1): check_status(frontend) → check_status(api) → check_status(database) → check_status(cache) → read_logs(cache) → check_recent_change(cache). Diagnosis `cache_configuration_regression`; complete=False; post-sufficiency=0; stop=`tool_budget`.
- [Budget 8, repetition 5](http://localhost:6006/projects/UHJvamVjdDoxMw==/traces/89e1193f5355d80fee506a5bfc601181): check_status(frontend) → check_status(api) → check_status(cache) → check_status(database) → read_logs(frontend) → read_logs(api) → read_logs(cache) → check_recent_change(cache). Diagnosis `cache_configuration_regression`; complete=True; post-sufficiency=0; stop=`tool_budget`.

## Interpretation boundary

Post-sufficiency is an evaluation-only checklist measure. It locates observable opportunities to save calls; it does not prove an online stopper can recognize those moments. Final diagnoses are observed at termination only. Do not infer stable intermediate diagnoses or hidden reasoning from a final answer. The stopper must decide from observed runtime evidence without these checklist labels.


## Opportunity gate — limited, but observable

The targeted medium/hard study has **zero post-sufficiency calls across all 50
runs**. This gives no support for a broad claim that these cases keep investigating
after completion. In particular, extra calls on `diag_008` at budget 8 complete
previously missing evidence. `diag_005` already answers voluntarily after four.

There is a narrower, recurring opportunity in the unchanged easy cases from the
previous pilot and Phoenix traces. In both independent studies, `diag_001` at
budgets 4/6/8 makes two calls after its first API status explicitly reports an
invalid zero request limit. `diag_003` at budgets 6/8 makes two/three calls after
database status and logs establish CPU saturation due to full-table scans. The
later calls return no changes or normal component observations. These patterns
recur across both prior studies, not just one selected run.

This justifies testing one generic evidence-based STOP/CONTINUE policy over the
full eight-case workload, with modest expectations. It does not justify tuning
against these scenario IDs or their checklist completion. A stopper may recognize
direct causal evidence online; whether it also stops too early on ambiguous
cases is precisely the experiment. The required check after every tool may cost
more than these localized savings. The preregistered hypothesis counts that cost.

In the targeted study, differing routes on `diag_007` reach the same supported
diagnosis in six or seven calls. That is an exploration-order opportunity rather
than demonstrated post-sufficiency waste; the stopper cannot select a better tool.
Stable diagnoses at budgets 6 and 8 on `diag_006` (allowing its documented alias)
and `diag_008` do not imply that their additional supporting observations lack value.

The new study did not show a dramatic within-cell tool-count efficiency gap: the
largest observed difference was one call (six versus seven for `diag_007`, seven
versus eight for `diag_004`). Calling those routes “much more efficient” would
overstate this evidence. Budget 8 added investigation without changing the scored
label on `diag_006` and `diag_008`, while raising evidence completeness. The report
keeps label stability distinct from evidence value.
