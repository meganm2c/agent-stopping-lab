"""Exactly three independent validation slots. Never runs the 20-run study."""
import json
from adapter import ROOT,dump,run_once
from phoenix.client import Client
from phoenix_adapter import publish_and_validate
from agent_tool_budget_lab.scenarios import load_scenarios

out=ROOT/'results/openclaw-recovery-validation';out.mkdir(parents=True,exist_ok=True)
assert not (out/'summary.json').exists(),'Mini-batch already attempted; do not silently repeat'
client=Client(base_url='http://127.0.0.1:6006');scenario=load_scenarios()['diag_007']
ds=client.datasets.create_dataset(name='openclaw-recovery-validation',inputs=[{'scenario_id':'diag_007','user_report':scenario.runtime.user_report}],outputs=[{'root_cause':scenario.root_cause}])
ex=client.experiments.create(dataset_id=ds.id,dataset_version_id=ds.version_id,experiment_name='openclaw-recovery-validation-budget-6',repetitions=3)
ex['dataset_id']=ds.id;dump(out/'manifest.json',ex)
summary={'purpose':'recovery validation, not repeatability study','runs':[]}
dump(out/'summary.json',summary)
for rep in range(1,4):
    try:
        row=run_once('diag_007',6,rep,out,namespace='recovery-validation')
        row=publish_and_validate(client,row,out,ex,next(iter(ds.examples)))
        result={'repetition':rep,'accepted':True,'run_id':row['run_id'],'trace_id':row['trace_id'],'trace_url':row['trace_url'],'tokens':row['run']['usage']['total_token_count'],'internal_attempts':row['accounting']['internal_attempts']}
    except Exception as exc:
        result={'repetition':rep,'accepted':False,'error':str(exc)}
    summary['runs'].append(result);dump(out/'summary.json',summary);print(json.dumps(result),flush=True)
summary['accepted']=sum(r['accepted'] for r in summary['runs']);summary['rejected']=3-summary['accepted'];dump(out/'summary.json',summary)
