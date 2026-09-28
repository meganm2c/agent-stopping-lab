# Reviewed research artifacts

These existing outputs are preserved byte-for-byte for independent inspection.
`SHA256SUMS` records every included JSON/JSONL/PNG artifact; run its check from the
repository root. No model execution or rescoring occurred during publication cleanup.

| Artifact | Contents |
|---|---|
| `live-pilot.jsonl`, `live-pilot.summary.json` | Original 32-run pilot and aggregates |
| `pilot-rescored-v2.jsonl` | Previously computed rubric-v2 comparison |
| `easy-live.json`, `hard-comparison.jsonl`, `experiment-manifest.json` | Supporting pilot artifacts linked from the report |
| `phoenix-20260928T011340Z/` | Completed Phase 2 experiments, evaluations, summary, and fetched traces |
| `phoenix-repeatability/` | Original optional 36-run repeatability check |
| `phase3-variation/` | 50 targeted runs, 550 evaluations, summaries, and trace exports |
| `phase3-comparison/` | 72 final runs, 1,368 evaluations, summaries, and trace exports |
| `phase3-frozen-policy.json` | Frozen prompt, schemas, and hypothesis fingerprint |
| `phase3-controls-before.json`, `phase3-tool-json-schemas.json` | Pre-change integrity records used in validation |
| `screenshots/` | Reviewed Phoenix views supporting the reports |

Ignored local files are retained on the original machine: logs, partial/failed
experiments, discovery/debug probes, duplicate annotation backups, and unused
screenshots. They are not required to inspect the completed results.

The local Phoenix database is not part of the archive. Historical localhost URLs
work on the original server; use the exported traces/screenshots elsewhere.
