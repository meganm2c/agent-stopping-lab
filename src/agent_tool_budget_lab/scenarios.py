"""Dataset loading and evaluation-only labels; never pass Scenario to the agent."""
import json
from pathlib import Path
from typing import Literal
from pydantic import Field, model_validator
from .models import COMPONENTS, Record, RuntimeState

DEFAULT_DATA = Path(__file__).resolve().parents[2] / "data" / "scenarios.json"


class Scenario(Record):
    scenario_id: str
    difficulty: Literal["easy", "medium", "hard"]
    root_cause: str
    acceptable_root_causes: list[str] = Field(default_factory=list)
    required_evidence: list[str]
    optional_supporting_evidence: list[str]
    distractor_evidence: list[str]
    runtime: RuntimeState

    @model_validator(mode="after")
    def validate_evidence(self):
        if self.acceptable_root_causes and (self.root_cause not in self.acceptable_root_causes or len(set(self.acceptable_root_causes)) != len(self.acceptable_root_causes)):
            raise ValueError("Accepted labels must include the canonical cause and contain no duplicates")
        if set(self.runtime.components) != set(COMPONENTS):
            raise ValueError("Every scenario must contain exactly the four components")
        ids = []
        for component, state in self.runtime.components.items():
            for output in (state.status, state.logs, state.recent_change):
                if output.component != component:
                    raise ValueError("Output component does not match its state")
                ids.append(output.evidence_id)
        if len(set(ids)) != len(ids):
            raise ValueError("Evidence IDs must be unique within a scenario")
        labels = self.required_evidence + self.optional_supporting_evidence + self.distractor_evidence
        if not self.required_evidence or len(labels) != len(set(labels)):
            raise ValueError("Evidence labels must be nonoverlapping and required evidence nonempty")
        if not set(labels) <= set(ids):
            raise ValueError("Labeled evidence must be retrievable")
        return self

    def accepts_root_cause(self, prediction: str) -> bool:
        return prediction in (self.acceptable_root_causes or [self.root_cause])


def load_scenarios(path: Path = DEFAULT_DATA) -> dict[str, Scenario]:
    scenarios = [Scenario.model_validate(row) for row in json.loads(path.read_text())]
    result = {s.scenario_id: s for s in scenarios}
    if len(result) != len(scenarios):
        raise ValueError("Duplicate scenario IDs")
    return result
