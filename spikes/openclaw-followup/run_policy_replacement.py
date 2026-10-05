"""One replacement, same intended slot, fresh physical attempt. No study runner."""
import json
from adapter import ROOT,run_once,dump
from phoenix.client import Client
from phoenix_adapter import publish_and_validate
out=ROOT/'results/openclaw-fail-replace'
failure=json.loads((out/'failed-trace.json').read_text());assert failure['policy_injection_pass']
assert not (out/'replacement.json').exists(),'Replacement already recorded'
row=run_once('diag_007',6,1,out,namespace='fail-replace/attempt-2',retry_zero=True,physical_attempt=2)
assert not row['run']['error'],row['run']['error']
client=Client(base_url='http://127.0.0.1:6006');ex=json.loads((out/'manifest.json').read_text());ds=client.datasets.get_dataset(dataset=ex['dataset_id'])
# Phoenix repetition represents physical attempts; intended repetition stays explicit.
row['intended_repetition']=1;row['physical_attempt']=2;row['repetition']=2
row=publish_and_validate(client,row,out,ex,next(iter(ds.examples)))
result={'accepted':True,'intended_repetition':1,'physical_attempt':2,'run_id':row['run_id'],'trace_id':row['trace_id'],'trace_url':row['trace_url'],'usage':row['run']['usage'],'executed_calls':row['executed_calls'],'blocked_calls':row['blocked_calls'],'requested_calls':row['requested_calls'],'model_invocations':len(row['accounting']['invocations']),'http_attempts':row['request_count'],'latency_seconds':row['run']['elapsed_seconds']}
dump(out/'replacement.json',result);print(json.dumps(result))
