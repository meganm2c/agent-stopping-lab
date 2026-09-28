"""Create/reuse the versioned pilot dataset and run four controlled experiments."""
import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys
from dataclasses import asdict, is_dataclass
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from agent_tool_budget_lab.agent import SYSTEM_PROMPT
from agent_tool_budget_lab.config import Settings
from agent_tool_budget_lab.scenarios import load_scenarios, DEFAULT_DATA
from agent_tool_budget_lab.phoenix_support import configure_phoenix, phoenix_client, traced_run
from agent_tool_budget_lab.phoenix_evaluators import make_evaluators


async def main():
    settings = Settings.from_env()
    provider = configure_phoenix()
    client = phoenix_client()
    from phoenix.client import AsyncClient
    async_client = AsyncClient(base_url=os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006"),
                               api_key=os.getenv("PHOENIX_API_KEY") or None)
    scenarios = load_scenarios()
    dataset_hash = hashlib.sha256(DEFAULT_DATA.read_bytes()).hexdigest()
    name = 'agent-tool-budget-pilot-v2-' + dataset_hash[:8]
    existing = [d for d in client.datasets.list() if d['name'] == name]
    if existing:
        dataset = client.datasets.get_dataset(dataset=existing[0]['id'])
    else:
        dataset = client.datasets.create_dataset(name=name,
            inputs=[{'scenario_id':s.scenario_id,'user_report':s.runtime.user_report} for s in scenarios.values()],
            outputs=[{'root_cause':s.root_cause,'acceptable_root_causes':s.acceptable_root_causes or [s.root_cause]} for s in scenarios.values()],
            metadata=[{'difficulty':s.difficulty,'category':s.root_cause,'rubric_version':2,
                       'dataset_sha256':dataset_hash} for s in scenarios.values()],
            dataset_description='Eight deterministic worlds; JSON source is canonical. Labels are evaluation-only.')
    expected_inputs = {(s.scenario_id,s.runtime.user_report) for s in scenarios.values()}
    if {(e['input']['scenario_id'],e['input']['user_report']) for e in dataset.examples} != expected_inputs:
        raise ValueError('Phoenix dataset does not match local runtime inputs')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output_dir = Path('results') / f'phoenix-{stamp}'
    output_dir.mkdir(parents=True)
    manifest = {'dataset_id':dataset.id,'dataset_version_id':dataset.version_id,'dataset_name':name,
                'dataset_sha256':dataset_hash, 'model_name':settings.model_name,
                'prompt_sha256':hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
                'temperature':settings.temperature,'experiments':[]}
    for budget in (2,4,6,8):
        async def task(input):
            # Only the dataset input is bound; references and metadata never enter this callable.
            scenario = scenarios[input['scenario_id']]
            if input['user_report'] != scenario.runtime.user_report:
                raise ValueError('Dataset report differs from the canonical scenario')
            row = await traced_run(scenario,settings,budget)
            if row['run']['error']:
                raise RuntimeError(row['run']['error'])
            return row
        # Explicit concurrency=1 preserves sequential execution for the async task.
        metadata = {'tool_budget':budget,'model_name':settings.model_name,
                'temperature':settings.temperature,'prompt_sha256':manifest['prompt_sha256'],
                'dataset_sha256':dataset_hash,'rubric_version':2}
        completed = [e for e in client.experiments.list(dataset_id=dataset.id)
                     if e['name'] == f'tool-budget-{budget}' and e['metadata'] == metadata
                     and e['dataset_version_id'] == dataset.version_id
                     and e['successful_run_count'] == 8 and e['failed_run_count'] == 0]
        if completed:
            experiment = client.experiments.get_experiment(experiment_id=completed[0]['id'])
        else:
            experiment = await async_client.experiments.run_experiment(dataset=dataset,task=task,
                evaluators=None, concurrency=1, experiment_name=f'tool-budget-{budget}',
                experiment_metadata=metadata, print_summary=False,retries=0)
        if len(experiment['task_runs']) != 8 or any(r.get('error') or r.get('output') is None for r in experiment['task_runs']):
            (output_dir / f'failed-budget-{budget}.json').write_text(json.dumps(experiment,indent=2,default=str))
            raise RuntimeError('Experiment tasks failed; inspect the saved failure before continuing')
        if len(experiment['evaluation_runs']) != 88:
            experiment = await async_client.experiments.evaluate_experiment(
                experiment=experiment,evaluators=make_evaluators(scenarios),print_summary=False,retries=0)
        if any(e.error for e in experiment['evaluation_runs']):
            raise RuntimeError('Experiment evaluations failed')
        provider.force_flush()
        (output_dir / f'budget-{budget}.json').write_text(json.dumps(experiment,indent=2,
            default=lambda obj: asdict(obj) if is_dataclass(obj) else str(obj))+'\n')
        manifest['experiments'].append({'budget':budget,'id':experiment['experiment_id'],
            'project_name':experiment['project_name'],
            'url':client.experiments.get_experiment_url(dataset.id,experiment['experiment_id'])})
        (output_dir/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        print(f"Completed tool-budget-{budget}: {manifest['experiments'][-1]['url']}",flush=True)
    print('Results:',output_dir)

if __name__ == '__main__':
    asyncio.run(main())
