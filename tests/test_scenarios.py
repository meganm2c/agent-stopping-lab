from collections import Counter
import pytest
from pydantic import ValidationError
from agent_tool_budget_lab.scenarios import Scenario


def test_dataset_and_evidence(scenarios):
    assert len(scenarios) == 8
    assert Counter(s.difficulty for s in scenarios.values()) == {'easy': 3, 'medium': 3, 'hard': 2}
    for s in scenarios.values():
        ids = {o.evidence_id for c in s.runtime.components.values() for o in (c.status,c.logs,c.recent_change)}
        assert set(s.required_evidence) <= ids
        assert set(s.distractor_evidence) <= ids
        expected_counts = [1, 2, 2, 4, 2, 3, 4, 6]
        assert len(s.required_evidence) == expected_counts[int(s.scenario_id[-3:]) - 1]
        if s.difficulty == 'hard':
            assert s.distractor_evidence


@pytest.mark.parametrize('mutation', ['missing_evidence','overlap','missing_component','wrong_component','duplicate_id','empty_required','unknown_field'])
def test_rejects_bad_scenarios(scenarios, mutation):
    data = scenarios['diag_001'].model_dump()
    if mutation == 'missing_evidence': data['required_evidence'] = ['does_not_exist']
    elif mutation == 'overlap': data['distractor_evidence'] = data['required_evidence']
    elif mutation == 'missing_component': del data['runtime']['components']['cache']
    elif mutation == 'wrong_component': data['runtime']['components']['api']['status']['component'] = 'cache'
    elif mutation == 'duplicate_id': data['runtime']['components']['api']['logs']['evidence_id'] = 'api_status'
    elif mutation == 'empty_required': data['required_evidence'] = []
    elif mutation == 'unknown_field': data['runtime']['root_cause'] = 'leaked'
    with pytest.raises(ValidationError):
        Scenario.model_validate(data)


def test_aliases_are_scenario_specific(scenarios):
    assert scenarios['diag_006'].accepts_root_cause('api_dependency_issue')
    assert scenarios['diag_006'].accepts_root_cause('api_configuration_issue')
    assert not scenarios['diag_001'].accepts_root_cause('api_dependency_issue')
    assert not scenarios['diag_006'].accepts_root_cause('API configuration issue')
    data = scenarios['diag_006'].model_dump()
    data['acceptable_root_causes'] = ['api_configuration_issue']
    with pytest.raises(ValidationError):
        Scenario.model_validate(data)
