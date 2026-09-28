import pytest
from agent_tool_budget_lab.environment import DiagnosticEnvironment
from agent_tool_budget_lab.models import COMPONENTS


def test_component_validation(scenarios):
    env = DiagnosticEnvironment.from_scenario(scenarios['diag_001'])
    for name in COMPONENTS:
        assert env.component(name).status.component == name
    for name in ('redis', '', 'API', '../cache'):
        with pytest.raises(ValueError, match='Unknown component'):
            env.component(name)


def test_isolation(scenarios):
    source = scenarios['diag_001']
    first = DiagnosticEnvironment.from_scenario(source)
    second = DiagnosticEnvironment.from_scenario(source)
    source.runtime.components.clear()
    assert first.component('api') == second.component('api')
    first._state.components.clear()
    assert second.component('api').status.status == 'unavailable'
    assert scenarios['diag_002'].runtime.components['api'].status.status == 'healthy'


def test_runtime_contains_no_evaluation_labels(scenarios):
    for scenario in scenarios.values():
        env = DiagnosticEnvironment.from_scenario(scenario)
        data = env._state.model_dump_json()
        for field in ('root_cause', 'acceptable_root_causes', 'required_evidence', 'difficulty', 'distractor_evidence', 'optional_supporting_evidence'):
            assert field not in data
            assert not hasattr(env, field)
        assert scenario.root_cause not in data
