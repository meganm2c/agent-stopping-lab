// Inspect the actual HTTP body without changing its model, tools, or prompt.
import {appendFileSync} from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(new URL('../openclaw-feasibility/node_modules/openclaw/package.json',import.meta.url));
const expected='gpt-4.1-mini-2025-04-14';
const names=['check_recent_change','check_status','read_logs'];
let attempts=0;
let ordinal=0;
function transport(value){if(process.env.SPIKE_TRANSPORT)appendFileSync(process.env.SPIKE_TRANSPORT,JSON.stringify(value)+'\n');}
function guarded(original){return async function(input,init){
  const url=new URL(typeof input==='string'||input instanceof URL?input:input.url);
  if(/\/(responses|chat\/completions)$/.test(url.pathname)){
    const raw=init?.body??await input.clone().text();
    const body=JSON.parse(typeof raw==='string'?raw:new TextDecoder().decode(raw));
    const visible=(body.tools??[]).map(t=>t.name??t.function?.name).sort();
    const valid=url.origin==='https://api.openai.com'&&body.model===expected&&body.temperature===0&&body.parallel_tool_calls===false&&JSON.stringify(visible)===JSON.stringify(names)&&++attempts<=32;
    const blocked=process.env.SPIKE_MODE!=='live'||!valid;
    const requestOrdinal=++ordinal;
    appendFileSync(process.env.SPIKE_REQUESTS,JSON.stringify({url:url.href,body,blocked,at:Date.now(),request_ordinal:requestOrdinal})+'\n');
    if(blocked) return new Response(JSON.stringify({error:{message:'SPIKE_GUARD: inference blocked',type:'invalid_request_error'}}),{status:400,headers:{'content-type':'application/json'}});
    if(process.env.SPIKE_INJECT_FAILURE==='1') {
      transport({request_ordinal:requestOrdinal,at:Date.now(),status:503,injected:true,forwarded_to_provider:false,unexpected_extra_attempt:requestOrdinal!==1});
      return new Response(JSON.stringify({error:{message:'Injected transient provider failure',type:'server_error'}}),{status:503,headers:{'content-type':'application/json'}});
    }
    try {
      const response=await original(input,init);
      transport({request_ordinal:requestOrdinal,at:Date.now(),status:response.status,provider_request_id:response.headers.get('x-request-id')});
      return response;
    } catch(error) {
      transport({request_ordinal:requestOrdinal,at:Date.now(),error_name:error.name,error_code:error.code??error.cause?.code??null});
      throw error;
    }
  } else {
    throw new Error('Spike network denied: '+url.origin+url.pathname);
  }
  return original(input,init);
};}
globalThis.fetch=guarded(globalThis.fetch);
const undici=require('undici/index.js');
undici.fetch=guarded(undici.fetch);
