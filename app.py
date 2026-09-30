"""Credential-free Gradio replay of the frozen Agent Tool-Budget Lab experiments."""
import os
from pathlib import Path

# Disable Gradio analytics; replay has no API/provider clients or live execution path.
os.environ['GRADIO_ANALYTICS_ENABLED'] = 'False'
import gradio as gr
from demo.replay import Archive, ArtifactError, GITHUB, ROOT, STRATEGIES, STORY_NOTES, render_run, render_story


def build_app(root=ROOT):
    archive = Archive(root)
    initial = render_run(archive, 'diag_004', 'Fixed 8', 1)
    stable = sum(g['diagnosis_consistency'] == 1 for g in archive.variation.values())
    variable = sum(g['trajectory_variants'] > 1 for g in archive.variation.values())
    groups = len(archive.variation)
    models = {r['run']['model_name'] for r in archive.rows.values()}
    if len(models) != 1:
        raise ArtifactError('Expected the same recorded model snapshot across replay strategies.')
    model = next(iter(models))

    def select(sid, strategy):
        reps = archive.repetitions(sid, strategy)
        return gr.Dropdown(choices=reps, value=reps[0], interactive=len(reps) > 1), *render_run(archive, sid, strategy, reps[0])

    def replay(sid, strategy, repetition):
        try:
            return render_run(archive, sid, strategy, repetition)
        except ArtifactError as exc:
            raise gr.Error(str(exc)) from exc

    with gr.Blocks(title='Agent Tool-Budget Lab', analytics_enabled=False) as ui:
        gr.Markdown('# Agent Tool-Budget Lab\n### Tracing how execution limits change agent reliability and efficiency.\n'
                    'Built with Microsoft Agent Framework and evaluated using Arize Phoenix.\n\n'
                    '**Stored replay** · No credentials or running Phoenix server needed. '
                    'Displayed latency and usage come from the recorded experiment, not this replay.')
        with gr.Tabs():
            with gr.Tab('Explore a trace'):
                with gr.Row():
                    scenario = gr.Dropdown(archive.scenario_choices(), value='diag_004', label='Scenario', scale=5)
                    strategy = gr.Dropdown(list(STRATEGIES), value='Fixed 8', label='Strategy', scale=2)
                    repetition = gr.Dropdown([1, 2, 3], value=1, label='Run / repetition', scale=1)
                gr.Markdown('Fixed 2/4 replay the earlier Phoenix sweep (one run). '
                            'Fixed 6/8/Adaptive replay the final comparison (three runs). '
                            'Use Strategy comparison for aggregate conclusions within the same study.')
                report = gr.Markdown(initial[0])
                trajectory = gr.Markdown(initial[1])
                final = gr.Markdown(initial[2])
                for control in (scenario, strategy):
                    control.input(select, [scenario, strategy], [repetition, report, trajectory, final], queue=False)
                repetition.input(replay, [scenario, strategy, repetition], [report, trajectory, final], queue=False)
            with gr.Tab('Strategy comparison'):
                gr.Markdown('## Final repeated comparison\n'
                            'Eight scenarios × three strategies × three repetitions = 72 runs. '
                            'Each column summarizes 24 runs from the same Phase 3 dataset. '
                            'Tokens and latency include all controller overhead.')
                gr.Dataframe(value=archive.comparison(), headers=['Metric', 'Fixed-6', 'Fixed-8', 'Adaptive'],
                             datatype=['str'] * 4, interactive=False, label='Verified final results')
                gr.Markdown(archive.findings())
                gr.Markdown('Fixed-8 is the reliability reference for this workload. Fixed-6 is a simpler '
                            'lower-cost option with reduced accuracy. These small synthetic experiments '
                            'do not establish a universal best tool budget.')
                with gr.Accordion('Phoenix experiment comparison screenshot', open=False):
                    gr.Image(value=str(Path(root) / 'results/screenshots/adaptive-comparison-metrics.png'),
                             label='Recorded Phoenix Metrics view', interactive=False)
                    gr.Markdown('The screenshot uses Fixed-6 as its visual baseline. The percentage changes '
                                'above compare Adaptive against Fixed-8.')
            with gr.Tab('Phoenix trace stories'):
                gr.Markdown('## Four traces worth inspecting\n'
                            'Replay the observations first, then inspect the evaluation and interpretation. '
                            'These are stored experiment records, not a live Phoenix connection.')
                story = gr.Dropdown([(title, i) for i, (title, _) in enumerate(STORY_NOTES)],
                                    value=0, label='Trace story')
                story_values = render_story(archive, 0)
                story_panels = [gr.Markdown(value) for value in story_values]
                story.input(lambda index: render_story(archive, index), story, story_panels, queue=False)
                gr.Markdown(f'## Outcome stability can hide trajectory instability\n'
                            f'The targeted repeatability study found stable diagnoses within all **{stable} of {groups} '
                            f'scenario/budget groups**, while **{variable} of {groups}** used varying tool trajectories. '
                            'Equivalent final labels can hide differences in evidence, calls, tokens, latency, and stopping. '
                            'This is why traces matter beyond final-answer accuracy.')
                with gr.Accordion('A recorded Phoenix stopping check', open=False):
                    gr.Image(value=str(Path(root) / 'results/screenshots/adaptive-stopping-check.png'),
                             label='Phoenix observed input and STOP reason', interactive=False)
            with gr.Tab('How the experiment works'):
                gr.Markdown(f'''## Research question
How does an agent's tool budget affect reliability and efficiency?

**Environment:** frontend, api, database, cache. Eight deterministic synthetic scenarios.

**Tools:** `check_status(component)`, `read_logs(component)`, `check_recent_change(component)`.

**Agent:** Microsoft Agent Framework. **Model snapshot:** `{model}`, temperature 0.

In the fixed-budget sweep, only the maximum function-call budget changed (2/4/6/8).
The model, prompt, scenarios, tools, output schema, and environment stayed fixed.
Parallel tool calls were disabled and an exact execution guard enforced the cap.
The later adaptive configuration added one STOP/CONTINUE check after each tool result,
using the same model and a hard ceiling of eight. Its prompt was frozen before results.

### Deterministic evaluation
- **Diagnosis correctness:** canonical or explicitly accepted label match.
- **Evidence completeness:** fraction of required evidence retrieved.
- **Evidence sufficiency:** all required evidence retrieved.
- **Premature stop:** investigation ends before evidence sufficiency.
- **Irrelevant investigation:** calls outside the required/supporting rubric.
- **Post-sufficiency calls:** investigation after the required set is complete.
- **Latency and tokens:** recorded execution time and model usage, with controller overhead shown separately.
- **False early stop:** an effective adaptive STOP before rubric sufficiency.

Evaluation-only root causes, evidence labels, and difficulty were hidden from both
the runtime agent and controller. Scoring happened afterward. No LLM judge was used.
Correctness and evidence sufficiency are separate: missing checklist evidence does
not prove a diagnosis was impossible.

### Why Phoenix mattered
A Python benchmark could have measured final accuracy. Phoenix added full model/tool
trajectory inspection, deterministic evaluations attached to experiments, and controlled
configuration comparison. It exposed evidence gaps, distinguished budget-forced and
voluntary stops, and traced every adaptive decision to its observed input. This made
it possible to diagnose why the controller stopped too early and why fewer diagnostic
calls did not reduce total system cost.

### Scope
This is one model on a small synthetic workload. Model trajectories varied even at
temperature 0, and live request conditions affect latency. No new experiment, policy,
model, or live inference is run by this demo.
''')
        gr.Markdown(f'[GitHub repository]({GITHUB}) · [README / methodology]({GITHUB}#readme) · '
                    f'[Detailed result report]({GITHUB}/blob/main/ADAPTIVE_RESULTS.md)\n\n'
                    'Phoenix was run locally for the experiments. '
                    'Reproduction instructions are available in the repository.')
    return ui


if __name__ == '__main__':
    build_app().launch(share=False, show_error=False)
