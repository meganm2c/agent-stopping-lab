"""One fresh Microsoft Agent Framework agent per diagnostic run."""
import asyncio
import hashlib
import json
from time import perf_counter
from agent_framework import Agent, ChatMiddleware
from .config import Settings, create_client
from .environment import DiagnosticEnvironment
from .models import AgentRunResult, Diagnosis, RuntimeState
from .tools import ToolRecorder

# Global vocabulary shared across every task, never selected from the scenario label.
SYSTEM_PROMPT = """You diagnose a small software system with frontend, api, database, and cache.
Use diagnostic tools to gather enough evidence to identify the most likely root cause.
Do not assume facts that have not been observed through tool results.
Avoid unnecessary repeated tool calls. Stop when you have enough evidence.
Return predicted_root_cause, a short explanation, and evidence_used (observed evidence IDs).
Use this shared root-cause vocabulary: frontend_deployment_regression,
api_configuration_issue, database_saturation, cache_configuration_regression,
database_connection_regression, api_dependency_issue. Use unknown if evidence is insufficient.
"""


class ModelRoundRecorder(ChatMiddleware):
    """Observe stop controls and usage without changing any model request."""
    def __init__(self):
        self.rounds: list[dict] = []

    async def process(self, context, call_next):
        options = context.options or {}
        row = {"tool_choice": str(options.get("tool_choice", "auto")),
               "tools_present": bool(options.get("tools"))}
        self.rounds.append(row)
        await call_next()
        response = context.result
        row.update(finish_reason=str(response.finish_reason),
                   usage=dict(response.usage_details or {}),
                   function_calls=sum(c.type == "function_call" for m in response.messages for c in m.contents))


async def run_agent(scenario_id: str, runtime: RuntimeState, settings: Settings,
                    max_tool_calls: int, *, client=None, stopper=None) -> AgentRunResult:
    """Evaluation labels cannot cross this interface. Client injection enables offline tests."""
    recorder = ToolRecorder(DiagnosticEnvironment(runtime), max_tool_calls)
    client = client if client is not None else create_client(settings)
    client.function_invocation_configuration.update({
        "max_function_calls": max_tool_calls,
        "max_iterations": 20,  # Fixed across 2/4/6/8 experiments, including final answer.
        "allow_concurrent_invocation": False,
    })
    rounds = ModelRoundRecorder()
    middleware = [rounds]
    if stopper is not None:
        from .stopping import CheckAfterTool, FinalizeAfterStop
        middleware = [FinalizeAfterStop(stopper), rounds,
                      CheckAfterTool(stopper, recorder, runtime.user_report, scenario_id)]
    agent = Agent(client=client, name="DiagnosticAgent", instructions=SYSTEM_PROMPT,
                  middleware=middleware,
                  tools=recorder.framework_tools())
    started = perf_counter()
    diagnosis, error, usage = None, None, {}
    try:
        response = await asyncio.wait_for(agent.run(runtime.user_report, options={
            "response_format": Diagnosis,
            "allow_multiple_tool_calls": False,
            "temperature": settings.temperature,
        }), timeout=180)
        usage = dict(response.usage_details or {})
        diagnosis = Diagnosis.model_validate_json(response.text)
    except Exception as exc:
        # Preserve partial trajectories; avoid provider error bodies that may include credentials.
        error = f"{type(exc).__name__}: run failed or returned an invalid diagnosis"
    evidence = list(dict.fromkeys(c.output["evidence_id"] for c in recorder.calls if "evidence_id" in c.output))
    executed = sum(c.executed for c in recorder.calls)
    if error:
        stop_reason = "error_or_timeout"
    elif stopper is not None and stopper.stop_call_index is not None:
        stop_reason = "adaptive_stop"
    elif rounds.rounds and rounds.rounds[-1]["tool_choice"] == "none":
        stop_reason = "tool_budget" if executed >= max_tool_calls else "other_framework_limit"
    else:
        stop_reason = "agent_answered"
    return AgentRunResult(scenario_id=scenario_id, user_report=runtime.user_report,
        model_name=settings.model_name, model_provider=settings.model_provider,
        configured_tool_budget=max_tool_calls, tool_calls=recorder.calls,
        evidence_ids_retrieved=evidence, number_of_tool_calls=executed,
        final_diagnosis=diagnosis, elapsed_seconds=perf_counter() - started, usage=usage, error=error,
        stop_reason=stop_reason, model_rounds=rounds.rounds,
        stopping_checks=stopper.checks if stopper is not None else [],
        adaptive_stop_call_index=stopper.stop_call_index if stopper is not None else None,
        model_settings={"temperature": settings.temperature, "reasoning_effort": None,
                        "allow_multiple_tool_calls": False, "max_iterations": 20},
        prompt_sha256=hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
        runtime_sha256=hashlib.sha256(json.dumps(runtime.model_dump(), sort_keys=True).encode()).hexdigest())
