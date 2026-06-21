import os
from pathlib import Path

import pytest

from deepagents_okf_backend import OKFBackend


@pytest.fixture()
def backend(tmp_path: Path) -> OKFBackend:
    return OKFBackend(tmp_path / "bundle")


def test_path_traversal_blocked(backend: OKFBackend) -> None:
    assert backend.read("/../../etc/passwd").error is not None
    assert backend.write("/../escape.md", "---\ntype: X\n---\n").error is not None
    assert backend.ls("/..").error is not None


def test_nul_byte_path_rejected(backend: OKFBackend) -> None:
    assert backend.read("/a\x00b.md").error is not None


def test_symlink_escaping_root_is_not_leaked(tmp_path: Path) -> None:
    secret = tmp_path / "secret.txt"
    secret.write_text("TOPSECRET")
    bundle = tmp_path / "bundle"
    be = OKFBackend(bundle)
    os.symlink(secret, bundle / "leak.txt")  # symlink inside root -> outside

    # ls must skip the escaping symlink
    ls = be.ls("/")
    assert ls.error is None
    assert all(e["path"] != "/leak.txt" for e in (ls.entries or []))

    # glob must not return it
    assert all("leak" not in m["path"] for m in (be.glob("*").matches or []))

    # grep must never read its contents
    assert (be.grep("TOPSECRET").matches or []) == []


def test_symlink_inside_root_is_allowed(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    be = OKFBackend(bundle)
    (bundle / "real").mkdir()
    (bundle / "real" / "a.txt").write_text("hello inside")
    os.symlink(bundle / "real", bundle / "link")  # contained symlink

    assert be.grep("hello inside").matches  # content still reachable
