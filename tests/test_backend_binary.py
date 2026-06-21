from pathlib import Path

import pytest

from deepagents_okf_backend import OKFBackend


@pytest.fixture()
def backend(tmp_path: Path) -> OKFBackend:
    return OKFBackend(tmp_path)


def test_upload_then_download_roundtrip(backend: OKFBackend) -> None:
    [up] = backend.upload_files([("/assets/logo.png", b"\x89PNG\r\n")])
    assert up.error is None
    assert up.path == "/assets/logo.png"

    [down] = backend.download_files(["/assets/logo.png"])
    assert down.error is None
    assert down.content == b"\x89PNG\r\n"


def test_download_missing_file(backend: OKFBackend) -> None:
    [down] = backend.download_files(["/nope.bin"])
    assert down.error == "file_not_found"
    assert down.content is None


def test_upload_path_escape_blocked(backend: OKFBackend) -> None:
    [up] = backend.upload_files([("/../escape.bin", b"x")])
    assert up.error == "permission_denied"


async def test_async_upload_download(backend: OKFBackend) -> None:
    await backend.aupload_files([("/a/b.bin", b"data")])
    [down] = await backend.adownload_files(["/a/b.bin"])
    assert down.content == b"data"
