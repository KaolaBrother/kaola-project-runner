"""Shared ACP record/socket paths; no caller-TMPDIR identity (#278).

Legacy discovery is bounded by known OS roots and one same-UID process table,
not a filesystem walk. Explicit record roots retain their scoped reader view;
Host uniqueness also includes the other live holder roots.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


class RecordRootMismatch(RuntimeError):
    pass


def default_root() -> Path:
    return Path('/tmp') / f'kaola-{os.getuid()}'


def record_root(explicit: str | Path | None = None) -> Path:
    return Path(explicit or os.environ.get('KAOLA_ACP_RECORD_ROOT') or default_root())


def live(pid) -> bool:
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except ProcessLookupError:
        return False


def read_record(directory: Path) -> dict | None:
    try:
        record = json.loads((directory / 'record.json').read_text(encoding='utf-8'))
        return record if isinstance(record, dict) else None
    except (OSError, ValueError):
        return None


def roots(explicit: str | Path | None = None, *, all_roots: bool = False
          ) -> tuple[list[Path], bool]:
    override = explicit or os.environ.get('KAOLA_ACP_RECORD_ROOT')
    candidates = [record_root(explicit)]
    if override and not all_roots:
        return candidates, True
    candidates.append(default_root())
    bases = ['/tmp', '/var/tmp', f'/run/user/{os.getuid()}', tempfile.gettempdir(),
             os.environ.get('TMPDIR'), os.environ.get('XDG_RUNTIME_DIR')]
    # Unlike gettempdir(), the macOS native login root is independent of TMPDIR.
    try:
        bases.append(os.confstr('CS_DARWIN_USER_TEMP_DIR'))
    except (ValueError, OSError):
        pass
    candidates.extend(Path(base) / f'kaola-{os.getuid()}' for base in bases if base)
    complete = True
    try:
        table = subprocess.run(['ps', '-axo', 'uid=,pid=,command='],
                               capture_output=True, text=True, timeout=3,
                               env=dict(os.environ, LC_ALL='C'))
        complete = table.returncode == 0
        for line in table.stdout.splitlines() if complete else []:
            fields = line.strip().split(None, 2)
            if (len(fields) != 3 or fields[0] != str(os.getuid())
                    or 'kaola-acp-holder.py' not in fields[2]):
                continue
            # Same ordered argv anchors as the runner; permits spaces in roots.
            match = re.search(r' --record-dir (.+?) --socket ', ' ' + fields[2])
            if match:
                directory = Path(match.group(1))
                record = read_record(directory)
                if record and record.get('holder_pid') == int(fields[1]):
                    candidates.append(directory.parent.parent.parent)
    except (OSError, subprocess.TimeoutExpired):
        complete = False
    # Resolve aliases for deduplication, preserve the original spelling (socket hash).
    unique = {}
    for root in candidates:
        unique.setdefault(os.path.realpath(root), root)
    return list(unique.values()), complete


def directories(platform: str, session: str, repo: str,
                explicit: str | Path | None = None) -> tuple[list[Path], bool]:
    candidates, complete = roots(explicit)
    digest = hashlib.sha256(repo.encode('utf-8')).hexdigest()[:16]
    return [root / platform / session / digest for root in candidates], complete


def find_directory(platform: str, session: str, repo: str,
                   explicit: str | Path | None = None) -> Path:
    candidates, complete = directories(platform, session, repo, explicit)
    recorded, alive = [], []
    for directory in candidates:
        record = read_record(directory)
        if record is None:
            continue
        recorded.append(directory)
        if live(record.get('holder_pid')):
            alive.append(directory)
    if len(alive) > 1:
        raise RecordRootMismatch('multiple live records for this exact session: '
                                 + ', '.join(str(p) for p in alive))
    if alive:
        return alive[0]
    if not complete:
        raise RecordRootMismatch('legacy holder roots could not be enumerated; retry from '
                                 'a shell with process visibility or set --record-root (Runner) or '
                                 'KAOLA_ACP_RECORD_ROOT from the original Runner receipt')
    return recorded[0] if recorded else candidates[0]


def record_paths(pattern: str, explicit: str | Path | None = None,
                 *, all_roots: bool = False) -> list[Path]:
    candidates, complete = roots(explicit, all_roots=all_roots)
    if not complete:
        raise RecordRootMismatch('legacy holder roots could not be enumerated; retry from '
                                 'a shell with process visibility; no absence is established')
    return sorted(path for root in candidates for path in root.glob(pattern))


def socket_path(directory: Path) -> Path:
    # Read the holder's applied path, never rederive an old socket using caller TMPDIR.
    record = read_record(directory) or {}
    path = record.get('socket_path')
    if isinstance(path, str) and os.path.isabs(path):
        return Path(path)
    link = directory / 'holder.sock'
    if link.is_symlink():
        target = link.readlink()
        return target if target.is_absolute() else link.parent / target
    digest = hashlib.sha256(str(directory).encode('utf-8')).hexdigest()[:24]
    return Path('/tmp') / f'kaola-{os.getuid()}-acp' / f'{digest}.sock'
