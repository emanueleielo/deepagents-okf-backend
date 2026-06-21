# deepagents-okf-backend

[![CI](https://github.com/emanueleielo/deepagents-okf-backend/actions/workflows/ci.yml/badge.svg)](https://github.com/emanueleielo/deepagents-okf-backend/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An **OKF-aware virtual filesystem backend** for [LangChain Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview).

It mounts an [Open Knowledge Format (OKF)](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)
bundle — *"a directory of markdown files with YAML frontmatter"* — as the agent's filesystem,
so a deep agent can **read, search, and curate** organizational knowledge while every write
stays a **valid OKF document**.

> Community backend, not maintained by LangChain. Intended for the
> [`integrations/backends`](https://docs.langchain.com/oss/python/integrations/backends) list.

## Why

A deep agent's knowledge memory is usually either **ephemeral** (`StateBackend`) or **closed**
(`ContextHubBackend` → LangSmith Hub). OKF is the **open, vendor-neutral** alternative:
git-versionable markdown, human-readable, parseable by any agent or framework.

`OKFBackend` gives you:

- **Open knowledge, no lock-in** — portable markdown bundles instead of a proprietary store.
- **Semantic, not blind** — frontmatter (`type`, `tags`, `timestamp`) is queryable.
- **Graph navigation** — OKF cross-links are followable like a knowledge graph.
- **Self-improving wiki** — the agent maintains the bundle; writes are validated as OKF.
- **Cross-agent sharing** — *"a bundle synthesized by one LLM can be queried by another."*

## Install

```bash
pip install deepagents-okf-backend
```

## Quickstart

```python
from deepagents import create_deep_agent
from deepagents_okf_backend import OKFBackend

backend = OKFBackend("./knowledge", validate=True, auto_timestamp=True)

agent = create_deep_agent(
    tools=[],
    instructions="You curate the organization's OKF knowledge bundle.",
    backend=backend,
)
```

Use it as a read-only **knowledge surface** alongside a scratch filesystem with `CompositeBackend`:

```python
from deepagents.backends import CompositeBackend, StateBackend
from deepagents_okf_backend import OKFBackend

backend = CompositeBackend(
    routes={"/knowledge": OKFBackend("./knowledge")},
    default=StateBackend(),
)
```

## What is OKF?

Open Knowledge Format (Google Cloud, 2026) represents knowledge as a directory of markdown
files with YAML frontmatter. The only required field is `type`; `title`, `description`,
`resource`, `tags`, and `timestamp` are optional. See the
[announcement](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing).

## Development

See [`DEVELOPMENT_PLAN.md`](DEVELOPMENT_PLAN.md). Contributions welcome — see [`CONTRIBUTING.md`](CONTRIBUTING.md).

```bash
pip install -e ".[dev]"
ruff check . && mypy src && pytest
```

## License

MIT © Emanuele Ielo
