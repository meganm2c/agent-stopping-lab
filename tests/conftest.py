import pytest
from agent_tool_budget_lab.scenarios import load_scenarios

@pytest.fixture
def scenarios():
    return load_scenarios()
