"""Phoenix setup and a run boundary; model/tool spans come from Microsoft."""
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter
from .agent import run_agent
from .evaluation import metrics


class NativeSpanPresentation(SpanExporter):
    """Add Phoenix display conventions to existing spans; create no new spans.

    Copy attributes at export time, preserving native span IDs, parentage, and timing.
    Native gen_ai attributes are retained verbatim for inspection.
    """
    def __init__(self, exporter):
        self.exporter = exporter

    def export(self, spans):
        copies = []
        for span in spans:
            copies.append(ReadableSpan(name=span.name, context=span.context, parent=span.parent,
                resource=span.resource, attributes=self.display_attributes(span.attributes or {}),
                events=span.events, links=span.links, kind=span.kind, status=span.status,
                start_time=span.start_time, end_time=span.end_time,
                instrumentation_scope=span.instrumentation_scope))
        return self.exporter.export(copies)

    def shutdown(self):
        self.exporter.shutdown()

    def force_flush(self, timeout_millis=30000):
        return self.exporter.force_flush(timeout_millis)

    @staticmethod
    def display_attributes(native):
        attrs = dict(native)
        operation = attrs.get('gen_ai.operation.name')
        kind = {'chat': 'LLM', 'execute_tool': 'TOOL', 'invoke_agent': 'AGENT'}.get(operation)
        if not kind:
            return attrs
        attrs['openinference.span.kind'] = kind
        for source, target in [('gen_ai.input.messages', 'input.value'),
                               ('gen_ai.output.messages', 'output.value')]:
            if source in attrs:
                attrs[target] = attrs[source]
                attrs[target.replace('.value', '.mime_type')] = 'application/json'
        if kind == 'LLM':
            attrs['llm.model_name'] = attrs.get('gen_ai.request.model', 'unknown')
            for source, target in [('gen_ai.usage.input_tokens', 'llm.token_count.prompt'),
                                   ('gen_ai.usage.output_tokens', 'llm.token_count.completion')]:
                if source in attrs:
                    attrs[target] = attrs[source]
            for direction in ('input', 'output'):
                raw = attrs.get(f'gen_ai.{direction}.messages', '[]')
                try:
                    messages = json.loads(raw)
                except (ValueError, TypeError):
                    continue
                for i, message in enumerate(messages):
                    prefix = f'llm.{direction}_messages.{i}.message'
                    attrs[prefix + '.role'] = message.get('role', 'unknown')
                    parts = message.get('parts', [])
                    attrs[prefix + '.content'] = '\n'.join(
                        p.get('content', '') if p.get('type') == 'text' else json.dumps(p)
                        for p in parts)
        return attrs


def configure_phoenix():
    from phoenix.otel import TracerProvider
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from agent_framework.observability import enable_instrumentation
    load_dotenv(Path(__file__).resolve().parents[2] / '.env')
    base = os.getenv('PHOENIX_COLLECTOR_ENDPOINT', 'http://localhost:6006').rstrip('/')
    # register() in phoenix-otel 0.17.1 reads removed exporter._headers even with
    # verbose=False on OTel 1.45. Use its public provider API and standard exporter.
    provider = TracerProvider(endpoint=base + '/v1/traces', protocol='http/protobuf',
        resource=Resource.create({'openinference.project.name':
            os.getenv('PHOENIX_PROJECT', 'agent-tool-budget-lab')}), verbose=False)
    key = os.getenv('PHOENIX_API_KEY')
    headers = {'authorization': f'Bearer {key}'} if key else {}
    provider.add_span_processor(BatchSpanProcessor(
        NativeSpanPresentation(OTLPSpanExporter(endpoint=base + '/v1/traces', headers=headers))))
    trace.set_tracer_provider(provider)
    # Synthetic reports/results are safe to record; credentials are never model inputs.
    enable_instrumentation(enable_sensitive_data=True)
    return provider


def phoenix_client():
    from phoenix.client import Client
    return Client(base_url=os.getenv('PHOENIX_COLLECTOR_ENDPOINT', 'http://localhost:6006'),
                  api_key=os.getenv('PHOENIX_API_KEY') or None)


async def traced_run(scenario, settings, budget, *, adaptive=False):
    tracer = trace.get_tracer('agent-tool-budget-lab')
    with tracer.start_as_current_span('diagnostic_run', attributes={
        'openinference.span.kind': 'CHAIN', 'scenario_id': scenario.scenario_id,
        'tool_budget': budget, 'model_name': settings.model_name,
        'input.value': scenario.runtime.user_report,
    }) as span:
        stopper = None
        if adaptive:
            from .stopping import ModelStopper
            stopper = ModelStopper(settings)
        result = await run_agent(scenario.scenario_id, scenario.runtime, settings, budget, stopper=stopper)
        span.set_attribute('strategy', 'adaptive-stopping' if adaptive else f'fixed-budget-{budget}')
        scores = metrics(result, scenario)  # Ground truth is accessed only after the agent finishes.
        span.set_attributes({'difficulty': scenario.difficulty,
                             'stop_reason': result.stop_reason,
                             'diagnosis_correct': scores['diagnosis_correct'],
                             'evidence_completeness': scores['evidence_completeness'],
                             'evidence_sufficient': scores['evidence_sufficient']})
        if result.final_diagnosis:
            span.set_attribute('predicted_root_cause', result.final_diagnosis.predicted_root_cause)
            span.set_attribute('output.value', result.final_diagnosis.model_dump_json())
            span.set_attribute('output.mime_type', 'application/json')
            with tracer.start_as_current_span('final_diagnosis', attributes={
                'openinference.span.kind': 'CHAIN',
                'output.value': result.final_diagnosis.model_dump_json(),
                'output.mime_type': 'application/json', 'stop_reason': result.stop_reason,
            }):
                pass
        if result.error:
            span.set_status(Status(StatusCode.ERROR, result.error))
        context = span.get_span_context()
        return {'run': result.model_dump(), 'metrics': scores, 'difficulty': scenario.difficulty,
                'trace_id': f'{context.trace_id:032x}', 'span_id': f'{context.span_id:016x}'}
