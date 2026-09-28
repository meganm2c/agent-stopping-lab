"""Read-only diagnostic world with an owned copy of runtime state."""
from typing import TYPE_CHECKING
from .models import COMPONENTS, RuntimeState, ComponentState
if TYPE_CHECKING:
    from .scenarios import Scenario


class DiagnosticEnvironment:
    def __init__(self, state: RuntimeState):
        self._state = state.model_copy(deep=True)

    @classmethod
    def from_scenario(cls, scenario: "Scenario") -> "DiagnosticEnvironment":
        return cls(scenario.runtime)

    @property
    def user_report(self) -> str:
        return self._state.user_report

    def component(self, name: str) -> ComponentState:
        if name not in COMPONENTS:
            raise ValueError(f"Unknown component {name!r}; choose from {', '.join(COMPONENTS)}")
        return self._state.components[name].model_copy(deep=True)
