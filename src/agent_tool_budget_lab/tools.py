"""Three deterministic tools and a per-run execution/recording boundary."""
from time import perf_counter
from opentelemetry import trace
import json
from .environment import DiagnosticEnvironment
from .models import StatusOutput, LogsOutput, ChangeOutput, ToolCall


class DiagnosticTools:
    def __init__(self, environment: DiagnosticEnvironment):
        self.environment = environment

    def check_status(self, component: str) -> StatusOutput:
        return self.environment.component(component).status

    def read_logs(self, component: str) -> LogsOutput:
        return self.environment.component(component).logs

    def check_recent_change(self, component: str) -> ChangeOutput:
        return self.environment.component(component).recent_change


class ToolRecorder:
    """Synchronous, atomic boundary: count attempts, gate execution, record results."""
    def __init__(self, environment: DiagnosticEnvironment, budget: int):
        if budget < 1:
            raise ValueError("Tool budget must be positive")
        self.tools = DiagnosticTools(environment)
        self.budget = budget
        self.calls: list[ToolCall] = []
        self.adaptive_stopped = False

    def invoke(self, name: str, component: str) -> dict:
        if name not in ("check_status", "read_logs", "check_recent_change"):
            raise ValueError(f"Unknown tool {name}")
        started = perf_counter()
        executed = not self.adaptive_stopped and sum(c.executed for c in self.calls) < self.budget
        if not executed:
            output = {"error": "adaptive_stopped" if self.adaptive_stopped else "tool_budget_exhausted", "detail": "Return your diagnosis using observed evidence."}
        else:
            try:
                output = getattr(self.tools, name)(component).model_dump()
            except ValueError as exc:
                output = {"error": "invalid_component", "detail": str(exc)}
        self.calls.append(ToolCall(tool_index=len(self.calls) + 1, tool_name=name,
            arguments={"component": component}, output=output, executed=executed,
            elapsed_seconds=perf_counter() - started))
        span = trace.get_current_span()
        if span.is_recording():
            span.set_attributes({"tool_index": len(self.calls), "tool_name": name,
                                 "component": component, "executed": executed,
                                 "input.value": json.dumps({"component": component}),
                                 "output.value": json.dumps(output),
                                 "input.mime_type": "application/json",
                                 "output.mime_type": "application/json",
                                 "openinference.span.kind": "TOOL"})
            if "evidence_id" in output:
                span.set_attribute("evidence_id", output["evidence_id"])
        return output

    def framework_tools(self):
        from agent_framework import tool

        @tool(approval_mode="never_require")
        def check_status(component: str) -> dict:
            """Check health and a short metric for frontend, api, database, or cache."""
            return self.invoke("check_status", component)

        @tool(approval_mode="never_require")
        def read_logs(component: str) -> dict:
            """Read log summary for frontend, api, database, or cache."""
            return self.invoke("read_logs", component)

        @tool(approval_mode="never_require")
        def check_recent_change(component: str) -> dict:
            """Check recent deployment/configuration change for a system component."""
            return self.invoke("check_recent_change", component)

        return [check_status, read_logs, check_recent_change]
