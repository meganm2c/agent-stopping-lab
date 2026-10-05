"""Read-only Phoenix/accounting verification after all inference has finished."""
import hashlib,json
from collections import Counter
from pathlib import Path
from phoenix.client import Client
from adapter import ROOT,HERE,MODEL,dump
from phoenix_adapter import validate_spans
from finalization_lifecycle import assemble
from agent_tool_budget_lab.phoenix_evaluators import evaluation_values
from agent_tool_budget_lab.scenarios import load_scenarios
OUT=ROOT/'results/openclaw-followup/study-v1'
m=json.loads((OUT/'manifest.json').read_text());assert m.get('completed')
assert all(hashlib.sha256((HERE/p).read_bytes()).hexdigest()==h for p,h in m['contract_sha256'].items())
slots=m['slots'];assert len(slots)==20 and all(s.get('accepted_run_id') for s in slots.values())
assert len({s['accepted_run_id'] for s in slots.values()})==20
assert Counter((s['scenario_id'],s['budget']) for s in slots.values())==Counter({(sid,b):5 for sid in ('diag_007','diag_008') for b in (6,8)})
client=Client(base_url='http://127.0.0.1:6006');scenarios=load_scenarios();checked=[]
experiments={ex['project_name']:client.experiments.get_experiment(experiment_id=ex['id']) for ex in m['experiments'].values()}
for key,slot in slots.items():
 rid=slot['accepted_run_id'];r=json.loads((OUT/'runs'/f'{rid}.json').read_text())
 assert r['run']['model_name']==MODEL and r['runtime_id']=='openclaw' and not r['run']['error']
 assert r['intended_repetition']==slot['intended_repetition'] and r['repetition']==slot['intended_repetition']
 assert r['accounting']['accepted'] and r['accounting']['internal_attempts']==1
 assert r['terminal_receipt']['effective']['responseModel']==MODEL and not r['terminal_receipt']['rerouted']
 assert r['accounting']['retry_settings_observed'] and all(s['settings']['maxRetries']==0 for s in r['accounting']['retry_settings_observed'])
 d=json.loads((OUT/'diagnostic/runs'/f'{rid}.json').read_text());f=json.loads((OUT/'finalization'/f'{rid}.json').read_text());requests=json.loads((OUT/'diagnostic/requests'/f'{rid}.json').read_text())
 recomputed,_=assemble(d,f,requests);assert recomputed['run']==r['run'] and recomputed['cost_split']==r['cost_split']
 spans=client.spans.get_spans(project_identifier=r['project_name'],trace_ids=[r['trace_id']],limit=1000)
 assert all(validate_spans(r,spans).values())
 anns=client.spans.get_span_annotations(project_identifier=r['project_name'],span_ids=[r['span_id']],limit=1000)
 found={a['name']:a for a in anns};values=evaluation_values(r,scenarios);assert len(values)==11
 assert all(name in found and found[name]['result']['score']==v for name,v in values.items())
 ev=[e for e in experiments[r['project_name']]['evaluation_runs'] if e.experiment_run_id==r['experiment_run_id']];assert len(ev)==11
 for e in ev:
  assert not e.error;result=e.result[0] if isinstance(e.result,list) else e.result
  assert result['score']==values[e.name]
 checked.append({'condition':key,'run_id':rid,'trace_id':r['trace_id'],'evaluation_count':11,'span_count':len(spans),'pass':True})
for p in ['/tmp/openclaw-resume-preservation.json','/tmp/openclaw-study-preservation.json']:
 snap=json.loads(Path(p).read_text());assert all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in snap.items()),p
summary={'pass':True,'accepted_runs':20,'groups':{f'{s}/{b}':5 for s in ('diag_007','diag_008') for b in (6,8)},'root_evaluations_verified':220,'experiment_evaluations_verified':220,'original_18_and_interrupted_artifacts_unchanged':True,'protected_historical_files_unchanged':True,'contract_hashes_unchanged':True,'runs':checked}
dump(OUT/'verification.json',summary)
m['status']='completed_verified';dump(OUT/'manifest.json',m)
print(json.dumps({k:v for k,v in summary.items() if k!='runs'},indent=2))
