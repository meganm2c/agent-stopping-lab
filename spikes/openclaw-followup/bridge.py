"""Parameterized serial bridge; no evaluation labels cross the runtime boundary."""
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from agent_tool_budget_lab.agent import SYSTEM_PROMPT
from agent_tool_budget_lab.scenarios import load_scenarios
from agent_tool_budget_lab.environment import DiagnosticEnvironment
from agent_tool_budget_lab.tools import ToolRecorder
from agent_tool_budget_lab.models import Diagnosis

def main():
    sid=os.environ['FOLLOWUP_SCENARIO'];budget=int(os.environ['FOLLOWUP_BUDGET'])
    assert (sid,budget)==('diag_001',2) or sid in ('diag_007','diag_008') and budget in (6,8)
    runtime=load_scenarios()[sid].runtime
    recorder=ToolRecorder(DiagnosticEnvironment(runtime),budget)
    if '--fixture' in sys.argv:
        print(json.dumps({'system':SYSTEM_PROMPT,'report':runtime.user_report,
          'diagnosis_schema':Diagnosis.model_json_schema(),
          'tools':[t.to_json_schema_spec() for t in recorder.framework_tools()]}));return
    for line in sys.stdin:
        request=json.loads(line)
        output=recorder.invoke(request['name'],request['component'])
        print(json.dumps({'output':output,'call':recorder.calls[-1].model_dump()}),flush=True)
if __name__=='__main__':main()
