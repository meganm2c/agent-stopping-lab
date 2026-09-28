"""Deterministic integration tests: actual framework loop, scripted model transport."""
import asyncio
from agent_framework import ChatResponse, Message, Content
from agent_framework.openai import OpenAIChatCompletionClient
from agent_tool_budget_lab.agent import run_agent
from agent_tool_budget_lab.config import Settings
from agent_tool_budget_lab.models import Diagnosis


class ScriptedClient(OpenAIChatCompletionClient):
    def __init__(self, plan, cause='unknown', batch=False, malformed=False):
        super().__init__(model='offline-script', api_key='unused-test-key')
        self.plan = list(plan)
        self.cause = cause
        self.batch = batch
        self.malformed = malformed
        self.requests = []

    async def _inner_get_response(self, *, messages, stream, options, **kwargs):
        self.requests.append((list(messages), dict(options)))
        assert not stream
        if self.plan and options.get('tools') and options.get('tool_choice') != 'none':
            chosen = list(self.plan) if self.batch else [self.plan[0]]
            del self.plan[:len(chosen)]
            return ChatResponse(messages=Message('assistant', [
                Content('function_call', name=name, call_id=f'{len(self.requests)}-{i}', arguments={'component': component})
                for i, (name, component) in enumerate(chosen)
            ]), usage_details={'input_token_count': 10, 'output_token_count': 5})
        diagnosis = Diagnosis(predicted_root_cause=self.cause, explanation='Scripted test response; not a measured model diagnosis.', evidence_used=[])
        return ChatResponse(messages=Message('assistant', ['not JSON' if self.malformed else diagnosis.model_dump_json()]),
                            usage_details={'input_token_count': 10, 'output_token_count': 5})


def run(scenario, budget, client):
    return asyncio.run(run_agent(scenario.scenario_id, scenario.runtime, Settings('openai','offline-script','unused'), budget, client=client))


def test_easy_framework_tool_execution(scenarios):
    client = ScriptedClient([('check_status','api')], 'api_configuration_issue')
    result = run(scenarios['diag_001'], 2, client)
    assert result.error is None
    assert result.stop_reason == 'agent_answered'
    assert result.number_of_tool_calls == 1
    assert result.final_diagnosis.predicted_root_cause == 'api_configuration_issue'
    assert result.evidence_ids_retrieved == ['api_status']
    assert result.usage['input_token_count'] == 20
    assert client.requests[0][1]['response_format'] is Diagnosis
    assert client.requests[0][1]['allow_multiple_tool_calls'] is False
    assert client.requests[0][1]['temperature'] == 0.0
    # Serialized model messages never receive evaluator field names.
    sent = str([m.to_dict() for messages, _ in client.requests for m in messages])
    for forbidden in ('required_evidence', 'distractor_evidence', 'difficulty', 'diag_001'):
        assert forbidden not in sent


def test_native_budget_changes_hard_trajectory(scenarios):
    plan = [('check_status','api'), ('read_logs','api'), ('check_status','database'), ('read_logs','database'), ('check_recent_change','api')]
    low_client, high_client = ScriptedClient(plan), ScriptedClient(plan)
    low = run(scenarios['diag_007'], 2, low_client)
    high = run(scenarios['diag_007'], 6, high_client)
    assert low.error is None and high.error is None
    assert low.number_of_tool_calls == 2
    assert high.number_of_tool_calls == 5
    assert low.stop_reason == 'tool_budget'
    assert high.stop_reason == 'agent_answered'
    assert low.prompt_sha256 == high.prompt_sha256
    assert low.runtime_sha256 == high.runtime_sha256
    assert low.model_settings == high.model_settings
    assert len(low_client.requests) == 3  # Includes final response without tools.
    assert set(scenarios['diag_007'].required_evidence) <= set(high.evidence_ids_retrieved)
    assert not set(scenarios['diag_007'].required_evidence) <= set(low.evidence_ids_retrieved)


def test_oversized_batch_does_not_execute_beyond_budget(scenarios):
    client = ScriptedClient([('check_status', c) for c in ('api','cache','database','frontend')], batch=True)
    result = run(scenarios['diag_001'], 2, client)
    assert result.error is None
    assert result.number_of_tool_calls == 2
    assert len(result.tool_calls) == 4
    assert sum(not c.executed for c in result.tool_calls) == 2


def test_invalid_diagnosis_preserves_tool_metadata(scenarios):
    result = run(scenarios['diag_001'], 2, ScriptedClient([('check_status','api')], malformed=True))
    assert result.error.startswith('ValidationError')
    assert result.final_diagnosis is None
    assert result.number_of_tool_calls == 1
