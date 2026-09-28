import json
import pytest
pytest.importorskip('phoenix.otel')
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from agent_tool_budget_lab.phoenix_support import NativeSpanPresentation


def test_native_export_preserves_identity_and_adds_display_attributes():
    sink = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(NativeSpanPresentation(sink)))
    with provider.get_tracer('test').start_as_current_span('chat test') as span:
        original = span.get_span_context()
        span.set_attributes({'gen_ai.operation.name':'chat','gen_ai.request.model':'test',
            'gen_ai.usage.input_tokens':12, 'gen_ai.usage.output_tokens':3,
            'gen_ai.input.messages':json.dumps([{'role':'user','parts':[{'type':'text','content':'symptom'}]}])})
    exported = sink.get_finished_spans()[0]
    assert exported.context == original
    assert exported.attributes['openinference.span.kind'] == 'LLM'
    assert exported.attributes['llm.input_messages.0.message.content'] == 'symptom'
    assert exported.attributes['llm.token_count.prompt'] == 12
    assert exported.attributes['gen_ai.usage.input_tokens'] == 12
    assert len(sink.get_finished_spans()) == 1
    provider.shutdown()


def test_alias_correctness_is_independent_of_evidence(scenarios):
    from agent_tool_budget_lab.phoenix_evaluators import evaluation_values
    from agent_tool_budget_lab.models import AgentRunResult, Diagnosis
    r = AgentRunResult(scenario_id='diag_006',user_report='test',model_name='test',model_provider='openai',
        configured_tool_budget=2,tool_calls=[],evidence_ids_retrieved=[],number_of_tool_calls=0,
        final_diagnosis=Diagnosis(predicted_root_cause='api_configuration_issue',explanation='test',evidence_used=[]),elapsed_seconds=1)
    values = evaluation_values({'run':r.model_dump()},scenarios)
    assert values['diagnosis_correct'] == 1
    assert values['evidence_completeness'] == 0
    assert values['evidence_sufficient'] == 0
    assert values['premature_stop'] == 1
    assert values['token_usage'] is None
