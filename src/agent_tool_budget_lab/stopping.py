"""One runtime-only stopping policy; no scenario or evaluator imports."""
import asyncio
import json
from time import perf_counter
from typing import Literal
from agent_framework import ChatMiddleware, FunctionMiddleware, Message
from opentelemetry import trace
from .config import create_client
from .models import Record, ToolCall

STOPPER_PROMPT = """You decide whether a diagnostic agent should continue investigating a software incident.
Use only the user report and observed tool results supplied below.
Return STOP only when the observed evidence supports a coherent diagnosis and another
call is unlikely to materially improve confidence or resolve an important ambiguity.
Return CONTINUE when important uncertainty remains. Do not assume unobserved facts.
Return a decision (STOP or CONTINUE) and a short reason grounded in observed evidence.
"""


class StopDecision(Record):
    decision: Literal['STOP', 'CONTINUE']
    reason: str


def observed_payload(user_report: str, calls: list[ToolCall]) -> dict:
    """Explicit allowlist: no world object or unobserved components cross this boundary."""
    observed = [c for c in calls if c.executed]
    return {'user_report': user_report,
            'tool_calls': [{'tool_name': c.tool_name, 'arguments': dict(c.arguments),
                            'output': dict(c.output)} for c in observed],
            'evidence_ids': list(dict.fromkeys(c.output['evidence_id'] for c in observed
                                             if 'evidence_id' in c.output))}


class ModelStopper:
    def __init__(self, settings, *, client=None):
        self.settings = settings
        self.client = client if client is not None else create_client(settings)
        self.checks: list[dict] = []
        self.stop_call_index: int | None = None

    async def check(self, user_report, calls, *, scenario_id, ceiling):
        payload = observed_payload(user_report, calls)
        index = sum(c.executed for c in calls)
        started = perf_counter(); usage = {}; error = None
        with trace.get_tracer('agent-tool-budget-lab').start_as_current_span('stopping_check', attributes={
            'openinference.span.kind': 'CHAIN', 'scenario_id': scenario_id,
            'tool_index': index, 'elapsed_calls': index, 'model_name': self.settings.model_name,
            'input.value': json.dumps(payload), 'input.mime_type': 'application/json',
        }) as span:
            try:
                response = await asyncio.wait_for(self.client.get_response([
                    Message('system', [STOPPER_PROMPT]), Message('user', [json.dumps(payload)])],
                    options={'response_format': StopDecision, 'temperature': self.settings.temperature}),
                    timeout=30)
                usage = dict(response.usage_details or {})
                decision = StopDecision.model_validate_json(response.text)
            except Exception as exc:
                error = type(exc).__name__
                decision = StopDecision(decision='CONTINUE', reason='Stopping check failed; continue under the hard ceiling.')
            elapsed = perf_counter() - started
            effective = decision.decision == 'STOP' and index < ceiling
            if effective:
                self.stop_call_index = index
            row = dict(tool_index=index, **decision.model_dump(), effective_stop=effective,
                       elapsed_seconds=elapsed, usage=usage, error=error,
                       model_name=self.settings.model_name)
            self.checks.append(row)
            span.set_attributes({'decision': decision.decision, 'reason': decision.reason,
                                 'effective_stop': effective, 'latency_seconds': elapsed,
                                 'output.value': decision.model_dump_json(),
                                 'output.mime_type': 'application/json'})
            if error:
                span.set_attribute('check_error', error)
            if 'input_token_count' in usage and 'output_token_count' in usage:
                # Metadata only: native child LLM spans own token counters, avoiding double counting.
                span.set_attribute('stopper_tokens', usage['input_token_count'] + usage['output_token_count'])
        return effective


class CheckAfterTool(FunctionMiddleware):
    def __init__(self, stopper, recorder, report, scenario_id):
        self.stopper, self.recorder = stopper, recorder
        self.report, self.scenario_id = report, scenario_id

    async def process(self, context, call_next):
        before = len(self.recorder.calls)
        await call_next()
        if len(self.recorder.calls) > before and self.recorder.calls[-1].executed:
            stopped = await self.stopper.check(self.report, self.recorder.calls,
                scenario_id=self.scenario_id, ceiling=self.recorder.budget)
            if stopped:
                self.recorder.adaptive_stopped = True


class FinalizeAfterStop(ChatMiddleware):
    def __init__(self, stopper):
        self.stopper = stopper

    async def process(self, context, call_next):
        if self.stopper.stop_call_index is not None:
            # Retain tools/schema/messages; use the same final-answer control as the native cap.
            context.options = dict(context.options or {}, tool_choice='none')
        await call_next()
