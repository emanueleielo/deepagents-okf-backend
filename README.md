# deepagents-okf-backend

[![CI](https://github.com/emanueleielo/deepagents-okf-backend/actions/workflows/ci.yml/badge.svg)](https://github.com/emanueleielo/deepagents-okf-backend/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/deepagents-okf-backend.svg)](https://pypi.org/project/deepagents-okf-backend/)
[![Python](https://img.shields.io/pypi/pyversions/deepagents-okf-backend.svg)](https://pypi.org/project/deepagents-okf-backend/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

An **OKF-aware virtual filesystem backend** for [LangChain Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview).

It mounts an [Open Knowledge Format (OKF)](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)
bundle — *"a directory of markdown files with YAML frontmatter"* — as the agent's filesystem,
so a deep agent can **read, search, and curate** organizational knowledge while every write
stays a **valid OKF document**.

> 🧩 Community backend (not maintained by LangChain), built for the
> [`integrations/backends`](https://docs.langchain.com/oss/python/integrations/backends) list.

## Why

A deep agent's knowledge memory is usually either **ephemeral** (`StateBackend`) or **closed**
(`ContextHubBackend` → LangSmith Hub). OKF is the **open, vendor-neutral** alternative:
git-versionable markdown, human-readable, parseable by any agent or framework.

| | `StateBackend` | `StoreBackend` | `FilesystemBackend` | **`OKFBackend`** |
|---|---|---|---|---|
| Persists across threads | ❌ | ✅ | ✅ | ✅ |
| Human-readable on disk | ❌ | ❌ | ✅ | ✅ |
| Vendor-neutral / portable bundle | ❌ | ❌ | ➖ | ✅ |
| Structured frontmatter query | ❌ | ❌ | ❌ | ✅ |
| Validates writes as a shareable format | ❌ | ❌ | ❌ | ✅ |

What `OKFBackend` adds:

- **Open knowledge, no lock-in** — portable markdown bundles, not a proprietary store.
- **Semantic, not blind** — query by `type` / `tags` / `title`, not just `grep`.
- **Self-improving wiki** — the agent maintains the bundle; writes are validated as OKF.
- **Cross-agent sharing** — *"a bundle synthesized by one LLM can be queried by another."*
- **Sync + async**, path-sandboxed to the bundle root, fully typed (`py.typed`).

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

### Knowledge surface + scratch space (`CompositeBackend`)

Mount the OKF bundle on `/knowledge` and keep an ephemeral scratch filesystem on `/`:

```python
from deepagents.backends import CompositeBackend, StateBackend
from deepagents_okf_backend import OKFBackend

backend = CompositeBackend(
    routes={"/knowledge": OKFBackend("./knowledge")},
    default=StateBackend(),
)
```

### Structured query tool

The six standard filesystem tools only `grep` raw text. Give the agent a typed lookup over
OKF frontmatter:

```python
from deepagents import create_deep_agent
from deepagents_okf_backend import OKFBackend, make_okf_query_tool

backend = OKFBackend("./knowledge")
agent = create_deep_agent(
    tools=[make_okf_query_tool(backend)],   # okf_query(type=..., tags=..., title_contains=...)
    instructions="Use okf_query to find tables and metrics before answering.",
    backend=backend,
)
```

You can also call it directly:

```python
from deepagents_okf_backend import query_bundle

hits = query_bundle(backend, type="Metric", tags=["growth"])
```

## What is OKF?

Open Knowledge Format (Google Cloud, 2026) represents knowledge as a directory of markdown
files with YAML frontmatter. The only required field is `type`; `title`, `description`,
`resource`, `tags`, and `timestamp` are optional. See the
[announcement](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing).

```markdown
---
type: BigQuery Table
title: Orders
description: One row per completed customer order.
tags: [sales, revenue]
---
# Schema
| Column | Type | Description |
|--------|------|-------------|
| `order_id` | STRING | Globally unique order identifier. |
```

## Development

Contributions welcome — see [`CONTRIBUTING.md`](CONTRIBUTING.md).

```bash
pip install -e ".[dev]"
ruff check . && mypy src && pytest --cov=deepagents_okf_backend
```

## License

MIT © Emanuele Ielo
