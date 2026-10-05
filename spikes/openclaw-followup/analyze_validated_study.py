"""Analyze only the 20 accepted finalized study rows; never invoke inference."""
import json
from collections import Counter
from itertools import combinations,product
from statistics import mean
from adapter import ROOT,dump
from analyze import summarize,grouped,trajectory,path,best_pairs
from agent_tool_budget_lab.scenarios import load_scenarios
OUT=ROOT/'results/openclaw-followup/study-v1'

def extended(rows):
    s=summarize(rows)
    if 'cost_split' in rows[0]:s['cost_split_mean']={k:mean(r['cost_split'][k] for r in rows) for k in rows[0]['cost_split']}
    s['diagnoses_stable']=len(s['diagnoses'])==1
    s['evidence_sufficiency_varies']=len({r['metrics']['evidence_sufficient'] for r in rows})>1
    s['tool_counts']=sorted({r['run']['number_of_tool_calls'] for r in rows})
    s['tokens_range']=[min(r['run']['usage']['total_token_count'] for r in rows),max(r['run']['usage']['total_token_count'] for r in rows)]
    s['latency_range']=[min(r['run']['elapsed_seconds'] for r in rows),max(r['run']['elapsed_seconds'] for r in rows)]
    s['same_diagnosis_different_sufficiency']=any(a['run']['final_diagnosis']['predicted_root_cause']==b['run']['final_diagnosis']['predicted_root_cause'] and a['metrics']['evidence_sufficient']!=b['metrics']['evidence_sufficient'] for a,b in combinations(rows,2))
    return s

def exemplar(r):
    return {'run_id':r['run_id'],'scenario':r['run']['scenario_id'],'budget':r['run']['configured_tool_budget'],'repetition':r['intended_repetition'],'physical_attempt':r['physical_attempt'],'trace_id':r['trace_id'],'trace_url':r['trace_url'],'tool_sequence':list(trajectory(r)),'evidence_set':sorted(r['run']['evidence_ids_retrieved']),'diagnosis':r['run']['final_diagnosis'],'correct':r['metrics']['diagnosis_correct'],'evidence_completeness':r['metrics']['evidence_completeness'],'evidence_sufficient':r['metrics']['evidence_sufficient'],'missing_required_evidence':r['metrics']['missing_required_evidence'],'cost_split':r['cost_split'],'blocked_calls':r['blocked_calls']}

def metrics_table(aggs):
    lines=['| Budget | N | Accuracy | Completeness | Sufficient | Premature stop | Avg executed calls |','|---|---:|---:|---:|---:|---:|---:|']
    for b,s in aggs.items():lines.append(f"| {b} | {s['n']} | {s['accuracy']:.0%} | {s['evidence_completeness']:.1%} | {s['evidence_sufficiency']:.0%} | {s['premature_stop']:.0%} | {s['executed_calls']:.2f} |")
    return lines

def example_lines(title,items):
    lines=[f'### {title}','']
    if not items:return lines+['No qualifying example was observed.','']
    for r in items:
        lines += [f"**{r['scenario']}, budget {r['budget']}, repetition {r['repetition']}, physical attempt {r['physical_attempt']}** — [trace `{r['trace_id']}`]({r['trace_url']}).",'',
          f"- Diagnosis: `{r['diagnosis']['predicted_root_cause']}`; correct={r['correct']}.",
          f"- Exact path: {' → '.join(t+'('+c+')' for t,c in r['tool_sequence'])}.",
          f"- Evidence set: {', '.join(r['evidence_set'])}.",
          f"- Completeness: {r['evidence_completeness']:.1%}; sufficient={r['evidence_sufficient']}; missing: {', '.join(r['missing_required_evidence']) or 'none'}.",
          f"- Tokens: {r['cost_split']['diagnostic_loop_tokens']} diagnostic + {r['cost_split']['finalization_tokens']} finalizer = {r['cost_split']['total_tokens']} total.",
          f"- Latency: {r['cost_split']['diagnostic_loop_seconds']:.3f}s diagnostic + {r['cost_split']['finalization_seconds']:.3f}s finalization phase = {r['cost_split']['total_seconds']:.3f}s trace; {r['cost_split']['end_to_end_wall_seconds']:.3f}s full wall time.",
          f"- Executed calls: {len(r['tool_sequence'])}; blocked requests: {r['blocked_calls']}.",'']
    return lines

