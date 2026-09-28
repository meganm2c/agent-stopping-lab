# Opportunity gate — limited, but observable

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
