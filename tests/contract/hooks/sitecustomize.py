"""Widen holder stdin writes so concurrent permit/cancel can interleave.

Loaded only when tests prepend this directory to PYTHONPATH. Python 3.13
makes ``BufferedWriter.write`` immutable, so this wraps ``subprocess.Popen``
stdin in the holder process instead.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path


class _SlowStdin:
    def __init__(self, real):
        self._real = real

    def write(self, data):
        blob = data if isinstance(data, (bytes, bytearray)) else b""
        if b'"outcome"' in blob and b'"jsonrpc"' in blob:
            time.sleep(0.05)
        return self._real.write(data)

    def __getattr__(self, name):
        return getattr(self._real, name)


if Path(sys.argv[0]).name == "kaola-acp-holder.py":
    _OrigPopen = subprocess.Popen

    class _Popen(_OrigPopen):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if self.stdin is not None:
                self.stdin = _SlowStdin(self.stdin)

    subprocess.Popen = _Popen  # type: ignore[misc]
