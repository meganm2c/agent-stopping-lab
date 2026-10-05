"""Run isolated OpenClaw and normalize its actual saved events to the existing contract."""
import hashlib,json,os,signal,subprocess,sys,tempfile,time,uuid
from pathlib import Path
from dotenv import dotenv_values
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];SPIKE=ROOT/'spikes/openclaw-feasibility'
sys.path.insert(0,str(ROOT/'src'))
from agent_tool_budget_lab.agent import SYSTEM_PROMPT
from agent_tool_budget_lab.models import AgentRunResult,Diagnosis,ToolCall
from agent_tool_budget_lab.scenarios import load_scenarios
from agent_tool_budget_lab.evaluation import metrics
MODEL='gpt-4.1-mini-2025-04-14'
TOOLS=['check_recent_change','check_status','read_logs']

def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,default=str)+'\n')

def config(workspace):
    handle='openai/'+MODEL
    return {
      'agents':{'defaults':{'workspace':str(workspace),'skipBootstrap':True,'contextInjection':'never',
        'model':{'primary':handle,'fallbacks':[]},'models':{handle:{'agentRuntime':{'id':'openclaw'},'params':{'temperature':0,'parallel_tool_calls':False,'responsesServerCompaction':False}}},
        'thinkingDefault':'off','modelPolicy':{'allow':[handle]},'maxConcurrent':1}},
      'memory':{'search':{'enabled':False}},
      'models':{'mode':'replace','providers':{'openai':{'baseUrl':'https://api.openai.com/v1','api':'openai-completions','apiKey':'${OPENAI_API_KEY}',
        'models':[{'id':MODEL,'name':MODEL,'reasoning':False,'input':['text'],'contextWindow':1047576,'maxTokens':32768}]}}},
      'tools':{'allow':TOOLS,'toolSearch':False,'codeMode':{'enabled':False}},
      'plugins':{'allow':['openai','diagnostic-spike'],'load':{'paths':[str(SPIKE/'plugin')]},'slots':{'memory':'none'},'entries':{'diagnostic-spike':{'enabled':True,'hooks':{'allowPromptInjection':True,'allowConversationAccess':True}}}},
      'skills':{'allowBundled':[]},'gateway':{'mode':'local'},'logging':{'level':'error','consoleLevel':'error'}}

