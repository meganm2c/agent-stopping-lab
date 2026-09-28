import asyncio
import json
from agent_framework import ChatResponse, Message
from agent_framework.openai import OpenAIChatCompletionClient
from agent_tool_budget_lab.agent import run_agent
from agent_tool_budget_lab.config import Settings
from agent_tool_budget_lab.stopping import ModelStopper, StopDecision, observed_payload
from agent_tool_budget_lab.adaptive_evaluators import adaptive_values
from test_agent import ScriptedClient


class DecisionClient(OpenAIChatCompletionClient):
    def __init__(self, decisions, malformed=False):
        super().__init__(model='offline-script', api_key='unused')
        self.decisions = iter(decisions)
        self.requests = []
        self.malformed = malformed

    async def _inner_get_response(self, *, messages, stream, options, **kwargs):
        self.requests.append((list(messages), dict(options)))
        assert not options.get('tools')
        result = StopDecision(decision=next(self.decisions), reason='Observed test evidence.')
        return ChatResponse(messages=Message('assistant', ['bad' if self.malformed else result.model_dump_json()]),
                            usage_details={'input_token_count': 7, 'output_token_count': 3})


def adaptive(scenario, plan, decisions, *, budget=8, malformed=False, batch=False):
    settings=Settings('openai','offline-script','unused')
    diagnostic=ScriptedClient(plan, batch=batch)
    decision=DecisionClient(decisions,malformed=malformed)
    stopper=ModelStopper(settings,client=decision)
    result=asyncio.run(run_agent(scenario.scenario_id,scenario.runtime,settings,budget,client=diagnostic,stopper=stopper))
    return result,diagnostic,decision


def test_stop_after_result_forces_final_answer_without_leaking_labels(scenarios):
    result, diagnostic, decision=adaptive(scenarios['diag_007'],
        [('check_status','api'),('read_logs','api')],['STOP'])
    assert result.error is None
    assert result.number_of_tool_calls==1 and result.stop_reason=='adaptive_stop'
    assert result.adaptive_stop_call_index==1
    assert diagnostic.requests[-1][1]['tool_choice']=='none'
    assert len(diagnostic.requests)==2
    assert result.usage['input_token_count']==20  # Stopper usage is separate.
    payload=json.loads(decision.requests[0][0][1].text)
    assert payload==observed_payload(scenarios['diag_007'].runtime.user_report,result.tool_calls)
    sent=str([m.to_dict() for messages,_ in decision.requests for m in messages])
    for forbidden in ('diag_007','required_evidence','difficulty','supporting_evidence','root_cause','distractor'):
        assert forbidden not in sent
    metrics=adaptive_values({'run':result.model_dump()},scenarios)
    assert metrics['false_early_stop']==1
    assert metrics['stopper_overhead_tokens']==10
    assert metrics['total_tokens']==40
    # Stopper reason is not appended to the diagnostic model's messages.
    assert 'Observed test evidence.' not in str(diagnostic.requests)


def test_continue_preserves_hard_ceiling_and_checks_last_result(scenarios):
    result,diagnostic,_=adaptive(scenarios['diag_007'],
        [('check_status','api'),('read_logs','api'),('read_logs','database')],
        ['CONTINUE','STOP'],budget=2)
    assert result.error is None and result.number_of_tool_calls==2
    assert result.stop_reason=='tool_budget' and result.adaptive_stop_call_index is None
    assert len(result.stopping_checks)==2
    assert result.stopping_checks[-1]['decision']=='STOP'
    assert result.stopping_checks[-1]['effective_stop'] is False
    assert diagnostic.requests[-1][1]['tool_choice']=='none'


def test_invalid_check_falls_back_to_continue_and_retains_usage(scenarios):
    result,_,_=adaptive(scenarios['diag_001'],[('check_status','api')],['STOP'],malformed=True)
    assert result.error is None and result.stop_reason=='agent_answered'
    assert result.stopping_checks[0]['error']=='ValidationError'
    assert result.stopping_checks[0]['decision']=='CONTINUE'
    assert result.stopping_checks[0]['usage']['input_token_count']==7


def test_unexpected_batch_cannot_execute_after_adaptive_stop(scenarios):
    result,_,_=adaptive(scenarios['diag_007'],
        [('check_status','api'),('read_logs','api'),('read_logs','database')],['STOP'],batch=True)
    assert result.error is None
    assert result.number_of_tool_calls==1
    assert len(result.stopping_checks)==1
    assert all(not c.executed for c in result.tool_calls[1:])


def test_no_policy_matches_fixed_and_tools_schema_unchanged(scenarios):
    from pathlib import Path
    from agent_tool_budget_lab.tools import ToolRecorder
    from agent_tool_budget_lab.environment import DiagnosticEnvironment
    s=scenarios['diag_001']
    tools=ToolRecorder(DiagnosticEnvironment(s.runtime),8).framework_tools()
    saved=Path('results/phase3-tool-json-schemas.json')
    if saved.exists():
        assert [t.to_json_schema_spec() for t in tools]==json.loads(saved.read_text())


def test_all_continue_preserves_diagnostic_requests(scenarios):
    from test_agent import run
    plan=[('check_status','api'),('read_logs','api')]
    scenario=scenarios['diag_007']
    fixed_client=ScriptedClient(plan)
    fixed=run(scenario,8,fixed_client)
    adaptive_result,adaptive_client,_=adaptive(scenario,plan,['CONTINUE','CONTINUE'])
    assert fixed.error is None and adaptive_result.error is None
    assert fixed.stop_reason==adaptive_result.stop_reason=='agent_answered'
    assert fixed.final_diagnosis==adaptive_result.final_diagnosis
    assert fixed.usage==adaptive_result.usage
    assert fixed.prompt_sha256==adaptive_result.prompt_sha256
    assert fixed.runtime_sha256==adaptive_result.runtime_sha256
    assert fixed.model_settings==adaptive_result.model_settings
    for (fm,fo),(am,ao) in zip(fixed_client.requests,adaptive_client.requests):
        def normalize(value):
            if isinstance(value,dict):
                return {k:normalize(v) for k,v in value.items() if k!='id'}
            if isinstance(value,list):return [normalize(v) for v in value]
            return value
        # Framework-generated internal content IDs differ across fresh runs.
        assert normalize([m.to_dict() for m in fm])==normalize([m.to_dict() for m in am])
        for key in ('temperature','response_format','tool_choice','allow_multiple_tool_calls'):
            assert fo.get(key)==ao.get(key)
