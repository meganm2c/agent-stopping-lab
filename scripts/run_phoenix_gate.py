"""Compatibility gate: trace easy/hard runs before creating experiments."""
import asyncio
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from agent_tool_budget_lab.config import Settings
from agent_tool_budget_lab.scenarios import load_scenarios
from agent_tool_budget_lab.phoenix_support import configure_phoenix, traced_run

async def main():
    settings = Settings.from_env()
    provider = configure_phoenix()
    scenarios = load_scenarios()
    rows = []
    for sid,budget in [('diag_001',2),('diag_007',8)]:
        row = await traced_run(scenarios[sid],settings,budget)
        rows.append(row)
        print(sid, row['trace_id'], row['run']['error'], flush=True)
    provider.force_flush()
    Path('results').mkdir(exist_ok=True)
    Path('results/phoenix-gate.json').write_text(json.dumps(rows,indent=2)+'\n')
    if any(r['run']['error'] for r in rows):
        raise SystemExit('Trace gate failed')

if __name__ == '__main__':
    asyncio.run(main())
