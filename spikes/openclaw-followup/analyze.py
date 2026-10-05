"""Derive reports from saved rows; never invoke models or edit historical artifacts."""
from collections import Counter,defaultdict
from itertools import combinations
from statistics import mean
import json,sys
from pathlib import Path
from adapter import ROOT,dump
from agent_tool_budget_lab.scenarios import load_scenarios
OUT=ROOT/'results/openclaw-followup'

def trajectory(row):
    return tuple((c['tool_name'],c['arguments']['component']) for c in row['run']['tool_calls'] if c['executed'])

def summarize(rows):
    counts=Counter((r['run'].get('final_diagnosis') or {}).get('predicted_root_cause','INVALID') for r in rows)
    return {'n':len(rows),'accuracy':mean(r['metrics']['diagnosis_correct'] for r in rows),
      'evidence_completeness':mean(r['metrics']['evidence_completeness'] for r in rows),
      'evidence_sufficiency':mean(r['metrics']['evidence_sufficient'] for r in rows),
      'premature_stop':mean(r['metrics']['premature_stop'] for r in rows),
      'executed_calls':mean(r['run']['number_of_tool_calls'] for r in rows),
      'tokens':mean(r['run']['usage']['total_token_count'] for r in rows),
      'latency_seconds':mean(r['run']['elapsed_seconds'] for r in rows),
      'diagnoses':dict(counts),'modal_diagnosis_fraction':max(counts.values())/len(rows),
      'trajectory_variants':len({trajectory(r) for r in rows}),
      'evidence_set_variants':len({tuple(sorted(r['run']['evidence_ids_retrieved'])) for r in rows}),
      'correct_but_insufficient':sum(r['metrics']['diagnosis_correct'] and not r['metrics']['evidence_sufficient'] for r in rows),
      'blocked_calls':sum(sum(not c['executed'] for c in r['run']['tool_calls']) for r in rows),
      'runs_with_blocked_calls':sum(any(not c['executed'] for c in r['run']['tool_calls']) for r in rows),
      'stop_reasons':dict(Counter(r['run']['stop_reason'] for r in rows))}

def grouped(rows):
    groups=defaultdict(list)
    for r in rows:groups[f"{r['run']['scenario_id']}/budget-{r['run']['configured_tool_budget']}"].append(r)
    return dict(groups)

def best_pairs(rows):
    pairs=[]
    for key,group in grouped(rows).items():
        for a,b in combinations(group,2):
            da=a['run']['final_diagnosis'];db=b['run']['final_diagnosis']
            if not da or not db or da['predicted_root_cause']!=db['predicted_root_cause'] or trajectory(a)==trajectory(b):continue
            sa,sb=set(trajectory(a)),set(trajectory(b))
            rank=10*(a['metrics']['evidence_sufficient']!=b['metrics']['evidence_sufficient'])+3*(a['metrics']['diagnosis_correct'] and b['metrics']['diagnosis_correct'])+len(sa^sb)+abs(len(trajectory(a))-len(trajectory(b)))
            pairs.append({'group':key,'rank':rank,'a':a,'b':b})
    return sorted(pairs,key=lambda p:p['rank'],reverse=True)

