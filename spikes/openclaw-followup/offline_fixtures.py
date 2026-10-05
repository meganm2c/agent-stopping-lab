"""Load compact synthetic fixtures; never read saved experiments or call providers."""
import copy
import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / 'fixtures'


def captured():
    fixture = json.loads((FIXTURES / 'trace_contract.json').read_text())
    return fixture['row'], fixture['spans']


def finalization_inputs():
    from finalization import freeze

    row, _ = captured()
    row.update(
        run_id='offline-fixture', run_end_ms=2000, cli_wall_seconds=1.0,
        wall_start=1.0, request_count=4, model_events=[],
        terminal_receipt={'effective': {'responseModel': row['run']['model_name']}, 'rerouted': False},
        accounting={'accepted': True, 'internal_attempts': 1, 'invocations': [], 'request_count': 4},
    )
    row['assistant_messages'] = [{'content': [{'type': 'text', 'text': 'Offline loop answer'}]}]
    frozen = freeze(row['run']['user_report'], row['run']['tool_calls'])
    f = json.loads((FIXTURES / 'finalization.json').read_text())
    model = row['run']['model_name']
    body = {'model': model, 'temperature': 0, 'messages': [
        {'role': 'system', 'content': frozen['system']},
        {'role': 'user', 'content': frozen['user']},
    ]}
    finalization = {
        'fixture': frozen,
        'completion': {'ok': True, 'start_ms': f['start_ms'], 'end_ms': f['end_ms'], 'result': {
            'model': model, 'provider': 'openai',
            'execution': {'mode': 'isolated-agent-runtime', 'owner': {'kind': 'harness', 'id': 'openclaw'}},
            'text': json.dumps(f['diagnosis']), 'usage': f['usage'],
        }},
        'requests': [{'blocked': False, 'at': f['request_ms'], 'body': body}],
        'transport': [{'status': 200, 'request_ordinal': 1}],
        'wall_seconds': 1.0, 'wall_end': 3.0,
    }
    return copy.deepcopy(row), finalization, []


def finalized_row():
    from finalization_lifecycle import assemble
    return assemble(*finalization_inputs())[0]
