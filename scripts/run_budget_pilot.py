"""Run the live 8-task pilot at budgets 2/4/6/8, saving each result immediately."""
import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys

# Support running these source-checkout scripts directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from statistics import mean
from agent_tool_budget_lab.agent import run_agent
from agent_tool_budget_lab.config import Settings
from agent_tool_budget_lab.scenarios import load_scenarios


from agent_tool_budget_lab.evaluation import metrics, total_tokens


def aggregate(rows):
    """Unavailable token values stay null; errors remain in the denominator."""
    tokens = [total_tokens(row['run']) for row in rows]
    return {
        "scenarios": len(rows),
        "accuracy": mean(r['metrics']['correct'] for r in rows),
        "avg_evidence_completeness": mean(r['metrics']['evidence_completeness'] for r in rows),
        "avg_tool_calls": mean(r['run']['number_of_tool_calls'] for r in rows),
        "premature_stop_rate": mean(r['metrics']['premature_stop'] for r in rows),
        "avg_redundant_calls": mean(r['metrics']['redundant_calls'] for r in rows),
        "avg_repeated_calls": mean(r['metrics']['repeated_calls'] for r in rows),
        "avg_outside_required_supporting_calls": mean(r['metrics']['outside_required_supporting_calls'] for r in rows),
        "avg_excess_calls": mean(r['metrics']['excess_calls'] for r in rows),
        "avg_latency": mean(r['run']['elapsed_seconds'] for r in rows),
        "avg_tokens": mean(tokens) if all(t is not None for t in tokens) else None,
        "token_usage_available_runs": sum(t is not None for t in tokens),
        "errors": sum(bool(r['run']['error']) for r in rows),
    }


def summarize(rows):
    summary = {}
    for difficulty in ('all', 'easy', 'medium', 'hard'):
        print(f"\n{difficulty}: budget | n | accuracy | completeness | calls | premature | redundant | seconds | tokens | errors")
        summary[difficulty] = {}
        for budget in (2, 4, 6, 8):
            group = [r for r in rows if r['run']['configured_tool_budget'] == budget
                     and (difficulty == 'all' or r['difficulty'] == difficulty)]
            if not group:
                continue
            a = aggregate(group)
            summary[difficulty][str(budget)] = a
            tokens = f"{a['avg_tokens']:.1f}" if a['avg_tokens'] is not None else 'unavailable'
            print(f"{budget} | {len(group)} | {a['accuracy']:.1%} | {a['avg_evidence_completeness']:.1%} | "
                  f"{a['avg_tool_calls']:.2f} | {a['premature_stop_rate']:.1%} | "
                  f"{a['avg_redundant_calls']:.2f} | {a['avg_latency']:.2f} | {tokens} | {a['errors']}")
    return summary


async def pilot(settings, output):
    import json
    scenarios = load_scenarios()
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    # Exclusive creation prevents accidental loss of earlier measurements.
    with output.open("x") as handle:
        for budget in (2, 4, 6, 8):
            for scenario in scenarios.values():
                print(f"Running {scenario.scenario_id}, budget={budget}", flush=True)
                result = await run_agent(scenario.scenario_id, scenario.runtime, settings, budget)
                row = {"run": result.model_dump(), "difficulty": scenario.difficulty,
                       "metrics": metrics(result, scenario)}
                rows.append(row)
                handle.write(json.dumps(row) + "\n")
                handle.flush()
                if result.error and result.number_of_tool_calls == 0:
                    raise RuntimeError(f"{result.error}; stopped pilot after a failed run with no tools. Partial result saved to {output}")
    summary = summarize(rows)
    output.with_suffix('.summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    signatures = []
    for budget in (2, 4, 6, 8):
        group = [r for r in rows if r['run']['configured_tool_budget'] == budget]
        signatures.append([(r['metrics']['correct'], r['metrics']['evidence_completeness'],
                            r['run']['number_of_tool_calls']) for r in group])
    if all(s == signatures[0] for s in signatures):
        print("DESIGN ISSUE: measured outcomes are identical across budgets. Do not expand the dataset.")
    else:
        print("Budget-dependent variation observed. Inspect individual trajectories before expanding the dataset.")
    print(f"Saved {len(rows)} runs to {output}. One run per cell is exploratory, not a statistical finding.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default = Path('results') / f"pilot-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.jsonl"
    parser.add_argument('--output', type=Path, default=default)
    args = parser.parse_args()
    try:
        settings = Settings.from_env()
        asyncio.run(pilot(settings, args.output))
    except (ValueError, RuntimeError, FileExistsError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == '__main__':
    main()
