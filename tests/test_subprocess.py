import sys

import pytest

from takopi.utils import subprocess as subprocess_utils


class _FakeProcess:
    def __init__(self, *, returncode: int | None = 0) -> None:
        self.returncode = returncode

    async def wait(self) -> int:
        self.returncode = 0 if self.returncode is None else self.returncode
        return self.returncode

    def terminate(self) -> None:
        self.returncode = -15

    def kill(self) -> None:
        self.returncode = -9


@pytest.mark.anyio
async def test_manage_subprocess_kills_when_terminate_times_out(
    monkeypatch,
) -> None:
    async def fake_wait_for_process(_proc, timeout: float) -> bool:
        _ = timeout
        return True

    monkeypatch.setattr(subprocess_utils, "wait_for_process", fake_wait_for_process)

    async with subprocess_utils.manage_subprocess(
        [
            sys.executable,
            "-c",
            "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(10)",
        ]
    ) as proc:
        assert proc.returncode is None

    assert proc.returncode is not None
    assert proc.returncode != 0


@pytest.mark.anyio
async def test_manage_subprocess_resolves_windows_bare_command(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_open_process(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        captured["kwargs"] = kwargs
        return _FakeProcess(returncode=0)

    monkeypatch.setattr(subprocess_utils.os, "name", "nt")
    monkeypatch.setattr(
        subprocess_utils.shutil,
        "which",
        lambda name: r"C:\Users\Administrator\AppData\Roaming\npm\codex.cmd"
        if name == "codex"
        else None,
    )
    monkeypatch.setattr(subprocess_utils.anyio, "open_process", fake_open_process)

    async with subprocess_utils.manage_subprocess(["codex", "--version"]):
        pass

    assert captured["cmd"] == [
        r"C:\Users\Administrator\AppData\Roaming\npm\codex.cmd",
        "--version",
    ]


@pytest.mark.anyio
async def test_manage_subprocess_leaves_explicit_windows_path_unchanged(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_open_process(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        captured["kwargs"] = kwargs
        return _FakeProcess(returncode=0)

    explicit = r"C:\tools\custom\codex"

    monkeypatch.setattr(subprocess_utils.os, "name", "nt")
    monkeypatch.setattr(
        subprocess_utils.shutil,
        "which",
        lambda _name: r"C:\Users\Administrator\AppData\Roaming\npm\codex.cmd",
    )
    monkeypatch.setattr(subprocess_utils.anyio, "open_process", fake_open_process)

    async with subprocess_utils.manage_subprocess([explicit, "--version"]):
        pass

    assert captured["cmd"] == [explicit, "--version"]


@pytest.mark.anyio
async def test_manage_subprocess_resolves_explicit_windows_extensionless_path(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_open_process(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        captured["kwargs"] = kwargs
        return _FakeProcess(returncode=0)

    explicit = r"C:\Users\Administrator\AppData\Roaming\npm\codex"

    monkeypatch.setattr(subprocess_utils.os, "name", "nt")
    monkeypatch.setattr(subprocess_utils.shutil, "which", lambda _name: None)
    monkeypatch.setattr(
        subprocess_utils.os.path,
        "isfile",
        lambda path: path == f"{explicit}.CMD",
    )
    monkeypatch.setattr(subprocess_utils.anyio, "open_process", fake_open_process)

    async with subprocess_utils.manage_subprocess([explicit, "--version"]):
        pass

    assert captured["cmd"] == [f"{explicit}.CMD", "--version"]
