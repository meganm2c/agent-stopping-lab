"""One normalized trace per run; native OpenClaw export stays disabled."""
import json,time
from datetime import datetime,timezone
from pathlib import Path
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans
from opentelemetry.trace import set_span_in_context
import httpx
from adapter import dump,MODEL,ROOT
from agent_tool_budget_lab.phoenix_evaluators import evaluation_values
from agent_tool_budget_lab.scenarios import load_scenarios

def build_trace(row,requests,project):
    run=row['run'];events=row['model_events']
    starts=[e for e in events if e['type']=='model_call_started'];ends=[e for e in events if e['type']=='model_call_ended']
    assert len(starts)==len(ends)==len(row['assistant_messages'])==len(requests),'Ambiguous model/retry accounting'
    if 'accounting' in row:
        assert row['accounting']['accepted']
        identities=[i['canonical_id'] for i in row['accounting']['invocations']]
        assert len(identities)==len(starts)==len(set(identities))
    else:
        assert len({e['event']['callId'] for e in starts})==len(starts),'Duplicate model call IDs'
    end_ms=row['run_end_ms'];start_ms=end_ms-round(run['elapsed_seconds']*1000)
    assert start_ms<=min(e['at'] for e in starts) and max(e['at'] for e in ends)<=end_ms
    provider=TracerProvider(resource=Resource.create({'service.name':'openclaw-followup','openinference.project.name':project,'openclaw.version':'2026.9.7'}))
    collector=InMemorySpanExporter();provider.add_span_processor(SimpleSpanProcessor(collector));tracer=provider.get_tracer('openclaw.followup.normalized')
    root=tracer.start_span('openclaw_diagnostic_run',start_time=start_ms*1_000_000,attributes={
      'openinference.span.kind':'CHAIN','scenario_id':run['scenario_id'],'tool_budget':run['configured_tool_budget'],
      'runtime.id':row['runtime_id'],'model.id':run['model_name'],'repetition':row['repetition'],
      'requested_calls':row['requested_calls'],'executed_calls':row['executed_calls'],'blocked_calls':row['blocked_calls'],
      'tools_remained_visible':row['tools_remained_visible'],'finalization_policy':'blocked result then natural answer; differs from Microsoft tools-disabled finalization',
      'stop_reason':run['stop_reason'],'latency_seconds':run['elapsed_seconds'],
      'input.value':run['user_report'],'output.value':json.dumps(run['final_diagnosis']),'output.mime_type':'application/json',
      'trace.source':'post-run normalized OpenClaw events; native exporter disabled',
      'timing.scope':'native run duration; event-anchored root, model and tool boundaries'})
    context=set_span_in_context(root)
    if 'physical_attempt' in row:
        root.set_attribute('physical_attempt',row['physical_attempt'])
        root.set_attribute('intended_repetition',row['intended_repetition'])
    for i,(start,end,message,request) in enumerate(zip(starts,ends,row['assistant_messages'],requests),1):
        usage=message['usage'];prompt=usage.get('input',0)+usage.get('cacheRead',0)+usage.get('cacheWrite',0)
        span=tracer.start_span(f'model_turn_{i}',context=context,start_time=start['at']*1_000_000,attributes={
          'openinference.span.kind':'LLM','llm.model_name':MODEL,'runtime.id':row['runtime_id'],'model_turn':i,
          'llm.token_count.prompt':prompt,'llm.token_count.completion':usage['output'],'llm.token_count.total':usage['totalTokens'],
          'llm.token_count.prompt_details.cache_read':usage.get('cacheRead',0),'input.value':json.dumps(request['body']),
          'output.value':json.dumps(message['content']),'input.mime_type':'application/json','output.mime_type':'application/json',
          'stop_reason':message['stopReason'],'native_model_duration_ms':end['event']['durationMs']})
        if 'accounting' in row:
            invocation=row['accounting']['invocations'][i-1]
            span.set_attribute('model.canonical_invocation_id',invocation['canonical_id'])
            span.set_attribute('model.accounting',json.dumps(invocation))
        phase=request.get('phase','diagnostic')
        span.set_attribute('phase',phase)
        if phase=='finalization':
            span.set_attribute('tools_enabled',False)
            span.set_attribute('finalization_adapter',True)
        span.end(end_time=end['at']*1_000_000)
    for call,recorded in zip(run['tool_calls'],row['tool_recorded_ms']):
        end_ns=recorded*1_000_000;start_ns=end_ns-int(call['elapsed_seconds']*1e9)
        assert start_ms*1_000_000<=start_ns<=end_ns<=end_ms*1_000_000
        attrs={'openinference.span.kind':'TOOL' if call['executed'] else 'CHAIN','tool.name':call['tool_name'],
          'tool_index':call['tool_index'],'executed':call['executed'],'blocked':not call['executed'],
          'input.value':json.dumps(call['arguments']),'output.value':json.dumps(call['output']),
          'input.mime_type':'application/json','output.mime_type':'application/json','latency.scope':'Python recorder invoke; excludes IPC'}
        if call['executed'] and 'evidence_id' in call['output']:attrs['evidence_id']=call['output']['evidence_id']
        span=tracer.start_span(call['tool_name'] if call['executed'] else 'blocked_diagnostic_request',context=context,start_time=start_ns,attributes=attrs)
        span.end(end_time=end_ns)
    root.end(end_time=end_ms*1_000_000)
    spans=collector.get_finished_spans();blob=encode_spans(spans).SerializeToString()
    ids={'trace_id':f'{root.get_span_context().trace_id:032x}','span_id':f'{root.get_span_context().span_id:016x}',
      'span_count':len(spans),'trace_start_ms':start_ms,'trace_end_ms':end_ms}
    provider.shutdown();return blob,ids

