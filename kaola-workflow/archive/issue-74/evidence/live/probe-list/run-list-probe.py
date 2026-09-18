#!/usr/bin/env python3
"""Bounded ZCode session/list probe in the owned isolation repo.

Does not start a Runner Host. Uses the same entry/node/env the adapter child
uses (iso shim + Homebrew node + ELECTRON_RUN_AS_NODE). Distinguishes
never-persisted vs close-deleted vs still-listed.
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path

ISO = Path("/Volumes/WorkspaceA/ylminiserver/workspace/kaola-i74-iso-ab")
ENTRY = ISO / ".zcode-runtime" / "zcode.cjs"
NODE = Path("/opt/homebrew/bin/node")
OUT = Path(__file__).resolve().parent
WORKSPACE = str(ISO)


class Backend:
    def __init__(self) -> None:
        allow = (
            "HOME", "PATH", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE", "USER",
            "LOGNAME", "SHELL", "TZ", "TERM",
        )
        env = {k: os.environ[k] for k in allow if k in os.environ}
        env["ELECTRON_RUN_AS_NODE"] = "1"
        self.err_path = OUT / "appserver.err"
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
        self.events: list[dict] = []
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
            self.events.append(msg)
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

    def stop(self) -> None:
        if self.proc.poll() is None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=3)
            except Exception:
                self.proc.kill()


def ids_in(msg: dict) -> list[str]:
    result = msg.get("result") or {}
    sessions = result.get("sessions") or []
    return [str(s.get("sessionId") or "") for s in sessions if isinstance(s, dict)]


def dump(name: str, payload: object) -> None:
    path = OUT / name
    if isinstance(payload, (dict, list)):
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        path.write_text(str(payload), encoding="utf-8")


def main() -> int:
    if not ENTRY.is_file() or not NODE.is_file():
        dump("00-fail.txt", f"missing entry/node: {ENTRY} {NODE}\n")
        return 2
    workspace = {"workspacePath": WORKSPACE, "workspaceKey": WORKSPACE}
    summary: dict = {"workspace": WORKSPACE, "entry": str(ENTRY), "node": str(NODE)}
    b = Backend()
    try:
        if not b.ready.wait(10):
            summary["error"] = "app-server storage not ready"
            dump("00-summary.json", summary)
            return 1
        created = b.call("session/create", {"workspace": workspace, "mode": "yolo"})
        dump("01-create.json", created)
        native = ((created.get("result") or {}).get("session") or {}).get("sessionId")
        if not native:
            # requestRuntimePreferences may race; scan events
            for ev in b.events:
                params = ev.get("params") or {}
                sid = params.get("sessionId")
                if isinstance(sid, str) and sid.startswith("sess_"):
                    native = sid
                    break
        summary["native_session_id"] = native
        listed = b.call("session/list", {"workspace": workspace})
        dump("02-list-after-create-before-prompt.json", listed)
        after_create = ids_in(listed)
        summary["list_after_create"] = after_create
        summary["present_after_create"] = native in after_create if native else False
        sent = b.call(
            "session/send",
            {"sessionId": native, "content": "ISSUE74-LIST-PROBE reply with KPR74-ORANGE-LANTERN"},
            timeout=30,
        )
        dump("03-send.json", sent)
        summary["send_error"] = sent.get("error")
        listed2 = b.call("session/list", {"workspace": workspace})
        dump("04-list-after-prompt.json", listed2)
        after_prompt = ids_in(listed2)
        summary["list_after_prompt"] = after_prompt
        summary["present_after_prompt"] = native in after_prompt if native else False
        closed = b.call("session/close", {"sessionId": native})
        dump("05-close.json", closed)
        listed3 = b.call("session/list", {"workspace": workspace})
        dump("06-list-after-close-same-process.json", listed3)
        after_close = ids_in(listed3)
        summary["list_after_close_same_process"] = after_close
        summary["present_after_close_same_process"] = native in after_close if native else False
    finally:
        b.stop()
    time.sleep(0.5)
    b2 = Backend()
    try:
        if not b2.ready.wait(10):
            summary["fresh_error"] = "second app-server not ready"
        else:
            listed4 = b2.call("session/list", {"workspace": workspace})
            dump("07-list-after-close-fresh-process.json", listed4)
            after_fresh = ids_in(listed4)
            summary["list_after_close_fresh_process"] = after_fresh
            summary["present_after_close_fresh_process"] = native in after_fresh if native else False
    finally:
        b2.stop()
    if summary.get("present_after_create") and not summary.get("present_after_close_same_process"):
        summary["verdict"] = "close-deleted"
    elif not summary.get("present_after_create") and not summary.get("present_after_prompt"):
        summary["verdict"] = "never-persisted"
    elif summary.get("present_after_close_fresh_process"):
        summary["verdict"] = "persisted-across-close"
    elif summary.get("present_after_close_same_process") and not summary.get("present_after_close_fresh_process"):
        summary["verdict"] = "listed-until-process-exit"
    else:
        summary["verdict"] = "inconclusive"
    dump("00-summary.json", summary)
    dump("00-events-first-process.json", b.events[-30:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
