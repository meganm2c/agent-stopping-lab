# Offline tests and experiment reproduction

## Publication test suite

Use Python 3.11+ and Node `>=24.16.0 <25` or `>=26.1.0` on PATH
(Node 26.10.0 was used for validation). From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,phoenix]'
npm ci --prefix spikes --ignore-scripts --no-audit --no-fund
.venv/bin/python -m pytest -q tests \
  spikes/openclaw-followup/test_contract.py \
  spikes/openclaw-followup/test_recovery.py \
  spikes/openclaw-followup/test_finalization.py \
  spikes/openclaw-followup/test_study_analysis.py
npm test --prefix spikes
```

These tests need no API key, `.env`, Phoenix server, OpenClaw runtime install,
local runtime binary, or raw OpenClaw experiment artifacts. The small npm test
package pins Undici because the outbound guards wrap both Node fetch and
Undici fetch. Test requests use mocked transports and never contact a provider.
The Node bridge tests use the `.venv` created above.

Raw OpenClaw results, request payloads, traces and runtime state remain intentionally
ignored. Full raw runs are not required to verify the analysis logic. Historical
Microsoft snapshots already tracked by this repository remain available for its
existing replay tests; this change adds no raw experimental evidence.

## Reviewed fixture scope

- `fixtures/trace_contract.json`: eight synthetic Phoenix-shaped spans and a
  minimal run. Two deterministic `diag_001` observations plus one blocked call
  exercise tool accounting, parentage, evidence matching, model/runtime identity,
  latency, diagnosis and token invariants. IDs, timing, usage and model text are
  synthetic. Only fields read by the validators/schema/evaluators are retained.
- `fixtures/finalization.json`: synthetic final diagnosis, usage and timing.
  `offline_fixtures.py` constructs the required finalizer envelope in memory
  using the real freeze/assembly functions. There are no saved provider payloads.
  Mutation tests still reject changed frozen evidence and invalid JSON/citations.
- `../openclaw-feasibility/fixtures/contract.mjs`: synthetic request and response
  shapes for the original Node assertions. Guard and concurrent Python bridge
  tests still execute the real code with mocked network access.

Fixtures are test inputs, not evidence for the measured study. They contain no
credentials, machine paths, real provider identifiers or captured system prompts.
The analysis tests use a finalized synthetic row and controlled mutations to
check aggregation, cost separation, trajectory order, evidence sets and pairing.
The eleven deterministic evaluator scores are checked explicitly.

## Live reproduction is separate

Live runs require the Python environment above, the exact pinned
`openclaw@2026.9.7` package and lockfile in `../openclaw-feasibility`, a supported
Node runtime, a local `.env` with `OPENAI_API_KEY`, and the local Phoenix service
configured in `../../PHOENIX.md`. See `FEASIBILITY_REPORT.md` in that spike and
the six root `OPENCLAW_*.md` reports for the validated controls and caveats.

The historical execution adapter is preserved byte-for-byte to retain its
recorded contract hashes. Its live finalizer expects a locally created
`.runtime/node/bin/node` link. If intentionally setting up future live runs,
create that ignored link to your installed Node executable (do not commit it):

```sh
npm ci --prefix spikes/openclaw-feasibility --ignore-scripts --no-audit --no-fund
mkdir -p spikes/openclaw-feasibility/.runtime/node/bin
ln -s "$(command -v node)" spikes/openclaw-feasibility/.runtime/node/bin/node
```

Do not replace an existing runtime link or resume historical runs casually.
`run_validated_study.py` is the validated study runner;
`analyze_validated_study.py` analyzes its saved results without inference.
Both require the local experiment artifacts for resumption/reanalysis.
`verify_completed_study.py` is a historical audit entry point: it additionally
requires the original local preservation manifests and live Phoenix database.
It is not part of the portable offline suite. Older runners/analyzers document
prior validation stages and must not overwrite the final study reports.

Links into ignored OpenClaw results and localhost Phoenix pages in the research
reports refer to the original local archive, not public hosted evidence. Aggregate
findings and trace IDs are preserved in the Markdown reports; offline fixtures
cannot re-establish live ingestion or independently reproduce those measurements.
