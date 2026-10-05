"""Offline fault injection against a minimal synthetic Phoenix contract fixture."""
import copy,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from adapter import ROOT
from phoenix_adapter import validate_spans

@pytest.fixture
def captured():
    from offline_fixtures import captured as load_captured
    return load_captured()

def test_offline_readback_contract_passes(captured):
    assert all(validate_spans(*captured).values())

def test_duplicate_tool_span_rejected(captured):
    row,spans=captured;spans.append(copy.deepcopy(next(s for s in spans if s['span_kind']=='TOOL')))
    with pytest.raises(AssertionError):validate_spans(row,spans)

def test_blocked_request_cannot_count_as_execution(captured):
    row,spans=captured
    blocked=next(s for s in spans if s['name']=='blocked_diagnostic_request');blocked['span_kind']='TOOL'
    with pytest.raises(AssertionError):validate_spans(row,spans)

def test_duplicate_root_tokens_rejected(captured):
    row,spans=captured;root=next(s for s in spans if not s['parent_id']);root['attributes']['llm.token_count.total']=row['run']['usage']['total_token_count']
    with pytest.raises(AssertionError):validate_spans(row,spans)

def test_changed_evidence_rejected(captured):
    row,spans=captured;tool=next(s for s in spans if s['span_kind']=='TOOL');tool['attributes']['evidence_id']='fabricated'
    with pytest.raises(AssertionError):validate_spans(row,spans)

def test_wrong_parent_rejected(captured):
    row,spans=captured;next(s for s in spans if s['span_kind']=='LLM')['parent_id']='wrong-parent'
    with pytest.raises(AssertionError):validate_spans(row,spans)

def test_changed_runtime_rejected(captured):
    row,spans=captured;next(s for s in spans if not s['parent_id'])['attributes']['runtime.id']='codex'
    with pytest.raises(AssertionError):validate_spans(row,spans)

def test_existing_raw_attempt_prevents_duplicate_inference(tmp_path,monkeypatch):
    import adapter
    monkeypatch.setattr(adapter,'HERE',tmp_path)
    (tmp_path/'.local'/'diag_007-b6-r1-rejected').mkdir(parents=True)
    with pytest.raises(RuntimeError,match='Saved attempt already exists'):
        adapter.run_once('diag_007',6,1,tmp_path/'output')

def test_invalid_final_result_cannot_publish_as_accepted(captured):
    from phoenix_adapter import publish_and_validate
    row,_=captured;row['run']['error']='No valid JSON Diagnosis';row['run']['final_diagnosis']=None
    with pytest.raises(AssertionError,match='invalid result'):
        publish_and_validate(None,row,None,None,None)

def test_offline_fixture_preserves_all_eleven_evaluations(captured):
    from agent_tool_budget_lab.phoenix_evaluators import evaluation_values
    from agent_tool_budget_lab.scenarios import load_scenarios
    row,_=captured
    assert evaluation_values(row,load_scenarios()) == {
        'diagnosis_correct':1,'evidence_completeness':1.0,'evidence_sufficient':1,
        'premature_stop':0,'tool_calls_used':2,'redundant_investigation':1,
        'irrelevant_calls':1,'post_sufficiency_calls':1,'identical_repeated_calls':0,
        'latency_seconds':1.0,'token_usage':40,
    }
