# Issue 447 delivery

Verdict: GREEN for the requested rc.5 credentialed ACP lifecycle, pending Host acceptance. Pin updated to cli=0.2.1-rc.5; agent=deepseek-harness-acp/0.0.1; protocol=1; condition=operator-declared-opencode-go-route. No self-finalization.

Acquisition: npm install @deepseek-ai/dsh@0.2.1-rc.5 into /tmp/kpr-447-rc5 with /tmp/kpr-447-cache; version.txt reports rc.5. DSH_HOME=/tmp/kpr-447-home. After initial profile bootstrap, the existing operator ACP patch and existing environment were copied into the isolated home; the copied environment was removed after the run. Fleet installation and PATH were not changed. The first bootstrap was refused before spawning due to inherited heartbeat binding; bootstrap2 and bootstrap-stop record the corrected isolated initialization.

Session dsh-KPR-i447-route, ACP session 840e99fb-eb18-44a2-a09b-06e132803880: start.json shows requested opencode-go/deepseek-v4.1-flash applied and effort max, agent deepseek-harness-acp/0.0.1, protocol 1; observe.json records live state. send.json and capture.json record KPR447_OK and end_turn; stop.json and status.json report stopped and no residual pids. The operator route condition remains necessary; this does not prove all protocol methods, resume, or other providers. Baseline R 3d67cf6976381e75ea6a73ee62f88df73c43d5a8 records rc.2 with the same agent, protocol and route condition.

Validation: render --write and --check PASS; focused suites 345, 351, 363 PASS. Initial suite 98 failed solely on its rc.2 assertion; updated it to rc.5, and reran suite 98 PASS (validation.log). Initial system Bash 3 invocation refused; first supported Bash run had nested watchdog skipped due to PATH; the final suite 98 run used Homebrew Bash on its process PATH. git diff --check PASS. Original three suites remain valid after the isolated test-98 assertion edit.

Receipts in this directory are local run evidence. Product changes and generated platform output remain uncommitted in the issue-447 worktree for Host acceptance.
