# Reproducing and reviewing this repository

The published snapshot preserves the completed research. Repository cleanup did
not rerun experiments, change the policy, rescore results, or edit observations.

## Offline review

Start with [README.md](README.md), [ADAPTIVE_RESULTS.md](ADAPTIVE_RESULTS.md), and
[the archived result inventory](results/README.md). Raw task/evaluation exports,
trace exports, summaries, and selected screenshots are included. No API key or
Phoenix database is needed to read them.

Verify the archived result bytes from the repository root:

```bash
shasum -a 256 -c results/SHA256SUMS
```

## Python environment and tests

The research used Python 3.12.12. Dependency snapshots capture the installed
versions without local paths, credentials, or private package URLs. They are
version pins, not cross-platform wheel/hash lockfiles.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-agent-lock.txt
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m pytest -q
```

The existing `pyproject.toml` also supports the smaller normal installation:
`pip install -e '.[dev,phoenix]'`. The snapshot additionally pins transitive
packages to the versions used for the completed experiments. Neither command runs
live experiments. Tests use scripted model responses and require no credentials.

## Phoenix and live execution

[PHOENIX.md](PHOENIX.md) documents server startup and experiment commands. For the
captured server environment:

```bash
python3.12 -m venv .phoenix-venv
.phoenix-venv/bin/python -m pip install -r requirements-phoenix-lock.txt
bash scripts/start_phoenix.sh
```

The local `.phoenix/` database is intentionally excluded. A new server starts
empty. The localhost trace links and IDs in historical reports refer to the
original local server; static trace exports and screenshots remain available in
the repository. Installing Phoenix does not restore that original database.

Live reruns require a private `.env` copied from `.env.example`, an OpenAI key,
and `MODEL_NAME=gpt-4.1-mini-2025-04-14` with temperature 0. They incur API usage
and may produce different trajectories. Keep the published results as the
historical reference and use a separate checkout when intentionally rerunning.

The Phase 3 runner checks the original dataset ID/version and hashes from the
archived Phase 2 manifest. On a fresh Phoenix instance, create the Phase 2 dataset
first and check the resulting IDs; historical IDs are not portable between
servers. The runner will refuse mismatches. No automatic migration or new live
run was added during repository cleanup.

See [ADAPTIVE_DESIGN.md](ADAPTIVE_DESIGN.md) for the documented Phoenix
span-annotation compatibility workaround. The original policy and criteria are
in [ADAPTIVE_HYPOTHESIS.md](ADAPTIVE_HYPOTHESIS.md).

## Publication boundaries

`.gitignore` allows only the reviewed result directories/files and screenshots.
New result directories, logs, failed-attempt exports, discovery/debug output,
removed duplicate span annotations, environments, caches, credentials, and Phoenix
state remain local. Earlier reports describe results as ignored; this publication
step adds the explicit archive allowlist without changing those historical reports.

`.env` and `.env.*` are ignored, with `.env.example` explicitly allowed. The
example contains empty credential fields. Never force-add private environment
files or the Phoenix database. The repository contains no Git history before this
initial publication, so there are no previous committed secrets to rewrite.