def run_once(sid,budget,repetition,output,namespace=None,retry_zero=True,inject_failure=False,physical_attempt=1):
    raw_root=HERE/'.local' if namespace is None else HERE/'.local'/namespace
    previous=list(raw_root.glob(f'{sid}-b{budget}-r{repetition}-*'))
    if previous:
        raise RuntimeError('Saved attempt already exists for this slot; inspect it instead of repeating inference')
    run_id=f'{sid}-b{budget}-r{repetition}-{uuid.uuid4().hex[:8]}'
    raw=raw_root/run_id;raw.mkdir(parents=True)
    workspace=Path(tempfile.mkdtemp(prefix='openclaw-followup-'));state=raw/'state';state.mkdir()
    env={k:v for k,v in os.environ.items() if k in ['PATH','HOME','TMPDIR','USER','LANG','SHELL']}
    env.update(FOLLOWUP_SCENARIO=sid,FOLLOWUP_BUDGET=str(budget))
    fixture=json.loads(subprocess.check_output([str(ROOT/'.venv/bin/python'),str(HERE/'bridge.py'),'--fixture'],env=env,cwd=workspace))
    dump(raw/'fixture.json',fixture);dump(raw/'config.json',config(workspace))
    if retry_zero:
        dump(state/'agents/main/agent/settings.json',{'retry':{'provider':{'maxRetries':0}}})
    dump(raw/'attempt.json',{'scenario_id':sid,'budget':budget,'intended_repetition':repetition,'physical_attempt':physical_attempt,'run_id':run_id,'retry_zero':retry_zero,'injected_failure':inject_failure})
    key=dotenv_values(ROOT/'.env').get('OPENAI_API_KEY');assert key,'No OpenAI key configured'
    env.update(OPENCLAW_STATE_DIR=str(state),OPENCLAW_CONFIG_PATH=str(raw/'config.json'),
      OPENCLAW_NO_RESPAWN='1',OPENCLAW_DISABLE_BONJOUR='1',OPENCLAW_SKIP_CHANNELS='1',OPENCLAW_EXEC_SHELL_SNAPSHOT='0',
      OPENAI_API_KEY=key,SPIKE_MODE='live',SPIKE_FIXTURE=str(raw/'fixture.json'),SPIKE_EVENTS=str(raw/'events.jsonl'),
      SPIKE_REQUESTS=str(raw/'requests.jsonl'),SPIKE_PYTHON=str(ROOT/'.venv/bin/python'),SPIKE_BRIDGE=str(HERE/'bridge.py'),
      SPIKE_TRANSPORT=str(raw/'transport.jsonl'),
      NODE_OPTIONS='--import='+str(HERE/'request_guard.mjs'))
    if retry_zero:
        env.update(SPIKE_RETRY_SETTINGS=str(raw/'retry-settings.jsonl'))
        env['NODE_OPTIONS']+=' --import='+str(HERE/'retry_observer.mjs')
    if inject_failure:env['SPIKE_INJECT_FAILURE']='1'
    node=Path(os.environ.get('OPENCLAW_SPIKE_NODE',str(SPIKE/'.runtime/node/bin/node')))
    command=[str(node),str(SPIKE/'node_modules/openclaw/openclaw.mjs'),'agent','--local','--session-id',str(uuid.uuid4()),'--message',fixture['report'],'--json','--timeout','180']
    started=time.time()
    with (raw/'stdout.json').open('w') as stdout,(raw/'stderr.log').open('w') as stderr:
        proc=subprocess.Popen(command,cwd=workspace,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
        try:code=proc.wait(timeout=240)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
            code=124
    ended=time.time()
    native=json.loads((raw/'stdout.json').read_text() or '{}')
    events=[json.loads(l) for l in (raw/'events.jsonl').read_text().splitlines()] if (raw/'events.jsonl').exists() else []
    requests=[json.loads(l) for l in (raw/'requests.jsonl').read_text().splitlines()] if (raw/'requests.jsonl').exists() else []
    transport=[json.loads(l) for l in (raw/'transport.jsonl').read_text().splitlines()] if (raw/'transport.jsonl').exists() else []
    from recovery import audit
    accounting=audit(events,requests,transport,fixture['system'],fixture['report'])
    settings=[json.loads(l) for l in (raw/'retry-settings.jsonl').read_text().splitlines()] if (raw/'retry-settings.jsonl').exists() else []
    accounting.update(intended_repetition=repetition,physical_attempt=physical_attempt,retry_settings_observed=settings)
    if retry_zero and (not settings or any(s['settings'].get('maxRetries')!=0 for s in settings)):
        accounting['accepted']=False;accounting['errors'].append('Effective retry maxRetries=0 not verified')
    if retry_zero and accounting['internal_attempts']!=1:
        accounting['accepted']=False;accounting['errors'].append('No-recovery policy requires exactly one internal attempt')
    dump(output/'accounting'/f'{run_id}.json',accounting)
    dump(output/'requests'/f'{run_id}.json',requests)
    try:
        assert accounting['accepted'], '; '.join(accounting['errors'])
        row=normalize(sid,budget,repetition,native,events,requests,code)
    except Exception as exc:
        dump(output/'rejections'/f'{run_id}.json',{
            'run_id':run_id,'scenario_id':sid,'budget':budget,'repetition':repetition,
            'accepted':False,'error':str(exc),'cli_wall_seconds':ended-started,
            'raw_artifacts':str(raw.relative_to(ROOT))})
        raise
    row.update(run_id=run_id,wall_start=started,wall_end=ended,cli_wall_seconds=ended-started,accounting=accounting)
    dump(output/'runs'/f'{run_id}.json',row)
    dump(output/'requests'/f'{run_id}.json',requests)
    # Raw paths, host metadata and local state stay in ignored .local/.
    return row

def normalize(sid,budget,repetition,native,events,requests,code=0):
    scenario=load_scenarios()[sid]
    call_events=[e for e in events if e['type']=='diagnostic_call'];calls=[ToolCall.model_validate(e['data']['call']) for e in call_events]
    final_event=next((e for e in reversed(events) if e['type']=='agent_end'),None)
    messages=final_event['data']['event']['messages'] if final_event else []
    assistant=[m for m in messages if m.get('role')=='assistant']
    meta=native.get('meta',{});agent=meta.get('agentMeta',{})
    text='\n'.join(p.get('text','') for p in native.get('payloads',[]));diagnosis=None;error=None
    try:diagnosis=Diagnosis.model_validate_json(text)
    except Exception:error='No valid JSON Diagnosis'
    if code:error=f'OpenClaw process exit {code}; '+(error or 'runtime failure')
    assert all(not r['blocked'] for r in requests),'Request guard rejected runtime controls'
    for r in requests:
        b=r['body'];assert b['model']==MODEL and b['temperature']==0 and b['parallel_tool_calls'] is False
        assert sorted(t['function']['name'] for t in b['tools'])==TOOLS
        system=[m['content'] for m in b['messages'] if m['role']=='system']
        expected=SYSTEM_PROMPT.rstrip()+'\n\nCurrent model identity: openai/'+MODEL+'. If asked what model you are, answer with this value for the current run.'
        assert system==[expected], 'Unexpected system context'
        users=[m['content'] for m in b['messages'] if m['role']=='user']
        assert len(users)==1 and users[0].endswith(scenario.runtime.user_report),'Unexpected user context'
        for forbidden in ['required_evidence','acceptable_root_causes','difficulty','rubric','README.md','/Desktop/']:
            assert forbidden not in json.dumps(b['messages']),f'Unexpected runtime context: {forbidden}'
    assert sum(c.executed for c in calls)<=budget
    assert [c.tool_index for c in calls]==list(range(1,len(calls)+1))
    usage={'input_token_count':sum(m.get('usage',{}).get('input',0)+m.get('usage',{}).get('cacheRead',0)+m.get('usage',{}).get('cacheWrite',0) for m in assistant),
      'output_token_count':sum(m.get('usage',{}).get('output',0) for m in assistant),
      'total_token_count':sum(m.get('usage',{}).get('totalTokens',0) for m in assistant)}
    assert usage['input_token_count']+usage['output_token_count']==usage['total_token_count']
    if not error:
        assert agent['agentHarnessId']=='openclaw' and agent['model']==MODEL
        assert agent['terminalReceipt']['effective']['responseModel']==MODEL
        assert not agent['terminalReceipt']['rerouted']
        assert usage['total_token_count']==agent['usage']['total']
    result=AgentRunResult(scenario_id=sid,user_report=scenario.runtime.user_report,model_name=MODEL,model_provider='openai',
      configured_tool_budget=budget,tool_calls=calls,evidence_ids_retrieved=sorted({c.output['evidence_id'] for c in calls if c.executed and 'evidence_id' in c.output}),
      number_of_tool_calls=sum(c.executed for c in calls),final_diagnosis=diagnosis,elapsed_seconds=meta.get('durationMs',0)/1000,
      usage=usage,error=error,stop_reason=(assistant[-1].get('stopReason','unavailable') if assistant else 'unavailable'),
      model_settings={'temperature':0,'parallel_tool_calls':False,'framework':'OpenClaw','framework_version':'2026.9.7','api':'openai-completions','finalization':'blocked-tool-result then natural answer'},
      prompt_sha256=hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),runtime_sha256=hashlib.sha256(scenario.runtime.model_dump_json().encode()).hexdigest())
    model_events=[{'type':e['type'],'at':e['at'],'event':e['data']['event']} for e in events if e['type'] in ['model_call_started','model_call_ended']]
    for m in assistant:m.get('usage',{}).pop('cost',None)
    return {'run':result.model_dump(),'metrics':metrics(result,scenario),'repetition':repetition,
      'runtime_id':agent.get('agentHarnessId'),'terminal_receipt':agent.get('terminalReceipt'),
      'requested_calls':len(calls),'executed_calls':result.number_of_tool_calls,'blocked_calls':sum(not c.executed for c in calls),
      'tools_remained_visible':all(len(r['body']['tools'])==3 for r in requests),'request_count':len(requests),
      'assistant_messages':assistant,'model_events':model_events,'tool_recorded_ms':[e['at'] for e in call_events],
      'run_end_ms':max((e['at'] for e in events if e['type'] in ['agent_end','llm_output']),default=0),
      'effective_system':requests[0]['body']['messages'][0]['content'] if requests else None,
      'effective_user':next((m['content'] for m in requests[0]['body']['messages'] if m['role']=='user'),None) if requests else None}