def main():
    manifest=json.loads((OUT/'manifest.json').read_text());assert manifest.get('completed')
    verification=json.loads((OUT/'verification.json').read_text());assert verification['pass'] and verification['accepted_runs']==20
    slots=manifest['slots'];assert len(slots)==20
    rows=[json.loads((OUT/'runs'/f"{s['accepted_run_id']}.json").read_text()) for s in slots.values()]
    assert len({(r['run']['scenario_id'],r['run']['configured_tool_budget'],r['intended_repetition']) for r in rows})==20
    assert all(len(r['gate'])==12 and all(r['gate'].values()) and not r['run']['error'] for r in rows)
    rows.sort(key=lambda r:(r['run']['configured_tool_budget'],r['run']['scenario_id'],r['intended_repetition']))
    (OUT/'runs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    microsoft=[json.loads(l) for l in (ROOT/'results/phase3-variation/runs.jsonl').read_text().splitlines()]
    microsoft=[r for r in microsoft if r['run']['scenario_id'] in ['diag_007','diag_008'] and r['run']['configured_tool_budget'] in [6,8]];assert len(microsoft)==20
    groups={k:extended(v) for k,v in grouped(rows).items()};ms_groups={k:extended(v) for k,v in grouped(microsoft).items()}
    by_budget={str(b):extended([r for r in rows if r['run']['configured_tool_budget']==b]) for b in (6,8)}
    ms_budgets={str(b):extended([r for r in microsoft if r['run']['configured_tool_budget']==b]) for b in (6,8)}
    counts={'stable_diagnosis_groups':sum(g['diagnoses_stable'] for g in groups.values()),'varying_trajectory_groups':sum(g['trajectory_variants']>1 for g in groups.values()),'stable_diagnoses_varying_trajectory_groups':sum(g['diagnoses_stable'] and g['trajectory_variants']>1 for g in groups.values()),'same_diagnosis_different_sufficiency_groups':sum(g['same_diagnosis_different_sufficiency'] for g in groups.values()),'correct_but_insufficient_groups':sum(g['correct_but_insufficient']>0 for g in groups.values()),'correct_but_insufficient_runs':sum(r['metrics']['diagnosis_correct'] and not r['metrics']['evidence_sufficient'] for r in rows)}
    incorrect=[exemplar(r) for r in rows if not r['metrics']['diagnosis_correct']]
    pairs=best_pairs(rows);A=[exemplar(pairs[0]['a']),exemplar(pairs[0]['b'])] if pairs else []
    bad=[r for r in rows if r['metrics']['diagnosis_correct'] and not r['metrics']['evidence_sufficient']]
    B=[exemplar(sorted(bad,key=lambda r:(r['metrics']['evidence_completeness'],-r['run']['configured_tool_budget'],r['run_id']))[0])] if bad else []
    cross=[]
    for a,b in product(rows,rows):
        if a['run']['configured_tool_budget']!=6 or b['run']['configured_tool_budget']!=8 or a['run']['scenario_id']!=b['run']['scenario_id']:continue
        gain=b['metrics']['evidence_completeness']-a['metrics']['evidence_completeness']
        if gain>0:cross.append((10*(b['metrics']['evidence_sufficient'] and not a['metrics']['evidence_sufficient'])+gain+int(a['metrics']['diagnosis_correct'] and b['metrics']['diagnosis_correct']),a,b))
    cross.sort(key=lambda p:p[0],reverse=True);C=[exemplar(cross[0][1]),exemplar(cross[0][2])] if cross else []
    blocked_runs=sum(r['blocked_calls']>0 for r in rows)
    gain=by_budget['8']['evidence_completeness']>by_budget['6']['evidence_completeness']
    classifications={
      'Correct diagnosis can still have insufficient evidence':'REPRODUCED' if bad else 'NOT REPRODUCED',
      'Stable outcomes can hide trajectory instability':'REPRODUCED' if counts['stable_diagnoses_varying_trajectory_groups'] else 'PARTIALLY REPRODUCED' if pairs else 'NOT REPRODUCED',
      'Larger budgets expose more discriminating evidence':'REPRODUCED' if gain and cross else 'PARTIALLY REPRODUCED' if cross else 'NOT REPRODUCED',
      'Tool-budget semantics materially affect investigation quality':'PARTIALLY REPRODUCED' if gain and blocked_runs else 'INCONCLUSIVE'}
    conclusion='YES, PARTIALLY GENERALIZED' if bad and pairs and gain else 'MIXED' if bad or pairs or gain else 'NO'
    attempts=[dict(a,condition=k) for k,s in slots.items() for a in s['attempts']]
    interrupted=[a for a in attempts if a['status']=='interrupted_by_user']
    failed=[a for a in attempts if a['status']=='failed'];replacements=sum(a['physical_attempt']>1 for a in attempts)
    scenarios=load_scenarios();retrieval={sid:{str(b):{eid:sum(eid in r['run']['evidence_ids_retrieved'] for r in rows if r['run']['scenario_id']==sid and r['run']['configured_tool_budget']==b) for eid in scenarios[sid].required_evidence} for b in (6,8)} for sid in ('diag_007','diag_008')}
    branch=[]
    for p in pairs:
        if p['group']!='diag_007/budget-6':continue
        a,b=p['a'],p['b'];ta,tb=set(trajectory(a)),set(trajectory(b))
        if a['metrics']['diagnosis_correct'] and b['metrics']['diagnosis_correct'] and a['metrics']['evidence_sufficient']!=b['metrics']['evidence_sufficient'] and ((('check_recent_change','api') in ta and ('read_logs','database') in tb) or (('check_recent_change','api') in tb and ('read_logs','database') in ta)):branch.append(p)
    summary={'accepted_runs':20,'physical_attempts':len(attempts),'failed_attempts':len(failed),'interrupted_attempts':len(interrupted),'replacement_attempts':replacements,'by_budget':by_budget,'groups':groups,'counts':counts,'required_evidence_retrieval':retrieval,'diag_007_requested_branch_recurred':bool(branch),'examples':{'A':A,'B':B,'C':C},'incorrect_final_diagnoses':incorrect,'blocked_call_count':sum(r['blocked_calls'] for r in rows),'runs_with_blocked_calls':blocked_runs,'classification':classifications,'conclusion':conclusion,'microsoft':{'by_budget':ms_budgets,'groups':ms_groups},'failed_attempt_records':failed,'interrupted_attempt_records':interrupted}
    dump(OUT/'summary.json',summary);dump(OUT/'exemplars.json',summary['examples'])
    lines=['# OpenClaw fixed-budget follow-up','',f"**20 accepted runs completed across {len(attempts)} physical attempts.** Failed attempts: {len(failed)}; user-interrupted attempts: {len(interrupted)}; replacements launched: {replacements}. Adaptive stopping excluded.",'',
      '## Design and controls','',
      'Two scenarios (`diag_007`, `diag_008`) × budgets 6/8 × five intended repetitions. OpenClaw 2026.9.7, exact `gpt-4.1-mini-2025-04-14`, temperature 0, serial diagnostic tools. Fresh isolated state/session/workspace; original diagnostic instruction, report, three tool definitions, deterministic Python environment and rubric. Provider recovery budget zero, empty fallback chain, outbound guards and canonical invocation accounting. No execution/finalization contract changed during this study; file hashes are in the manifest.',
      '', 'Every run uses the validated evidence-only, tools-disabled finalizer through the pinned OpenClaw isolated runtime. It receives no prior loop answer or evaluation labels. Final JSON is validated strictly with the existing Diagnosis schema and observed-only evidence citations; no response repair. Exactly one finalizer call per accepted physical attempt.',
      '', 'Serial order: budget 6, then budget 8; diag_007, then diag_008; repetitions 1–5. This is a small fixed-scenario descriptive follow-up, not a randomized harness comparison. All smoke tests, original rejected attempts and finalizer validation runs are excluded.',
      '', '## Aggregate results','']+metrics_table(by_budget)
    if incorrect:
        lines += ['', '**Accepted means protocol-valid, not necessarily correct.** The incorrect final diagnosis is retained in the accuracy denominator; it was not replaced.', '']
        for r in incorrect:
            lines += [f"{r['scenario']}, budget {r['budget']}, repetition {r['repetition']}: final label `{r['diagnosis']['predicted_root_cause']}`, with {r['evidence_completeness']:.0%} evidence completeness. [Trace `{r['trace_id']}`]({r['trace_url']}).", '']
    lines += ['', 'Premature stop uses the unchanged rubric definition: required evidence is incomplete. It includes forced budget exhaustion and is not a claim that every such stop was voluntary.',
      '', '| Budget | Diagnostic tokens | Finalizer tokens | Total tokens | Diagnostic s | Finalization s | Trace total s | Full wall s |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for b,s in by_budget.items():
        c=s['cost_split_mean'];lines.append(f"| {b} | {c['diagnostic_loop_tokens']:.1f} | {c['finalization_tokens']:.1f} | {c['total_tokens']:.1f} | {c['diagnostic_loop_seconds']:.3f} | {c['finalization_seconds']:.3f} | {c['total_seconds']:.3f} | {c['end_to_end_wall_seconds']:.3f} |")
    lines += ['', 'All cost columns are means over accepted runs. Diagnostic tokens include the loop’s intermediate answer; finalizer cost is additional and separately counted. Finalization phase time includes setup after the diagnostic event boundary; total trace duration is diagnostic native duration plus that phase. Full wall time additionally includes CLI startup/shutdown. No direct cross-harness latency superiority is claimed. Failed attempts are excluded from these scientific means and retained separately.',
      '', '## Repeatability','', '| Scenario / budget | Stable diagnosis | Ordered paths | Evidence sets | Sufficiency varies | Tool counts | Token range | Trace seconds range |','|---|---|---:|---:|---|---|---|---|']
    for key,g in groups.items():lines.append(f"| {key} | {g['diagnoses_stable']} | {g['trajectory_variants']} | {g['evidence_set_variants']} | {g['evidence_sufficiency_varies']} | {g['tool_counts']} | {g['tokens_range'][0]}–{g['tokens_range'][1]} | {g['latency_range'][0]:.3f}–{g['latency_range'][1]:.3f} |")
    lines += ['',f"Of four scenario/budget groups: **{counts['stable_diagnosis_groups']}** had stable diagnosis labels, **{counts['varying_trajectory_groups']}** had varying ordered trajectories, **{counts['same_diagnosis_different_sufficiency_groups']}** had a same-label pair with different evidence sufficiency, and **{counts['correct_but_insufficient_groups']}** contained correct-but-insufficient runs ({counts['correct_but_insufficient_runs']}/20 runs). Stable labels and varying paths coexisted throughout {counts['stable_diagnoses_varying_trajectory_groups']}/4 groups.",
      '', 'Computed directly from saved ordered executed calls: trajectory signature is `(tool_name, component)` in invocation order; evidence-set signature is sorted unique retrieved IDs; diagnosis stability compares exact final labels. Blocked calls are excluded from trajectory/execution counts and reported separately. Token/latency ranges above show their variation; five repetitions do not establish deterministic behavior.',
      '', '## Trace exemplars','']
    lines+=example_lines('A. Same scenario, budget and diagnosis; different trajectory',A)
    if A:lines+=['Pair selected within one exact scenario/budget group, prioritizing a sufficiency difference and correct diagnoses.','']
    lines+=example_lines('B. Correct diagnosis with insufficient evidence',B)
    lines+=example_lines('C. Budget 6 versus 8: additional discriminating evidence',C)
    if C:lines+=['This compares independent repetitions across budgets, not a replayed counterfactual.','']
    lines += ['## Scenario-specific checks','',f"The specific Microsoft `diag_007` budget-6 branch (`check_recent_change(api)` versus `read_logs(database)`, same correct diagnosis but different sufficiency) **{'recurred' if branch else 'did not recur'}**. This was verified from raw trajectories, not inferred from aggregate accuracy.",'', '| Scenario / discriminating evidence | Budget 6 retrieval | Budget 8 retrieval |','|---|---:|---:|']
    for sid,budgets in retrieval.items():
        for eid in budgets['6']:lines.append(f"| {sid}: {eid} | {budgets['6'][eid]}/5 | {budgets['8'][eid]}/5 |")
    lines += ['', '## Phoenix and finalization','',f"Blocked diagnostic requests: {summary['blocked_call_count']} across {blocked_runs}/20 runs. These are never counted as executed tools. Diagnostic tools remain visible until the loop ends; only the explicit finalizer is tools-disabled. All accepted final stop reasons are `adapter_finalization`.",
      '', 'Each accepted trace contains one root, diagnostic model/tool spans, any blocked-request CHAIN spans, and exactly one model span with `phase=finalization`, `tools_enabled=false`, `finalization_adapter=true`. Only model spans carry standard token attributes. Every accepted trace passed the 12 readback gates, and all 11 deterministic evaluations were attached and verified at root/experiment level.',
      '', 'Experiments: `openclaw-repeatability-budget-6-finalized-v1` and `openclaw-repeatability-budget-8-finalized-v1`, on a separate dataset. The suffix distinguishes this validated finalizer study from the earlier halted experiment.',
      '', '## Failures and saved evidence','',f"Physical attempts: {len(attempts)}; failed: {len(failed)}; user-interrupted: {len(interrupted)}; replacement attempts: {replacements}. Intended repetition and physical attempt indices are distinct in the manifest and per-run records. No failed native session was resumed."]
    if interrupted:
        lines += ['', 'The user-interrupted physical attempt was preserved separately. No model/tool events or request capture were saved for that interrupted attempt; its cost is not assumed to be zero. It is excluded from accepted-run means. The subsequent replacement used new isolated state and a new run ID.']
    if failed or interrupted:
        lines+=['','| Condition | Attempt | Run ID | Failure kind |','|---|---:|---|---|']
        lines += [f"| {a['condition']} | {a['physical_attempt']} | {a['run_id']} | {a.get('failure_kind','user interruption')} |" for a in failed+interrupted]
    lines += ['', '[Summary](results/openclaw-followup/study-v1/summary.json), [20 accepted rows](results/openclaw-followup/study-v1/runs.jsonl), [manifest and physical-attempt ledger](results/openclaw-followup/study-v1/manifest.json), [trace exemplars](results/openclaw-followup/study-v1/exemplars.json). Per-run diagnostic artifacts, finalizer inputs/outputs, requests, OTLP bytes, fetched spans and annotations are in the same directory. Full native local state remains in the ignored spike directory. Results follow the repository’s existing ignore policy and must be included explicitly when packaging.',
      '', 'The validated adapter files were used unchanged. The new runner is `spikes/openclaw-followup/run_validated_study.py`; it resumes saved publication work without silently rerunning inference. Analysis is `spikes/openclaw-followup/analyze_validated_study.py` and performs no model calls. Do not use the older pre-finalization analyzer to regenerate these reports.',
      '', 'All four prerequisite validation reports remain unchanged. Earlier OpenClaw result/comparison drafts are archived under `study-v1/prior_reports/`. Historical Microsoft results/reports, README and demo were preserved. See [cross-harness interpretation](OPENCLAW_COMPARISON.md).','']
    (ROOT/'OPENCLAW_RESULTS.md').write_text('\n'.join(lines))
    ms_bad=sum(r['metrics']['diagnosis_correct'] and not r['metrics']['evidence_sufficient'] for r in microsoft);ms_var=sum(g['trajectory_variants']>1 for g in ms_groups.values())
    comparison=['# Microsoft–OpenClaw follow-up comparison','',f'## Conclusion: {conclusion}','',
      f"Across the matched 20-run subsets, Microsoft had {ms_bad}/20 correct-but-insufficient diagnoses and trajectory variation in {ms_var}/4 groups. OpenClaw had {counts['correct_but_insufficient_runs']}/20 and variation in {counts['varying_trajectory_groups']}/4 groups. These are observed patterns under different runtime/finalization implementations, not causal framework effects.",'',
      'Microsoft source: [actual targeted-repeatability artifacts](results/phase3-variation/runs.jsonl), filtered to diag_007/diag_008, budgets 6/8, five repetitions each. The full Microsoft study had 50 runs; its 6/10 variation claim is not substituted for this matched four-group comparison.',
      '', '## Findings','', '| Microsoft finding | Classification | OpenClaw evidence |','|---|---|---|']
    evidence=[f"{counts['correct_but_insufficient_runs']}/20 correct-but-insufficient runs in {counts['correct_but_insufficient_groups']}/4 groups.",f"{counts['stable_diagnoses_varying_trajectory_groups']}/4 groups had stable labels across all five repetitions and varying ordered paths.",f"Completeness {by_budget['6']['evidence_completeness']:.1%} → {by_budget['8']['evidence_completeness']:.1%}; sufficiency {by_budget['6']['evidence_sufficiency']:.0%} → {by_budget['8']['evidence_sufficiency']:.0%}.",f"{blocked_runs}/20 runs reached a blocked diagnostic request. Budget effects are observed descriptively; the causal effect of blocked-call versus tools-disabled semantics was not isolated."]
    comparison += [f'| {name} | {classification} | {why} |' for (name,classification),why in zip(classifications.items(),evidence)]
    if incorrect:
        comparison += ['', f"**Outcome variation also occurred:** {len(incorrect)} accepted final diagnosis was incorrect despite complete evidence. In diag_007/budget-8/repetition-5, the diagnostic-loop text named `database_connection_regression`, while the separate finalizer returned `api_configuration_issue`; the unchanged rubric scores the final label as incorrect. The finalizer did not receive that earlier answer. This observed label change makes finalization a material comparability caveat, not grounds to relabel the result or blame the harness."]
    comparison += ['', 'The fourth classification separates evidence that budget constraints affect investigation from any claim about why the two harnesses differ. The finalizer cannot retrieve missing evidence; correctness after finalization still does not certify a sufficient diagnostic trajectory.',
      '', '## Historical Microsoft matched subset','']+metrics_table(ms_budgets)+['','## OpenClaw with explicit finalization adapter','']+metrics_table(by_budget)
    comparison += ['', '## What was held constant','', '- Exact model snapshot and temperature 0.', '- Original diagnostic instruction and incident report text.', '- Three diagnostic tool names/definitions backed by the same deterministic Python environment.', '- Same executed-call budgets, scenario ground truth and evidence rubric.', '- Fresh session/state; no memory, project context, adaptive controller or evaluation labels in model input.',
      '', '## What differed','',
      '- Microsoft finalizes within its conversation with tools disabled at the framework cap and its response-format control. OpenClaw retains diagnostic tools until loop termination, may return blocked-call observations, then makes a separate fresh, zero-tool completion over frozen evidence.',
      '- The adapter adds one model call and its full cost. It validates final JSON strictly but does not use provider-constrained JSON-schema decoding. OpenClaw’s isolated runtime does not expose that control.',
      '- Effective diagnostic prompts include OpenClaw model identity and timestamp context. The finalizer receives a separate instruction/schema and observed evidence instead of Microsoft’s full conversation.',
      '- Runtime versions, execution dates/provider conditions, process startup, bridge and finalization overhead differ. Budget/scenario order was serial, not randomized.',
      '- Blocked calls are recorded separately and cannot execute additional tools. Their observations can affect loop stopping, unlike immediate tools-disabled finalization. The finalizer does not receive blocked calls as evidence.',
      '', 'Do not claim framework superiority, causality, or direct latency superiority. OpenClaw’s token/latency split is in [the results report](OPENCLAW_RESULTS.md); even its trace duration excludes some CLI startup that is included in full wall time.',
      '', f"The specific diag_007 budget-6 API-change versus database-log sufficiency branch {'recurred' if branch else 'did not recur'}. Lack of recurrence in five repetitions is not proof of impossibility. The diag_008 required-cache-evidence counts and exact examples are in the results report.",
      '', '## Packaging recommendation','',
      'Package this as a bounded cross-harness follow-up for Aparna, with the failed-attempt ledger, exact trace exemplars and finalization caveat visible. It is sufficient to discuss evaluation engineering and whether patterns recur; it is not a framework leaderboard or a statistical population claim. Further model calls are not needed for that presentation. A fresh Microsoft subset using a matched evidence-only finalizer would be the next step if stronger causal comparability is required. Do not add adaptive stopping merely to strengthen the story.',
      '',f'**{conclusion}**','']
    (ROOT/'OPENCLAW_COMPARISON.md').write_text('\n'.join(comparison))
    print(json.dumps({'accepted':20,'failed':len(failed),'replacement_attempts':replacements,'by_budget':by_budget,'counts':counts,'classification':classifications,'conclusion':conclusion},indent=2))

if __name__=='__main__':main()
