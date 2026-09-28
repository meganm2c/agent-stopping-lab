"""Fetch authoritative Phoenix results, verify evaluations/traces, and compare rubrics."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from agent_tool_budget_lab.phoenix_support import phoenix_client
from agent_tool_budget_lab.phoenix_evaluators import evaluation_values
from agent_tool_budget_lab.evaluation import metrics
from agent_tool_budget_lab.models import AgentRunResult
from agent_tool_budget_lab.scenarios import load_scenarios
from agent_tool_budget_lab.config import Settings
from run_budget_pilot import summarize


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    args=parser.parse_args()
    Settings.from_env()  # Loads configuration without printing credentials.
    manifest=json.loads(args.manifest.read_text())
    client=phoenix_client(); scenarios=load_scenarios();rows=[]
    trace_dir=args.manifest.parent/'traces';trace_dir.mkdir(exist_ok=True)
    for item in manifest['experiments']:
        exp=client.experiments.get_experiment(experiment_id=item['id'])
        assert len(exp['task_runs'])==8 and len(exp['evaluation_runs'])==88
        for task in exp['task_runs']:
            assert not task.get('error')
            row=task['output'];run=row['run'];expected=evaluation_values(row,scenarios)
            evaluations=[e for e in exp['evaluation_runs'] if e.experiment_run_id==task['id']]
            assert len(evaluations)==11
            for e in evaluations:
                assert not e.error
                result=e.result[0] if isinstance(e.result,list) else e.result
                assert result['score']==expected[e.name],(e.name,result,expected[e.name])
            spans=client.spans.get_spans(project_identifier=exp['project_name'],trace_ids=[task['trace_id']],limit=1000)
            tools=sorted([s for s in spans if s['span_kind']=='TOOL'],key=lambda s:s['attributes']['tool_index'])
            llms=[s for s in spans if s['span_kind']=='LLM']
            assert len(tools)==run['number_of_tool_calls']<=run['configured_tool_budget']
            assert len(llms)==len(run['model_rounds'])
            assert row['trace_id']==task['trace_id']
            for tool,call in zip(tools,run['tool_calls']):
                a=tool['attributes']
                assert a['component']==call['arguments']['component']
                assert a['evidence_id']==call['output']['evidence_id']
                assert json.loads(a['output.value'])==call['output']
            for span in llms:
                inputs=span['attributes'].get('gen_ai.input.messages','')
                for field in ('required_evidence','acceptable_root_causes','distractor_evidence','difficulty'):
                    assert field not in inputs
            for name in ('diagnosis_correct','evidence_completeness','evidence_sufficient'):
                client.spans.add_span_annotation(span_id=row['span_id'],annotation_name=name,
                    annotator_kind='CODE',score=expected[name],identifier='rubric-v2',sync=True)
            row['experiment_id']=item['id'];row['project_name']=exp['project_name']
            (trace_dir/f"{run['scenario_id']}-{run['configured_tool_budget']}.json").write_text(json.dumps(spans,indent=2,default=str)+'\n')
            rows.append(row)
    (args.manifest.parent/'runs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    print('\nPHOENIX RUNS — RUBRIC V2')
    current=summarize(rows)
    old=[json.loads(line) for line in Path('results/live-pilot.jsonl').read_text().splitlines()]
    for row in old:
        r=AgentRunResult.model_validate(row['run']);row['metrics']=metrics(r,scenarios[r.scenario_id])
    print('\nORIGINAL RUNS RESCORED — RUBRIC V2')
    baseline=summarize(old)
    (args.manifest.parent/'comparison.json').write_text(json.dumps({'phoenix':current,'baseline_rescored':baseline},indent=2)+'\n')
    # Check treatment integrity against the original pilot.
    for row in rows:
        r=row['run'];same=next(x['run'] for x in old if x['run']['scenario_id']==r['scenario_id'])
        for key in ('prompt_sha256','runtime_sha256','model_name','model_settings'):
            assert r[key]==same[key],key
    print('PASS: all 32 tasks, 352 evaluations, native spans, and treatment controls verified.')

if __name__=='__main__':
    main()
