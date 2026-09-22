import json, subprocess, sys, os, threading, queue
meta = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {"parameterizedModelPicker": True}
sets = json.loads(sys.argv[2]) if len(sys.argv) > 2 else []
p = subprocess.Popen(["cursor-agent", "--yolo", "acp"], cwd="/tmp", stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
q = queue.Queue()
threading.Thread(target=lambda: [q.put(l) for l in p.stdout], daemon=True).start()
nid = [0]
def req(method, params):
    nid[0] += 1; i = nid[0]
    p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": i, "method": method, "params": params}) + "\n"); p.stdin.flush()
    while True:
        m = json.loads(q.get(timeout=60))
        if m.get("id") == i and "method" not in m: return m
        if m.get("method"): print("NOTIFY", json.dumps(m)[:600])
out = {}
out["init"] = req("initialize", {"protocolVersion": 1, "clientCapabilities": {"fs": {"readTextFile": False, "writeTextFile": False}, "terminal": False, "_meta": meta}})
r = req("session/new", {"cwd": "/tmp", "mcpServers": []})
out["new"] = r
sid = r.get("result", {}).get("sessionId")
for cid, val in sets:
    rr = req("session/set_config_option", {"sessionId": sid, "configId": cid, "value": val})
    out.setdefault("sets", []).append({"configId": cid, "value": val, "resp": rr})
p.terminate()
print(json.dumps(out, indent=1))
