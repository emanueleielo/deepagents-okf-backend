"""Knowledge surface + scratch space, with a structured OKF query tool.

The agent reads/curates an OKF bundle on ``/knowledge`` (durable, validated) while using an
ephemeral ``StateBackend`` for everything else, and can look documents up by frontmatter.

Run:  python examples/composite_knowledge.py
"""

from __future__ import annotations

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend

from deepagents_okf_backend import OKFBackend, make_okf_query_tool


def build_agent():  # type: ignore[no-untyped-def]
    okf = OKFBackend("./knowledge", validate=True, auto_timestamp=True)
    backend = CompositeBackend(
        routes={"/knowledge": okf},
        default=StateBackend(),
    )
    return create_deep_agent(
        tools=[make_okf_query_tool(okf)],
        instructions=(
            "Knowledge lives under /knowledge as an OKF bundle. "
            "Use okf_query to find tables/metrics before answering, and keep scratch notes "
            "elsewhere."
        ),
        backend=backend,
    )


if __name__ == "__main__":
    agent = build_agent()
    print("Agent ready with OKF knowledge surface on /knowledge")
