"""Run one live scenario; install the project with pip install -e '.[dev]' first."""
import argparse
import asyncio
from pathlib import Path
import sys

# Support running these source-checkout scripts directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from agent_tool_budget_lab.agent import run_agent
from agent_tool_budget_lab.config import Settings
from agent_tool_budget_lab.scenarios import load_scenarios


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default="diag_001")
    parser.add_argument("--max-tool-calls", type=int, choices=range(1, 9), default=4)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    scenarios = load_scenarios()
    if args.scenario not in scenarios:
        parser.error("Unknown scenario; choose " + ", ".join(scenarios))
    try:
        settings = Settings.from_env()
    except ValueError as exc:
        parser.error(str(exc))
    scenario = scenarios[args.scenario]
    result = asyncio.run(run_agent(scenario.scenario_id, scenario.runtime, settings, args.max_tool_calls))
    print(f"Scenario: {result.scenario_id}\n{result.user_report}\n\nTool budget: {result.configured_tool_budget}\nTool calls:")
    for call in result.tool_calls:
        print(f"{call.tool_index}. {call.tool_name}({call.arguments['component']})" + (" [blocked]" if not call.executed else ""))
    print("\nRetrieved evidence: " + ", ".join(result.evidence_ids_retrieved))
    print("\nFinal diagnosis:\n" + (result.final_diagnosis.model_dump_json(indent=2) if result.final_diagnosis else str(result.error)))
    print(f"\nElapsed: {result.elapsed_seconds:.2f}s; usage: {result.usage}")
    print(f"Stop reason: {result.stop_reason}")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result.model_dump_json(indent=2) + "\n")
    if result.error:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