def table(aggregates):
    lines=['| Budget | N | Accuracy | Completeness | Sufficient | Premature stop | Executed calls | Tokens | Seconds |',
      '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for b,s in aggregates.items():lines.append(f"| {b} | {s['n']} | {s['accuracy']:.0%} | {s['evidence_completeness']:.1%} | {s['evidence_sufficiency']:.0%} | {s['premature_stop']:.0%} | {s['executed_calls']:.2f} | {s['tokens']:.1f} | {s['latency_seconds']:.2f} |")
    return lines

def path(row):return ' → '.join(f'{t}({c})' for t,c in trajectory(row))

def write_stage_a():
    gate=json.loads((OUT/'stage-a-gate.json').read_text());row=json.loads((OUT/'runs'/f"{gate['run_id']}.json").read_text())
    lines=['# OpenClaw Phoenix validation','',f"**Stage A: {'PASS' if gate['pass'] else 'FAIL'}.** One new `diag_001`, budget-2 run; excluded from the measured study.",'',
      f"Experiment: [openclaw-phoenix-validation]({row['experiment_url']}). Phoenix project: `{row['project_name']}`.",
      f"Trace: [`{row['trace_id']}`]({row['trace_url']}); root span `{row['span_id']}`.",'',
      '## Gate read back from Phoenix','', '| Check | Result |','|---|---|']
    lines += [f"| {k.replace('_',' ')} | {'PASS' if v else 'FAIL'} |" for k,v in gate['checks'].items()]
    lines += ['', '## Exact structure and accounting','',
      f"{row['span_count']} spans: one CHAIN root, {len(row['assistant_messages'])} LLM children, {row['executed_calls']} executed TOOL children, and {row['blocked_calls']} blocked-request CHAIN child. Every child points to the same root. No native OpenClaw exporter ran.",
      '',f"Tokens: {row['run']['usage']['input_token_count']} input + {row['run']['usage']['output_token_count']} output = {row['run']['usage']['total_token_count']} total. Only LLM spans carry standard token attributes; the root carries none. The total equals the native OpenClaw result. One span per completed assistant response, not per streaming fragment.",
      '',f"Latency: {row['run']['elapsed_seconds']:.3f}s native run duration; {row['cli_wall_seconds']:.3f}s CLI wall time recorded separately. Root duration matches the former within 2ms. Tool durations are the Python recorder's invocation timings and exclude IPC. Model spans preserve hook timestamps and also store native model-call duration.",
      '', 'Spans are normalized after the actual run and exported via OTLP HTTP/protobuf, then fetched from Phoenix for semantic checks. Root boundaries are event-anchored using the native duration; this is transparent post-run normalization, not native OpenClaw distributed tracing. Exact intra-millisecond timing should not be inferred.',
      '', '## Evaluations and finalization','',
      'All 11 existing rubric-v2 deterministic evaluations were attached both to the root span and to the experiment run, then fetched back and checked: diagnosis_correct, evidence_sufficient, evidence_completeness, premature_stop, tool_calls_used, redundant_investigation, irrelevant_calls, post_sufficiency_calls, identical_repeated_calls, token_usage, latency_seconds.',
      '',f"Ordered attempts: {'; '.join(c['tool_name']+'('+c['arguments']['component']+') '+('executed' if c['executed'] else 'BLOCKED') for c in row['run']['tool_calls'])}.",
      '',f"Final diagnosis: `{row['run']['final_diagnosis']['predicted_root_cause']}`; correct={row['metrics']['diagnosis_correct']}; sufficient={row['metrics']['evidence_sufficient']}; stop reason `{row['run']['stop_reason']}`.",
      '', 'Tools remained visible after exhaustion. The third requested call returned a budget-exhausted observation; the final answer followed it. This differs from Microsoft’s tools-disabled finalization. A `finalization_semantics` annotation and root attributes preserve this distinction. Blocked spans are CHAIN, not TOOL, and have `executed=false`.',
      '', '## Controls and evidence','',
      'Configured, internal, outbound and returned model: `gpt-4.1-mini-2025-04-14`; completed runtime `openclaw`. All submitted bodies were checked for three-tool isolation and absence of evaluation labels/project content. Ground truth was accessed for scoring only after inference. The original diagnostic prompt remains, plus OpenClaw’s model-identity line and timestamp prefix.',
      '',f"Machine evidence: [gate](results/openclaw-followup/stage-a-gate.json), [normalized run](results/openclaw-followup/runs/{row['run_id']}.json), [Phoenix spans](results/openclaw-followup/traces/{row['run_id']}.json), [fetched annotations](results/openclaw-followup/annotations/{row['run_id']}.json), [outbound requests](results/openclaw-followup/requests/{row['run_id']}.json).",
      '', 'Verification was programmatic through the Phoenix API; no screenshot is claimed. Local Phoenix links require the saved local database/server. The JSON/OTLP artifacts preserve the evidence independently of that UI.', '']
    (ROOT/'OPENCLAW_PHOENIX_VALIDATION.md').write_text('\n'.join(lines))

def main():
    write_stage_a()
    if '--stage-a-only' in sys.argv:return
    rows=[json.loads(p.read_text()) for p in (OUT/'runs').glob('diag_00[78]-*.json')]
    assert len(rows)==20 and len({(r['run']['scenario_id'],r['run']['configured_tool_budget'],r['repetition']) for r in rows})==20
    assert all(len(r['gate'])==12 and all(r['gate'].values()) for r in rows)
    rows.sort(key=lambda r:(r['run']['configured_tool_budget'],r['run']['scenario_id'],r['repetition']))
    (OUT/'runs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    baseline=[json.loads(l) for l in (ROOT/'results/phase3-variation/runs.jsonl').read_text().splitlines()]
    ms=[r for r in baseline if r['run']['scenario_id'] in ('diag_007','diag_008')]
    assert len(ms)==20
    groups=grouped(rows);gs={k:summarize(v) for k,v in groups.items()};mgs={k:summarize(v) for k,v in grouped(ms).items()}
    aggs={str(b):summarize([r for r in rows if r['run']['configured_tool_budget']==b]) for b in (6,8)}
    maggs={str(b):summarize([r for r in ms if r['run']['configured_tool_budget']==b]) for b in (6,8)}
    pairs=best_pairs(rows);mpairs=best_pairs(ms)
    varying=sum(g['trajectory_variants']>1 for g in gs.values());stable=sum(g['modal_diagnosis_fraction']==1 for g in gs.values())
    stable_varying=sum(g['modal_diagnosis_fraction']==1 and g['trajectory_variants']>1 for g in gs.values())
    same_diagnosis_path_groups=len({p['group'] for p in pairs})
    insufficient_groups=sum(g['correct_but_insufficient']>0 for g in gs.values())
    scenarios=load_scenarios();cache={str(b):{eid:sum(eid in r['run']['evidence_ids_retrieved'] for r in rows if r['run']['scenario_id']=='diag_008' and r['run']['configured_tool_budget']==b) for eid in scenarios['diag_008'].required_evidence} for b in (6,8)}
    def analogous(pair):
        if pair['group']!='diag_007/budget-6':return False
        a,b=pair['a'],pair['b'];ta,tb=set(trajectory(a)),set(trajectory(b))
        return a['metrics']['diagnosis_correct'] and b['metrics']['diagnosis_correct'] and a['metrics']['evidence_sufficient']!=b['metrics']['evidence_sufficient'] and ((('check_recent_change','api') in ta and ('read_logs','database') in tb) or (('check_recent_change','api') in tb and ('read_logs','database') in ta))
    branch=[p for p in pairs if analogous(p)]
    summary={'run_count':20,'errors':sum(bool(r['run']['error']) for r in rows),'by_budget':aggs,'groups':gs,
      'varying_trajectory_groups':varying,'stable_diagnosis_groups':stable,'stable_diagnosis_varying_trajectory_groups':stable_varying,
      'same_diagnosis_different_path_groups':same_diagnosis_path_groups,'correct_but_insufficient_groups':insufficient_groups,
      'diag_007_analogous_branch':bool(branch),'diag_008_required_evidence_retrieval':cache,
      'microsoft_matched_subset':{'by_budget':maggs,'groups':mgs},
      'top_pairs':[{'group':p['group'],'rank':p['rank'],'run_ids':[p['a']['run_id'],p['b']['run_id']],'trace_ids':[p['a']['trace_id'],p['b']['trace_id']]} for p in pairs[:3]]}
    dump(OUT/'summary.json',summary)
    lines=['# OpenClaw fixed-budget follow-up','', '**20/20 measured runs completed. Adaptive stopping excluded.** Stage A passed before this batch; its run is excluded from these numbers.','',
      'Design: diag_007 and diag_008 × budgets 6 and 8 × five repetitions. OpenClaw 2026.9.7, exact `gpt-4.1-mini-2025-04-14`, temperature 0, parallel tool calls false. Fresh state/session/workspace each run; original Python environment and deterministic rubric. Serial order: budget 6 before budget 8, then scenario, then repetition.','',
      '## Aggregate results','']+table(aggs)+['',f"Errors: {summary['errors']}. All 20 traces passed the same 12 readback checks, including experiment/span evaluations. Calls in this table are executions; blocked requests are excluded. Tokens are actual response usage; seconds are native run duration, not CLI startup or cross-harness speed evidence.",'',
      '## Repetition-level variation','', '| Scenario / budget | Stable diagnosis fraction | Tool paths | Evidence sets | Correct but insufficient | Runs with blocked requests |','|---|---:|---:|---:|---:|---:|']
    lines += [f"| {k} | {g['modal_diagnosis_fraction']:.0%} | {g['trajectory_variants']} | {g['evidence_set_variants']} | {g['correct_but_insufficient']}/{g['n']} | {g['runs_with_blocked_calls']}/{g['n']} |" for k,g in sorted(gs.items())]
    lines += ['',f"Trajectories varied in **{varying}/4 groups**. Diagnoses were stable in {stable}/4 groups; {stable_varying}/4 had stable diagnoses and varying trajectories. {same_diagnosis_path_groups}/4 groups contained at least one same-diagnosis/different-path pair; {insufficient_groups}/4 contained a correct-but-insufficient run.",
      '', 'Trajectory signature = ordered `(tool_name, component)` pairs for executed calls only. Evidence-set signature = sorted unique evidence IDs. Diagnosis stability = modal exact label / five runs. Accepted aliases still apply to correctness. These are descriptive repetitions over two scenarios, not independent evidence of population-wide effects.',
      '', '## Strongest trace pairs','']
    for i,p in enumerate(pairs[:3],1):
        lines += [f"### {i}. {p['group']}",'']
        for tag,r in [('A',p['a']),('B',p['b'])]:
            lines += [f"- {tag}: [repetition {r['repetition']}]({r['trace_url']}) — `{r['run']['final_diagnosis']['predicted_root_cause']}`; correct={r['metrics']['diagnosis_correct']}; sufficient={r['metrics']['evidence_sufficient']}; {r['executed_calls']} executions, {r['blocked_calls']} blocked requests.",
              f"  Path: {path(r)}. Evidence: {', '.join(r['run']['evidence_ids_retrieved'])}."]
        lines += ['']
    if not pairs:lines+=['No same-diagnosis/different-executed-path pair was observed.','']
    lines += ['## Scenario-specific findings','',f"**diag_007:** The requested budget-6 branch with same correct diagnosis, different evidence sufficiency, and `check_recent_change(api)` versus `read_logs(database)` **{'recurred' if branch else 'did not recur'}** in these five repetitions. This was checked from ordered raw calls, not inferred from aggregate accuracy.",
      '', '**diag_008:** Required/discriminating evidence retrieval counts below are out of five runs per budget.','', '| Evidence ID | Budget 6 | Budget 8 |','|---|---:|---:|']
    lines += [f"| {eid} | {cache['6'][eid]}/5 | {cache['8'][eid]}/5 |" for eid in cache['6']]
    lines += ['', '## Finalization and interpretation','',f"Blocked calls: {sum(r['blocked_calls'] for r in rows)} across {sum(r['blocked_calls']>0 for r in rows)}/20 runs. Stop reasons: {dict(Counter(r['run']['stop_reason'] for r in rows))}. All requests retained the three tools, including after exhaustion; the recorder, not tool removal, enforced the cap.",
      '', 'OpenClaw finalization differs from Microsoft: a denied execution returns a budget-exhausted observation, after which the model may naturally answer. Effective prompts differ by model-identity context and timestamp; tool ordering/strictness and structured-output handling also differ. Runtime/IPC/startup overhead and execution order differ. No superiority or causal harness claim follows from the cost/latency columns.',
      '', '## Reproduction and saved evidence','', '[Machine summary](results/openclaw-followup/summary.json), [all measured rows](results/openclaw-followup/runs.jsonl), [Phoenix manifest](results/openclaw-followup/manifest.json), [Stage A validation](OPENCLAW_PHOENIX_VALIDATION.md). Per-run HTTP bodies, fetched Phoenix spans, annotations, and OTLP bytes are saved in sibling subdirectories. Raw host state stays ignored under `spikes/openclaw-followup/.local/`.',
      '', 'Runner: `spikes/openclaw-followup/run_study.py a`, then `b`; Stage B refuses to start without the saved 12-check Stage A pass. Existing run slots are reused for ingestion recovery; model calls are not silently rerun. `spikes/openclaw-followup/analyze.py` only reads saved data and regenerates these new reports.','']
    (ROOT/'OPENCLAW_RESULTS.md').write_text('\n'.join(lines))
    old_insufficient=sum(r['metrics']['diagnosis_correct'] and not r['metrics']['evidence_sufficient'] for r in ms)
    new_insufficient=sum(r['metrics']['diagnosis_correct'] and not r['metrics']['evidence_sufficient'] for r in rows)
    old_var=sum(g['trajectory_variants']>1 for g in mgs.values())
    conclusion='YES, PARTIALLY' if new_insufficient and same_diagnosis_path_groups else 'MIXED'
    summary['cross_harness_conclusion']=conclusion;dump(OUT/'summary.json',summary)
    compare=['# Microsoft–OpenClaw comparison','',f'## Conclusion: {conclusion}','',
      f"The historical **matched 20-run subset** contains {old_insufficient}/20 correct-but-insufficient runs; OpenClaw contains {new_insufficient}/20. Executed trajectories vary in {old_var}/4 Microsoft groups and {varying}/4 OpenClaw groups. This compares observed patterns under the recorded implementations, not a causal framework effect.",'',
      'Historical source: [targeted repeatability raw runs](results/phase3-variation/runs.jsonl), filtered to diag_007/diag_008 and budgets 6/8, five repetitions each. The full historical study contains 50 runs and its 6/10 variation claim is not substituted for this matched subset. No Microsoft run was rerun or altered.','',
      '## Historical Microsoft subset','']+table(maggs)+['','## OpenClaw follow-up','']+table(aggs)
    compare += ['', '## Which findings generalized?','', '| Finding | Classification | Evidence |','|---|---|---|',
      f"| Correct diagnosis can hide insufficient evidence | {'Reproduced across harnesses' if new_insufficient else 'Not reproduced in this OpenClaw sample'} | Microsoft {old_insufficient}/20; OpenClaw {new_insufficient}/20. |",
      f"| Stable outcomes can hide varying paths | {'Reproduced across harnesses' if same_diagnosis_path_groups else 'Not reproduced in this OpenClaw sample'} | OpenClaw {same_diagnosis_path_groups}/4 groups have a same-label/different-path pair; {stable_varying}/4 have stable labels throughout. |",
      f"| Larger budgets expose more discriminating evidence | {'Reproduced across harnesses' if aggs['8']['evidence_sufficiency']>aggs['6']['evidence_sufficiency'] else 'Not reproduced as an aggregate sufficiency increase'} | OpenClaw sufficiency {aggs['6']['evidence_sufficiency']:.0%} → {aggs['8']['evidence_sufficiency']:.0%}; completeness {aggs['6']['evidence_completeness']:.1%} → {aggs['8']['evidence_completeness']:.1%}. See cache evidence counts. |",
      '| Execution semantics affect stopping | Changed under OpenClaw; causal effect inconclusive | Blocked-result continuation was observed; Microsoft removes tool availability. The two policies were not experimentally isolated. |',
      '', '## Controls and remaining differences','',
      '| Held constant | Differed / not controlled |','|---|---|',
      '| Exact model snapshot and temperature 0 | Runtime versions, wall-clock run dates and provider conditions |',
      '| Same scenario data, incident report text and diagnostic instruction text | OpenClaw adds model identity and incident timestamp; effective prompts are not identical |',
      '| Same Python diagnostic tools and descriptions; serial execution | Tool schema ordering/strictness; OpenClaw sends strict tools, while final JSON is host-validated rather than API-constrained to Diagnosis |',
      '| Same hard cap on executed diagnostic calls | Blocked-call observations vs Microsoft tools-disabled finalization; requested calls can exceed the execution budget |',
      '| Fresh run/session and deterministic evidence rubric | Harness, bridge, setup and tracing overhead differ; no direct latency superiority claim |',
      '', f"The specific diag_007 budget-6 sufficiency branch **{'recurred' if branch else 'did not recur'}**. The absence of a branch in five repetitions does not establish impossibility. diag_008 details and top pairs are in [OpenClaw results](OPENCLAW_RESULTS.md).",
      '', 'No claim that one framework is better, that OpenClaw caused an improvement, or that native duration establishes latency superiority is justified. These are five stochastic repetitions per cell over two fixed scenarios; larger-budget effects are descriptive and may include ordering/provider variation.',
      '', '## Recommended next step','',
      '**Run a matched fresh Microsoft 20-run subset** if the goal is a stronger cross-harness comparison. Keep this evidence as a small replication and first make the finalization policy and effective request differences explicit in the matched protocol. Defer adaptive stopping: OpenClaw’s after-tool observer is not awaited, and tools-disabled finalization is still not established. The current result can be shared with Aparna with those boundaries, but does not need another harness yet.','']
    (ROOT/'OPENCLAW_COMPARISON.md').write_text('\n'.join(compare))
    print(json.dumps({'by_budget':aggs,'varying_groups':varying,'same_diagnosis_path_groups':same_diagnosis_path_groups,'conclusion':conclusion},indent=2))

if __name__=='__main__':main()