def publish_and_validate(client,row,output,experiment,example):
    assert not row['run']['error'] and row['run']['final_diagnosis'] is not None,'Cannot publish an invalid result as an accepted run'
    rowfile=output/'runs'/f"{row['run_id']}.json";project=experiment['project_name']
    requests=json.loads((output/'requests'/f"{row['run_id']}.json").read_text())
    if 'trace_id' not in row:
        blob,ids=build_trace(row,requests,project);row.update(ids,project_name=project)
        path=output/'traces'/f"{row['run_id']}.otlp.pb";path.parent.mkdir(exist_ok=True);path.write_bytes(blob);dump(rowfile,row)
    else:blob=(output/'traces'/f"{row['run_id']}.otlp.pb").read_bytes()
    response=httpx.post('http://127.0.0.1:6006/v1/traces',content=blob,headers={'Content-Type':'application/x-protobuf'},timeout=30);response.raise_for_status()
    # Re-export uses the same span IDs; Phoenix upserts rather than adding spans.
    spans=[]
    for _ in range(30):
        spans=client.spans.get_spans(project_identifier=project,trace_ids=[row['trace_id']],limit=1000)
        if len(spans)==row['span_count']:break
        time.sleep(1)
    checks=validate_spans(row,spans)
    values=evaluation_values(row,load_scenarios())
    if 'experiment_run_id' not in row:
        record=client.experiments.log_run(experiment_id=experiment['id'],dataset_example_id=example['id'],output=row,
          start_time=datetime.fromtimestamp(row['trace_start_ms']/1000,timezone.utc),end_time=datetime.fromtimestamp(row['trace_end_ms']/1000,timezone.utc),
          repetition_number=row['repetition'],trace_id=row['trace_id'],error=row['run']['error'])
        row['experiment_run_id']=record['id'];dump(rowfile,row)
    for name,value in values.items():
        explanation='Existing deterministic rubric v2; executed calls only. OpenClaw finalization differs from Microsoft.'
        client.spans.add_span_annotation(span_id=row['span_id'],annotation_name=name,annotator_kind='CODE',score=value,label=str(value),explanation=explanation,identifier='openclaw-followup-v1',sync=True)
        client.experiments.log_evaluation(experiment_run_id=row['experiment_run_id'],name=name,annotator_kind='CODE',score=value,label=str(value),explanation=explanation)
    client.spans.add_span_annotation(span_id=row['span_id'],annotation_name='finalization_semantics',annotator_kind='CODE',
      label='tools_visible_after_cap',explanation=f"Requested={row['requested_calls']}; executed={row['executed_calls']}; blocked={row['blocked_calls']}. Natural final answer after observed results; no tools-disabled transition.",identifier='openclaw-followup-v1',sync=True)
    annotations=client.spans.get_span_annotations(project_identifier=project,span_ids=[row['span_id']],limit=1000)
    found={a['name']:a for a in annotations}
    assert all(name in found and found[name]['result']['score']==value for name,value in values.items()),'Evaluator annotation mismatch'
    experiment_back=client.experiments.get_experiment(experiment_id=experiment['id'])
    ev=[e for e in experiment_back['evaluation_runs'] if e.experiment_run_id==row['experiment_run_id']]
    assert len(ev)==len(values)
    for e in ev:
        assert not e.error
        result=e.result[0] if isinstance(e.result,list) else e.result
        assert result['score']==values[e.name]
    checks['evaluator_attachment_works']=True
    project_info=client.projects.get(project_name=project)
    row['trace_url']=f"http://127.0.0.1:6006/projects/{project_info['id']}/traces/{row['trace_id']}"
    row['experiment_url']=client.experiments.get_experiment_url(experiment['dataset_id'],experiment['id'])
    row['gate']=checks;dump(rowfile,row)
    dump(output/'traces'/f"{row['run_id']}.json",spans);dump(output/'annotations'/f"{row['run_id']}.json",annotations)
    return row

