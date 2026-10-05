# Static cross-harness replay

Entry point: `index.html`. Title: **When Should an Agent Stop? — Cross-Harness
Evaluation with OpenClaw + Phoenix**. The deployment is plain HTML/CSS/JS and
static assets; no Python backend, Gradio server, credentials, CDN or Phoenix
service is required. Python is only an optional local file server.

## Preview and restart

```sh
bash scripts/start_static_demo.sh
```

Open `http://127.0.0.1:8000/`. An optional port argument selects another port.
The launcher works from any working directory. Stop with Ctrl-C; run the same
command tomorrow to restart. All page content and assets are committed.
Use HTTP rather than `file://`, which restricts loading local JSON/modules.

## Page structure

1. Overview: research question, Microsoft origin, motivation for OpenClaw.
2. OpenClaw Follow-Up: 20 accepted runs, 21 attempts, evidence and full cost tables.
3. Cross-Harness Results: three reproduced patterns, one partially reproduced.
4. Explore OpenClaw Traces: three curated report-derived examples; budget-8 pair
   and budget-6 versus budget-8 cache-evidence comparison.
5. What Phoenix Revealed: deterministic evaluations alongside ordered traces.
6. Microsoft Baseline: original design, all 88 replay runs, phase-specific tables,
   four trace examples and original Phoenix screenshots.
7. Challenges & Runtime Differences: evidence quality, trajectory stability and
   validating execution equivalence.
8. Developer Learnings: six lessons for evaluating the full inference system.
9. Methodology / Reproducibility: scope/caveats and separate Microsoft methodology.

`static/openclaw.json` is a compact presentation extract from the committed
`OPENCLAW_RESULTS.md`, not raw experimental evidence or a provider transcript.
It preserves three trace IDs, exact ordered calls, evidence IDs and measured
metrics. No unseen run or screenshot is invented. The eleven evaluators computed
scores offline during research; this page only formats saved findings.
Raw OpenClaw results remain ignored. Original Microsoft replay data is already
tracked and is read unchanged through `static/archive.js`.

## Deployment output and assets

There is no build step. The repository root is the static output. Upload the
committed tree to a Hugging Face **Static HTML** Space. The root README metadata
sets `sdk: static` and `app_file: index.html`.

Required page files:

- `index.html`, `sw.js`, `static/` (including the five baseline PNG screenshots).
- `data/scenarios.json`.
- `results/phoenix-20260928T011340Z/{runs.jsonl,comparison.json}`.
- `results/phase3-comparison/{runs.jsonl,summary.json,demo-traces.json}`.
- `results/phase3-variation/{runs.jsonl,summary.json}`.
- `results/screenshots/adaptive-comparison-metrics.png`.
- `OPENCLAW_RESULTS.md`, `OPENCLAW_COMPARISON.md` and
  `spikes/openclaw-followup/TESTING.md` for the page's relative report links.
- `README.md` for the Space configuration.

Uploading the complete committed tree also preserves the reports' other relative
links. Do not upload `.env`, virtual environments, ignored results, runtime state,
node_modules, or databases. `app.py` and requirements files are not executed by
this static page. No build command or paid compute is required.

To publish manually, clone your existing/new Static Space separately, copy the
committed tree using `git archive HEAD`, review that clone's diff, commit and push
there. Authenticate through Git's credential flow; never embed tokens in URLs.
A push to GitHub alone does not deploy a Hugging Face Space. No Space URL is
configured in this repository.

## Offline behavior and cache updates

Initial load fetches only same-origin static files. No remote API calls occur.
`sw.js` caches the complete replay bundle on a supporting HTTPS host (or local
preview). Once installation completes, reload and all replay controls work with
network disabled. External GitHub links still need internet access. Hosts that
restrict service workers can serve the page normally but cannot guarantee an
offline reload. No cache contains secrets or live provider responses.

Bump the cache version in `sw.js` when publishing changed assets. A new worker
installs a complete cache before activation and removes only this app's old
versioned caches. For local edits without a version bump, unregister the worker
and clear this site's storage in browser developer tools before reloading.

## Validation

Run the publication Python/Node suite documented in
[OpenClaw TESTING](spikes/openclaw-followup/TESTING.md). Browser QA additionally
checks all 88 baseline replays, original comparison values, four baseline stories,
screenshots, three OpenClaw examples against the committed report, OpenClaw tables,
all nine tabs, keyboard navigation, mobile overflow, error states, relative assets,
zero external requests, and a cached reload with network disabled.

With the local server running, use a separate developer environment:

```sh
python3 -m venv /tmp/static-demo-qa
/tmp/static-demo-qa/bin/python -m pip install playwright
/tmp/static-demo-qa/bin/python -m playwright install chromium
/tmp/static-demo-qa/bin/python scripts/check_static_demo.py
```

`STATIC_DEMO_URL` selects another origin/subdirectory; `CHROME_BINARY` can select
an installed Chrome. Browser QA packages are not deployment dependencies.
