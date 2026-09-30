"""Standard-library archive reader and presentation. No model or Phoenix imports."""
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SWEEP = 'results/phoenix-20260928T011340Z/runs.jsonl'
FINAL = 'results/phase3-comparison/runs.jsonl'
SUMMARY = 'results/phase3-comparison/summary.json'
STORIES = 'results/phase3-comparison/demo-traces.json'
VARIATION = 'results/phase3-variation/summary.json'
STRATEGIES = ('Fixed 2', 'Fixed 4', 'Fixed 6', 'Fixed 8', 'Adaptive')
EXPERIMENTS = {'fixed-budget-6': 'Fixed 6', 'fixed-budget-8': 'Fixed 8',
               'adaptive-stopping': 'Adaptive'}
GITHUB = 'https://github.com/meganm2c/agent-stopping-lab'
STORY_NOTES = (
    ('Low-budget premature stop',
     'The two-call limit ends investigation after frontend and API status checks. API logs, database health, and the API change remain unseen. '
     'The final answer is wrong: a budget-forced response can turn an evidence gap into a diagnosis.'),
    ('Fixed-8 successful investigation',
     'Database status and logs establish saturation, yet the agent continues investigating. '
     'The final label is correct; the trace exposes the cost of extra confirmation.'),
    ('Adaptive supported early stop',
     'The first API status explicitly identifies an invalid zero request limit. '
     'STOP is supported here. One successful easy case does not establish controller reliability.'),
    ('Adaptive false early stop',
     'The controller treats slow API reads as a coherent explanation and stops before checking '
     'database health and cache evidence. The diagnostic agent then names the wrong cause.'),
)


class ArtifactError(ValueError):
    """An archive is absent or cannot support the requested replay."""


def number(value, places=0):
    if value is None:
        return 'Unavailable'
    return f'{Decimal(str(value)).quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP):,.{places}f}'


def tokens(usage):
    if 'total_token_count' in usage:
        return usage['total_token_count']
    if 'input_token_count' in usage and 'output_token_count' in usage:
        return usage['input_token_count'] + usage['output_token_count']
    return None


def token_breakdown(row):
    run = row['run']
    agent = tokens(run['usage'])
    checks = [tokens(c['usage']) for c in run.get('stopping_checks', [])]
    overhead = sum(checks) if all(t is not None for t in checks) else None
    total = agent + overhead if agent is not None and overhead is not None else None
    return agent, overhead, total


