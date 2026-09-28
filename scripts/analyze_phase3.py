"""Fetch Phase 3 experiments, validate controls/evals, and summarize variation."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from statistics import mean, pstdev
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from agent_tool_budget_lab.config import Settings
from agent_tool_budget_lab.phoenix_support import phoenix_client
from agent_tool_budget_lab.phoenix_evaluators import evaluation_values
from agent_tool_budget_lab.scenarios import load_scenarios
from agent_tool_budget_lab.evaluation import total_tokens


def trajectory(row):
    return tuple((c['tool_name'],c['arguments']['component']) for c in row['run']['tool_calls'] if c['executed'])


def summarize_group(rows):
    runs=[r['run'] for r in rows]; counts=[r['number_of_tool_calls'] for r in runs]
    causes=Counter(r['final_diagnosis']['predicted_root_cause'] for r in runs)
    return dict(n=len(rows),diagnoses=dict(causes),diagnosis_consistency=max(causes.values())/len(rows),
        accuracy=mean(r['metrics']['diagnosis_correct'] for r in rows),
        evidence_completeness=mean(r['metrics']['evidence_completeness'] for r in rows),
        evidence_sufficient=mean(r['metrics']['evidence_sufficient'] for r in rows),
        premature_stop=mean(r['metrics']['premature_stop'] for r in rows),
        calls_mean=mean(counts),calls_min=min(counts),calls_max=max(counts),calls_sd=pstdev(counts),
        trajectory_variants=len({trajectory(r) for r in rows}),
        evidence_set_variants=len({tuple(sorted(r['evidence_ids_retrieved'])) for r in runs}),
        stop_reasons=dict(Counter(r['stop_reason'] for r in runs)),
        post_sufficiency_calls=mean(r['metrics']['excess_calls'] for r in rows),
        irrelevant_calls=mean(r['metrics']['outside_required_supporting_calls'] for r in rows),
        agent_tokens=mean(total_tokens(r) for r in runs),
        latency_seconds=mean(r['elapsed_seconds'] for r in runs))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=['variation','comparison']);args=parser.parse_args()
    Settings.from_env();client=phoenix_client();scenarios=load_scenarios()
    directory=Path('results')/f'phase3-{args.stage}'
    manifest=json.loads((directory/'manifest.json').read_text())
    baseline=[json.loads(s)['run'] for s in Path('results/live-pilot.jsonl').read_text().splitlines()]
    rows=[];aggregates={};groups={}
    traces=directory/'traces';traces.mkdir(exist_ok=True)
    for item in manifest['experiments']:
        exp=client.experiments.get_experiment(experiment_id=item['id'])
        project=client.projects.get(project_name=exp['project_name'])
        collected=[]
        for task in exp['task_runs']:
            assert not task.get('error');row=task['output'];run=row['run'];assert not run['error']
            same=next(b for b in baseline if b['scenario_id']==run['scenario_id'])
            for k in ('prompt_sha256','runtime_sha256','model_name','model_settings'): assert run[k]==same[k],k
            assert run['number_of_tool_calls']<=run['configured_tool_budget']
            expected=evaluation_values(row,scenarios)
            if args.stage=='comparison':
                from agent_tool_budget_lab.adaptive_evaluators import adaptive_values
                expected.update(adaptive_values(row,scenarios))
            ev=[e for e in exp['evaluation_runs'] if e.experiment_run_id==task['id']]
            assert len(ev)==len(expected)
            for e in ev:
                assert not e.error
                result=e.result[0] if isinstance(e.result,list) else e.result
                assert result['score']==expected[e.name],(e.name,result,expected[e.name])
            spans=client.spans.get_spans(project_identifier=exp['project_name'],trace_ids=[task['trace_id']],limit=1000)
            tools=sorted((s for s in spans if s['span_kind']=='TOOL'),key=lambda s:s['attributes']['tool_index'])
            assert len(tools)==run['number_of_tool_calls']
            for span,call in zip(tools,run['tool_calls']):
                assert json.loads(span['attributes']['output.value'])==call['output']
            for span in spans:
                if span['span_kind']=='LLM':
                    inputs=span['attributes'].get('input.value','')
                    for field in ('required_evidence','supporting_evidence','distractor_evidence','difficulty','acceptable_root_causes'):
                        assert field not in inputs
            checks = sorted((s for s in spans if s['name']=='stopping_check'),
                            key=lambda s:s['attributes']['tool_index'])
            assert len(checks)==len(run.get('stopping_checks', []))
            if run.get('stopping_checks'):
                from agent_tool_budget_lab.stopping import observed_payload
                from agent_tool_budget_lab.models import ToolCall
                assert len(checks)==run['number_of_tool_calls']
                for check,record in zip(checks,run['stopping_checks']):
                    index=record['tool_index'];a=check['attributes']
                    assert a['decision']==record['decision'] and a['effective_stop']==record['effective_stop']
                    expected_payload=observed_payload(run['user_report'],[
                        ToolCall.model_validate(c) for c in run['tool_calls'][:index]])
                    assert json.loads(a['input.value'])==expected_payload
                    children=[s for s in spans if s['parent_id']==check['context']['span_id'] and s['span_kind']=='LLM']
                    assert len(children)==1
                    child=children[0]['attributes'];usage=record['usage']
                    assert child['llm.token_count.prompt']==usage['input_token_count']
                    assert child['llm.token_count.completion']==usage['output_token_count']
                    assert check['start_time']>=tools[index-1]['start_time']
                    if index<len(tools):assert check['end_time']<=tools[index]['start_time']
                if run['adaptive_stop_call_index'] is not None:
                    assert run['number_of_tool_calls']==run['adaptive_stop_call_index']<8
                    assert run['stop_reason']=='adaptive_stop'
                    assert run['model_rounds'][-1]['tool_choice']=='none'
            if args.stage=='comparison':
                llms=[s for s in spans if s['span_kind']=='LLM']
                assert len(llms)==len(run['model_rounds'])+len(run.get('stopping_checks',[]))
                traced_tokens=sum(s['attributes']['llm.token_count.prompt']+
                                  s['attributes']['llm.token_count.completion'] for s in llms)
                assert traced_tokens==expected['total_tokens']
                # Scores remain attached to experiments. Phoenix 20.16's installed GraphQL
                # stack fails on annotation summary numpy.int64 counts for root annotations.
            row.update(experiment_name=item['name'],experiment_id=item['id'],repetition=task['repetition_number'],
                       trace_url=f"http://localhost:6006/projects/{project['id']}/traces/{task['trace_id']}")
            (traces/f"{item['name']}-{run['scenario_id']}-{task['repetition_number']}.json").write_text(json.dumps(spans,indent=2,default=str)+'\n')
            collected.append(row);rows.append(row)
        aggregates[item['name']]=summarize_group(collected)
        if args.stage=='comparison':
            values=[adaptive_values(r,scenarios) for r in collected]
            stats=aggregates[item['name']]
            for key in ('adaptive_stop_triggered','false_early_stop','avoided_calls_vs_budget8',
                        'stopper_overhead_tokens','stopper_overhead_latency','total_tokens','stopper_errors'):
                stats[key]=mean(v[key] for v in values)
            stops=[v['stop_call_index'] for v in values if v['stop_call_index'] is not None]
            stats['mean_stop_call_index']=mean(stops) if stops else None
            stats['false_early_stop_given_trigger']=sum(v['false_early_stop'] for v in values)/len(stops) if stops else None
        for sid in sorted({r['run']['scenario_id'] for r in collected}):
            groups[f"{item['name']}/{sid}"]=summarize_group([r for r in collected if r['run']['scenario_id']==sid])
    (directory/'runs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    (directory/'summary.json').write_text(json.dumps(dict(aggregates=aggregates,groups=groups),indent=2)+'\n')
    print(json.dumps(dict(aggregates=aggregates,groups=groups),indent=2))

if __name__=='__main__': main()
