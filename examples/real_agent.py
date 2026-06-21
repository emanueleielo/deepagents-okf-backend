"""End-to-end smoke test: a real deep agent curating an OKF bundle via OKFBackend.

Builds a deep agent backed by ``OKFBackend`` and a Claude (Haiku) model, asks it to
author an OKF document, then verifies the file the agent wrote is a valid OKF doc.

Requires an Anthropic API key in the environment:

    export ANTHROPIC_API_KEY=sk-ant-...
    python examples/real_agent.py

(If `python-dotenv` is installed, a local `.env` is loaded automatically.)
"""

from __future__ import annotations

import os
import tempfile

from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic

from deepagents_okf_backend import OKFBackend, make_okf_query_tool

try:  # optional convenience, not required
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

MODEL = "claude-haiku-4-5"

SYSTEM_PROMPT = (
    "You curate an Open Knowledge Format (OKF) bundle. Every document is a markdown "
    "file with YAML frontmatter that MUST start with a `type` field, e.g.\n"
    "---\n"
    "type: BigQuery Table\n"
    "title: Orders\n"
    "tags: [sales]\n"
    "---\n"
    "# Schema\n"
    "...body...\n"
    "Always include the `type` field or the write will be rejected."
)

TASK = (
    "Create an OKF document at /tables/customers.md for a warehouse table named "
    "'customers' (type: 'BigQuery Table', tags: [sales, crm]) with a short schema of "
    "customer_id and email. Then list the files under /tables and confirm what you created."
)


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set — export it (or put it in a .env) and retry.")
        return 1

    root = tempfile.mkdtemp(prefix="okf-bundle-")
    backend = OKFBackend(root, validate=True, auto_timestamp=True)

    agent = create_deep_agent(
        model=ChatAnthropic(model=MODEL, temperature=0),
        tools=[make_okf_query_tool(backend)],
        system_prompt=SYSTEM_PROMPT,
        backend=backend,
    )

    print(f"Running deep agent ({MODEL}) on bundle: {root}\n")
    result = agent.invoke({"messages": [{"role": "user", "content": TASK}]})
    final = result["messages"][-1].content
    print("--- agent final message ---")
    print(final)

    # Verify the agent actually wrote a valid OKF doc through the backend.
    print("\n--- verification ---")
    ls = backend.ls("/tables")
    if ls.error or not ls.entries:
        print(f"❌ no files under /tables ({ls.error})")
        return 1
    doc_path = ls.entries[0]["path"]
    read = backend.read(doc_path)
    content = read.file_data["content"] if read.file_data else ""
    print(f"created: {doc_path}")
    print(content)

    hits = make_okf_query_tool(backend).invoke({"type": "BigQuery Table"})
    print("okf_query(type='BigQuery Table') ->", hits)

    ok = "type:" in content and doc_path.endswith(".md")
    print("\n✅ OKFBackend works with a real agent" if ok else "\n❌ doc is not valid OKF")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
