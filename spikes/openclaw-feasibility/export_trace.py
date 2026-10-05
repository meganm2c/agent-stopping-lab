"""Offline OpenInference/OTLP prototype from the single captured smoke run.

Writes protobuf bytes; does not send data or start Phoenix. This is custom
normalization, not a test of OpenClaw's separate diagnostics-otel plugin.
"""
import json
from pathlib import Path
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import set_span_in_context
from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

base=Path(__file__).resolve().parent/'evidence'
run=json.loads((base/'smoke.json').read_text())
provider=TracerProvider(resource=Resource.create({'service.name':'openclaw-feasibility','openclaw.version':run['openclawVersion']}))
exporter=InMemorySpanExporter();provider.add_span_processor(SimpleSpanProcessor(exporter))
tracer=provider.get_tracer('spike.offline-normalization')
calls=run['modelCalls'];starts=[c for c in calls if c['type']=='model_call_started'];ends=[c for c in calls if c['type']=='model_call_ended']
end_ms=max(c['at'] for c in ends);start_ms=end_ms-run['durationMs']
root=tracer.start_span('OpenClaw diag_001 smoke',start_time=start_ms*1_000_000,attributes={
 'openinference.span.kind':'CHAIN','runtime.id':run['actualRuntime'],'model.id':run['model'],
 'scenario.id':run['scenario'],'tool.budget':run['budget'],'tool.executed':sum(c['executed'] for c in run['calls']),
 'output.value':json.dumps(run['finalDiagnosis']),'output.mime_type':'application/json','stop_reason':run['stopReason'],
 'trace.source':'offline reconstruction from saved smoke; not native exporter'})
context=set_span_in_context(root)
for i,(start,end,message) in enumerate(zip(starts,ends,run['assistantMessages']),1):
    span=tracer.start_span(f'model turn {i}',context=context,start_time=start['at']*1_000_000,attributes={
      'openinference.span.kind':'LLM','llm.model_name':run['model'],'model.turn':i,
      'llm.token_count.prompt':message['usage']['input'],'llm.token_count.completion':message['usage']['output'],
      'llm.token_count.total':message['usage']['totalTokens'],'stop_reason':message['stopReason']})
    span.end(end_time=end['at']*1_000_000)
for call in run['calls']:
    # Python invoke elapsed time, excluding IPC and model work.
    end_ns=call['recordedAtMs']*1_000_000
    attrs={'openinference.span.kind':'TOOL','tool.name':call['tool_name'],'tool.index':call['tool_index'],
      'tool.executed':call['executed'],'input.value':json.dumps(call['arguments']),
      'output.value':json.dumps(call['output']),'input.mime_type':'application/json','output.mime_type':'application/json'}
    if 'evidence_id' in call['output']:attrs['evidence.id']=call['output']['evidence_id']
    span=tracer.start_span(call['tool_name'],context=context,start_time=end_ns-int(call['elapsed_seconds']*1e9),attributes=attrs)
    span.end(end_time=end_ns)
root.end(end_time=end_ms*1_000_000)
spans=exporter.get_finished_spans()
blob=encode_spans(spans).SerializeToString();decoded=ExportTraceServiceRequest.FromString(blob)
assert sum(len(s.spans) for r in decoded.resource_spans for s in r.scope_spans)==8
(base/'trace.otlp.pb').write_bytes(blob)
(base/'trace-summary.json').write_text(json.dumps({'spanCount':8,'source':'offline custom normalization','transport':'OTLP HTTP/protobuf compatible payload','phoenixIngestionTested':False,'nativeExporterTested':False,'modelTokens':sum(m['usage']['totalTokens'] for m in run['assistantMessages'])},indent=2)+'\n')
print('8 spans encoded and decoded; no network export performed.')
provider.shutdown()
