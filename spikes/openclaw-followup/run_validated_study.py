"""Twenty accepted fixed-budget slots using the unchanged validated adapter."""
import json,hashlib,sys,time
from datetime import datetime,timezone
from pathlib import Path
from phoenix.client import Client
from adapter import ROOT,HERE,MODEL,dump
from finalized_attempt import run_finalized_attempt
from phoenix_adapter import publish_and_validate
from agent_tool_budget_lab.scenarios import load_scenarios,DEFAULT_DATA

OUT=ROOT/'results/openclaw-followup/study-v1'
CONTRACT_FILES=['adapter.py','bridge.py','request_guard.mjs','retry_observer.mjs','recovery.py','finalization.py','finalizer_guard.mjs','finalizer-plugin/index.js','finalized_attempt.py','finalization_lifecycle.py','phoenix_adapter.py']
def contract_hashes():return {p:hashlib.sha256((HERE/p).read_bytes()).hexdigest() for p in CONTRACT_FILES}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for rep in (1,2):
        gate=json.loads((ROOT/f'results/openclaw-finalization-validation/repetition-{rep}.json').read_text())
        assert gate['accepted'] and all(gate['gate'].values())
    manifest_path=OUT/'manifest.json'
    if manifest_path.exists():manifest=json.loads(manifest_path.read_text());assert manifest['contract_sha256']==contract_hashes()
    else:
        manifest={'created':datetime.now(timezone.utc).isoformat(),'model':MODEL,'runtime':'openclaw','version':'2026.9.7','contract_sha256':contract_hashes(),'dataset_sha256':hashlib.sha256(DEFAULT_DATA.read_bytes()).hexdigest(),'execution_order':'budget 6, then 8; diag_007 then diag_008; reps 1 through 5; serial','experiments':{},'policy':'preserve failures; fresh physical replacement; never resume native session; stop on scientific invariant failure','slots':{}}
        dump(manifest_path,manifest)
    client=Client(base_url='http://127.0.0.1:6006');scenarios=load_scenarios()
    if 'dataset_id' not in manifest:
        ds=client.datasets.create_dataset(name='openclaw-followup-validated-finalization-v1',inputs=[{'scenario_id':sid,'user_report':scenarios[sid].runtime.user_report} for sid in ('diag_007','diag_008')])
        manifest.update(dataset_id=ds.id,dataset_version_id=ds.version_id);dump(manifest_path,manifest)
    ds=client.datasets.get_dataset(dataset=manifest['dataset_id'])
    for budget in (6,8):
        name=f'openclaw-repeatability-budget-{budget}-finalized-v1'
        if name not in manifest['experiments']:
            ex=client.experiments.create(dataset_id=ds.id,dataset_version_id=ds.version_id,experiment_name=name,repetitions=5,experiment_metadata={'runtime':'openclaw','model':MODEL,'budget':budget,'finalization':'validated isolated evidence-only adapter','retry_provider_maxRetries':0})
            ex['dataset_id']=ds.id;manifest['experiments'][name]=ex;dump(manifest_path,manifest)
        ex=manifest['experiments'][name]
        for sid in ('diag_007','diag_008'):
            example=next(e for e in ds.examples if e['input']['scenario_id']==sid)
            for rep in range(1,6):
                key=f'{sid}/budget-{budget}/repetition-{rep}'
                slot=manifest['slots'].setdefault(key,{'scenario_id':sid,'budget':budget,'intended_repetition':rep,'attempts':[]})
                if slot.get('accepted_run_id'):continue
                while True:
                    assert contract_hashes()==manifest['contract_sha256'],'Execution contract changed mid-study'
                    previous=slot['attempts'][-1] if slot['attempts'] else None
                    if previous and previous['status']=='awaiting_publication':
                        attempt=previous;row=json.loads((OUT/'runs'/f"{attempt['run_id']}.json").read_text())
                    else:
                        assert not previous or previous['status'] in ('failed','interrupted_by_user'),'Blocked slot requires inspection, not a silent model rerun'
                        physical=len(slot['attempts'])+1
                        assert physical<=3,'Three failures in one slot: stop for investigation'
                        attempt={'physical_attempt':physical,'started':datetime.now(timezone.utc).isoformat(),'status':'running'}
                        slot['attempts'].append(attempt);dump(manifest_path,manifest)
                        print(json.dumps({'event':'started','slot':key,'physical_attempt':physical}),flush=True)
                        try:
                            row=run_finalized_attempt(sid,budget,rep,OUT,namespace='study-v1',physical_attempt=physical)
                        except Exception as exc:
                            raws=list((HERE/f'.local/study-v1/attempt-{physical}').glob(f'{sid}-b{budget}-r{rep}-*'))
                            assert len(raws)==1,'No unique raw physical attempt'
                            raw=raws[0];rid=raw.name
                            events=[json.loads(l) for l in (raw/'events.jsonl').read_text().splitlines()] if (raw/'events.jsonl').exists() else []
                            public=[{'type':e['type'],'at':e['at'],'event':e['data'].get('event',e['data'])} for e in events]
                            dump(OUT/'failed-events'/f'{rid}.json',public)
                            final_path=OUT/'finalization'/f'{rid}.json';final=json.loads(final_path.read_text()) if final_path.exists() else None
                            native_failed=any(e['type']=='model_call_ended' and e['data']['event'].get('outcome')=='error' for e in events)
                            infrastructure=native_failed or isinstance(exc,TimeoutError) or type(exc).__name__=='TimeoutExpired' or (final is not None and not final['completion'].get('ok'))
                            schema_failure=type(exc).__name__=='ValidationError' and final is not None and final['completion'].get('ok')
                            attempt.update(run_id=rid,status='failed' if infrastructure or schema_failure else 'blocked',error_type=type(exc).__name__,error=str(exc),failure_kind='infrastructure/runtime' if infrastructure else 'final_schema' if schema_failure else 'scientific_invariant',raw_artifacts=str(raw.relative_to(ROOT)))
                            dump(manifest_path,manifest);dump(OUT/'attempts'/f'{rid}.json',dict(attempt,condition=key))
                            print(json.dumps({'event':attempt['status'],'slot':key,'run_id':rid,'error_type':type(exc).__name__,'failure_kind':attempt['failure_kind']}),flush=True)
                            if attempt['status']=='blocked':raise
                            continue
                        attempt.update(run_id=row['run_id'],status='awaiting_publication');dump(manifest_path,manifest)
                    # Publishing failure never repeats inference. Resume this saved row.
                    row=publish_and_validate(client,row,OUT,ex,example)
                    assert len(row['gate'])==12 and all(row['gate'].values())
                    attempt.update(status='accepted',trace_id=row['trace_id'],completed=datetime.now(timezone.utc).isoformat())
                    slot['accepted_run_id']=row['run_id'];dump(manifest_path,manifest);dump(OUT/'attempts'/f"{row['run_id']}.json",dict(attempt,condition=key))
                    print(json.dumps({'event':'accepted','slot':key,'physical_attempt':attempt['physical_attempt'],'run_id':row['run_id'],'trace_id':row['trace_id'],'correct':row['metrics']['diagnosis_correct'],'sufficient':row['metrics']['evidence_sufficient'],'calls':row['executed_calls'],'tokens':row['run']['usage']['total_token_count']}),flush=True)
                    break
    assert len(manifest['slots'])==20 and all(s.get('accepted_run_id') for s in manifest['slots'].values())
    manifest['completed']=datetime.now(timezone.utc).isoformat();dump(manifest_path,manifest);print('20 ACCEPTED RUNS COMPLETE',flush=True)

if __name__=='__main__':main()
