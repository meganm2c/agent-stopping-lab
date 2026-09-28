"""Render the verified final comparison without selecting a new policy."""
import json
from pathlib import Path
from statistics import mean
from collections import defaultdict


def main():
    directory=Path('results/phase3-comparison')
    summary=json.loads((directory/'summary.json').read_text());g=summary['aggregates']
    manifest=json.loads((directory/'manifest.json').read_text())
    rows=[json.loads(s) for s in (directory/'runs.jsonl').read_text().splitlines()]
    compare='http://localhost:6006/datasets/'+manifest['dataset_id']+'/compare?'+ '&'.join('experimentId='+e['id'] for e in manifest['experiments'])
    lines=['# Adaptive stopping results','',
        'The final comparison uses the unchanged eight-example Phoenix dataset, three runs per example and configuration: '
        '72 agent runs with deterministic post-run evaluations. The 50-run targeted study is reported separately in '
        '[TRAJECTORY_VARIATION.md](TRAJECTORY_VARIATION.md). The single policy was frozen before these runs; it was not tuned against the outcomes.','',
        f'[Phoenix comparison]({compare}) — use **Metrics** and **List**. The Phase 2 Grid view was blank; no cosmetic debugging was required.', '',
        '## Aggregate comparison','',
        '| Metric | fixed-budget-6 | fixed-budget-8 | adaptive-stopping |',
        '|---|---:|---:|---:|']
    names=['fixed-budget-6','fixed-budget-8','adaptive-stopping']
    fields=[('accuracy','Diagnosis accuracy',True),('evidence_completeness','Evidence completeness',True),
        ('evidence_sufficient','Evidence sufficiency',True),('premature_stop','Premature-stop rate',True),
        ('calls_mean','Average tool calls',False),('post_sufficiency_calls','Post-sufficiency calls',False),
        ('irrelevant_calls','Irrelevant calls',False),('latency_seconds','End-to-end seconds',False),
        ('agent_tokens','Agent tokens',False),('stopper_overhead_tokens','Stopper tokens',False),
        ('total_tokens','Total tokens',False),('stopper_overhead_latency','Stopper seconds',False)]
    for key,label,percent in fields:
        values=[f'{g[name][key]:.1%}' if percent else f'{g[name][key]:.2f}' for name in names]
        lines.append('| '+label+' | '+' | '.join(values)+' |')
    lines += ['', 'Each mean uses all 24 runs in that configuration. Agent tokens exclude stopping requests; total tokens include them. '
              'Latency covers the complete agent execution, including all checks and the final answer.','', '### Stop reasons','']
    for name in names:lines.append(f"- `{name}`: {g[name]['stop_reasons']}")
    a,b=g['adaptive-stopping'],g['fixed-budget-8']
    call_saving=b['calls_mean']-a['calls_mean'];token_saving=b['total_tokens']-a['total_tokens'];latency_saving=b['latency_seconds']-a['latency_seconds']
    lines += ['', '## Adaptive outcomes','',
        f"- Effective stop rate: {a['adaptive_stop_triggered']:.1%} ({round(a['adaptive_stop_triggered']*24)}/24).",
        f"- False early-stop rate: {a['false_early_stop']:.1%} ({round(a['false_early_stop']*24)}/24).",
        f"- False early-stop rate among effective stops: {a['false_early_stop_given_trigger']:.1%}.",
        f"- Mean call index among effective stops: {a['mean_stop_call_index']:.2f}.",
        f"- Mean ceiling slack (`8 - calls`): {a['avoided_calls_vs_budget8']:.2f}; this is not a counterfactual saving.",
        f"- Actual mean call saving vs fixed-8: {call_saving:.2f} ({call_saving/b['calls_mean']:.1%}).",
        f"- Actual mean total-token saving vs fixed-8: {token_saving:.2f} ({token_saving/b['total_tokens']:.1%}); negative means added cost.",
        f"- Actual mean latency saving vs fixed-8: {latency_saving:.2f} seconds ({latency_saving/b['latency_seconds']:.1%}); negative means slower.",
        f"- Stopper errors: {round(a['stopper_errors']*24)}.", '',
        'These are differences of observed configuration means. Repetition indices do not create identical counterfactual trajectories, '
        'and serial configuration order/network conditions limit interpretation of latency differences.','', '## Preregistered criteria','',
        '| Criterion | Observed result | Passed |','|---|---|---|']
    criteria=[('Accuracy within one correct run of fixed-8',f"{a['accuracy']:.1%} vs {b['accuracy']:.1%}",a['accuracy']+1/24+1e-9>=b['accuracy']),
        ('At least 10% fewer calls',f'{call_saving/b["calls_mean"]:.1%}',call_saving/b['calls_mean']>=.10),
        ('At least 5% lower total tokens or latency',f"tokens {token_saving/b['total_tokens']:.1%}; latency {latency_saving/b['latency_seconds']:.1%}",token_saving/b['total_tokens']>=.05 or latency_saving/b['latency_seconds']>=.05),
        ('At most one false early stop',str(round(a['false_early_stop']*24)),a['false_early_stop']<=1/24+1e-9),
        ('No execution/parse failures or budget violations', 'Verified runs; stopper errors '+str(round(a['stopper_errors']*24)),a['stopper_errors']==0)]
    for label,observed,passed in criteria:lines.append(f'| {label} | {observed} | {passed} |')
    lines += ['', '**Hypothesis supported:** '+str(all(c[2] for c in criteria))+'. No threshold or prompt was changed after results.', '',
        '## Per-scenario comparison','',
        '| Scenario | Strategy | Correct / 3 | Completeness | Calls | Agent tokens | Stopper tokens | Seconds |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for sid in sorted({r['run']['scenario_id'] for r in rows}):
        for name in names:
            group=[r for r in rows if r['experiment_name']==name and r['run']['scenario_id']==sid]
            stats=summary['groups'][f'{name}/{sid}']
            overhead=mean(sum(c['usage']['input_token_count']+c['usage']['output_token_count'] for c in r['run'].get('stopping_checks',[])) for r in group)
            lines.append(f"| {sid} | {name} | {sum(r['metrics']['diagnosis_correct'] for r in group)} | {stats['evidence_completeness']:.1%} | {stats['calls_mean']:.2f} | {stats['agent_tokens']:.0f} | {overhead:.0f} | {stats['latency_seconds']:.2f} |")
    fixed6=[r for r in rows if r['experiment_name']==names[0]]
    fixed8=[r for r in rows if r['experiment_name']==names[1]]
    adaptive=[r for r in rows if r['experiment_name']==names[2]]
    cases=[('Fixed-6 premature stop',next((r for r in fixed6 if not r['metrics']['diagnosis_correct'] and r['metrics']['premature_stop']),None)),
           ('Fixed-8 successful but inefficient',max((r for r in fixed8 if r['metrics']['diagnosis_correct']),key=lambda r:r['metrics']['excess_calls'])),
           ('Adaptive supported early stop',min((r for r in adaptive if r['run']['stop_reason']=='adaptive_stop' and r['metrics']['diagnosis_correct'] and r['metrics']['evidence_sufficient']),key=lambda r:r['run']['number_of_tool_calls'],default=None)),
           ('Adaptive failure or edge case',min((r for r in adaptive if not r['metrics']['diagnosis_correct']),key=lambda r:r['run']['number_of_tool_calls'],default=None) or next((r for r in adaptive if r['run']['stop_reason']=='adaptive_stop' and not r['metrics']['evidence_sufficient']),None))]
    lines += ['', '## Demo traces','']
    selected=[]
    for title,r in cases:
        lines += ['### '+title,'']
        if r is None:
            lines += ['No matching observed run; do not manufacture an example.',''];continue
        run=r['run'];m=r['metrics'];selected.append(dict(title=title,url=r['trace_url'],trace_id=r['trace_id']))
        lines += [f"[{run['scenario_id']}, repetition {r['repetition']}]({r['trace_url']}) — `{run['final_diagnosis']['predicted_root_cause']}`, "
                  f"correct={m['diagnosis_correct']}, sufficiency={m['evidence_sufficient']}, stop=`{run['stop_reason']}`.", '',
                  '| Step | Tool | Observed output | Stopping decision |','|---:|---|---|---|']
        for c in run['tool_calls']:
            check=next((x for x in run.get('stopping_checks',[]) if x['tool_index']==c['tool_index']),None)
            decision=(check['decision']+': '+check['reason']) if check else '—'
            observed=json.dumps(c['output'],ensure_ascii=False).replace('|','\\|')
            lines.append(f"| {c['tool_index']} | {c['tool_name']}({c['arguments']['component']}) | {observed} | {decision.replace('|','/')} |")
        lines += ['',f"Missing required evidence after execution: {', '.join(m['missing_required_evidence']) or 'none'}. "
                  f"Post-sufficiency calls: {m['excess_calls']}. Agent explanation: {run['final_diagnosis']['explanation']}", '']
    (directory/'demo-traces.json').write_text(json.dumps(selected,indent=2)+'\n')
    discussion=Path('ADAPTIVE_DISCUSSION.md')
    if discussion.exists():lines += ['',discussion.read_text()]
    Path('ADAPTIVE_RESULTS.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(call_saving=call_saving,token_saving=token_saving,latency_saving=latency_saving,hypothesis=all(c[2] for c in criteria)),indent=2))

if __name__=='__main__': main()
