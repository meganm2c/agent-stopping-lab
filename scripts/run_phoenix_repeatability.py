"""Optional 36-run check: four existing scenarios, budgets 4/6/8, three repeats."""
import asyncio
from dataclasses import asdict, is_dataclass
import hashlib
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from phoenix.client import AsyncClient
from agent_tool_budget_lab.config import Settings
from agent_tool_budget_lab.scenarios import load_scenarios, DEFAULT_DATA
from agent_tool_budget_lab.phoenix_support import configure_phoenix, phoenix_client, traced_run
from agent_tool_budget_lab.phoenix_evaluators import make_evaluators

async def main():
    settings=Settings.from_env();provider=configure_phoenix();client=phoenix_client()
    scenarios=load_scenarios()
    selected=[scenarios[s] for s in ('diag_004','diag_006','diag_007','diag_008')]
    digest=hashlib.sha256(DEFAULT_DATA.read_bytes()).hexdigest()
    name='pilot-repeatability-v2-'+digest[:8]
    existing=[d for d in client.datasets.list() if d['name']==name]
    dataset=client.datasets.get_dataset(dataset=existing[0]['id']) if existing else client.datasets.create_dataset(
        name=name,inputs=[{'scenario_id':s.scenario_id,'user_report':s.runtime.user_report} for s in selected],
        outputs=[{'root_cause':s.root_cause,'acceptable_root_causes':s.acceptable_root_causes or [s.root_cause]} for s in selected],
        metadata=[{'difficulty':s.difficulty,'rubric_version':2,'source_dataset_sha256':digest} for s in selected])
    ac=AsyncClient(base_url=os.getenv('PHOENIX_COLLECTOR_ENDPOINT','http://localhost:6006'),api_key=os.getenv('PHOENIX_API_KEY') or None)
    output=Path('results/phoenix-repeatability');output.mkdir(exist_ok=True)
    for budget in (4,6,8):
        async def task(input):
            s=scenarios[input['scenario_id']]
            assert input['user_report']==s.runtime.user_report
            row=await traced_run(s,settings,budget)
            if row['run']['error']: raise RuntimeError(row['run']['error'])
            return row
        result=await ac.experiments.run_experiment(dataset=dataset,task=task,concurrency=1,repetitions=3,
            experiment_name=f'repeatability-budget-{budget}',evaluators=make_evaluators(scenarios),
            experiment_metadata={'model':settings.model_name,'temperature':settings.temperature,
                                 'budget':budget,'dataset_sha256':digest},print_summary=False,retries=0)
        assert len(result['task_runs'])==12 and not any(r.get('error') for r in result['task_runs'])
        assert len(result['evaluation_runs'])==132 and not any(e.error for e in result['evaluation_runs'])
        provider.force_flush()
        (output/f'budget-{budget}.json').write_text(json.dumps(result,indent=2,
            default=lambda o:asdict(o) if is_dataclass(o) else str(o))+'\n')
        print('Completed',budget,client.experiments.get_experiment_url(dataset.id,result['experiment_id']),flush=True)

if __name__=='__main__':
    asyncio.run(main())
