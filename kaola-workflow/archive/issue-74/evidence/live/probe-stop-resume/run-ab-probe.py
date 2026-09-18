#!/usr/bin/env python3
"""A/B: backend session/close vs process-exit-only on the isolation workspace.

Does not start a production Runner Host. Same entry/node/env as the adapter child.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
import time
from pathlib import Path

ISO = Path("/Volumes/WorkspaceA/ylminiserver/workspace/kaola-i74-iso-ab")
ENTRY = ISO / ".zcode-runtime" / "zcode.cjs"
NODE = Path("/opt/homebrew/bin/node")
OUT = Path(__file__).resolve().parent
WORKSPACE = str(ISO)
WS = {"workspacePath": WORKSPACE, "workspaceKey": WORKSPACE}


class Backend:
    def __init__(self, label: str) -> None:
        allow = (
            "HOME", "PATH", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE", "USER",
            "LOGNAME", "SHELL", "TZ", "TERM",
        )
        env = {k: os.environ[k] for k in allow if k in os.environ}
        env["ELECTRON_RUN_AS_NODE"] = "1"
        self.err_path = OUT / f"appserver-{label}.err"
        self.proc = subprocess.Popen(
            [str(NODE), str(ENTRY), "app-server", "--stdio"],
            cwd=str(ISO),
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=open(self.err_path, "ab"),
            start_new_session=True,
        )
        self._next = 0
        self._pending: dict[int, dict] = {}
        self._lock = threading.Lock()
        self.ready = threading.Event()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        assert self.proc.stdout is not None
        for raw in self.proc.stdout:
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            method = msg.get("method")
            if method == "startup/storageState" and (msg.get("params") or {}).get("phase") == "ready":
                self.ready.set()
            if method and "id" in msg:
                if method == "session/requestRuntimePreferences":
                    self._write({"id": msg["id"], "result": {
                        "nativeSearchEnhancementsEnabled": True,
                        "memoryEnabled": False,
                        "askUserQuestionAutoResolutionEnabled": True,
                        "modelContextBudgetStrategy": "preflight-v1",
                    }})
                else:
                    self._write({"id": msg["id"], "result": {}})
                continue
            rid = msg.get("id")
            with self._lock:
                slot = self._pending.pop(rid, None) if rid is not None else None
            if slot is not None:
                slot["msg"] = msg
                slot["event"].set()

    def _write(self, msg: dict) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write((json.dumps(msg) + "\n").encode())
        self.proc.stdin.flush()

    def call(self, method: str, params: dict, timeout: float = 20.0) -> dict:
        with self._lock:
            self._next += 1
            rid = self._next
            slot = {"event": threading.Event()}
            self._pending[rid] = slot
        self._write({"id": rid, "method": method, "params": params})
        if not slot["event"].wait(timeout):
            raise TimeoutError(method)
        return slot["msg"]

    def kill_without_close(self) -> None:
        proc = self.proc
        if proc.poll() is not None:
            return
        try:
            if proc.stdin:
                proc.stdin.close()
        except OSError:
            pass
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            try:
                proc.terminate()
            except OSError:
                pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
            proc.wait(timeout=2)


def native_id(create_msg: dict) -> str | None:
    return ((create_msg.get("result") or {}).get("session") or {}).get("sessionId")


def listed_ids(list_msg: dict) -> list[str]:
    sessions = (list_msg.get("result") or {}).get("sessions") or []
    return [str(s.get("sessionId") or "") for s in sessions if isinstance(s, dict)]


def dump(name: str, payload: object) -> None:
    path = OUT / name
    if isinstance(payload, (dict, list)):
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        path.write_text(str(payload), encoding="utf-8")


def main() -> int:
    summary: dict = {"workspace": WORKSPACE}
    # Leg A: create + session/close + fresh list
    a = Backend("a")
    try:
        if not a.ready.wait(10):
            dump("00-summary.json", {"error": "A not ready"})
            return 1
        created = a.call("session/create", {"workspace": WS, "mode": "yolo"})
        dump("a-01-create.json", created)
        sid_a = native_id(created)
        listed = a.call("session/list", {"workspace": WS})
        dump("a-02-list-before-close.json", listed)
        closed = a.call("session/close", {"sessionId": sid_a})
        dump("a-03-close.json", closed)
    finally:
        a.kill_without_close()
    time.sleep(0.4)
    a2 = Backend("a2")
    try:
        if not a2.ready.wait(10):
            summary["a_error"] = "A2 not ready"
        else:
            listed = a2.call("session/list", {"workspace": WS})
            dump("a-04-list-fresh-after-close.json", listed)
            ids = listed_ids(listed)
            resume_a = a2.call("session/resume", {"sessionId": sid_a, "workspace": WS})
            dump("a-05-resume.json", resume_a)
            summary["leg_a"] = {
                "native": sid_a,
                "listed_before_close": True,
                "listed_fresh_after_close": sid_a in ids,
                "fresh_ids": ids,
                "resume_error": resume_a.get("error"),
            }
    finally:
        a2.kill_without_close()

    # Leg B: create + kill without close + fresh list + resume
    b = Backend("b")
    try:
        if not b.ready.wait(10):
            dump("00-summary.json", {**summary, "error": "B not ready"})
            return 1
        created = b.call("session/create", {"workspace": WS, "mode": "yolo"})
        dump("b-01-create.json", created)
        sid_b = native_id(created)
        listed = b.call("session/list", {"workspace": WS})
        dump("b-02-list-before-kill.json", listed)
        summary["leg_b_native"] = sid_b
        summary["leg_b_listed_before_kill"] = sid_b in listed_ids(listed)
    finally:
        b.kill_without_close()
    time.sleep(0.4)
    b2 = Backend("b2")
    try:
        if not b2.ready.wait(10):
            dump("00-summary.json", {**summary, "error": "B2 not ready"})
            return 1
        listed = b2.call("session/list", {"workspace": WS})
        dump("b-03-list-fresh-after-kill-no-close.json", listed)
        ids = listed_ids(listed)
        present = sid_b in ids
        resume_msg = b2.call("session/resume", {"sessionId": sid_b, "workspace": WS})
        dump("b-04-resume.json", resume_msg)
        summary["leg_b"] = {
            "native": sid_b,
            "listed_before_kill": summary.get("leg_b_listed_before_kill"),
            "listed_fresh_after_kill_no_close": present,
            "fresh_ids": ids,
            "resume_error": resume_msg.get("error"),
            "resume_session": (
                ((resume_msg.get("result") or {}).get("session") or {}).get("sessionId")
            ),
        }
        a_listed = (summary.get("leg_a") or {}).get("listed_fresh_after_close")
        b_resume_ok = resume_msg.get("error") is None and summary["leg_b"]["resume_session"]
        if b_resume_ok:
            summary["verdict"] = "skip-close-resume-works-even-if-unlistable" if not present else "skip-close-preserves-and-resume-works"
        elif present:
            summary["verdict"] = "skip-close-listed-but-resume-failed"
        elif a_listed is False:
            summary["verdict"] = "process-exit-and-close-both-unresumable"
        else:
            summary["verdict"] = "process-exit-also-drops-session"
    finally:
        b2.kill_without_close()
    dump("00-summary.json", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
