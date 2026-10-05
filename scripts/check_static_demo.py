"""Browser QA for the static replay. Requires Playwright; runs no experiments."""
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from demo.replay import Archive, STRATEGIES, final_markdown
from playwright.sync_api import sync_playwright, expect

url = os.environ.get('STATIC_DEMO_URL', 'http://127.0.0.1:8000/')
archive = Archive()
launch = {'headless': True}
if os.environ.get('CHROME_BINARY'):
    launch['executable_path'] = os.environ['CHROME_BINARY']

with sync_playwright() as p:
    browser = p.chromium.launch(**launch)
    page = browser.new_page(viewport={'width': 1440, 'height': 1000}, service_workers='block')
    errors, external = [], []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    page.on('request', lambda r: external.append(r.url) if not r.url.startswith(url) else None)
    page.goto(url)
    expect(page.locator('#demo')).to_be_visible()
    expect(page.locator('#tab-intro')).to_have_attribute('aria-selected', 'true')
    page.locator('#tab-baseline').click()
    count = 0
    for sid in archive.scenarios:
        page.locator('#scenario').select_option(sid)
        for strategy in STRATEGIES:
            page.locator('#strategy').select_option(strategy)
            reps = archive.repetitions(sid, strategy)
            assert page.locator('#repetition').is_disabled() == (len(reps) == 1)
            for rep in reps:
                if len(reps) > 1:
                    page.locator('#repetition').select_option(str(rep))
                row = archive.resolve(sid, strategy, rep)
                expected = [line.strip('|').strip().split(' | ') for line in final_markdown(row).splitlines()
                            if line.startswith('| ')][1:]
                expected.append(['Premature stop', 'Yes' if row['metrics']['premature_stop'] else 'No'])
                if row['run'].get('stopping_checks'):
                    expected.insert(9, expected.pop())
                actual = page.locator('#replay table tr').evaluate_all('(rows)=>rows.map(r=>Array.from(r.cells,c=>c.textContent))')
                assert actual == expected, (sid, strategy, rep, actual, expected)
                assert page.locator('#replay .step').count() == len(row['run']['tool_calls'])
                assert page.locator('#replay .check').count() == len(row['run'].get('stopping_checks', []))
                assert not page.locator('#replay .trajectory').get_by_text('Required evidence missing', exact=False).count()
                count += 1
    assert page.get_by_role('tab').all_text_contents() == ['Overview', 'OpenClaw Follow-Up', 'Cross-Harness Results', 'Explore OpenClaw Traces', 'What Phoenix Revealed', 'Microsoft Baseline', 'Challenges & Runtime Differences', 'Developer Learnings', 'Methodology / Reproducibility']
    page.locator('#tab-baseline').click()
    page.get_by_text('Eight actual user-reported symptoms', exact=True).click()
    for scenario in archive.scenarios.values():
        assert scenario['runtime']['user_report'] in page.locator('#scenario-examples').inner_text()
    for example in ('1', '2'):
        page.locator('#tab-challenges').click()
        assert page.locator('#challenges .challenge-card').count() == 3
        assert page.locator('#challenges table, #challenges img').count() == 0
        page.locator(f'#challenges [data-story="{example}"]').click()
        expect(page.locator('#tab-baseline')).to_have_attribute('aria-selected', 'true')
        expect(page.locator('#story')).to_have_value(example)
        expect(page.locator('#story')).to_be_focused()
    page.locator('#tab-learnings').click()
    assert page.locator('.learning-list > li').count() == 6
    page.locator('#tab-baseline').click()
    sweep = page.locator('#sweep-results tbody tr').evaluate_all('(rows)=>rows.map(r=>Array.from(r.cells,c=>c.textContent))')
    assert sweep == [['2','50.0%','25.0%','1.88','87.5%'],['4','62.5%','64.6%','3.75','62.5%'],['6','87.5%','82.3%','5.13','50.0%'],['8','100.0%','96.9%','5.75','12.5%']]
    actual = page.locator('#comparison tbody tr').evaluate_all('(rows)=>rows.map(r=>Array.from(r.cells,c=>c.textContent))')
    assert actual == archive.comparison()
    for value in ('32.4%', '10.4%', '48.7%', '16 of 24'):
        assert value in page.locator('#comparison').inner_text()
    page.get_by_text('Phoenix experiment comparison screenshot', exact=True).click()
    for image in page.locator('#compare img').all():
        image.evaluate('(img)=>{img.loading="eager";return img.decode()}')
    page.locator('#tab-baseline').click()
    for index in range(4):
        page.locator('#story').select_option(str(index))
        expect(page.locator('#story-replay').get_by_role('heading', name='Interpretation')).to_be_visible()
        if index == 2:
            assert page.locator('.trajectory-pair .report').count() == 2
            assert page.locator('.trajectory-pair').get_by_text('database_connection_regression', exact=True).count() == 2
            assert '75.0%' in page.locator('.trajectory-pair').inner_text()
            assert '100.0%' in page.locator('.trajectory-pair').inner_text()
        else:
            key = ('diag_007', 'Fixed 2', 1) if index == 0 else ('diag_008', 'Adaptive', 1) if index == 1 else archive.by_trace[archive.stories[3]['trace_id']]
            cause = archive.resolve(*key)['run']['final_diagnosis']['predicted_root_cause']
            assert cause in page.locator('#story-replay .result').inner_text()
            if index == 1:
                assert '66.7%' in page.locator('#story-replay .result').inner_text()
                assert 'Correct' in page.locator('#story-replay .result').inner_text()
        images = page.locator('#story-replay .phoenix-snapshots img')
        assert images.count() == (2 if index == 2 else 1)
        for image in images.all():
            image.evaluate('(img)=>{img.loading="eager";return img.decode()}')
    assert '6 of 10' in page.locator('#repeatability').inner_text()
    page.locator('#tab-method').click()
    page.locator('#method > details > summary').click()
    page.locator('#method img').evaluate('(img)=>{img.loading="eager";return img.decode()}')
    assert 'LIVE PHOENIX' not in page.locator('body').text_content()
    assert page.locator('#model').inner_text() == 'gpt-4.1-mini-2025-04-14'
    page.locator('#tab-method').focus()
    page.keyboard.press('Home')
    expect(page.locator('#tab-intro')).to_have_attribute('aria-selected', 'true')
    page.screenshot(path='/tmp/static-demo-desktop.png', full_page=False)
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.screenshot(path='/tmp/static-demo-mobile.png', full_page=False)
    page.locator('#tab-challenges').click()
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.screenshot(path='/tmp/static-challenges-mobile.png', full_page=True)
    assert not errors, errors
    assert not external, external
    print(f'PASS: {count} replays match Python metric tables; comparison, four stories, images, keyboard tabs, mobile, zero external requests.')
    # Fresh page: missing and malformed artifacts must produce a visible error.
    for content, status in [('missing', 404), ('{broken', 200)]:
        failure = browser.new_page(service_workers='block')
        failure.route('**/phase3-comparison/runs.jsonl', lambda route, request, body=content, code=status:
                      route.fulfill(status=code, body=body))
        failure.goto(url)
        expect(failure.locator('#status')).to_have_attribute('data-error', 'true')
        assert 'results/phase3-comparison/runs.jsonl' in failure.locator('#status').inner_text()
        expect(failure.locator('#demo')).to_be_hidden()
        failure.close()
    failure = browser.new_page(service_workers='block')
    failure.route('**/adaptive-comparison-metrics.png', lambda route: route.fulfill(status=404, body='missing'))
    failure.goto(url)
    expect(failure.locator('#demo')).to_be_visible()
    failure.locator('#tab-baseline').click()
    failure.get_by_text('Phoenix experiment comparison screenshot', exact=True).click()
    expect(failure.get_by_text('Screenshot unavailable.', exact=False)).to_be_visible()
    failure.close()
    failure = browser.new_page(service_workers='block')
    failure.route('**/budget-evals.png', lambda route: route.fulfill(status=404, body='missing'))
    failure.goto(url)
    expect(failure.locator('#demo')).to_be_visible()
    failure.locator('#tab-baseline').click()
    failure.locator('#story-replay img').scroll_into_view_if_needed()
    expect(failure.locator('#story-replay').get_by_text('Screenshot unavailable.', exact=False)).to_be_visible()
    print('PASS: missing data, malformed data, and static/dynamic missing screenshot handling.')
    # OpenClaw values are checked independently of the presentation formatter.
    import json
    from urllib.parse import urljoin, urlparse
    root = Path(__file__).resolve().parents[1]
    oc = json.loads((root/'static/openclaw.json').read_text())
    report = (root/'OPENCLAW_RESULTS.md').read_text()
    page.set_viewport_size({'width': 1440, 'height': 1000})
    page.locator('#tab-openclaw').click()
    rows = page.locator('#oc-results tbody tr').evaluate_all('(rows)=>rows.map(r=>Array.from(r.cells,c=>c.textContent))')
    assert rows == [['6','100%','73.3%','10%','90%','6.0'],['8','90%','96.7%','90%','10%','7.0']]
    costs = page.locator('#oc-cost tbody tr').evaluate_all('(rows)=>rows.map(r=>Array.from(r.cells,c=>c.textContent))')
    assert costs == [['6','3,977.9','754.8','4,732.7','18.63s','16.09s','34.73s'],['8','4,224.2','829.0','5,053.2','16.84s','13.62s','30.46s']]
    for r in oc['examples']:
        assert r['trace_id'] in report
        assert ' → '.join(r['sequence']) in report
        assert ', '.join(r['evidence']) in report
        assert f"Tokens: {r['tokens'][0]} diagnostic + {r['tokens'][1]} finalizer = {r['tokens'][2]} total" in report
    page.locator('#tab-octraces').click()
    for i,r in enumerate(oc['examples']):
        page.locator('#oc-selector').select_option(str(i))
        assert page.locator('#oc-replay .path-list code').all_text_contents()==r['sequence']
        assert r['trace_id'] in page.locator('#oc-replay').inner_text()
        assert r['missing'] in page.locator('#oc-replay').inner_text()
    for tab in page.get_by_role('tab').all():
        tab.click()
        expect(page.locator('#'+tab.get_attribute('aria-controls'))).to_be_visible()
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        page.set_viewport_size({'width':1440,'height':1000})
    for href in page.locator('a[href],link[href]').evaluate_all('(items)=>items.map(x=>x.getAttribute("href"))'):
        assert '127.0.0.1' not in href and '/Users/' not in href
        if not urlparse(href).scheme and not href.startswith('#'):
            assert page.request.get(urljoin(url,href)).ok, href
    assert not errors,errors
    assert not external,external
    # First successful load installs a static-only cache, then reload offline.
    offline=browser.new_context()
    cached=offline.new_page()
    offline_errors=[]
    cached.on('pageerror',lambda e:offline_errors.append(str(e)))
    cached.goto(url)
    expect(cached.locator('#demo')).to_be_visible()
    cached.evaluate("navigator.serviceWorker.ready")
    cached.wait_for_function('navigator.serviceWorker.controller !== null')
    offline.set_offline(True)
    cached.reload()
    expect(cached.locator('#demo')).to_be_visible()
    cached.locator('#tab-octraces').click()
    cached.locator('#oc-selector').select_option('2')
    assert oc['examples'][2]['trace_id'] in cached.locator('#oc-replay').inner_text()
    cached.locator('#tab-baseline').click()
    cached.locator('#story').select_option('2')
    for img in cached.locator('#story-replay img').all():
        img.evaluate('(img)=>{img.loading="eager";return img.decode()}')
    assert not offline_errors,offline_errors
    offline.close()
    print('PASS: OpenClaw tables, three report-verified traces, nine tabs, mobile, relative links, no backend/external requests, cached offline reload.')
    browser.close()
