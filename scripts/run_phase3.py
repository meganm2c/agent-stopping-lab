"""Controlled Phase 3 studies on the unchanged Phoenix pilot dataset."""
import argparse
import asyncio
from dataclasses import asdict, is_dataclass
import hashlib
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from phoenix.client import AsyncClient
from phoenix.client.resources.datasets import Dataset
from agent_tool_budget_lab.agent import SYSTEM_PROMPT
from agent_tool_budget_lab.config import Settings
from agent_tool_budget_lab.scenarios import load_scenarios, DEFAULT_DATA
from agent_tool_budget_lab.phoenix_support import configure_phoenix, phoenix_client, traced_run
from agent_tool_budget_lab.phoenix_evaluators import make_evaluators


def dump(path, value):
    path.write_text(json.dumps(value, indent=2,
        default=lambda o: asdict(o) if is_dataclass(o) else str(o)) + '\n')


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['variation', 'comparison'])
    args = parser.parse_args()
    settings = Settings.from_env()
    assert settings.model_name == 'gpt-4.1-mini-2025-04-14' and settings.temperature == 0
    provider = configure_phoenix(); client = phoenix_client()
    ac = AsyncClient(base_url=os.getenv('PHOENIX_COLLECTOR_ENDPOINT', 'http://localhost:6006'),
                     api_key=os.getenv('PHOENIX_API_KEY') or None)
    scenarios = load_scenarios()
    original = json.loads(Path('results/phoenix-20260928T011340Z/manifest.json').read_text())
    digest = hashlib.sha256(DEFAULT_DATA.read_bytes()).hexdigest()
    prompt = hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest()
    assert digest == original['dataset_sha256'] and prompt == original['prompt_sha256']
    dataset = client.datasets.get_dataset(dataset=original['dataset_id'])
    assert dataset.version_id == original['dataset_version_id'] and len(dataset.examples) == 8
    for e in dataset.examples:
        assert e['input']['user_report'] == scenarios[e['input']['scenario_id']].runtime.user_report
    if args.stage == 'variation':
        # Local filtered view preserves the original dataset/version/example IDs.
        data = dataset.to_dict()
        data['examples'] = [e for e in data['examples'] if e['input']['scenario_id'] in
                            ('diag_004', 'diag_005', 'diag_006', 'diag_007', 'diag_008')]
        dataset = Dataset.from_dict(data)
        configurations = [('repeatability-budget-6-phase3', 6, False),
                          ('repeatability-budget-8-phase3', 8, False)]
        repetitions = 5
    else:
        assert Path('ADAPTIVE_HYPOTHESIS.md').exists()
        configurations = [('fixed-budget-6', 6, False), ('fixed-budget-8', 8, False),
                          ('adaptive-stopping', 8, True)]
        repetitions = 3
    output = Path('results') / f'phase3-{args.stage}'; output.mkdir(exist_ok=True)
    manifest = dict(dataset_id=dataset.id, dataset_version_id=dataset.version_id,
                    dataset_sha256=digest, prompt_sha256=prompt, experiments=[])
    for name, budget, adaptive in configurations:
        async def task(input):
            scenario = scenarios[input['scenario_id']]
            assert input['user_report'] == scenario.runtime.user_report
            if adaptive:
                row = await traced_run(scenario, settings, budget, adaptive=True)
            else:
                row = await traced_run(scenario, settings, budget)
            if row['run']['error']:
                raise RuntimeError(row['run']['error'])
            return row
        metadata = dict(phase=3, stage=args.stage, budget=budget, adaptive=adaptive,
                        model=settings.model_name, temperature=settings.temperature,
                        prompt_sha256=prompt, dataset_sha256=digest, repetitions=repetitions)
        if args.stage == 'comparison':
            metadata['hypothesis_sha256'] = hashlib.sha256(Path('ADAPTIVE_HYPOTHESIS.md').read_bytes()).hexdigest()
            from agent_tool_budget_lab.stopping import STOPPER_PROMPT, StopDecision
            metadata['stopper_prompt_sha256'] = hashlib.sha256(STOPPER_PROMPT.encode()).hexdigest()
            metadata['stopper_schema'] = StopDecision.model_json_schema()
        count = len(dataset.examples) * repetitions
        existing = [e for e in client.experiments.list(dataset_id=dataset.id)
                    if e['name'] == name and e['metadata'] == metadata
                    and e['successful_run_count'] == count and e['failed_run_count'] == 0]
        if existing:
            result = client.experiments.get_experiment(experiment_id=existing[0]['id'])
        else:
            result = await ac.experiments.run_experiment(dataset=dataset, task=task,
                concurrency=1, repetitions=repetitions, experiment_name=name,
                experiment_metadata=metadata, print_summary=False, retries=0, timeout=180)
        dump(output / f'{name}.json', result)
        assert len(result['task_runs']) == count and not any(r.get('error') for r in result['task_runs'])
        evaluators = make_evaluators(scenarios)
        if args.stage == 'comparison':
            from agent_tool_budget_lab.adaptive_evaluators import make_adaptive_evaluators
            evaluators.update(make_adaptive_evaluators(scenarios))
        if len(result['evaluation_runs']) != count * len(evaluators):
            result = await ac.experiments.evaluate_experiment(experiment=result,
                evaluators=evaluators, print_summary=False, retries=0)
        assert len(result['evaluation_runs']) == count * len(evaluators)
        assert not any(e.error for e in result['evaluation_runs'])
        provider.force_flush()
        dump(output / f'{name}.json', result)
        manifest['experiments'].append(dict(name=name,id=result['experiment_id'],
            project_name=result['project_name'],budget=budget,adaptive=adaptive,
            url=client.experiments.get_experiment_url(dataset.id,result['experiment_id'])))
        dump(output / 'manifest.json', manifest)
        print('Completed', name, count, flush=True)
    provider.force_flush()

if __name__ == '__main__':
    asyncio.run(main())
