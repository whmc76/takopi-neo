from __future__ import annotations

import os
import shutil
import signal
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager
from typing import Any

import anyio
from anyio.abc import Process

from ..logging import get_logger

logger = get_logger(__name__)


def _windows_pathext() -> tuple[str, ...]:
    pathext = os.environ.get("PATHEXT")
    if not pathext:
        return (".COM", ".EXE", ".BAT", ".CMD")
    exts: list[str] = []
    for item in pathext.split(os.pathsep):
        ext = item.strip()
        if not ext:
            continue
        exts.append(ext if ext.startswith(".") else f".{ext}")
    return tuple(exts) or (".COM", ".EXE", ".BAT", ".CMD")


def _resolve_windows_program(program: str) -> str:
    if os.name != "nt" or not program:
        return program

    if not os.path.dirname(program):
        match = shutil.which(program)
        if match:
            return match
        return program

    _base, ext = os.path.splitext(program)
    if ext:
        return program

    for suffix in _windows_pathext():
        candidate = f"{program}{suffix}"
        if os.path.isfile(candidate):
            return candidate
    return program


def _resolve_windows_command(cmd: Sequence[str]) -> list[str]:
    """Resolve bare command names to PATHEXT-backed executables on Windows.

    npm-installed CLIs often create both an extensionless shim and a `.cmd` file.
    `CreateProcess()` may try the extensionless shim first and fail with
    `WinError 5` even though the `.cmd` entry works. Resolving through
    `shutil.which()` ensures we use the actual launchable target.
    """
    resolved = list(cmd)
    if os.name != "nt" or not resolved:
        return resolved

    resolved[0] = _resolve_windows_program(resolved[0])
    return resolved


async def wait_for_process(proc: Process, timeout: float) -> bool:
    with anyio.move_on_after(timeout) as scope:
        await proc.wait()
    return scope.cancel_called


def terminate_process(proc: Process) -> None:
    _signal_process(
        proc,
        signal.SIGTERM,
        fallback=proc.terminate,
        log_event="subprocess.terminate.failed",
    )


def kill_process(proc: Process) -> None:
    _signal_process(
        proc,
        getattr(signal, "SIGKILL", signal.SIGTERM),
        fallback=proc.kill,
        log_event="subprocess.kill.failed",
    )


def _signal_process(
    proc: Process,
    sig: signal.Signals,
    *,
    fallback: Callable[[], None],
    log_event: str,
) -> None:
    if proc.returncode is not None:
        return
    if os.name == "posix" and proc.pid is not None:
        try:
            os.killpg(proc.pid, sig)
            return
        except ProcessLookupError:
            return
        except OSError as exc:
            logger.debug(
                log_event,
                error=str(exc),
                error_type=exc.__class__.__name__,
                pid=proc.pid,
            )
    try:
        fallback()
    except ProcessLookupError:
        return


@asynccontextmanager
async def manage_subprocess(
    cmd: Sequence[str], **kwargs: Any
) -> AsyncIterator[Process]:
    """Ensure subprocesses receive SIGTERM, then SIGKILL after a 2s timeout."""
    cmd = _resolve_windows_command(cmd)
    if os.name == "posix":
        kwargs.setdefault("start_new_session", True)
    proc = await anyio.open_process(cmd, **kwargs)
    try:
        yield proc
    finally:
        if proc.returncode is None:
            with anyio.CancelScope(shield=True):
                terminate_process(proc)
                timed_out = await wait_for_process(proc, timeout=2.0)
                if timed_out:
                    kill_process(proc)
                    await proc.wait()