class Archive:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.scenarios = {s['scenario_id']: s for s in self._read('data/scenarios.json')}
        self.summary = self._read(SUMMARY)['aggregates']
        self.variation = self._read(VARIATION)['groups']
        self.rows = {}
        self.by_trace = {}
        for row in self._read_lines(SWEEP):
            if row['run']['configured_tool_budget'] in (2, 4):
                self._add(row, f"Fixed {row['run']['configured_tool_budget']}", 1)
        for row in self._read_lines(FINAL):
            self._add(row, EXPERIMENTS[row['experiment_name']], row['repetition'])
        self.stories = self._read(STORIES)
        if len(self.scenarios) != 8 or len(self.stories) != 4:
            raise ArtifactError('Expected eight scenarios and four curated trace stories in the archive.')
        for sid in self.scenarios:
            for strategy in STRATEGIES:
                expected = [1] if strategy in ('Fixed 2', 'Fixed 4') else [1, 2, 3]
                if self.repetitions(sid, strategy) != expected:
                    raise ArtifactError(f'Incomplete archived runs for {sid}, {strategy}.')
        if any(s['trace_id'] not in self.by_trace for s in self.stories):
            raise ArtifactError('A curated trace ID is missing from the final run archive.')

    def _read(self, relative):
        try:
            return json.loads((self.root / relative).read_text())
        except FileNotFoundError as exc:
            raise ArtifactError(f'Missing replay artifact: {relative}. Include the committed data/results files.') from exc
        except (ValueError, UnicodeError) as exc:
            raise ArtifactError(f'Cannot read replay artifact: {relative}. Restore the committed file.') from exc

    def _read_lines(self, relative):
        try:
            return [json.loads(line) for line in (self.root / relative).read_text().splitlines() if line.strip()]
        except FileNotFoundError as exc:
            raise ArtifactError(f'Missing replay artifact: {relative}. Include the committed data/results files.') from exc
        except (ValueError, UnicodeError) as exc:
            raise ArtifactError(f'Cannot read replay artifact: {relative}. Restore the committed file.') from exc

    def _add(self, row, strategy, repetition):
        run = row['run']; sid = run['scenario_id']
        if sid not in self.scenarios or run['user_report'] != self.scenarios[sid]['runtime']['user_report']:
            raise ArtifactError(f'Archived user report does not match scenario {sid}.')
        key = (sid, strategy, int(repetition))
        if key in self.rows:
            raise ArtifactError(f'Duplicate archived run: {sid}, {strategy}, repetition {repetition}.')
        self.rows[key] = row
        self.by_trace[row['trace_id']] = key

    def repetitions(self, scenario, strategy):
        return sorted(rep for sid, label, rep in self.rows if sid == scenario and label == strategy)

    def resolve(self, scenario, strategy, repetition=1):
        try:
            return deepcopy(self.rows[(scenario, strategy, int(repetition))])
        except (KeyError, ValueError, TypeError) as exc:
            raise ArtifactError('Stored run not found. Choose an available scenario, strategy, and repetition.') from exc

    def scenario_choices(self):
        # No hidden cause or difficulty label in the selector.
        return [(f"{sid} — {s['runtime']['user_report']}", sid) for sid, s in sorted(self.scenarios.items())]

    def comparison(self):
        keys = [('Accuracy', 'accuracy', 1, True),
                ('Evidence completeness', 'evidence_completeness', 1, True),
                ('Evidence sufficiency', 'evidence_sufficient', 1, True),
                ('Average tool calls', 'calls_mean', 2, False),
                ('Total tokens/run', 'total_tokens', 0, False),
                ('Seconds/run', 'latency_seconds', 2, False)]
        return [[label, *[number(self.summary[name][key] * (100 if pct else 1), places) + ('%' if pct else '')
                         for name in EXPERIMENTS]] for label, key, places, pct in keys]

    def findings(self):
        fixed, adaptive = self.summary['fixed-budget-8'], self.summary['adaptive-stopping']
        fewer = 100 * (1 - adaptive['calls_mean'] / fixed['calls_mean'])
        more_tokens = 100 * (adaptive['total_tokens'] / fixed['total_tokens'] - 1)
        slower = 100 * (adaptive['latency_seconds'] / fixed['latency_seconds'] - 1)
        false = round(adaptive['false_early_stop'] * adaptive['n'])
        return (f'### Fewer tool calls did not mean a more efficient system.\n\n'
                f'Adaptive stopping used **{number(fewer, 1)}% fewer tool calls** than Fixed-8, '
                f'but **{number(more_tokens, 1)}% more total tokens** and **{number(slower, 1)}% more time**. '
                f'**{false} of {adaptive["n"]} runs stopped without sufficient evidence.**\n\n'
                'The controller added a model inference after each tool result. It often accepted a plausible '
                'intermediate explanation before resolving the cause. Reliability fell while total cost increased. '
                'The frozen hypothesis was not supported, and the prompt was not tuned after the results.')


def trajectory_markdown(row):
    run = row['run']; checks = {c['tool_index']: c for c in run.get('stopping_checks', [])}
    lines = ['## Ordered trajectory', 'Observed tool results and controller decisions, in execution order.']
    for call in run['tool_calls']:
        output = call['output']; index = call['tool_index']
        lines += ['', f"### {index}. `{escape(call['tool_name'])}({escape(call['arguments']['component'])})`"]
        if not call['executed']:
            lines.append('**Execution blocked.**')
        if 'status' in output:
            lines.append(f"**Status:** {escape(output['status'])}")
        if 'changed' in output:
            lines.append(f"**Recent change:** {'Yes' if output['changed'] else 'No'}")
        for field in ('detail', 'log_summary', 'description', 'error'):
            if output.get(field):
                lines.append(escape(str(output[field])))
        if 'evidence_id' in output:
            lines.append(f"\n**Evidence returned:** `{escape(output['evidence_id'])}`")
        if index in checks:
            check = checks[index]
            lines += ['', f"**Stopping check — {check['decision']}**", escape(check['reason']),
                      f"\nController: {number(check['elapsed_seconds'], 2)}s · {number(tokens(check['usage']))} tokens"]
    if not run['tool_calls']:
        lines.append('No tool calls recorded.')
    return '\n\n'.join(lines)


