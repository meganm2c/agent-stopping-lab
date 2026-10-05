import {readFileSync,writeFileSync} from 'node:fs';
export default {id:'diagnostic-finalizer',name:'Diagnostic finalization adapter',register(api){
 api.registerCli(({program})=>{
  program.command('diagnostic-finalize').action(async()=>{
   const fixture=JSON.parse(readFileSync(process.env.FINALIZER_FIXTURE,'utf8'));
   const params={systemPrompt:fixture.system,messages:[{role:'user',content:fixture.user}],model:'openai/gpt-4.1-mini-2025-04-14',temperature:0,execution:{mode:'isolated-agent-runtime',timeoutMs:60000}};
   if(process.env.FINALIZER_NATIVE_PROBE==='1')params.responseFormat=fixture.schema;
   const start=Date.now();
   try {
    const result=await api.runtime.llm.complete(params);
    writeFileSync(process.env.FINALIZER_RESULT,JSON.stringify({ok:true,start_ms:start,end_ms:Date.now(),result},null,2));
   } catch(error) {
    writeFileSync(process.env.FINALIZER_RESULT,JSON.stringify({ok:false,start_ms:start,end_ms:Date.now(),error_code:error.code,error_message:error.message},null,2));
    process.exitCode=1;
   }
  });
 },{descriptors:[{name:'diagnostic-finalize',description:'Run one isolated diagnostic finalizer',hasSubcommands:false}]});
}};
