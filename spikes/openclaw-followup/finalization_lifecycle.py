"""Join diagnostic observations and one isolated finalizer into an audited run."""
import copy,json
from pathlib import Path
from adapter import MODEL,dump
from finalization import freeze,parse_final
from recovery import digest
from agent_tool_budget_lab.scenarios import load_scenarios
from agent_tool_budget_lab.evaluation import metrics
from agent_tool_budget_lab.models import AgentRunResult

def assemble(diagnostic,finalization,diagnostic_requests):
    row=copy.deepcopy(diagnostic);run=row['run'];f=finalization;c=f['completion']
    assert row['accounting']['accepted'] and row['accounting']['internal_attempts']==1
    assert run['error'] in [None,'No valid JSON Diagnosis']
    assert row['terminal_receipt']['effective']['responseModel']==MODEL and not row['terminal_receipt']['rerouted']
    assert run['number_of_tool_calls']<=run['configured_tool_budget']
    assert run['stop_reason']=='stop','Diagnostic loop did not terminate normally'
    expected=freeze(run['user_report'],run['tool_calls']);assert f['fixture']==expected,'Frozen evidence changed'
    assert c['ok'],c
    result=c['result'];assert result['model']==MODEL and result['provider']=='openai'
    assert result['execution']=={'mode':'isolated-agent-runtime','owner':{'kind':'harness','id':'openclaw'}}
    assert len(f['requests'])==len(f['transport'])==1
    req=f['requests'][0];receipt=f['transport'][0];body=req['body']
    assert not req['blocked'] and receipt['status']==200 and receipt['request_ordinal']==1
    assert body['model']==MODEL and body['temperature']==0 and not body.get('tools') and not body.get('functions')
    assert body['messages']==[{'role':'system','content':expected['system']},{'role':'user','content':expected['user']}]
    diagnosis=parse_final(result['text'],expected)
    usage=result['usage'];prompt=usage['inputTokens']+usage.get('cacheReadTokens',0)+usage.get('cacheWriteTokens',0);completion=usage['outputTokens'];total=usage['totalTokens']
    assert prompt+completion==total and total>0
    diag_usage=dict(run['usage']);diag_native=run['elapsed_seconds'];diag_end=row['run_end_ms']
    final_phase=(c['end_ms']-diag_end)/1000
    assert final_phase>0 and diag_end<=c['start_ms']<=req['at']<=c['end_ms']
    row['cost_split']={'diagnostic_loop_tokens':diag_usage['total_token_count'],'finalization_tokens':total,'total_tokens':diag_usage['total_token_count']+total,'diagnostic_loop_seconds':diag_native,'finalization_seconds':final_phase,'total_seconds':diag_native+final_phase,'finalization_completion_seconds':(c['end_ms']-c['start_ms'])/1000,'diagnostic_cli_wall_seconds':row['cli_wall_seconds'],'finalization_cli_wall_seconds':f['wall_seconds'],'end_to_end_wall_seconds':f['wall_end']-row['wall_start']}
    row['diagnostic_loop_final_output']=copy.deepcopy(row['assistant_messages'][-1]['content'])
    row['diagnostic_loop_parse_error']=run['error']
    # The new adapter always finalizes frozen evidence, irrespective of loop-answer format.
    # It never repairs or feeds the earlier answer to the finalizer.
    run.update(final_diagnosis=diagnosis.model_dump(),error=None,elapsed_seconds=diag_native+final_phase,stop_reason='adapter_finalization')
    run['usage']={k:diag_usage[k]+v for k,v in {'input_token_count':prompt,'output_token_count':completion,'total_token_count':total}.items()}
    run['model_settings']['finalization']='explicit isolated OpenClaw completion; zero tools; strict Diagnosis validation'
    row['finalization']={'mechanism':'adapter-level isolated-agent-runtime','evidence_sha256':expected['evidence_sha256'],'tools_enabled':False,'schema_valid':True,'runtime_owner':result['execution']['owner'],'finalizer_input_verified':True}
    final_usage={'input':usage['inputTokens'],'output':completion,'cacheRead':usage.get('cacheReadTokens',0),'cacheWrite':usage.get('cacheWriteTokens',0),'totalTokens':total}
    row['assistant_messages'].append({'role':'assistant','content':[{'type':'text','text':result['text']}],'usage':final_usage,'stopReason':'stop','model':MODEL,'provider':'openai'})
    native_id=row['run_id']+':finalization:1'
    for kind,at in [('model_call_started',c['start_ms']),('model_call_ended',c['end_ms'])]:
        row['model_events'].append({'type':kind,'at':at,'event':{'callId':native_id,'durationMs':c['end_ms']-c['start_ms'],'source':'adapter completion boundaries, not diagnostic-loop hooks'}})
    row['accounting']['invocations'].append({'canonical_id':native_id,'phase':'finalization','execution_owner':result['execution']['owner'],'start_ms':c['start_ms'],'end_ms':c['end_ms'],'requests':[{'request_ordinal':1,'transport':[receipt],'effective_context_sha256':digest(body['messages']),'semantic_context_sha256':digest(body['messages']),'full_messages_sha256':digest(body['messages']),'allowed_context':True}],'usage':final_usage})
    row['accounting']['request_count']+=1;row['request_count']+=1
    row['run_end_ms']=c['end_ms'];row['metrics']=metrics(AgentRunResult.model_validate(run),load_scenarios()[run['scenario_id']])
    requests=copy.deepcopy(diagnostic_requests)+[dict(req,phase='finalization')]
    return row,requests
