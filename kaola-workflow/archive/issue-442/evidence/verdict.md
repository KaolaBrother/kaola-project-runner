# Issue 442: DSH rc.5 validation

Verdict: NOT-GREEN for adoption. Do not update platforms/dsh.yaml to rc.5 until a credentialed, operator-declared opencode-go route completes the full Runner path and confirms the route condition. Host acceptance is pending; do not finalize.

Acquisition: npm install @deepseek-ai/dsh@0.2.1-rc.5 under /tmp/kpr-442-rc5 with cache /tmp/kpr-442-cache completed (618 packages); absolute binary reported 0.2.1-rc.5. No PATH or fleet installation changes.

Accepted R 3d67cf6976381e75ea6a73ee62f88df73c43d5a8: cli rc.2, deepseek-harness-acp/0.0.1, protocol 1, operator-declared opencode-go route. rc.5 initialize and session/new yielded the same identity, protocol and close/list/resume capabilities. Stock default opencode-go model was rejected (-32602); copying the existing operator ACP patch into isolated DSH_HOME also yielded the same rejection. This does not establish why the patch was ineffective or that a correctly configured operator route fails. The shell lacked OPENCODE_GO_API_KEY and DEEPSEEK_API_KEY.

First start refused heartbeat-host-conflict without spawning; status returned no-session. Subsequent isolated test removed inherited unrelated heartbeat binding. Stock and copied-patch starts created ACP IDs 04087472-09c2-4f73-85d5-3e2f0d8dcff5 and 24b6ad49-d619-478c-aaec-ee0d15955a93, respectively, but were automatically stopped after model rejection, no residual pids. A separate explicit deepseek-official model start created Runner session dsh-rc5-i442-direct, ACP ID 96e47e51-b50f-41ee-a293-4fa5372528c2. Observe showed idle and live, protocol 1, no malformed stdout. Send reached ACP but ended turn_failed -32603, no API key for deepseek-official; capture recorded initialize and turn failure. Exact stop reported stopped true, agent exit 0, residual_pids [], and subsequent status stopped. Successful response and complete protocol conformance are not established.

Evidence: start.json, start-sandbox.json, start-route.json, start-direct.json, observe.json, send.json, capture.json, stop.json, status-after-stop.json. The fallback argument attempt was rejected by runtime-tmux; start-fallback.json records that fact.
