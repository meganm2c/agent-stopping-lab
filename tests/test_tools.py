import pytest
from agent_tool_budget_lab.environment import DiagnosticEnvironment
from agent_tool_budget_lab.tools import DiagnosticTools, ToolRecorder

@pytest.mark.parametrize('method,field', [('check_status','status'), ('read_logs','logs'), ('check_recent_change','recent_change')])
def test_tool_outputs_and_validation(scenarios, method, field):
    for scenario in scenarios.values():
        tools = DiagnosticTools(DiagnosticEnvironment.from_scenario(scenario))
        for component, state in scenario.runtime.components.items():
            output = getattr(tools, method)(component)
            assert output == getattr(state, field)
            assert output == getattr(tools, method)(component)
            assert output.evidence_id
        with pytest.raises(ValueError):
            getattr(tools, method)('unknown')


def test_budget_guard_and_invalid_attempt_count(scenarios):
    recorder = ToolRecorder(DiagnosticEnvironment.from_scenario(scenarios['diag_001']), 2)
    assert recorder.invoke('check_status', 'invalid')['error'] == 'invalid_component'
    assert recorder.invoke('check_status', 'api')['evidence_id'] == 'api_status'
    assert recorder.invoke('read_logs', 'api')['error'] == 'tool_budget_exhausted'
    assert [c.executed for c in recorder.calls] == [True, True, False]
    assert [c.tool_index for c in recorder.calls] == [1, 2, 3]
    with pytest.raises(ValueError):
        ToolRecorder(recorder.tools.environment, 0)
