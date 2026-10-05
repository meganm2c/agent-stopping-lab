import {readFileSync,appendFileSync} from 'node:fs';
import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';

export default {
  id:'diagnostic-spike', name:'Diagnostic feasibility spike',
  register(api) {
    const fixture=JSON.parse(readFileSync(process.env.SPIKE_FIXTURE,'utf8'));
    const record=(type,data)=>appendFileSync(process.env.SPIKE_EVENTS,JSON.stringify({type,at:Date.now(),data})+'\n');
    let child, lines, serial=Promise.resolve();
    const invoke=async(name,component)=>{
      if(process.env.SPIKE_MODE!=='live') throw new Error('Preflight cannot execute tools');
      if(!child){
        child=spawn(process.env.SPIKE_PYTHON,[process.env.SPIKE_BRIDGE],{stdio:['pipe','pipe','inherit']});
        lines=createInterface({input:child.stdout})[Symbol.asyncIterator]();
        process.once('exit',()=>child.kill());
      }
      child.stdin.write(JSON.stringify({name,component})+'\n');
      const line=await lines.next();
      if(line.done) throw new Error('Python bridge exited');
      const result=JSON.parse(line.value);record('diagnostic_call',result);
      return {content:[{type:'text',text:JSON.stringify(result.output)}],details:result};
    };
    for(const spec of fixture.tools){
      const f=spec.function??spec;
      api.registerTool({name:f.name,label:f.name,description:f.description,parameters:f.parameters,
        execute:(_id,args)=>{
          const result=serial.then(()=>invoke(f.name,args.component));
          serial=result.catch(()=>{});return result;
        }});
    }
    api.on('before_prompt_build',()=>({systemPrompt:fixture.system,toolsAllow:fixture.tools.map(t=>(t.function??t).name)}));
    for(const type of ['before_agent_run','llm_input','llm_output','model_call_started','model_call_ended','agent_end']){
      api.on(type,(event,ctx)=>{record(type,{event,context:ctx});if(type==='agent_end') child?.stdin.end();});
    }
    api.on('before_tool_call',(event)=>{record('before_tool_call',event);});
    api.on('after_tool_call',(event)=>{record('after_tool_call',event);});
  }
};
