"""Publish the one injected failure only after verifying fail-closed behavior."""
import json,time
from datetime import datetime,timezone
from pathlib import Path
import httpx
from phoenix.client import Client
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans
from opentelemetry.trace import set_span_in_context,Status,StatusCode
from adapter import ROOT,HERE,dump,MODEL

out=ROOT/'results/openclaw-fail-replace'
raws=list((HERE/'.local/fail-replace/attempt-1').glob('*'));assert len(raws)==1
raw=raws[0];rid=raw.name
assert not (out/'failed-trace.json').exists(),'Failure already published'
def lines(name):return [json.loads(l) for l in (raw/name).read_text().splitlines()]
events=lines('events.jsonl');requests=lines('requests.jsonl');transport=lines('transport.jsonl');settings=lines('retry-settings.jsonl')
starts=[e for e in events if e['type']=='model_call_started'];ends=[e for e in events if e['type']=='model_call_ended'];inputs=[e for e in events if e['type']=='llm_input']
assert len(starts)==len(ends)==len(inputs)==len(requests)==len(transport)==1
assert transport[0]['injected'] and transport[0]['forwarded_to_provider'] is False and not transport[0]['unexpected_extra_attempt']
assert all(s['settings']['maxRetries']==0 for s in settings) and settings
assert not any(e['type']=='diagnostic_call' for e in events)
assert ends[0]['data']['event']['outcome']=='error'
assert all(e['data']['event']['model']==MODEL and e['data']['event']['provider']=='openai' for e in starts+ends)
assert 'Continue the current task' not in json.dumps(inputs+requests) and 'Queued user message' not in json.dumps(inputs+requests)
fixture=json.loads((raw/'fixture.json').read_text());config=json.loads((raw/'config.json').read_text())
assert config['agents']['defaults']['model']['fallbacks']==[]
assert not list((raw/'state').rglob('auth-profiles.json'))
agent_ends=[e for e in events if e['type']=='agent_end'];assert len(agent_ends)==1
messages=agent_ends[0]['data']['event']['messages'];assistants=[m for m in messages if m.get('role')=='assistant'];assert len(assistants)==1
assert assistants[0]['stopReason']=='error' and assistants[0]['usage']['totalTokens']==0
client=Client(base_url='http://127.0.0.1:6006')
ds=client.datasets.create_dataset(name='openclaw-fail-replace-policy',inputs=[{'scenario_id':'diag_007','user_report':fixture['report']}])
ex=client.experiments.create(dataset_id=ds.id,dataset_version_id=ds.version_id,experiment_name='openclaw-fail-replace-policy',repetitions=2);ex['dataset_id']=ds.id
dump(out/'manifest.json',ex)
provider=TracerProvider(resource=Resource.create({'openinference.project.name':ex['project_name'],'service.name':'openclaw-policy-validation'}))
collector=InMemorySpanExporter();provider.add_span_processor(SimpleSpanProcessor(collector));tracer=provider.get_tracer('openclaw.failed-attempt')
start=starts[0]['at'];end=ends[0]['at'];canonical=out/'accounting'/f'{rid}.json';accounting=json.loads(canonical.read_text())
attrs={'openinference.span.kind':'CHAIN','runtime.id':'openclaw','model.id':MODEL,'run_id':rid,'scenario_id':'diag_007','tool_budget':6,'intended_repetition':1,'physical_attempt':1,'accepted':False,'failure.injected':True,'provider_requests_forwarded':0,'executed_calls':0,'stop_reason':'injected_provider_error','retry.provider.maxRetries':0}
root=tracer.start_span('openclaw_failed_attempt',start_time=start*1000000,attributes=attrs);root.set_status(Status(StatusCode.ERROR,'Injected 503; no recovery; excluded from measured metrics'))
span=tracer.start_span('model_invocation_1_failed',context=set_span_in_context(root),start_time=start*1000000,attributes={'openinference.span.kind':'LLM','llm.model_name':MODEL,'model.canonical_invocation_id':accounting['invocations'][0]['canonical_id'],'input.value':json.dumps(requests[0]['body']),'llm.token_count.total':0,'llm.token_count.prompt':0,'llm.token_count.completion':0,'usage.zero_basis':'injected before provider forwarding','retry.provider.maxRetries':0,'output.value':'Injected HTTP 503; no provider response'})
span.set_status(Status(StatusCode.ERROR,'Injected HTTP 503'));span.end(end_time=end*1000000);root.end(end_time=end*1000000)
trace=f'{root.get_span_context().trace_id:032x}';rootid=f'{root.get_span_context().span_id:016x}'
blob=encode_spans(collector.get_finished_spans()).SerializeToString();(out/'failure.otlp.pb').write_bytes(blob)
httpx.post('http://127.0.0.1:6006/v1/traces',content=blob,headers={'Content-Type':'application/x-protobuf'},timeout=30).raise_for_status()
for _ in range(30):
 spans=client.spans.get_spans(project_identifier=ex['project_name'],trace_ids=[trace],limit=100)
 if len(spans)==2:break
 time.sleep(1)
assert len(spans)==2 and all(s['status_code']=='ERROR' for s in spans)
assert sum(s['attributes'].get('llm.token_count.total',0) for s in spans)==0
assert not any(s['span_kind']=='TOOL' for s in spans)
record=client.experiments.log_run(experiment_id=ex['id'],dataset_example_id=next(iter(ds.examples))['id'],output=attrs,start_time=datetime.fromtimestamp(start/1000,timezone.utc),end_time=datetime.fromtimestamp(end/1000,timezone.utc),repetition_number=1,trace_id=trace,error='Injected infrastructure failure; excluded; physical attempt 1 of intended repetition 1')
client.spans.add_span_annotation(span_id=rootid,annotation_name='run_acceptance',annotator_kind='CODE',label='REJECTED_INFRASTRUCTURE',explanation='Injected failure before provider forwarding; zero usage proven; preserved outside measured metrics',sync=True)
result=dict(attrs,trace_id=trace,experiment_run_id=record['id'],model_attempts=1,http_attempts=1,tokens=0,elapsed_model_seconds=(end-start)/1000,policy_injection_pass=True)
dump(out/'failed-trace.json',result);dump(out/'failed-spans.json',spans);dump(out/'failed-events.json',[{'type':e['type'],'at':e['at'],'data':e['data'].get('event',e['data'])} for e in events]);dump(out/'failed-transport.json',transport)
print(json.dumps(result));provider.shutdown()
