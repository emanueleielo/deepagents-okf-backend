# Contributing

Thanks for helping improve `deepagents-okf-backend`!

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Checks (must pass before a PR)

```bash
ruff check .
mypy src
pytest
```

## Guidelines

- **Never raise from backend methods.** Return the appropriate result type with `error` set
  (this is the `BackendProtocol` contract).
- Keep `frontmatter.py` and `okf.py` free of `deepagents` imports — they are pure helpers and
  the bulk of the test coverage lives there.
- Add/extend tests under `tests/` for any behavior change; keep the sample bundle in
  `tests/fixtures/sample_bundle/` a **valid** OKF bundle.
- Match the existing code style; imports go at the top of the file.

## Releasing

1. Bump `version` in `pyproject.toml` and update `CHANGELOG.md`.
2. Tag `vX.Y.Z`, push, let CI build.
3. Publish to PyPI, create a GitHub release.
4. Open a PR to the LangChain docs repo adding a row to the `integrations/backends` table.
