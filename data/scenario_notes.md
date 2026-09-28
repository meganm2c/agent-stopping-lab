# Pilot scenario design

All observations refer to the same fixed incident window. Components not involved
in a fault have explicit normal observations and no recent change. Reports name
symptoms, not hidden fault labels. Tool order is unrestricted.

| ID | Hidden cause | Evidence rubric and intended diagnostic path |
|---|---|---|
| diag_001 | API configuration issue | API status directly reports rejection caused by a zero request limit. One useful call. |
| diag_002 | Frontend deployment regression | Frontend logs identify the missing bundle; the change record links it to a release omission. Two useful calls. |
| diag_003 | Database saturation | Database status reports capacity exhaustion; logs identify CPU-bound scans rather than connection or lock faults. Two useful calls. |
| diag_004 | Cache configuration regression | API degradation establishes impact; healthy database rules out saturation; cache expiry logs and TTL change establish mechanism. Four useful calls. Frontend CPU elevation is incidental. |
| diag_005 | Database connection regression | Database TLS failures and protocol change establish the mismatch. Two required calls; API write failures support the affected path. |
| diag_006 | API dependency issue | API logs identify cache access failure; cache health rules out a cache outage; the API destination change establishes wrong-port routing. Three useful calls. |
| diag_007 | Database connection regression | API status/logs establish blocked handlers and pool waits; database status rules out server saturation; API change identifies a reduced client pool. Four required calls; database logs provide supporting confirmation. Frontend analytics CPU is a distractor. |
| diag_008 | Cache configuration regression | Frontend logs locate stale data upstream; API logs establish successful writes and invalidation namespace; database status rules out replica lag; cache status rules out general overload; cache logs/change establish a namespace mismatch. Six useful calls. A frontend theme change is irrelevant. |

## Interpretation limits to inspect in live runs

These are explicit, reproducible sufficient-evidence checklists, not a theorem
that no smaller set can support the diagnosis. In particular, recent-change
records can suggest the cause early. Accuracy can therefore exceed completeness.
The pilot must establish whether the harder tasks actually require more
investigation from the chosen model. If confident diagnoses routinely shortcut the
intended path, revise the scenario evidence and review the rubric before scaling.

The same machine-readable root-cause category can appear in different scenarios;
exact matching evaluates the category, while explanation and evidence IDs preserve
more specific details. Diagnosis vocabulary is fixed globally in the baseline
prompt. Evidence IDs repeat across scenarios and must be joined with scenario ID.

Optional supporting evidence and distractors are disjoint from required evidence.
Other normal observations remain available but unlabeled; their absence from
`distractor_evidence` does not mean they are required. Repeated calls are counted
by exact tool name and component. Calls after checklist completion are labeled
excess by this rubric, even if the model considers them useful confirmation.

Current rubric is v2; see [documented changes](RUBRIC_CHANGES.md). The original pilot report retains v1 scores.
