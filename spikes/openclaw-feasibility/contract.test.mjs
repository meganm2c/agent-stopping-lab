import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,readFileSync,writeFileSync,rmSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {execFileSync} from 'node:child_process';
import plugin from './plugin/index.js';
import {requests, run} from './fixtures/contract.mjs';

const root=resolve(import.meta.dirname,'../..');
const python=join(root,'.venv/bin/python');
test('guard blocks byte-encoded bodies, mismatched snapshots and header logging',()=>{
  const temp=mkdtempSync(join(tmpdir(),'openclaw-guard-'));
  try {
    const code=`
      import assert from 'node:assert/strict';
      import {readFileSync} from 'node:fs';
      let network=0;globalThis.fetch=async()=>{network++;throw Error('Network forbidden');};
      await import(${JSON.stringify(new URL('./request_guard.mjs',import.meta.url).href)});
      const body={model:'gpt-4.1-mini-2025-04-14',temperature:0,parallel_tool_calls:false,
        tools:['check_status','read_logs','check_recent_change'].map(name=>({function:{name}}))};
      const send=()=>fetch('https://api.openai.com/v1/chat/completions',{method:'POST',
        headers:{authorization:'Bearer secret-test-sentinel'},body:new TextEncoder().encode(JSON.stringify(body))});
      assert.equal((await send()).status,400);
      process.env.SPIKE_MODE='live';body.model='gpt-4.1-mini';
      assert.equal((await send()).status,400);assert.equal(network,0);
      assert.equal(readFileSync(process.env.SPIKE_REQUESTS,'utf8').includes('secret-test-sentinel'),false);
    `;
    execFileSync(process.execPath,['--input-type=module','-e',code],{env:{...process.env,SPIKE_MODE:'preflight',SPIKE_REQUESTS:join(temp,'requests.jsonl')}});
  } finally {rmSync(temp,{recursive:true,force:true});}
});
test('concurrent wrapper requests are serialized, capped, and fresh per registration',async()=>{
  const temp=mkdtempSync(join(tmpdir(),'openclaw-contract-'));
  const previous={...process.env};
  try {
    const fixture=execFileSync(python,[join(import.meta.dirname,'bridge.py'),'--fixture']);
    writeFileSync(join(temp,'fixture.json'),fixture);
    Object.assign(process.env,{SPIKE_MODE:'live',SPIKE_PYTHON:python,
      SPIKE_BRIDGE:join(import.meta.dirname,'bridge.py'),SPIKE_FIXTURE:join(temp,'fixture.json'),SPIKE_EVENTS:join(temp,'events.jsonl')});
    const create=()=>{
      const tools={},hooks={};
      plugin.register({registerTool:t=>tools[t.name]=t,on:(name,handler)=>hooks[name]=handler});
      return {tools,hooks};
    };
    const first=create();
    assert.deepEqual(Object.keys(first.tools).sort(),['check_recent_change','check_status','read_logs']);
    const results=await Promise.all(Array.from({length:12},(_,i)=>first.tools.check_status.execute(String(i),{component:'api'})));
    assert.deepEqual(results.map(r=>r.details.call.tool_index),Array.from({length:12},(_,i)=>i+1));
    assert.equal(results.filter(r=>r.details.call.executed).length,2);
    assert.ok(results.slice(2).every(r=>r.details.output.error==='tool_budget_exhausted'&&!('evidence_id' in r.details.output)));
    first.hooks.agent_end({},{});
    const second=create();
    const next=await second.tools.check_status.execute('fresh',{component:'api'});
    assert.equal(next.details.call.tool_index,1);assert.equal(next.details.call.executed,true);
    second.hooks.agent_end({},{});
  } finally {
    for(const key of Object.keys(process.env)) if(!(key in previous))delete process.env[key];
    Object.assign(process.env,previous);rmSync(temp,{recursive:true,force:true});
  }
});
test('offline request fixtures preserve snapshot/settings and expose only diagnostic schemas',()=>{
  assert.equal(requests.length,4);
  for(const {body,blocked} of requests){
    assert.equal(blocked,false);assert.equal(body.model,'gpt-4.1-mini-2025-04-14');
    assert.equal(body.temperature,0);assert.equal(body.parallel_tool_calls,false);
    assert.deepEqual(body.tools.map(t=>t.function.name).sort(),['check_recent_change','check_status','read_logs']);
    assert.equal(body.messages.some(m=>/required_evidence|difficulty|rubric|README\.md|Desktop\//.test(JSON.stringify(m))),false);
  }
});
test('offline final answer follows denied execution and usage is counted once',()=>{
  assert.deepEqual(run.calls.map(c=>c.executed),[true,true,false]);
  assert.equal(run.finalDiagnosis.predicted_root_cause,'api_configuration_issue');
  assert.equal(run.stopReason,'stop');assert.equal(run.actualRuntime,'openclaw');
  assert.equal(run.assistantMessages.reduce((sum,m)=>sum+m.usage.totalTokens,0),run.usage.total);
});