def final_markdown(row):
    run, m = row['run'], row['metrics']; diagnosis = run['final_diagnosis']
    agent, overhead, total = token_breakdown(row)
    reason = {'tool_budget': 'Budget-forced final answer', 'agent_answered': 'Voluntary answer',
              'adaptive_stop': 'Adaptive controller STOP'}.get(run['stop_reason'], run['stop_reason'])
    lines = ['## Final result', '**Evaluation below was applied after execution. These labels were hidden from the agent and controller.**',
             f"**Predicted root cause:** `{escape(diagnosis['predicted_root_cause'])}`",
             escape(diagnosis['explanation']), '', '| Metric | Recorded value |', '|---|---|',
             f"| Diagnosis | {'Correct' if m['diagnosis_correct'] else 'Incorrect'} |",
             f"| Evidence completeness | {number(100*m['evidence_completeness'],1)}% |",
             f"| Evidence sufficient | {'Yes' if m['evidence_sufficient'] else 'No'} |",
             f"| Tool calls | {run['number_of_tool_calls']} |",
             f"| Total latency | {number(run['elapsed_seconds'],2)}s |",
             f"| Agent tokens | {number(agent)} |", f"| Total tokens | {number(total)} |",
             f"| Stop reason | {reason} |",
             f"| Post-sufficiency calls | {m['excess_calls']} |"]
    if run.get('stopping_checks'):
        index = run.get('adaptive_stop_call_index'); triggered = index is not None
        lines += [f"| Adaptive stop triggered | {'Yes' if triggered else 'No'} |",
                  f"| Stopping call index | {index if triggered else 'Not triggered'} |",
                  f"| False early stop | {'Yes' if triggered and not m['evidence_sufficient'] else 'No'} |",
                  f"| Stopper overhead | {number(overhead)} tokens; {number(sum(c['elapsed_seconds'] for c in run['stopping_checks']),2)}s |"]
    lines += ['', '**Required evidence retrieved:** '+(', '.join(f'`{e}`' for e in m['required_evidence_retrieved']) or 'None'),
              '**Required evidence missing:** '+(', '.join(f'`{e}`' for e in m['missing_required_evidence']) or 'None'),
              '\nEvidence sufficiency is a fixed rubric; a correct label can still lack supporting evidence. '
              'Total tokens and latency include stopping checks.']
    return '\n'.join(lines)


def render_run(archive, scenario, strategy, repetition=1):
    row = archive.resolve(scenario, strategy, repetition)
    source = ('Phoenix fixed-budget sweep · one run per scenario/budget' if strategy in ('Fixed 2', 'Fixed 4')
              else 'Final repeated Phase 3 comparison · three runs per scenario/strategy')
    intro = f"## User report\n\n{escape(row['run']['user_report'])}\n\n**{strategy} · Run {repetition}**  \n{source}.\n\nStored replay; no model requests are made."
    return intro, trajectory_markdown(row), final_markdown(row)


def render_story(archive, index):
    index = int(index); item = archive.stories[index]
    # Low-budget case from Phase 2; remaining stories use the curated Phase 3 IDs.
    sid, strategy, repetition = (('diag_007', 'Fixed 2', 1) if index == 0
                                 else archive.by_trace[item['trace_id']])
    intro, trajectory, final = render_run(archive, sid, strategy, repetition)
    title, explanation = STORY_NOTES[index]
    # Interpretation/hidden evidence appears only after the final result.
    insight = f'## What Phoenix revealed\n\n{explanation}\n\nTrace inspection links the stop reason to the exact observed evidence and controller decision. Final accuracy alone hides that distinction.'
    return f'# {title}\n\n{intro}', trajectory, final, insight
