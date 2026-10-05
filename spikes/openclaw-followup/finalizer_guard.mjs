import {readFileSync,appendFileSync} from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(new URL('../openclaw-feasibility/node_modules/openclaw/package.json',import.meta.url));
const fixture=JSON.parse(readFileSync(process.env.FINALIZER_FIXTURE,'utf8'));let count=0;
const record=value=>appendFileSync(process.env.SPIKE_TRANSPORT,JSON.stringify(value)+'\n');
function guard(original){return async function(input,init){
 const url=new URL(typeof input==='string'||input instanceof URL?input:input.url);
 if(url.href!=='https://api.openai.com/v1/chat/completions')throw new Error('Finalizer endpoint denied');
 const raw=init?.body??await input.clone().text();const body=JSON.parse(typeof raw==='string'?raw:new TextDecoder().decode(raw));
 const ordinal=++count;
 const valid=ordinal===1&&body.model==='gpt-4.1-mini-2025-04-14'&&body.temperature===0&&!(body.tools?.length)&&!body.functions&&JSON.stringify(body.messages)===JSON.stringify([{role:'system',content:fixture.system},{role:'user',content:fixture.user}]);
 appendFileSync(process.env.SPIKE_REQUESTS,JSON.stringify({at:Date.now(),request_ordinal:ordinal,url:url.href,body,blocked:!valid||process.env.SPIKE_MODE!=='live'})+'\n');
 if(!valid||process.env.SPIKE_MODE!=='live')throw new Error('Finalizer outbound invariant rejected');
 try{const result=await original(input,init);record({at:Date.now(),request_ordinal:ordinal,status:result.status,provider_request_id:result.headers.get('x-request-id')});return result;}
 catch(error){record({at:Date.now(),request_ordinal:ordinal,error_name:error.name,error_code:error.code??error.cause?.code});throw error;}
};}
globalThis.fetch=guard(globalThis.fetch);const undici=require('undici/index.js');undici.fetch=guard(undici.fetch);
