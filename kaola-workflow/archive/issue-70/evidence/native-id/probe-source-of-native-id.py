import importlib.util, json, sys
from pathlib import Path
ROOT = Path("/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-70")
spec = importlib.util.spec_from_file_location("hb", ROOT/"tests/contract/test-zcode-heartbeat-contract.py")
hb = importlib.util.module_from_spec(spec); spec.loader.exec_module(hb)
sb = hb.Sandbox("i70-native-id")
try:
    s = sb.session()
    start = sb.start(s, "basic")
    print("start session_meta:", json.dumps(start.get("session_meta"))[:300])
    print("start acp_session_id:", start.get("acp_session_id"))
    sb.cli("send", "--text", "hello", session=s)
    obs = sb.cli("observe", session=s)
    print("observe session_meta:", json.dumps(obs.get("session_meta"))[:400])
    ids = [e for e in hb.read_events(sb.record_dir(s))
           if (e.get("update") or {}).get("sessionUpdate") == "native_session_identity"]
    print("identity events:", json.dumps(ids)[:400])
    native = (ids[-1]["update"]["nativeSessionId"] if ids else None)
    print("native id:", native)
    sb.cli("stop", session=s)
    if native:
        r = sb.cli("start", "--mode", "yolo", "--resume", native, session=s, scenario="basic")
        print("resume state:", r.get("state"), "err:", r.get("error"))
        print("resumed session_meta:", json.dumps(r.get("session_meta"))[:300])
        sb.cli("stop", session=s)
finally:
    sb.cleanup()
