# Original Microsoft Gradio replay demo

**For free hosted deployment, use the [HTML/JavaScript Static Space](STATIC_DEMO.md).**
The original local Gradio app remains unchanged. The compute-Space instructions
below are optional and require the appropriate Hugging Face plan. Root README
metadata now targets the static page; a separate compute Space must use
`sdk: gradio`, `sdk_version: 6.28.0`, `python_version: "3.12"`, and `app_file: app.py`.

The static page now leads with the OpenClaw cross-harness follow-up; this original
Gradio app continues to present the Microsoft baseline only.

The Gradio demo reads committed experiment records. It makes no model requests,
loads no `.env` file, and needs neither Phoenix nor Microsoft Agent Framework.
Live mode is not implemented. Research code and measured artifacts are unchanged.

## Run locally

From the repository root, use Python 3.12 and a separate environment:

```bash
python3.12 -m venv .demo-venv
source .demo-venv/bin/activate
python -m pip install -r requirements-demo.txt
python app.py
```

Gradio prints the local URL (normally `http://127.0.0.1:7860`). Stop with Ctrl-C.
Keep the research `.venv` and `.phoenix-venv` separate. The demo's only direct
package dependency is `gradio==6.28.0`; pip installs its transitive dependencies.
The root `requirements.txt` delegates to this same file for Spaces.

## What to show in a panel

1. **Explore a trace:** select a scenario, strategy, and repetition. Read each
   tool result and adaptive decision before inspecting the final evaluation.
2. **Strategy comparison:** all 24 runs per strategy from the final comparison.
   Fewer tool calls increased total tokens and latency while accuracy fell.
3. **Phoenix trace stories:** budget-forced failure, supported Fixed-8 diagnosis,
   supported adaptive STOP, and false early STOP. The separate repeatability
   finding shows why stable answers do not guarantee stable trajectories.
4. **How the experiment works:** controls, hidden evaluation labels, model
   snapshot, deterministic rubric, and what Phoenix made diagnosable.

Evaluation annotations appear after the trajectory. Recorded latency is experiment
latency, not UI response time. Tokens include diagnostic agent and stopper usage.
No public Phoenix deployment is assumed; links lead to the GitHub repository.

## Artifact mapping

`demo/replay.py` reads the original JSON/JSONL directly; there is no second results
format. Paths resolve from the repository directory, independent of working directory.

| Input | Use |
|---|---|
| `data/scenarios.json` | Eight scenario IDs and user reports; evaluation labels are not shown in selectors |
| `results/phoenix-20260928T011340Z/runs.jsonl` | Fixed 2/4: 16 earlier sweep runs, one repetition |
| `results/phase3-comparison/runs.jsonl` | Fixed 6/8/Adaptive: all 72 final runs, three repetitions |
| `results/phase3-comparison/summary.json` | Exact final aggregate comparison and percentage changes |
| `results/phase3-comparison/demo-traces.json` | Curated final trace IDs; local trace URLs are not rendered |
| `results/phase3-variation/summary.json` | Ten repeatability groups, six with varying trajectories |

The explorer has 88 selectable records. Fixed 2/4 belong to an earlier batch;
the aggregate comparison uses only the final batch. The first curated story is
`diag_007`, Fixed 2, from the earlier sweep. The other three use the final archive's
curated trace IDs. The original pilot is described in the README, not replayed here.

Two existing images appear in optional accordions:

- `results/screenshots/adaptive-comparison-metrics.png`
- `results/screenshots/adaptive-stopping-check.png`

The first screenshot's visual baseline is Fixed-6; the main cost percentages compare
Adaptive with Fixed-8. Neither image is regenerated.

## Validation

Use the existing research environment for the full suite:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest tests/test_demo.py -q
```

The new tests use only the standard library and pytest. They check all 88 selections,
source-record equality, exact aggregate values, controller overhead, curated stories,
and readable errors for missing runs/artifacts. No experiment is run by these tests.

## Deploy to Hugging Face Spaces

No deployment has been performed. After reviewing and committing the demo:

1. Create a new Hugging Face Space and select **Gradio** and **CPU Basic**.
2. Upload the committed repository files to the Space, preserving directories.
   Include the root `README.md`, `requirements.txt`, `requirements-demo.txt`,
   `app.py`, `demo/`, and every artifact/image listed above. Uploading the committed
   repository also preserves the linked research documentation and checksums.
3. For a separate compute Space, replace the root README configuration with: `sdk: gradio`, `sdk_version: 6.28.0`,
   `python_version: "3.12"`, and `app_file: app.py`. No secrets are needed.
4. Let the Space build, then open every tab, replay an adaptive run, and expand both
   screenshot accordions. Confirm the final table matches `ADAPTIVE_RESULTS.md`.

Do not upload local `.env`, virtual environments, Phoenix databases, caches, or logs.
Missing artifacts produce a startup error naming the file to restore. Filenames and
paths preserve case for Linux. Local testing does not replace the first hosted build;
verify that build before sharing the public Space URL.

See Hugging Face's [Space configuration reference](https://huggingface.co/docs/hub/spaces-config-reference)
and [dependency instructions](https://huggingface.co/docs/hub/spaces-dependencies).

### Required Space files

Preserve this exact layout (14 files). `DEMO.md` and research reports are also
recommended when publishing the whole repository.

```text
README.md
app.py
requirements.txt
requirements-demo.txt
demo/__init__.py
demo/replay.py
data/scenarios.json
results/phoenix-20260928T011340Z/runs.jsonl
results/phase3-comparison/runs.jsonl
results/phase3-comparison/summary.json
results/phase3-comparison/demo-traces.json
results/phase3-variation/summary.json
results/screenshots/adaptive-comparison-metrics.png
results/screenshots/adaptive-stopping-check.png
```

### Manual Git upload

First review and commit the demo changes to your local project. Create the Space
through Hugging Face's website, then run the following **from this repository's
root**, replacing `YOUR_USERNAME`. Authenticate when Git prompts; do not put a
token in the URL. These commands upload your committed snapshot to the Space:

```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/agent-tool-budget-lab ../agent-tool-budget-lab-space
git archive HEAD | tar -x -C ../agent-tool-budget-lab-space
git -C ../agent-tool-budget-lab-space add .
git -C ../agent-tool-budget-lab-space commit -m "Add frozen experiment replay demo"
git -C ../agent-tool-budget-lab-space push
```

The separate clone preserves the Space's own Git history. `git archive` exports
only committed files, so ignored environments and `.env` are excluded. It also
means uncommitted demo changes will not be uploaded: commit them first.

Wait for the build to finish, open the public Space URL, and repeat the four-tab
smoke check above. Replace the README's live-demo placeholder with that verified
URL, then commit and upload the README update. Allow roughly 10–20 minutes for
manual deployment and verification; build queues and account setup can add time.
