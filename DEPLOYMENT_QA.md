# Deployment QA — 2026-09-30

## Local validation

- All **88 replay selections** passed browser checks: eight scenarios, five
  strategies, all available repetitions. Fixed/adaptive trajectories and final
  results rendered without browser errors.
- All final comparison cells match the stored Phase 3 aggregates. Adaptive changes
  remain −32.4% calls, +10.4% tokens, +48.7% latency, and 16/24 insufficient stops.
- Four Phoenix stories, both screenshot accordions, and methodology rendered.
- No raw trajectory JSON, machine paths, or public links to local Phoenix appeared
  in the rendered panels. Gradio serves screenshot assets from its own host.
- A missing artifact raises a readable `ArtifactError` naming the relative file
  and asking for the committed artifact to be restored; startup fails rather than
  presenting an incomplete experiment.
- **41 tests passed, 0 failed:** 32 existing tests and nine demo loader tests.
- No UI defects were found that required application changes in this QA pass.

## Clean-environment startup

A fresh Python 3.12 environment installed the root `requirements.txt` successfully;
`pip check` found no broken requirements. The exact 14-file Space bundle started
from a different working directory with an empty environment apart from PATH and
Gradio settings. No `.env` file or provider credentials were present. OpenAI,
Phoenix, and Microsoft Agent Framework packages were absent. Browser checks passed
for strategy/repetition changes, all four stories, screenshots, and methodology.

All six final aggregate metrics were independently recomputed from each group of
24 stored records and matched the committed summary. This was a read-only check
of existing records, not a new experiment.

## Security and links

- No credential matches found in publishable files or **263 reachable Git-history
  blobs across three commits**, including saved trace records. Checks included
  known local credential values, provider/token patterns, private keys, bearer
  tokens, and literal credential assignments. Values were never printed.
- OCR scanning of **all 11 committed screenshots** found no credential matches.
  Pattern matching and OCR cannot prove the absence of every possible secret.
- `.env` is ignored and absent from reachable Git history. Credential fields in
  `.env.example` are empty placeholders.
- No machine-specific absolute paths were found in public Markdown documents.
  Historical local Phoenix trace URLs remain in frozen artifacts; the public UI
  does not render them as external links.
- All **23 README/demo relative links** checked resolve locally. The public GitHub
  repository, README, and `ADAPTIVE_RESULTS.md` returned HTTP 200 without login.

## Deployment boundary

Gradio remains pinned to **6.28.0**, isolated from research/Phoenix environments.
README metadata follows the current Hugging Face Spaces configuration reference.
No live mode exists, and no experiment or inference request was run during QA.

See [DEMO.md](DEMO.md) for the exact 14-file deployment layout and manual Git
commands. The README contains a live-demo placeholder, not an invented Space URL.
No deployment or push was performed.

A first hosted Linux build and public-URL smoke check are still required. The local
QA host is macOS. Transitive dependencies are resolved by pip rather than fully
locked, so future resolver changes remain a reproducibility risk. Missing uploaded
artifacts and directory-case changes are the main packaging risks.
