"""Analysis invariants against a synthetic finalized row; no inference."""
import copy,json
from adapter import ROOT
from analyze_validated_study import extended
from analyze import trajectory,best_pairs

def row():
 from offline_fixtures import finalized_row
 return finalized_row()

def test_order_variation_is_distinct_from_evidence_set_variation():
 a=row();b=copy.deepcopy(a);b['run']['tool_calls'][0:2]=reversed(b['run']['tool_calls'][0:2])
 g=extended([a,b]);assert g['diagnoses_stable'] and g['trajectory_variants']==2 and g['evidence_set_variants']==1
 assert len(best_pairs([a,b]))==1

def test_blocked_calls_do_not_change_executed_trajectory():
 a=row();b=copy.deepcopy(a);blocked=copy.deepcopy(b['run']['tool_calls'][0]);blocked['executed']=False;b['run']['tool_calls'].append(blocked)
 assert trajectory(a)==trajectory(b)

def test_pairs_require_same_condition():
 a=row();b=copy.deepcopy(a);b['run']['tool_calls'].reverse();b['run']['configured_tool_budget']=8
 assert not best_pairs([a,b])

def test_same_label_different_sufficiency_detected_separately():
 a=row();b=copy.deepcopy(a);b['metrics']['evidence_sufficient']=not a['metrics']['evidence_sufficient']
 g=extended([a,b]);assert g['same_diagnosis_different_sufficiency'] and g['evidence_sufficiency_varies']

def test_numeric_aggregation_keeps_finalizer_cost_and_blocked_calls_separate():
 a=row();b=copy.deepcopy(a)
 b['run']['usage']['total_token_count']=70
 b['cost_split']['finalization_tokens']=30
 b['cost_split']['total_tokens']=70
 b['run']['elapsed_seconds']=4
 g=extended([a,b])
 assert g['n']==2 and g['accuracy']==1 and g['executed_calls']==2
 assert g['blocked_calls']==2 and g['runs_with_blocked_calls']==2
 assert g['tokens']==60 and g['tokens_range']==[50,70]
 assert g['latency_seconds']==3 and g['latency_range']==[2,4]
 assert g['cost_split_mean']['diagnostic_loop_tokens']==40
 assert g['cost_split_mean']['finalization_tokens']==20
 assert g['cost_split_mean']['total_tokens']==60
