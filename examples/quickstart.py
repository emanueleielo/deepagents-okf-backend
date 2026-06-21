"""Minimal example: mount an OKF bundle as a deep agent's filesystem.

Run:  python examples/quickstart.py
(Requires `pip install deepagents-okf-backend` and a model configured for deepagents.)
"""

from __future__ import annotations

from deepagents_okf_backend import OKFBackend


def main() -> None:
    backend = OKFBackend("./knowledge", validate=True, auto_timestamp=True)

    # Write a valid OKF document directly through the backend.
    doc = """---
type: BigQuery Table
title: Orders
description: One row per completed customer order.
tags: [sales, revenue]
---
# Schema
| Column | Type | Description |
|--------|------|-------------|
| `order_id` | STRING | Globally unique order identifier. |
"""
    result = backend.write("/tables/orders.md", doc)
    print("write ->", result)

    print("read ->", backend.read("/tables/orders.md").file_data["content"][:60], "...")
    print("grep ->", backend.grep("revenue"))

    # An invalid OKF doc (no `type`) is rejected without touching disk.
    bad = backend.write("/tables/broken.md", "# no frontmatter here")
    print("invalid write ->", bad.error)


if __name__ == "__main__":
    main()
