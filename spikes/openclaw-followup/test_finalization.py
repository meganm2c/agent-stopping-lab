import json,pytest
from finalization import freeze,parse_final
from pydantic import ValidationError

def fixture():
 return freeze('Incident',[{'tool_index':1,'tool_name':'check_status','arguments':{'component':'api'},'output':{'component':'api','status':'healthy','detail':'Observed','evidence_id':'api_status'},'executed':True,'elapsed_seconds':0.1}])

def test_strict_json():
 f=fixture();assert parse_final(json.dumps({'predicted_root_cause':'unknown','explanation':'Observed','evidence_used':['api_status']}),f).predicted_root_cause=='unknown'
@pytest.mark.parametrize('text',['predicted_root_cause: unknown','```json\n{}\n```','{"predicted_root_cause":"unknown","explanation":"x","evidence_used":[],"extra":true}','{"predicted_root_cause":1,"explanation":"x","evidence_used":[]}'])
def test_no_repair_or_extra_fields(text):
 with pytest.raises(ValidationError):parse_final(text,fixture())
def test_unobserved_evidence_rejected():
 with pytest.raises(AssertionError):parse_final(json.dumps({'predicted_root_cause':'unknown','explanation':'x','evidence_used':['secret_evidence']}),fixture())
def test_freeze_allowlist():
 f=fixture();p=json.loads(f['user']);assert set(p)=={'original_user_report','ordered_observed_evidence','allowed_root_cause_vocabulary'}
 assert 'final_diagnosis' not in f['user'] and 'required_evidence' not in f['user']
 assert len(p['allowed_root_cause_vocabulary'])==7

def test_tool_output_cannot_carry_hidden_rubric():
 f=fixture();call=json.loads(f['user'])['ordered_observed_evidence'][0]
 call['output']['required_evidence']=['private'];call.update(executed=True,elapsed_seconds=0.1)
 with pytest.raises(ValidationError):freeze('Incident',[call])

def test_frozen_evidence_cannot_be_changed_after_run():
 from pathlib import Path
 from finalization_lifecycle import assemble
 from adapter import ROOT
 import copy
 from offline_fixtures import finalization_inputs
 row,f,requests=finalization_inputs()
 corrupted=copy.deepcopy(f);corrupted['fixture']['user']+=' extra'
 with pytest.raises(AssertionError,match='Frozen evidence changed'):assemble(row,corrupted,requests)
 combined,_=assemble(row,f,requests)
 assert combined['run']['usage']['total_token_count']==combined['cost_split']['diagnostic_loop_tokens']+combined['cost_split']['finalization_tokens']

@pytest.mark.parametrize('mutation',['none','extra_tool','previous_answer','different_model'])
def test_finalizer_outbound_guard(tmp_path,mutation):
 import os,subprocess
 from pathlib import Path
 here=Path(__file__).resolve().parent;f=fixture();(tmp_path/'fixture').write_text(json.dumps(f))
 body={'model':'gpt-4.1-mini-2025-04-14','temperature':0,'messages':[{'role':'system','content':f['system']},{'role':'user','content':f['user']}]}
 if mutation=='extra_tool':body['tools']=[{'function':{'name':'read_logs'}}]
 if mutation=='previous_answer':body['messages'].append({'role':'assistant','content':'previous malformed answer'})
 if mutation=='different_model':body['model']='gpt-4.1-mini'
 script="""
 let forwarded=0;globalThis.fetch=async()=>{forwarded++;return new Response('{}',{status:200,headers:{'x-request-id':'test'}});};
 await import(process.env.TEST_GUARD);
 let rejected=false;try{await fetch('https://api.openai.com/v1/chat/completions',{body:process.env.TEST_BODY});}catch{rejected=true;}
 const valid=process.env.TEST_VALID==='1';if(valid?(rejected||forwarded!==1):(!rejected||forwarded!==0))process.exit(1);
 """
 env=dict(os.environ,FINALIZER_FIXTURE=str(tmp_path/'fixture'),SPIKE_REQUESTS=str(tmp_path/'requests'),SPIKE_TRANSPORT=str(tmp_path/'transport'),SPIKE_MODE='live',TEST_GUARD=(here/'finalizer_guard.mjs').as_uri(),TEST_BODY=json.dumps(body),TEST_VALID='1' if mutation=='none' else '0')
 subprocess.run(['node','--input-type=module','-e',script],env=env,check=True,capture_output=True)
