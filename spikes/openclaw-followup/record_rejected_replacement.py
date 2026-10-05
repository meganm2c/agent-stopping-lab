"""Preserve invalid final JSON as a rejected replacement, without inference."""
import json,time
from datetime import datetime,timezone
from pathlib import Path
import httpx
from phoenix.client import Client
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from adapter import ROOT,HERE,dump
out=ROOT/'results/openclaw-fail-replace';path=next((out/'runs').glob('*.json'));row=json.loads(path.read_text())
assert row['run']['error']=='No valid JSON Diagnosis' and row['run']['final_diagnosis'] is None
assert row['accounting']['accepted'] and row['accounting']['internal_attempts']==1
assert all(s['settings']['maxRetries']==0 for s in row['accounting']['retry_settings_observed'])
client=Client(base_url='http://127.0.0.1:6006');ex=json.loads((out/'manifest.json').read_text())
spans=client.spans.get_spans(project_identifier=ex['project_name'],trace_ids=[row['trace_id']],limit=100)
root=next(s for s in spans if not s.get('parent_id'))
assert root['attributes']['output.value']=='null'
assert len(spans)==row['span_count'] and len({s['context']['span_id'] for s in spans})==len(spans)
assert sum(s['attributes'].get('llm.token_count.total',0) for s in spans)==row['run']['usage']['total_token_count']
assert len([s for s in spans if s['span_kind']=='TOOL'])==row['executed_calls']
ds=client.datasets.get_dataset(dataset=ex['dataset_id'])
record=client.experiments.log_run(experiment_id=ex['id'],dataset_example_id=next(iter(ds.examples))['id'],output=row,start_time=datetime.fromtimestamp(row['trace_start_ms']/1000,timezone.utc),end_time=datetime.fromtimestamp(row['trace_end_ms']/1000,timezone.utc),repetition_number=2,trace_id=row['trace_id'],error=row['run']['error'])
client.spans.add_span_annotation(span_id=row['span_id'],annotation_name='run_acceptance',annotator_kind='CODE',label='REJECTED_FINAL_CONTRACT',explanation='Fresh replacement; zero recovery; final response is not valid JSON. Excluded from measured metrics.',sync=True)
annotations=client.spans.get_span_annotations(project_identifier=ex['project_name'],span_ids=[row['span_id']],limit=100)
assert any(a['name']=='run_acceptance' and a['result']['label']=='REJECTED_FINAL_CONTRACT' for a in annotations)
dump(out/'replacement-rejection-annotations.json',annotations)
result={'accepted':False,'reason':row['run']['error'],'intended_repetition':1,'physical_attempt':2,'run_id':row['run_id'],'trace_id':row['trace_id'],'usage':row['run']['usage'],'executed_calls':row['executed_calls'],'blocked_calls':row['blocked_calls'],'requested_calls':row['requested_calls'],'model_invocations':len(row['accounting']['invocations']),'http_attempts':row['request_count'],'latency_seconds':row['run']['elapsed_seconds'],'no_recovery':True,'experiment_run_id':record['id']}
dump(out/'replacement.json',result);dump(out/'replacement-rejected-spans.json',spans)
# Check fresh state, identical scientific settings and explicit absence of auth-profile stores.
raw1=next((HERE/'.local/fail-replace/attempt-1').glob('*'));raw2=next((HERE/'.local/fail-replace/attempt-2').glob('*'))
c1=json.loads((raw1/'config.json').read_text());c2=json.loads((raw2/'config.json').read_text());w1=c1['agents']['defaults'].pop('workspace');w2=c2['agents']['defaults'].pop('workspace');assert w1!=w2 and c1==c2
assert (raw1/'fixture.json').read_bytes()==(raw2/'fixture.json').read_bytes()
assert (raw1/'state/agents/main/agent/settings.json').read_bytes()==(raw2/'state/agents/main/agent/settings.json').read_bytes()
assert not list((raw1/'state').rglob('auth-profiles.json')) and not list((raw2/'state').rglob('auth-profiles.json'))
s1=json.loads((out/'accounting'/f'{raw1.name}.json').read_text())['invocations'][0]['session_id'];s2=row['accounting']['invocations'][0]['session_id'];assert s1!=s2
summary={'condition':{'scenario':'diag_007','budget':6,'intended_repetition':1},'attempts':[json.loads((out/'failed-trace.json').read_text()),result],'retry_zero_worked':True,'semantic_recovery_eliminated_in_test':True,'fresh_session_and_identical_treatment_verified':True,'accepted':0,'rejected':2,'recovery_policy_check':'PASS','end_to_end_accepted_replacement':'FAIL','recommendation':'NOT READY'}
dump(out/'policy-summary.json',summary);print(json.dumps(result))
