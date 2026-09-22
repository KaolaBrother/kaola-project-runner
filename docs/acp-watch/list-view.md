# Issue #26 — ACP human watch CLI `list` / `view`

设计权威：[GitHub #26](https://github.com/KaolaBrother/kaola-project-runner/issues/26)。  
状态：设计冻结（2026-09-13；2026-09-13 第二次修订补齐发现入口与类型化 schema）；**已实现**（issue #26）。这是与 Kaola Terminal 共享的 stdout **契约**，单独落地。下面「当前代码事实」是施工前快照；实现以 `scripts/kaola-acp.py`、`scripts/kaola-acp-holder.py`、`scripts/install-local.sh` 为准。

## 决策

人类旁观不碰 agent stdio。holder 在 `session/update` / permission / 回合终态上维护内存 **ViewProjection**。CLI 增加：

- `kaola-acp list [--platform <p>] [--repo <canonical-git-root>]` —— **主机级**列举：默认扫描全部平台、全部 repo，两个过滤器可选。这是 Kaola Terminal 标签条并集**唯一**的发现入口；Terminal 不知道远端有哪些 repo，不得要求它枚举。
- `kaola-acp <platform> view --repo … --session … [--since CURSOR]`

`list` 是命令面上**唯一**不带 `<platform>` 位置参数、`--repo` 非必填的命令。当前 argparse 把 `platform` 设为 `choices=PLATFORMS` 的必填位置参数、`--repo` 为 `required=True`；实现可在主解析器之前按 `sys.argv[1] == "list"` 分流，也可放开主解析器约束，但 argv 形状以上面为准。`kaola-tmux.sh` 不分发 `list`（它始终带平台与 repo）。

`view` 的 stdout 是**一个** JSON 对象，schema 名冻结为 `kaola-acp-view/1`。`list` 的 stdout 也是一个 JSON 对象，schema 名 `kaola-acp-list/1`。两者**永不**进入 `send --wait` L0 回执。

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

- 命令面：`preflight start send wait observe capture permit key answer cancel stop status`。无 `list`/`view`。`scripts/kaola-acp.py` 约 439–444 行：`platform` 位置参数 `choices=PLATFORMS`，`--repo required=True`。
- 套接字：`$TMPDIR/kaola-<uid>-acp/<24-hex>.sock`（`0600`，父目录 `0700`，Darwin `getpeereid` / Linux `SO_PEERCRED`，`listen(16)`）。`record_dir/holder.sock` 是 symlink。CLI 已按短路径计算，**不要**改去跟随 symlink 或 `record.json` 的 `socket_path`。
- `record.json`（`write_record`）已含 `transport` `platform` `session` `repo` `holder_pid` `agent_alive` `state` `pending_permissions` `event_cursor`；`list` 只需遍历目录并核对 `holder_pid` 存活，不需要连接套接字。
- holder `self.state` 取值：`starting` `ready` `agent_exited` `stopping` `stopped` `error`。
- holder 内部 `pending_permissions` 条目的 `options` 为 `{id, kind, label}`（`on_request_permission`，约 543–545 行），并原样进入 L0 回执与 `record.json`。**L0 这组键不改。**
- `EventLog.__init__` 的 `cursor = 0`。新 holder 在同一 `record_dir` 上会在残留高 cursor 行之后再从 1 编号。`read_since` 只读当前 `events.jsonl`，不读 `.jsonl.1–.3`。
- `on_session_update`：拼接 `final_text`、计数 thinking、按 `toolCallId` overlay、替换 usage；**plan 只记日志不进 turn**；tool `content` 压成 `error_head[:200]`。人类投影必须保留 plan 全表与工具 text/diff。
- `install-local.sh` 只把 Skill 链到 `$CODEX_HOME/skills`。
- 源文件：`scripts/kaola-acp.py`、`scripts/kaola-acp-holder.py`、`templates/references/acp.md.tmpl`、合同测试。然后 `render-skills.py --write`。禁止手改 `skills/`。

## `kaola-acp-list/1`

一个 JSON 对象。`rows` 只含活着的 `holder_pid`（死 holder 从 live list 省略；`status`/`observe` 仍可报 holder-lost）。

```json
{
  "schema": "kaola-acp-list/1",
  "rows": [
    {
      "platform": "grok",
      "session": "fix-login",
      "repo": "/Users/me/src/app",
      "state": "ready",
      "holder_pid": 48213,
      "agent_alive": true,
      "event_cursor": 418,
      "mutation_status": "clean",
      "pending_count": 0,
      "socket_ok": true,
      "transport": "acp"
    }
  ]
}
```

| 键 | 类型 |
|---|---|
| `platform` | string，∈ `PLATFORMS` |
| `session` | string，匹配 `SESSION_PATTERN` |
| `repo` | string，绝对规范 git 根 |
| `state` | string，∈ `starting` `ready` `agent_exited` `stopping` `stopped` `error` |
| `holder_pid` | int |
| `holder_instance_id` | string \| null；holder 进程实例身份（#39，随机一次铸造）；老版本记录可为 null |
| `agent_alive` | bool |
| `event_cursor` | int ≥ 0 |
| `mutation_status` | string，既有五态 |
| `pending_count` | int |
| `socket_ok` | bool（短路径套接字文件存在且可连接） |
| `transport` | 恒为 `"acp"` |

扫描根：`${KAOLA_ACP_RECORD_ROOT:-XDG_RUNTIME_DIR|TMPDIR}/kaola-<uid>/<platform>/<session>/<sha16>/record.json`。`--platform` / `--repo` 只做过滤。

## `kaola-acp-view/1`

一个 JSON 对象。**实现可多不可少；消费者忽略未知键。** 类型冻结如下；`null` 只允许出现在标明 `|null` 的位置。

| 键 | 类型 / 含义 |
|---|---|
| `schema` | 恒为 `"kaola-acp-view/1"` |
| `platform` `session` `repo` | 身份三元组，同 list 行 |
| `state` | 同 list 行 |
| `holder_pid` | int；世代栅栏，Terminal permit 必须核对 |
| `holder_instance_id` | string；本 holder 进程实例身份（#39），比 PID 更强的绑定，`permit`/`cancel` 可用 `--expected-holder-instance-id` 钉住 |
| `agent_alive` | bool |
| `event_cursor` | int，单调 |
| `truncated` | bool；任一 cap 生效或 `cursor_gap` 时为 true |
| `cursor_gap` | bool；`--since` 低于仍保留的最老 cursor |
| `messages` | **数组**，按时间序：`{role: "user"\|"assistant", text: string, messageId: string\|null, cursor: int}`；同 `messageId` 的 chunk 已拼接成一条 |
| `thinking` | `{chars: int, text_tail: string, messageId: string\|null}`；L0 仍只见 `thinking_chars` |
| `tools` | **数组**，按首次出现序，`toolCallId` 唯一：`{toolCallId: string, title: string\|null, kind: string\|null, status: string\|null, locations: [{path: string, line: int\|null}], content: [ContentItem], truncated: bool}` |
| `plan` | `{entries: [{content: string, priority: string\|null, status: string\|null}]}` \| `null`；每次 `sessionUpdate: plan` **整表替换**，禁止合并；从未发过 plan 则 `null` |
| `pending_permissions` | 数组：`{request_id: string, title: string\|null, tool_call_id: string\|null, options: [{optionId: string, name: string, kind: string\|null}]}` |
| `mode` | `{current: string\|null, available: [{id: string, name: string}]}` \| `null` |
| `commands` | `[{name: string, description: string\|null}]` \| `null` |
| `usage` | `{used: int, size: int}` \| `null`（Grok 常不报） |
| `turn` | `{mutation_status: string, outcome: string\|null, stop_reason: string\|null, active: bool}` |
| `unparsed_update_count` | int；未知 `session/update` 变体计数，不当控件 |

`ContentItem` 三选一：

- `{type: "text", text: string}`
- `{type: "diff", path: string, oldText: string|null, newText: string}`
- `{type: "terminal", terminalId: string}`（只是标签；消费者 `clientCapabilities.terminal=false`）

**`pending_permissions[].options` 在 view 中使用 ACP 原生键 `optionId` / `name` / `kind`。** holder 内部与 L0 回执继续用 `{id, kind, label}`，view 序列化时做一次映射；`permit --option` 的取值就是 `optionId`。

### 样例

```json
{
  "schema": "kaola-acp-view/1",
  "platform": "kimi-cli",
  "session": "fix-login",
  "repo": "/Users/me/src/app",
  "state": "ready",
  "holder_pid": 48213,
  "holder_instance_id": "9f2ab1c4d8e0736fa051b2c9d4e68a71",
  "agent_alive": true,
  "event_cursor": 418,
  "truncated": false,
  "cursor_gap": false,
  "messages": [
    {"role": "user", "text": "Fix the login redirect loop.", "messageId": null, "cursor": 12},
    {"role": "assistant", "text": "I'll start by reading the auth middleware.", "messageId": "m1", "cursor": 40}
  ],
  "thinking": {"chars": 1532, "text_tail": "…the cookie is cleared before redirect.", "messageId": "m1"},
  "tools": [
    {
      "toolCallId": "call_7",
      "title": "Edit src/auth/middleware.ts",
      "kind": "edit",
      "status": "completed",
      "locations": [{"path": "src/auth/middleware.ts", "line": 88}],
      "content": [
        {"type": "diff", "path": "src/auth/middleware.ts", "oldText": "res.redirect('/login')", "newText": "if (!req.path.startsWith('/login')) res.redirect('/login')"}
      ],
      "truncated": false
    }
  ],
  "plan": {"entries": [
    {"content": "Read middleware", "priority": "high", "status": "completed"},
    {"content": "Patch redirect guard", "priority": "high", "status": "in_progress"}
  ]},
  "pending_permissions": [
    {
      "request_id": "42",
      "title": "Exit plan mode and start editing?",
      "tool_call_id": "call_8",
      "options": [
        {"optionId": "allow_once", "name": "Allow once", "kind": "allow_once"},
        {"optionId": "reject_once", "name": "Reject", "kind": "reject_once"}
      ]
    }
  ],
  "mode": {"current": "plan", "available": [{"id": "plan", "name": "Plan"}, {"id": "yolo", "name": "Yolo"}]},
  "commands": null,
  "usage": {"used": 38211, "size": 262144},
  "turn": {"mutation_status": "clean", "outcome": null, "stop_reason": null, "active": true},
  "unparsed_update_count": 0
}
```

该样例以文件形式冻结在 `tests/contract/fixtures/kaola-acp-view-1.sample.json`，合同测试必须断言真实 `view` 输出与样例**键集合与类型**一致；Kaola Terminal 把同一文件拷进测试 bundle 作为解码 fixture。

上限（超限置 `truncated=true` 并**实际裁剪**，不报错）：thinking 只保留 8KiB 尾巴；单工具 content 裁到 32KiB（整项保留，首个溢出项截断 text/newText）；timeline 只保留最近 200 条；整 view 超过 256KiB 时先丢最旧的工具卡，再丢最旧的消息。没有 `messageId` 的 chunk（Grok 实测全部如此）按同角色连续拼接，直到 tool_call、新 prompt 或回合结束为止。

### `--since` 语义

`view` 返回的**永远是当前压实态**，不是增量，也不是残缺历史。`--since C` 只影响 `cursor_gap`：C 低于仍保留的最老 cursor 时置 `truncated=true` + `cursor_gap=true`，投影本身照常返回。消费者只靠轮询快照的情况下可以**不传** `--since`。

### EventLog 重载（本单必做，不是加固）

新 holder 进程必须从 `events.jsonl` 及轮转 `.jsonl.1–.jsonl.3` **按序**恢复最大 cursor，随后只递增。禁止在残留高 cursor 上从 1 再数。否则 Terminal 的 `lastAppliedCursor` 会静默丢历史。

## 错误

用法错误仍 exit 2。运行时事实与既有回执同形：stdout **一个 JSON 对象**，带 `schema` 与 `error: {code, message}`，code ∈ `holder-lost` / `holder-unreachable` / `no-session`。经 `kaola-tmux.sh` 分发 `view` 给显式 `view-unsupported`（`follow` 同理为 `follow-unsupported`），不自动回退；请直接用 `kaola-acp`。

## Skill 文案

改写「acp 无可视界面」：人类用 Terminal 或 `list`/`view`（本机后续 `follow`）订阅；编排器普通回合仍不得轮询原始帧；登录是 Runner 之外的人类原生终端动作（PTY 已退役，#130）。

## 验收

- `kaola-acp list`（无参数）列出本机全部活 holder；加 `--platform` / `--repo` 只做过滤；杀死 holder 后该行从 live list 消失。  
- `view` 对 mock 的 tool+plan+thought 给出卡片与整表 plan，键集合与类型与 `tests/contract/fixtures/kaola-acp-view-1.sample.json` 一致；`options[]` 使用 `optionId`/`name`/`kind`。  
- L0 `send --wait` 键集合不变（无 `timeline` / `thinking_text` / `plan`；`pending_permissions[].options` 仍为 `{id, kind, label}`）。  
- 同 `record_dir` 重启 holder 后 cursor 不从 1 覆盖。  
- `install-local.sh` 后 `$HOME/.local/bin/kaola-acp` 为属主 symlink。  
- `render-skills.py --check`；`./scripts/validate.sh`。

## 非本单

`follow`（#27）；permit 双应答（#25）；HTTP/SSE；Terminal UI；Watch composer。
