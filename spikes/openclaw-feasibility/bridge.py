"""Serial JSON-lines boundary around the unchanged diagnostic environment."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from agent_tool_budget_lab.agent import SYSTEM_PROMPT
from agent_tool_budget_lab.scenarios import load_scenarios
from agent_tool_budget_lab.environment import DiagnosticEnvironment
from agent_tool_budget_lab.tools import ToolRecorder
from agent_tool_budget_lab.models import Diagnosis

def main():
    scenario = load_scenarios()['diag_001']
    recorder = ToolRecorder(DiagnosticEnvironment(scenario.runtime), 2)
    if '--fixture' in sys.argv:
        print(json.dumps({'system': SYSTEM_PROMPT, 'report': scenario.runtime.user_report,
                          'diagnosis_schema': Diagnosis.model_json_schema(),
                          'tools': [t.to_json_schema_spec() for t in recorder.framework_tools()]}))
        return
    for line in sys.stdin:
        request = json.loads(line)
        output = recorder.invoke(request['name'], request['component'])
        print(json.dumps({'output': output, 'call': recorder.calls[-1].model_dump()}), flush=True)

if __name__ == '__main__':
    main()