def validate_spans(row,spans):
    run=row['run'];roots=[s for s in spans if not s.get('parent_id')]
    assert len(spans)==row['span_count'] and len({s['context']['span_id'] for s in spans})==len(spans)
    assert len(roots)==1 and roots[0]['context']['span_id']==row['span_id']
    root=roots[0];attrs=root['attributes']
    assert all(s is root or s['parent_id']==row['span_id'] for s in spans)
    tools=sorted((s for s in spans if s['span_kind']=='TOOL'),key=lambda s:s['attributes']['tool_index'])
    executed=[c for c in run['tool_calls'] if c['executed']]
    assert len(tools)==len(executed)==run['number_of_tool_calls']
    from agent_tool_budget_lab.environment import DiagnosticEnvironment
    from agent_tool_budget_lab.tools import DiagnosticTools
    reference=DiagnosticTools(DiagnosticEnvironment(load_scenarios()[run['scenario_id']].runtime))
    for span,call in zip(tools,executed):
        a=span['attributes'];assert a['executed'] is True
        assert a['tool_index']==call['tool_index'] and a['tool.name']==call['tool_name']
        assert json.loads(a['input.value'])==call['arguments'] and json.loads(a['output.value'])==call['output']
        assert call['output']==getattr(reference,call['tool_name'])(call['arguments']['component']).model_dump()
        assert a['evidence_id']==call['output']['evidence_id']
    blocked=[s for s in spans if s['name']=='blocked_diagnostic_request']
    assert len(blocked)==row['blocked_calls'] and all(s['attributes']['executed'] is False and s['span_kind']!='TOOL' for s in blocked)
    llms=[s for s in spans if s['span_kind']=='LLM'];assert len(llms)==len(row['assistant_messages'])
    if 'accounting' in row:
        expected={i['canonical_id']:i for i in row['accounting']['invocations']}
        assert len(expected)==len(llms)
        assert {s['attributes'].get('model.canonical_invocation_id') for s in llms}==set(expected)
        for s in llms:
            assert json.loads(s['attributes']['model.accounting'])==expected[s['attributes']['model.canonical_invocation_id']]
    if 'finalization' in row:
        final=[s for s in llms if s['attributes'].get('phase')=='finalization']
        assert len(final)==1
        attrs_final=final[0]['attributes']
        assert attrs_final['tools_enabled'] is False and attrs_final['finalization_adapter'] is True
        request=json.loads(attrs_final['input.value'])
        assert not request.get('tools')
        assert attrs_final['llm.token_count.total']==row['cost_split']['finalization_tokens']
    assert sum(s['attributes'].get('llm.token_count.total',0) for s in spans)==run['usage']['total_token_count']
    assert not any(k.startswith('llm.token_count') for k in attrs)
    assert attrs['model.id']==MODEL and attrs['runtime.id']=='openclaw'
    assert json.loads(attrs['output.value'])==run['final_diagnosis'] and run['final_diagnosis'] is not None
    assert attrs['latency_seconds']==run['elapsed_seconds']>0
    span_duration=(datetime.fromisoformat(root['end_time'].replace('Z','+00:00'))-datetime.fromisoformat(root['start_time'].replace('Z','+00:00'))).total_seconds()
    assert abs(span_duration-run['elapsed_seconds'])<0.002
    for s in llms:
        assert s['attributes']['llm.model_name']==MODEL
        for forbidden in ['required_evidence','acceptable_root_causes','difficulty','rubric','README.md']:
            assert forbidden not in s['attributes']['input.value']
    return {name:True for name in ['phoenix_ingestion_works','correct_tool_count','no_duplicate_spans','token_accounting_trustworthy',
      'latency_accounting_trustworthy','evidence_ids_preserved','exact_model_id_preserved','runtime_id_preserved',
      'blocked_calls_distinguishable','final_diagnosis_captured','no_ground_truth_leakage']}
