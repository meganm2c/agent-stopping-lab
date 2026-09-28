"""Serializable runtime records. Evaluation labels live in scenarios.py only."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Component = Literal["frontend", "api", "database", "cache"]
COMPONENTS = ("frontend", "api", "database", "cache")


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class StatusOutput(Record):
    component: Component
    status: Literal["healthy", "degraded", "unavailable"]
    detail: str
    evidence_id: str


class LogsOutput(Record):
    component: Component
    log_summary: str
    evidence_id: str


class ChangeOutput(Record):
    component: Component
    changed: bool
    description: str
    evidence_id: str


class ComponentState(Record):
    status: StatusOutput
    logs: LogsOutput
    recent_change: ChangeOutput


class RuntimeState(Record):
    user_report: str
    components: dict[Component, ComponentState]


class Diagnosis(Record):
    predicted_root_cause: str
    explanation: str
    evidence_used: list[str]


class ToolCall(Record):
    tool_index: int
    tool_name: str
    arguments: dict[str, str]
    output: dict
    executed: bool
    elapsed_seconds: float


class AgentRunResult(Record):
    scenario_id: str
    user_report: str
    model_name: str
    model_provider: str
    configured_tool_budget: int
    tool_calls: list[ToolCall]
    evidence_ids_retrieved: list[str]
    number_of_tool_calls: int
    final_diagnosis: Diagnosis | None
    elapsed_seconds: float
    usage: dict = Field(default_factory=dict)
    error: str | None = None
    stop_reason: str = "unavailable"
    model_rounds: list[dict] = Field(default_factory=list)
    stopping_checks: list[dict] = Field(default_factory=list)
    adaptive_stop_call_index: int | None = None
    model_settings: dict = Field(default_factory=dict)
    prompt_sha256: str | None = None
    runtime_sha256: str | None = None
