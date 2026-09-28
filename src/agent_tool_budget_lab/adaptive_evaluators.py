"""Post-run adaptive metrics. Never imported by the runtime stopper."""
from .evaluation import metrics, total_tokens
from .models import AgentRunResult


def adaptive_values(output, scenarios):
    run = AgentRunResult.model_validate(output['run'])
    sufficient = metrics(run, scenarios[run.scenario_id])['evidence_sufficient']
    triggered = run.adaptive_stop_call_index is not None
    tokens = [total_tokens({'usage': check['usage']}) for check in run.stopping_checks]
    overhead = sum(tokens) if all(t is not None for t in tokens) else None
    agent_tokens = total_tokens(output['run'])
    return dict(adaptive_stop_triggered=int(triggered), stop_call_index=run.adaptive_stop_call_index,
                false_early_stop=int(triggered and not sufficient),
                avoided_calls_vs_budget8=max(0, 8 - run.number_of_tool_calls),
                stopper_overhead_tokens=overhead,
                stopper_overhead_latency=sum(c['elapsed_seconds'] for c in run.stopping_checks),
                total_tokens=agent_tokens + overhead if agent_tokens is not None and overhead is not None else None,
                stopper_errors=sum(c['error'] is not None for c in run.stopping_checks))


def make_adaptive_evaluators(scenarios):
    names = ('adaptive_stop_triggered','stop_call_index','false_early_stop','avoided_calls_vs_budget8',
             'stopper_overhead_tokens','stopper_overhead_latency','total_tokens','stopper_errors')
    def build(name):
        def evaluator(output):
            value = adaptive_values(output, scenarios)[name]
            return dict(score=value,label='unavailable' if value is None else str(value),
                        explanation='Post-run adaptive metric; ceiling slack is not a counterfactual saving.')
        return evaluator
    return {name: build(name) for name in names}
