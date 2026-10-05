"""Stage A must pass from fetched Phoenix records before Stage B is allowed."""
import argparse,json,sys
from pathlib import Path
from datetime import datetime,timezone
from phoenix.client import Client
from adapter import run_once,dump,ROOT,MODEL
from phoenix_adapter import publish_and_validate
from agent_tool_budget_lab.scenarios import load_scenarios,DEFAULT_DATA
import hashlib

OUTPUT=ROOT/'results/openclaw-followup'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['a','b']);args=parser.parse_args()
    OUTPUT.mkdir(parents=True,exist_ok=True)
    manifest_path=OUTPUT/'manifest.json'
    manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {'created':datetime.now(timezone.utc).isoformat(),'model':MODEL,'runtime':'openclaw','openclaw_version':'2026.9.7','dataset_sha256':hashlib.sha256(DEFAULT_DATA.read_bytes()).hexdigest(),'experiments':{}}
    client=Client(base_url='http://127.0.0.1:6006');scenarios=load_scenarios()
    if args.stage=='b':
        gate=json.loads((OUTPUT/'stage-a-gate.json').read_text());assert gate['pass'] and len(gate['checks'])==12 and all(gate['checks'].values()),'Stage A must pass'
        if (OUTPUT/'stage-b-failure.json').exists():
            raise RuntimeError('Stage B halted: inspect the saved failure before authorizing any further inference')
    selected=['diag_001'] if args.stage=='a' else ['diag_007','diag_008']
    namespace='stage-a' if args.stage=='a' else 'stage-b'
    if namespace not in manifest:
        ds=client.datasets.create_dataset(name='openclaw-followup-'+namespace+'-'+manifest['created'].replace(':','').replace('.',''),
          inputs=[{'scenario_id':sid,'user_report':scenarios[sid].runtime.user_report} for sid in selected],
          outputs=[{'root_cause':scenarios[sid].root_cause} for sid in selected],metadata=[{'rubric_version':2,'namespace':namespace} for _ in selected])
        manifest[namespace]={'dataset_id':ds.id,'dataset_version_id':ds.version_id};dump(manifest_path,manifest)
    ds=client.datasets.get_dataset(dataset=manifest[namespace]['dataset_id'])
    for budget in ([2] if args.stage=='a' else [6,8]):
        name='openclaw-phoenix-validation' if args.stage=='a' else f'openclaw-repeatability-budget-{budget}'
        if name not in manifest['experiments']:
            experiment=client.experiments.create(dataset_id=ds.id,dataset_version_id=ds.version_id,experiment_name=name,repetitions=1 if args.stage=='a' else 5,
              experiment_metadata={'runtime':'openclaw','model':MODEL,'budget':budget,'finalization':'blocked result then natural answer','native_exporter_enabled':False})
            manifest['experiments'][name]=experiment;dump(manifest_path,manifest)
        experiment=manifest['experiments'][name];experiment['dataset_id']=ds.id
        for sid in selected:
            for repetition in range(1,2 if args.stage=='a' else 6):
                files=list((OUTPUT/'runs').glob(f'{sid}-b{budget}-r{repetition}-*.json')) if (OUTPUT/'runs').exists() else []
                assert len(files)<=1,'Refuse ambiguous duplicate run slot'
                row=json.loads(files[0].read_text()) if files else run_once(sid,budget,repetition,OUTPUT)
                try:
                    assert not row['run']['error'],row['run']['error']
                    row=publish_and_validate(client,row,OUTPUT,experiment,next(e for e in ds.examples if e['input']['scenario_id']==sid))
                except Exception as exc:
                    dump(OUTPUT/f'{namespace}-failure.json',{'run_id':row['run_id'],'error':str(exc),'stage':args.stage})
                    if args.stage=='a':dump(OUTPUT/'stage-a-gate.json',{'pass':False,'checks':row.get('gate',{}),'error':str(exc)})
                    raise
                if args.stage=='a':dump(OUTPUT/'stage-a-gate.json',{'pass':all(row['gate'].values()),'checks':row['gate'],'run_id':row['run_id'],'trace_id':row['trace_id'],'project_name':row['project_name'],'experiment_name':name})
                print(json.dumps({'stage':args.stage,'scenario':sid,'budget':budget,'repetition':repetition,'correct':row['metrics']['diagnosis_correct'],'sufficient':row['metrics']['evidence_sufficient'],'executed':row['executed_calls'],'blocked':row['blocked_calls'],'trace_id':row['trace_id']}),flush=True)
    print('STAGE '+args.stage.upper()+' COMPLETE',flush=True)

if __name__=='__main__':main()
