"""Check pilot aggregation and persistence without inventing live results."""
import asyncio
import importlib.util
import json
from copy import deepcopy
from pathlib import Path
from agent_tool_budget_lab.config import Settings
from agent_tool_budget_lab.models import AgentRunResult, Diagnosis, ToolCall

spec = importlib.util.spec_from_file_location('pilot', Path(__file__).resolve().parents[1] / 'scripts/run_budget_pilot.py')
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


def test_metrics_count_repetition_excess_and_unobserved_citations(scenarios):
    result = AgentRunResult(scenario_id='diag_001', user_report='test', model_name='test',
        model_provider='openai', configured_tool_budget=2,
        tool_calls=[ToolCall(tool_index=i,tool_name='check_status', arguments={'component':'api'},
                            output={'evidence_id':'api_status'}, executed=True, elapsed_seconds=0) for i in (1,2)],
        evidence_ids_retrieved=['api_status'], number_of_tool_calls=2,
        final_diagnosis=Diagnosis(predicted_root_cause='api_configuration_issue', explanation='test',
                                 evidence_used=['api_status','invented']), elapsed_seconds=0)
    values = pilot.metrics(result, scenarios['diag_001'])
    assert values['correct'] is True
    assert values['evidence_completeness'] == 1.0
    assert values['premature_stop'] is False
    assert values['excess_calls'] == values['repeated_calls'] == values['redundant_calls'] == 1
    assert values['unobserved_citations'] == ['invented']
    assert values['required_evidence_count'] == values['required_evidence_retrieved_count'] == 1
    assert values['missing_required_evidence'] == []
    assert values['outside_required_supporting_calls'] == 0


def test_pilot_runs_all_cells_and_flags_identical_outcomes(scenarios, monkeypatch, tmp_path, capsys):
    async def fake_run(scenario_id, runtime, settings, budget):
        return AgentRunResult(scenario_id=scenario_id,user_report=runtime.user_report,model_name='test',
            model_provider='openai',configured_tool_budget=budget,tool_calls=[],evidence_ids_retrieved=[],
            number_of_tool_calls=0,final_diagnosis=Diagnosis(predicted_root_cause='unknown', explanation='test', evidence_used=[]),
            elapsed_seconds=0)
    monkeypatch.setattr(pilot,'run_agent',fake_run)
    output = tmp_path/'pilot.jsonl'
    asyncio.run(pilot.pilot(Settings('openai','test','unused'),output))
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(rows) == 32
    assert {(r['run']['scenario_id'],r['run']['configured_tool_budget']) for r in rows} == {
        (s,b) for s in scenarios for b in (2,4,6,8)}
    assert 'DESIGN ISSUE' in capsys.readouterr().out


def test_missing_tokens_are_not_reported_as_zero():
    rows = [{'run': {'usage': {}, 'number_of_tool_calls': 2, 'elapsed_seconds': 1, 'error': None},
             'metrics': {'correct': False, 'evidence_completeness': .5, 'premature_stop': True,
                         'redundant_calls': 1, 'repeated_calls': 0,
                         'outside_required_supporting_calls': 1, 'excess_calls': 0}}]
    assert pilot.aggregate(rows)['avg_tokens'] is None
    complete = deepcopy(rows)
    complete[0]['run']['usage'] = {'input_token_count': 20, 'output_token_count': 5}
    assert pilot.aggregate(complete)['avg_tokens'] == 25
    assert pilot.aggregate(rows + complete)['avg_tokens'] is None


def test_failed_run_still_has_incomplete_evidence(scenarios):
    result = AgentRunResult(scenario_id='diag_001',user_report='test',model_name='test',
        model_provider='openai',configured_tool_budget=2,tool_calls=[],evidence_ids_retrieved=[],
        number_of_tool_calls=0,final_diagnosis=None,elapsed_seconds=0,error='test failure')
    values = pilot.metrics(result,scenarios['diag_001'])
    assert values['premature_stop'] is True
    assert values['required_evidence_retrieved_count'] == 0
    assert values['missing_required_evidence'] == ['api_status']
