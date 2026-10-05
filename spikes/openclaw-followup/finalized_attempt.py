"""Reusable adapter for a newly authorized physical attempt; never retries internally."""
import json
from adapter import run_once,dump,MODEL
from finalization import freeze,run_finalizer
from finalization_lifecycle import assemble

def run_finalized_attempt(scenario,budget,repetition,output,*,namespace,physical_attempt=1):
    """Caller must explicitly choose fresh physical_attempt for any replacement.

    No prior answer is passed to the finalizer. Diagnostic prose is an intermediate
    loop artifact under this contract, even when it happens to be valid JSON.
    """
    row=None
    try:
        row=run_once(scenario,budget,repetition,output/'diagnostic',namespace=f'{namespace}/attempt-{physical_attempt}',physical_attempt=physical_attempt)
        assert row['accounting']['accepted'] and row['accounting']['internal_attempts']==1
        assert row['run']['error'] in [None,'No valid JSON Diagnosis']
        assert row['runtime_id']=='openclaw' and not row['terminal_receipt']['rerouted']
        assert row['terminal_receipt']['effective']['responseModel']==MODEL
        final=run_finalizer(freeze(row['run']['user_report'],row['run']['tool_calls']),output,row['run_id'])
        requests=json.loads((output/'diagnostic/requests'/f"{row['run_id']}.json").read_text())
        completed,requests=assemble(row,final,requests)
        completed.update(intended_repetition=repetition,physical_attempt=physical_attempt)
        dump(output/'runs'/f"{row['run_id']}.json",completed)
        dump(output/'requests'/f"{row['run_id']}.json",requests)
        return completed
    except Exception as exc:
        identifier=row['run_id'] if row else f'{scenario}-b{budget}-r{repetition}-attempt-{physical_attempt}'
        dump(output/'rejections'/f'{identifier}.json',{'accepted':False,'scenario_id':scenario,'budget':budget,'intended_repetition':repetition,'physical_attempt':physical_attempt,'run_id':row['run_id'] if row else None,'error_type':type(exc).__name__,'reason':'Diagnostic invariants, finalizer transport, or strict final contract failed; inspect preserved phase artifacts. No repair or automatic session resume.'})
        raise
