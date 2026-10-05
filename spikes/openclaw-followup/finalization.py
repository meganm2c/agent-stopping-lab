"""An explicit, zero-tool finalization boundary. No response repair or evaluation input."""
import json,os,subprocess,tempfile,time,uuid
from pathlib import Path
from dotenv import dotenv_values
from adapter import ROOT,HERE,SPIKE,MODEL,config,dump
from agent_tool_budget_lab.models import Diagnosis,ToolCall,StatusOutput,LogsOutput,ChangeOutput
from agent_tool_budget_lab.agent import SYSTEM_PROMPT
from recovery import digest

VOCABULARY=SYSTEM_PROMPT.split('Use this shared root-cause vocabulary: ',1)[1].split('. Use unknown',1)[0].replace('\n','').split(',')
VOCABULARY=[v.strip() for v in VOCABULARY]+['unknown']

def freeze(report,calls):
    ordered=[]
    for value in calls:
        c=ToolCall.model_validate(value)
        if c.executed:
            {'check_status':StatusOutput,'read_logs':LogsOutput,'check_recent_change':ChangeOutput}[c.tool_name].model_validate(c.output,strict=True)
            ordered.append({'tool_index':c.tool_index,'tool_name':c.tool_name,'arguments':c.arguments,'output':c.output})
    payload={'original_user_report':report,'ordered_observed_evidence':ordered,'allowed_root_cause_vocabulary':VOCABULARY}
    schema=Diagnosis.model_json_schema()
    system='Using only the observed evidence below, produce the final diagnosis. Return valid JSON matching this exact schema. Do not call tools. Do not add markdown or commentary.\n'+json.dumps(schema,sort_keys=True)
    return {'system':system,'user':json.dumps(payload,sort_keys=True),'schema':schema,'evidence_sha256':digest(ordered)}

def parse_final(text,fixture):
    diagnosis=Diagnosis.model_validate_json(text,strict=True)
    observed={e['output']['evidence_id'] for e in json.loads(fixture['user'])['ordered_observed_evidence']}
    assert set(diagnosis.evidence_used)<=observed,'Finalizer cited unobserved evidence'
    return diagnosis

def run_finalizer(fixture,output,run_id,native_probe=False):
    raw=HERE/'.local/finalization'/run_id
    assert not raw.exists(),'Refuse duplicate finalizer inference'
    raw.mkdir(parents=True);workspace=Path(tempfile.mkdtemp(prefix='openclaw-finalizer-'));state=raw/'state'
    cfg=config(workspace);cfg['tools']={'deny':['*'],'toolSearch':False,'codeMode':{'enabled':False}}
    cfg['plugins']={'allow':['openai','diagnostic-finalizer'],'load':{'paths':[str(HERE/'finalizer-plugin')]},'slots':{'memory':'none'},'entries':{'diagnostic-finalizer':{'enabled':True,'llm':{'allowModelOverride':True,'allowedCompletionModels':['openai/'+MODEL]}}}}
    dump(raw/'config.json',cfg);dump(raw/'fixture.json',fixture);dump(state/'agents/main/agent/settings.json',{'retry':{'provider':{'maxRetries':0}}})
    env={k:v for k,v in os.environ.items() if k in ['PATH','HOME','TMPDIR','USER','LANG','SHELL']}
    env.update(OPENCLAW_STATE_DIR=str(state),OPENCLAW_CONFIG_PATH=str(raw/'config.json'),OPENCLAW_NO_RESPAWN='1',OPENCLAW_DISABLE_BONJOUR='1',OPENCLAW_SKIP_CHANNELS='1',OPENCLAW_EXEC_SHELL_SNAPSHOT='0',OPENAI_API_KEY=dotenv_values(ROOT/'.env')['OPENAI_API_KEY'],FINALIZER_FIXTURE=str(raw/'fixture.json'),FINALIZER_RESULT=str(raw/'result.json'),SPIKE_REQUESTS=str(raw/'requests.jsonl'),SPIKE_TRANSPORT=str(raw/'transport.jsonl'),SPIKE_MODE='preflight' if native_probe else 'live',NODE_OPTIONS='--import='+str(HERE/'finalizer_guard.mjs'))
    if native_probe:env['FINALIZER_NATIVE_PROBE']='1'
    started=time.time()
    with (raw/'stdout.log').open('w') as stdout,(raw/'stderr.log').open('w') as stderr:
        proc=subprocess.run([str(SPIKE/'.runtime/node/bin/node'),str(SPIKE/'node_modules/openclaw/openclaw.mjs'),'diagnostic-finalize'],cwd=workspace,env=env,stdout=stdout,stderr=stderr,timeout=120)
    ended=time.time()
    result=json.loads((raw/'result.json').read_text()) if (raw/'result.json').exists() else {'ok':False,'error':'No finalizer result','returncode':proc.returncode}
    def lines(name):return [json.loads(l) for l in (raw/name).read_text().splitlines()] if (raw/name).exists() else []
    saved={'run_id':run_id,'fixture':fixture,'completion':result,'requests':lines('requests.jsonl'),'transport':lines('transport.jsonl'),'wall_start':started,'wall_end':ended,'wall_seconds':ended-started}
    dump(output/'finalization'/f'{run_id}.json',saved)
    return saved
