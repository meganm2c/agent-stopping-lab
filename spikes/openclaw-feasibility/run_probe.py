"""One isolated preflight by default. Live smoke requires an explicit flag."""
import json,os,subprocess,sys,tempfile,uuid
from pathlib import Path

SPIKE=Path(__file__).resolve().parent
ROOT=SPIKE.parents[1]
live='--live' in sys.argv
mode='live' if live else 'preflight'
run=SPIKE/'outputs'/f'{mode}-{uuid.uuid4().hex[:10]}'
run.mkdir(parents=True)
workspace=Path(tempfile.mkdtemp(prefix='openclaw-diagnostic-'))
state=run/'state';state.mkdir()
fixture=json.loads(subprocess.check_output([str(ROOT/'.venv/bin/python'),str(SPIKE/'bridge.py'),'--fixture'],cwd=ROOT))
(run/'fixture.json').write_text(json.dumps(fixture))
model='gpt-4.1-mini-2025-04-14';handle='openai/'+model
config={
 'agents':{'defaults':{'workspace':str(workspace),'skipBootstrap':True,'contextInjection':'never',
   'model':{'primary':handle,'fallbacks':[]},'models':{handle:{'agentRuntime':{'id':'openclaw'},'params':{'temperature':0,'parallel_tool_calls':False,'responsesServerCompaction':False}}},
   'thinkingDefault':'off','modelPolicy':{'allow':[handle]},'maxConcurrent':1}},
 'memory':{'search':{'enabled':False}},
 'models':{'mode':'replace','providers':{'openai':{'baseUrl':'https://api.openai.com/v1','api':'openai-completions','apiKey':'${OPENAI_API_KEY}',
    'models':[{'id':model,'name':model,'reasoning':False,'input':['text'],'contextWindow':1047576,'maxTokens':32768}]}}},
 'tools':{'allow':['check_status','read_logs','check_recent_change'],'toolSearch':False,'codeMode':{'enabled':False}},
 'plugins':{'allow':['openai','diagnostic-spike'],'load':{'paths':[str(SPIKE/'plugin')]},'slots':{'memory':'none'},'entries':{'diagnostic-spike':{'enabled':True,'hooks':{'allowPromptInjection':True,'allowConversationAccess':True}}}},
 'skills':{'allowBundled':[]},'gateway':{'mode':'local'},'logging':{'level':'error','consoleLevel':'error'}
}
(run/'config.json').write_text(json.dumps(config,indent=2))
env={k:v for k,v in os.environ.items() if k in ['PATH','HOME','TMPDIR','USER','LANG','SHELL']}
key='preflight-placeholder-not-a-real-key'
if live:
 proven=False
 for captured in (SPIKE/'outputs').glob('preflight-*/requests.jsonl'):
  for line in captured.read_text().splitlines():
   r=json.loads(line);b=r['body']
   proven |= r['blocked'] and b.get('model')==model and b.get('temperature')==0 and b.get('parallel_tool_calls') is False and sorted(t.get('function',{}).get('name','') for t in b.get('tools',[]))==['check_recent_change','check_status','read_logs']
 if not proven:raise SystemExit('A passing guarded preflight is required before live inference')
 from dotenv import dotenv_values
 key=dotenv_values(ROOT/'.env').get('OPENAI_API_KEY')
 if not key:raise SystemExit('No OpenAI key configured')
env.update(OPENCLAW_STATE_DIR=str(state),OPENCLAW_CONFIG_PATH=str(run/'config.json'),
 OPENCLAW_NO_RESPAWN='1',OPENCLAW_DISABLE_BONJOUR='1',OPENCLAW_SKIP_CHANNELS='1',OPENCLAW_EXEC_SHELL_SNAPSHOT='0',
 OPENAI_API_KEY=key,SPIKE_MODE=mode,SPIKE_FIXTURE=str(run/'fixture.json'),SPIKE_EVENTS=str(run/'events.jsonl'),
 SPIKE_REQUESTS=str(run/'requests.jsonl'),SPIKE_PYTHON=str(ROOT/'.venv/bin/python'),SPIKE_BRIDGE=str(SPIKE/'bridge.py'),
 NODE_OPTIONS='--import='+str(SPIKE/'request_guard.mjs'))
node=Path(os.environ.get('OPENCLAW_SPIKE_NODE',str(SPIKE/'.runtime/node/bin/node')))
command=[str(node),str(SPIKE/'node_modules/openclaw/openclaw.mjs'),'agent','--local','--session-id',str(uuid.uuid4()),'--message',fixture['report'],'--json','--timeout','120']
with (run/'stdout.json').open('w') as stdout,(run/'stderr.log').open('w') as stderr:
 try:result=subprocess.run(command,cwd=workspace,env=env,stdout=stdout,stderr=stderr,timeout=180);code=result.returncode
 except subprocess.TimeoutExpired:code=124
(run/'process.json').write_text(json.dumps({'mode':mode,'exitCode':code,'selectedRuntime':'openclaw','model':handle,'workspace':str(workspace)}))
print(json.dumps({'outputDirectory':str(run.relative_to(ROOT)),'exitCode':code}))
sys.exit(code)
