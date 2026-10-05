// Inspect the actual HTTP body without changing its model, tools, or prompt.
import {appendFileSync} from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(new URL('./node_modules/openclaw/package.json',import.meta.url));
const expected='gpt-4.1-mini-2025-04-14';
const names=['check_recent_change','check_status','read_logs'];
let attempts=0;
function guarded(original){return async function(input,init){
  const url=new URL(typeof input==='string'||input instanceof URL?input:input.url);
  if(/\/(responses|chat\/completions)$/.test(url.pathname)){
    const raw=init?.body??await input.clone().text();
    const body=JSON.parse(typeof raw==='string'?raw:new TextDecoder().decode(raw));
    const visible=(body.tools??[]).map(t=>t.name??t.function?.name).sort();
    const valid=url.origin==='https://api.openai.com'&&body.model===expected&&body.temperature===0&&body.parallel_tool_calls===false&&JSON.stringify(visible)===JSON.stringify(names)&&++attempts<=8;
    const blocked=process.env.SPIKE_MODE!=='live'||!valid;
    appendFileSync(process.env.SPIKE_REQUESTS,JSON.stringify({url:url.href,body,blocked})+'\n');
    if(blocked) return new Response(JSON.stringify({error:{message:'SPIKE_GUARD: inference blocked',type:'invalid_request_error'}}),{status:400,headers:{'content-type':'application/json'}});
  } else {
    throw new Error('Spike network denied: '+url.origin+url.pathname);
  }
  return original(input,init);
};}
globalThis.fetch=guarded(globalThis.fetch);
const undici=require('undici/index.js');
undici.fetch=guarded(undici.fetch);
