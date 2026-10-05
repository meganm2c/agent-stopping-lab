import copy
from recovery import audit

def fixture():
    system='Diagnose';report='Incident';s={'runId':'run','callId':'reused','sessionId':'session'}
    message={'role':'assistant','timestamp':12,'responseId':'response1','content':[],'usage':{'input':1,'output':1,'totalTokens':2},'stopReason':'stop'}
    events=[{'type':'before_agent_run','at':1,'data':{}},{'type':'model_call_started','at':10,'data':{'event':s}},{'type':'model_call_ended','at':20,'data':{'event':dict(s,outcome='completed')}},{'type':'agent_end','at':21,'data':{'event':{'messages':[message]}}}]
    body={'messages':[{'role':'system','content':system+'\n\nCurrent model identity: openai/gpt-4.1-mini-2025-04-14. If asked what model you are, answer with this value for the current run.'},{'role':'user','content':'[Fri 2026-10-02 09:23 PDT] '+report}]}
    return events,[{'at':11,'request_ordinal':1,'body':body}],[{'request_ordinal':1,'status':200,'provider_request_id':'req1'}],system,report

def test_clean():assert audit(*fixture())['accepted']
def test_prompt_drift():
    e,r,t,s,u=fixture();r[0]['body']['messages'][1]['content']+=' Continue task'
    assert not audit(e,r,t,s,u)['accepted']
def test_missing_request():
    e,r,t,s,u=fixture();assert not audit(e,[],t,s,u)['accepted']
def test_retried_http_not_collapsed():
    e,r,t,s,u=fixture();r.append(dict(copy.deepcopy(r[0]),request_ordinal=2));t.append({'request_ordinal':2,'status':200})
    a=audit(e,r,t,s,u);assert not a['accepted'];assert len(a['invocations'][0]['requests'])==2

def test_reused_call_id_has_unique_canonical_identity():
    e,r,t,s,u=fixture();other=copy.deepcopy(e)
    for x in other:x['at']+=30
    other[-1]['data']['event']['messages'][0].update(timestamp=42,responseId='response2')
    r.append(dict(copy.deepcopy(r[0]),at=41,request_ordinal=2));t.append({'request_ordinal':2,'status':200})
    a=audit(e+other,r,t,s,u);assert a['accepted'];assert len({i['canonical_id'] for i in a['invocations']})==2

def test_failed_usage_unknown():
    e,r,t,s,u=fixture();e[-1]['data']['event']['messages'][0]['stopReason']='error'
    assert not audit(e,r,t,s,u)['accepted']

def test_new_transport_guard_records_receipt_without_headers(tmp_path):
    import subprocess,json,os
    from pathlib import Path
    here=Path(__file__).resolve().parent
    node='node'
    script="""
    globalThis.fetch=async()=>new Response('{}',{status:200,headers:{'x-request-id':'req-test'}});
    await import(process.env.TEST_GUARD);
    await fetch('https://api.openai.com/v1/chat/completions',{method:'POST',headers:{Authorization:'Bearer TEST_NOT_A_SECRET'},body:JSON.stringify({model:'gpt-4.1-mini-2025-04-14',temperature:0,parallel_tool_calls:false,tools:['check_status','read_logs','check_recent_change'].map(name=>({function:{name}}))})});
    """
    env=dict(os.environ,TEST_GUARD=(here/'request_guard.mjs').as_uri(),SPIKE_MODE='live',SPIKE_REQUESTS=str(tmp_path/'requests'),SPIKE_TRANSPORT=str(tmp_path/'transport'))
    subprocess.run([str(node),'--input-type=module','-e',script],env=env,check=True,capture_output=True)
    request=json.loads((tmp_path/'requests').read_text());receipt=json.loads((tmp_path/'transport').read_text())
    assert request['request_ordinal']==receipt['request_ordinal']==1
    assert request['at']<=receipt['at'] and receipt['provider_request_id']=='req-test'
    assert 'TEST_NOT_A_SECRET' not in (tmp_path/'requests').read_text()+(tmp_path/'transport').read_text()

def test_injected_failure_never_forwards_to_provider(tmp_path):
    import subprocess,json,os
    from pathlib import Path
    here=Path(__file__).resolve().parent
    script="""
    globalThis.fetch=async()=>{throw new Error('Provider must never be contacted');};
    await import(process.env.TEST_GUARD);
    const r=await fetch('https://api.openai.com/v1/chat/completions',{method:'POST',body:JSON.stringify({model:'gpt-4.1-mini-2025-04-14',temperature:0,parallel_tool_calls:false,tools:['check_status','read_logs','check_recent_change'].map(name=>({function:{name}}))})});
    if(r.status!==503)process.exit(1);
    """
    env=dict(os.environ,TEST_GUARD=(here/'request_guard.mjs').as_uri(),SPIKE_MODE='live',SPIKE_INJECT_FAILURE='1',SPIKE_REQUESTS=str(tmp_path/'requests'),SPIKE_TRANSPORT=str(tmp_path/'transport'))
    subprocess.run(['node','--input-type=module','-e',script],env=env,check=True,capture_output=True)
    receipt=json.loads((tmp_path/'transport').read_text())
    assert receipt['injected'] and receipt['forwarded_to_provider'] is False
    assert receipt['request_ordinal']==1 and not receipt['unexpected_extra_attempt']
