# Issue #26 — ACP human watch CLI `list` / `view`

设计权威：[GitHub #26](https://github.com/KaolaBrother/kaola-project-runner/issues/26)。  
状态：设计冻结（2026-09-13）；**未实现**。这是与 Kaola Terminal 共享的 stdout **契约**，单独落地。

## 决策

人类旁观不碰 agent stdio。holder 在 `session/update` / permission / 回合终态上维护内存 **ViewProjection**。CLI 增加：

- `kaola-acp <platform> list --repo <canonical-git-root>`
- `kaola-acp <platform> view --repo … --session … [--since CURSOR]`

`view` 的 stdout 是**一个** JSON 对象，schema 名冻结为 `kaola-acp-view/1`。它**永不**进入 `send --wait` L0 回执。

`install-local.sh` 必须安装属主拥有的 `$HOME/.local/bin/kaola-acp` 与 `kaola-acp-holder` 符号链接（拒覆盖外源文件；卸载只拆这些属主链接）。Kaola Terminal 的 PATH 前缀已经包含 `$HOME/.local/bin`。

## 为何不是 hydra / HTTP / `session/attach`

| 选项 | 事实 | v1 |
|---|---|---|
| 第二进程抢 agent stdio | ACP v1：client 拉起子进程，stdin/stdout 只承载 ACP JSON-RPC | 否决 |
| 官方 Streamable HTTP / WS | 稳定 Transports 页仍标 draft；`agent-client-protocol-http` 2.1.0 是 RFD 实现 | 否决为产品契约 |
| RFD #533 `session/attach` | PR 未合并；已去掉 controller/observer | 否决 |
| hydra-acp / acp-mux | 全局或 mux 进程**自己** spawn agent 再扇出 | holder 已占 stdio；不引入 |
| `capture --since` 给编排器当 UI | 毁掉 L0 约 12× token 优势 | 否决作为人类主路径 |
| SSH 转发 `holder.sock` | 无 ACP 产品文档；转发后对端即完整 ACP 客户端 | 否决为远程 v1 |

本单只做「holder 投影 + 本机 Unix 套接字上的一对象 JSON」。远程运输由 Terminal 用既有 15s `execute()` 调用本 CLI。

## 当前代码事实

- 命令面：`preflight start send wait observe capture permit key answer cancel stop status`。无 `list`/`view`。
- 套接字：`$TMPDIR/kaola-<uid>-acp/<24-hex>.sock`（`0600`，父目录 `0700`，Darwin `getpeereid` / Linux `SO_PEERCRED`，`listen(16)`）。`record_dir/holder.sock` 是 symlink。CLI 已按短路径计算，**不要**改去跟随 symlink 或 `record.json` 的 `socket_path`。
- `EventLog.__init__` 的 `cursor = 0`。新 holder 在同一 `record_dir` 上会在残留高 cursor 行之后再从 1 编号。`read_since` 只读当前 `events.jsonl`，不读 `.jsonl.1–.3`。
- `on_session_update`：拼接 `final_text`、计数 thinking、按 `toolCallId` overlay、替换 usage；**plan 只记日志不进 turn**；tool `content` 压成 `error_head[:200]`。人类投影必须保留 plan 全表与工具 text/diff。
- `install-local.sh` 只把 Skill 链到 `$CODEX_HOME/skills`。
- 源文件：`scripts/kaola-acp.py`、`scripts/kaola-acp-holder.py`、`templates/references/acp.md.tmpl`、合同测试。然后 `render-skills.py --write`。禁止手改 `skills/`。

## ViewProjection（`kaola-acp-view/1`）

字段（实现可多不可少；未知键消费者忽略）：

| 键 | 含义 |
|---|---|
| `schema` | 恒为 `kaola-acp-view/1` |
| `platform` `session` `repo` | 身份三元组 |
| `holder_pid` `agent_alive` | 世代栅栏；Terminal permit 必须核对 `holder_pid` |
| `event_cursor` | 单调整数 |
| `truncated` | 因 cap 或 cursor gap 裁剪时为 true |
| `cursor_gap` | `--since` 低于仍保留的最老 cursor 时为 true |
| `messages[]` | user/assistant；有 `messageId` 则拼接 chunk |
| `thinking` | `{chars, text_tail, messageId?}`；L0 仍只见 `thinking_chars` |
| `tools` | `toolCallId` → title/kind/status/locations/content（text / diff / terminalId 标签） |
| `plan.entries` | 每次 `sessionUpdate: plan` **整表替换**，禁止合并 |
| `pending_permissions[]` | `request_id`、title、`tool_call_id`、options |
| `mode` / `commands` | 有则带 |
| `usage` | `{used,size}` 或 `null`（Grok 常不报） |
| `turn` | `{mutation_status, outcome, stop_reason, active}` |
| `unparsed_update_count` | 未知变体；不当控件 |

上限（超限只设 `truncated`，不硬门）：thinking 约 8KiB、单工具 32KiB、整 view 256KiB、timeline 约 200。

`list`：扫描 `${KAOLA_ACP_RECORD_ROOT:-XDG_RUNTIME_DIR|TMPDIR}/kaola-<uid>/<platform>/<session>/<sha16>/record.json`，只报告活着的 `holder_pid`。死 holder 从 live list 省略（`status`/`observe` 仍可报 holder-lost）。行内含 platform、session、repo、state、`event_cursor`、`mutation_status`、pending 计数、`socket_ok`、`transport:acp`。

`view --since C`：投影永远是**当前**压实态，不是残缺历史。C 过旧 → `truncated=true` + `cursor_gap=true`。

### EventLog 重载（本单必做，不是加固）

新 holder 进程必须从 `events.jsonl` 及轮转 `.jsonl.1–.jsonl.3` **按序**恢复最大 cursor，随后只递增。禁止在残留高 cursor 上从 1 再数。否则 Terminal 的 `lastAppliedCursor` 会静默丢历史。

## 错误

用法错误仍 exit 2。运行时事实在 **stdout 一个 JSON 对象**：`holder-lost` / `holder-unreachable` / `no-session`。pty 上若经 `kaola-tmux.sh` 分发这些命令，给显式 `*-unsupported`，不自动回退。

## Skill 文案

改写「acp 无可视界面」：人类用 Terminal 或 `list`/`view`（本机后续 `follow`）订阅；编排器普通回合仍不得轮询原始帧；PTY 仍是登录与原生 TUI 接管。

## 验收

- 活 holder 出现在 `list`；杀死 holder 后从 live list 消失。  
- `view` 对 mock 的 tool+plan+thought 给出卡片与整表 plan，且 L0 `send --wait` 键集合不变（无 `timeline` / `thinking_text` / `plan`）。  
- 同 `record_dir` 重启 holder 后 cursor 不从 1 覆盖。  
- `install-local.sh` 后 `$HOME/.local/bin/kaola-acp` 为属主 symlink。  
- `render-skills.py --check`；`./scripts/validate.sh`。

## 非本单

`follow`（#27）；permit 双应答（#25）；HTTP/SSE；Terminal UI；Watch composer。
