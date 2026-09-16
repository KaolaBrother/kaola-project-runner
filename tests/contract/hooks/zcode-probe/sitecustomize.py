"""Record adapter filesystem/network use. Loaded only via test PYTHONPATH."""

from __future__ import annotations

import builtins
import os
import socket

_LOG = os.environ.get("ZCODE_OPEN_LOG")
_REAL_OPEN = builtins.open
_REAL_OS_OPEN = os.open
_REAL_CONNECT = socket.socket.connect


def _note(entry: str) -> None:
    if not _LOG:
        return
    try:
        with _REAL_OPEN(_LOG, "a", encoding="utf-8") as handle:
            handle.write(entry + "\n")
    except OSError:
        return


def _open(file, *args, **kwargs):
    try:
        mode = kwargs.get("mode", args[0] if args else "r")
        _note(f"open:{file}:mode={mode}")
    except Exception:
        pass
    return _REAL_OPEN(file, *args, **kwargs)


def _os_open(path, *args, **kwargs):
    try:
        flags = kwargs.get("flags", args[0] if args else 0)
        writable = bool(int(flags) & (os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC))
        _note(f"os.open:{path}:mode={'w' if writable else 'r'}")
    except Exception:
        pass
    return _REAL_OS_OPEN(path, *args, **kwargs)


def _connect(self, address):
    try:
        _note(f"socket.connect:{address!r}")
    except Exception:
        pass
    return _REAL_CONNECT(self, address)


builtins.open = _open  # type: ignore[misc]
os.open = _os_open  # type: ignore[misc]
socket.socket.connect = _connect  # type: ignore[misc]
