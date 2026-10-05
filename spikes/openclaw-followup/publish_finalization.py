"""Publish saved finalization evidence only; this script never performs inference."""
import sys,json
from pathlib import Path
from phoenix.client import Client
from adapter import ROOT,dump
from finalization_lifecycle import assemble
from phoenix_adapter import publish_and_validate
out=ROOT/'results/openclaw-finalization-validation'
rep=int(sys.argv[1]);assert rep in [1,2]
files=list((out/'diagnostic/runs').glob(f'diag_007-b6-r{rep}-*.json'));assert len(files)==1
original=json.loads(files[0].read_text());rid=original['run_id']
final=json.loads((out/'finalization'/f'{rid}.json').read_text());requests=json.loads((out/'diagnostic/requests'/f'{rid}.json').read_text())
row,requests=assemble(original,final,requests)
assert not (out/'runs'/f'{rid}.json').exists(),'Already assembled: inspect saved trace before republishing'
dump(out/'runs'/f'{rid}.json',row);dump(out/'requests'/f'{rid}.json',requests)
client=Client(base_url='http://127.0.0.1:6006')
manifest=out/'manifest.json'
if manifest.exists():ex=json.loads(manifest.read_text());ds=client.datasets.get_dataset(dataset=ex['dataset_id'])
else:
 ds=client.datasets.create_dataset(name='openclaw-finalization-validation',inputs=[{'scenario_id':'diag_007','user_report':row['run']['user_report']}])
 ex=client.experiments.create(dataset_id=ds.id,dataset_version_id=ds.version_id,experiment_name='openclaw-finalization-validation-budget-6',repetitions=2);ex['dataset_id']=ds.id;dump(manifest,ex)
row=publish_and_validate(client,row,out,ex,next(iter(ds.examples)))
summary={'accepted':True,'run_id':rid,'trace_id':row['trace_id'],'trace_url':row['trace_url'],'diagnosis':row['run']['final_diagnosis'],'cost_split':row['cost_split'],'gate':row['gate'],'span_count':row['span_count']}
dump(out/f'repetition-{rep}.json',summary);print(json.dumps(summary))
