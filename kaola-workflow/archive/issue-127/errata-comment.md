**#127 勘误(实现者活体实测,Host 裁决 Option 1:以实测名为准)**

| 单内假设 | 实测值 | 探针证据 |
|---|---|---|
| Cursor 默认 slug `cursor-grok-4.7-xhigh` | `grok-4.7-xhigh`(4.7 picker 去掉 `cursor-` 前缀;Fast 为 `grok-4.7-xhigh-fast`) | `agent --list-models`,cursor-agent 2026.09.15-d2fe57e;`cursor-grok-4.6-*` 仍在列 |
| `acp_model_map` 左键 `cursor-grok-4.7-xhigh[-fast]` | `grok-4.7-xhigh[-fast]=grok-4.7` | ACP initialize(`clientCapabilities._meta.parameterizedModelPicker=true`)+ session/new:model `grok-4.7\|grok-4.6\|grok-4.5`,effort low..xhigh,fast false/true |
| TUI 页脚 `Cursor Grok 4.7 Extra High` | `Grok 4.7 256K Extra High`(无 `Cursor` 前缀,带上下文 token;Fast 变体尾随 ` Fast`) | tmux 起 `cursor-agent --trust --model grok-4.7-xhigh[-fast]/-high/-medium`,`CURSOR_CONFIG_DIR` 指向临时目录;真实 `~/.cursor/cli-config.json` mtime/size 前后不变 |
| 策略解析返回 `cursor-grok-4.7-{effort}` | `grok-4.7-{effort}[-fast]`;另修单内 grep 漏掉的第三处 `kaola-model-policy.py:353` 滚屏回退判定(原字面量 `"Cursor Grok 4.6"`) | 新增 `test_cursor_grok_47_footer_is_parsed`(banner tip 仍写 "Cursor Grok 4.6",不得被当作模型) |
| Grok CLI `grok-4.7` | ✅ 一致(1.0.40 ACP model current `grok-4.7`,另有 `grok-4.7-build-fast`) | ACP session/new |
| `acp_verified_versions` | cursor-cli 更新为 `cli=2026.09.15-d2fe57e` | `cursor-agent --version` |

候选提交 `af6b45d`(分支 `workflow/issue-127`,未 merge)。另:`tests/fixtures/observations/cursor-cli/ready-cursor-x0.frame.txt` 为 2026.08.25 真实抓帧(test_13 钉其版本行),按 G 节历史保留原则**未改**;合成夹具 `raw-mode-tui.py` 已按实测页脚更新。
