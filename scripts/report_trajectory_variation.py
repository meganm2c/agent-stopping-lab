"""Render verified targeted-study summaries and inspectable trajectories."""
import json
from pathlib import Path
from collections import defaultdict
from analyze_phase3 import trajectory


def main():
    directory=Path('results/phase3-variation')
    stats=json.loads((directory/'summary.json').read_text())
    rows=[json.loads(s) for s in (directory/'runs.jsonl').read_text().splitlines()]
    lines=['# Trajectory variation study','',
        '50 fresh runs: all three medium and both hard scenarios, budgets 6/8, five repetitions per cell. '
        'The same eight-example Phoenix dataset/version was used through a local five-example view; no dataset rows were added or changed. '
        'Original prompt/runtime/model/settings fingerprints, deterministic evaluations, and fetched tool spans were verified. '
        'Execution was serial, with budget 6 before budget 8; latency comparisons may include order/network effects.','',
        '| Scenario | Budget | Modal diagnosis fraction | Calls mean (min–max; SD) | Sequences | Evidence sets | Stops | Post-sufficiency | Irrelevant | Tokens | Seconds |',
        '|---|---:|---:|---|---:|---:|---|---:|---:|---:|---:|']
    for key,g in stats['groups'].items():
        name,sid=key.split('/');budget=6 if '-6-' in name else 8
        lines.append(f"| {sid} | {budget} | {g['diagnosis_consistency']:.0%} | {g['calls_mean']:.2f} ({g['calls_min']}–{g['calls_max']}; {g['calls_sd']:.2f}) | {g['trajectory_variants']} | {g['evidence_set_variants']} | {g['stop_reasons']} | {g['post_sufficiency_calls']:.2f} | {g['irrelevant_calls']:.2f} | {g['agent_tokens']:.0f} | {g['latency_seconds']:.2f} |")
    varied=sum(g['trajectory_variants']>1 for g in stats['groups'].values())
    stable=sum(g['diagnosis_consistency']==1 for g in stats['groups'].values())
    lines += ['',f'Diagnoses were stable in {stable}/10 groups; trajectories varied in {varied}/10 groups. '
              'Consistency uses exact predicted labels (modal-label count / runs); scoring still accepts scenario-specific aliases. '
              'Standard deviation is descriptive population SD across the five observed runs, not uncertainty over independent scenarios.', '', '## Representative sequences','']
    for sid in sorted({r['run']['scenario_id'] for r in rows}):
        lines += [f'### {sid}', '']
        candidates=[r for r in rows if r['run']['scenario_id']==sid]
        seen=set()
        for r in sorted(candidates,key=lambda r:(r['run']['configured_tool_budget'],r['run']['number_of_tool_calls'])):
            run=r['run'];key=(run['configured_tool_budget'],trajectory(r))
            if key in seen:continue
            seen.add(key)
            path=' → '.join(f'{t}({c})' for t,c in trajectory(r))
            lines += [f"- [Budget {run['configured_tool_budget']}, repetition {r['repetition']}]({r['trace_url']}): {path}. "
                      f"Diagnosis `{run['final_diagnosis']['predicted_root_cause']}`; complete={r['metrics']['evidence_sufficient']}; "
                      f"post-sufficiency={r['metrics']['excess_calls']}; stop=`{run['stop_reason']}`."]
        lines.append('')
    lines += ['## Interpretation boundary','',
        'Post-sufficiency is an evaluation-only checklist measure. It locates observable opportunities to save calls; '
        'it does not prove an online stopper can recognize those moments. Final diagnoses are observed at termination only. '
        'Do not infer stable intermediate diagnoses or hidden reasoning from a final answer. '
        'The stopper must decide from observed runtime evidence without these checklist labels.','']
    gate=Path('ADAPTIVE_OPPORTUNITY.md')
    if gate.exists(): lines += ['',gate.read_text().replace('# Opportunity gate', '## Opportunity gate', 1)]
    Path('TRAJECTORY_VARIATION.md').write_text('\n'.join(lines))

if __name__=='__main__':main()
