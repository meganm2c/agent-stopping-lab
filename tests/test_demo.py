"""Deterministic archive checks; no Gradio, provider, or Phoenix dependency."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from demo.replay import (Archive, ArtifactError, FINAL, ROOT, STRATEGIES, SUMMARY,
                         render_run, render_story, token_breakdown)


@pytest.fixture(scope='module')
def archive():
    return Archive()


def test_all_scenarios_strategies_and_repetitions_resolve(archive):
    assert len(archive.rows) == 88
    assert len(archive.scenario_choices()) == 8
    for sid, scenario in archive.scenarios.items():
        for strategy in STRATEGIES:
            reps = [1] if strategy in ('Fixed 2', 'Fixed 4') else [1, 2, 3]
            assert archive.repetitions(sid, strategy) == reps
            for rep in reps:
                row = archive.resolve(sid, strategy, rep)
                assert row['run']['user_report'] == scenario['runtime']['user_report']
                intro, trajectory, final = render_run(archive, sid, strategy, rep)
                assert 'Ordered trajectory' in trajectory
                assert 'Final result' in final
                assert 'Required evidence missing' not in trajectory
                assert 'Evaluation below' in final
                assert ('fixed-budget sweep' in intro) == (strategy in ('Fixed 2', 'Fixed 4'))


def test_final_rows_are_the_original_records(archive):
    rows = [json.loads(line) for line in (ROOT / FINAL).read_text().splitlines()]
    for row in rows:
        assert archive.resolve(*archive.by_trace[row['trace_id']]) == row
    copy = archive.resolve('diag_001', 'Adaptive', 1)
    copy['run']['user_report'] = 'changed'
    assert archive.resolve('diag_001', 'Adaptive', 1)['run']['user_report'] != 'changed'


def test_aggregates_match_archive_and_verified_values(archive):
    assert archive.summary == json.loads((ROOT / SUMMARY).read_text())['aggregates']
    assert archive.comparison() == [
        ['Accuracy', '87.5%', '100.0%', '79.2%'],
        ['Evidence completeness', '83.3%', '97.9%', '70.1%'],
        ['Evidence sufficiency', '54.2%', '91.7%', '33.3%'],
        ['Average tool calls', '4.96', '5.79', '3.92'],
        ['Total tokens/run', '3,047', '3,698', '4,083'],
        ['Seconds/run', '4.31', '4.85', '7.20'],
    ]
    for text in ('32.4%', '10.4%', '48.7%', '16 of 24'):
        assert text in archive.findings()


def test_adaptive_overhead_and_decision_order(archive):
    row = archive.resolve('diag_004', 'Adaptive', 1)
    run = row['run']
    agent, overhead, total = token_breakdown(row)
    assert overhead == sum(c['usage']['input_token_count'] + c['usage']['output_token_count']
                           for c in run['stopping_checks'])
    assert total == agent + overhead
    _, trajectory, final = render_run(archive, 'diag_004', 'Adaptive', 1)
    assert trajectory.count('Stopping check') == len(run['stopping_checks'])
    assert trajectory.index('Evidence returned') < trajectory.index('Stopping check')
    assert '| False early stop | Yes |' in final


def test_curated_stories_and_public_links(archive):
    for index in range(4):
        panels = render_story(archive, index)
        assert len(panels) == 4
        assert 'What Phoenix revealed' in panels[3]
        assert 'localhost' not in ''.join(panels)
    assert 'Fixed 2' in render_story(archive, 0)[0]
    assert '| Diagnosis | Incorrect |' in render_story(archive, 3)[2]


@pytest.mark.parametrize('selection', [('unknown', 'Fixed 8', 1), ('diag_001', 'unknown', 1),
                                      ('diag_001', 'Fixed 2', 3)])
def test_missing_run_is_readable(archive, selection):
    with pytest.raises(ArtifactError, match='Stored run not found'):
        archive.resolve(*selection)


def test_missing_artifact_is_readable(tmp_path):
    with pytest.raises(ArtifactError, match='Missing replay artifact: data/scenarios.json'):
        Archive(tmp_path)
