import importlib.machinery, importlib.util, json, os, socket, sys, tempfile, threading
HOLDER = "/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-92/scripts/kaola-acp-holder.py"
spec = importlib.util.spec_from_loader("h", importlib.machinery.SourceFileLoader("h", HOLDER))
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)

sock_path = os.path.join(tempfile.mkdtemp(), "peer.sock")

def serve(reply: bytes):
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(sock_path); srv.listen(1)
    def run():
        c, _ = srv.accept()
        c.recv(65536); c.sendall(reply); c.close(); srv.close()
    threading.Thread(target=run, daemon=True).start()

class FakeHolder:
    heartbeat_notify_lock = threading.Lock()
    _carrier_send = h.Holder._carrier_send

for label, reply in (("string error", b'{"error":"boom"}\n'),
                     ("non-dict reply", b'"hello"\n')):
    serve(reply)
    receipt = FakeHolder()._carrier_send({"socket": sock_path, "session": "x"}, {"kind": "permission_required"})
    print(f"{label}: receipt={receipt!r}")
    try:
        # the exact expression at :1904 / :1951 in the frozen candidate
        code = (receipt.get("error") or {}).get("code")
        print(f"  -> error code extraction OK: {code!r}")
    except Exception as exc:
        print(f"  -> RAISES {type(exc).__name__}: {exc}")
    os.unlink(sock_path)
