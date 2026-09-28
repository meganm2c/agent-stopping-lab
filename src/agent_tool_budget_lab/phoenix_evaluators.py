"""Phoenix-compatible deterministic evaluators; no eval-model dependency."""
from .evaluation import metrics, total_tokens
from .models import AgentRunResult


def evaluation_values(output, scenarios):
    run = AgentRunResult.model_validate(output['run'])
    m = metrics(run, scenarios[run.scenario_id])
    return {
        'diagnosis_correct': int(m['diagnosis_correct']),
        'evidence_completeness': m['evidence_completeness'],
        'evidence_sufficient': int(m['evidence_sufficient']),
        'premature_stop': int(m['premature_stop']),
        'tool_calls_used': run.number_of_tool_calls,
        'redundant_investigation': m['redundant_calls'],
        'irrelevant_calls': m['outside_required_supporting_calls'],
        'post_sufficiency_calls': m['excess_calls'],
        'identical_repeated_calls': m['repeated_calls'],
        'latency_seconds': run.elapsed_seconds,
        'token_usage': total_tokens(output['run']),
    }


def make_evaluators(scenarios):
    names = ('diagnosis_correct', 'evidence_completeness', 'evidence_sufficient',
             'premature_stop', 'tool_calls_used', 'redundant_investigation',
             'irrelevant_calls', 'post_sufficiency_calls', 'identical_repeated_calls',
             'latency_seconds', 'token_usage')
    def build(name):
        def evaluator(output):
            value = evaluation_values(output, scenarios)[name]
            return {'score': value, 'label': 'unavailable' if value is None else str(value),
                    'explanation': f"Deterministic rubric v2; stop_reason={output['run']['stop_reason']}"}
        return evaluator
    return {name: build(name) for name in names}
