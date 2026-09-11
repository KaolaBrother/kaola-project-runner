# Kaola Project Runner v2 设计文档：ACP 优先、tmux 兜底的双通道架构

状态：草案 v0.2（已整合独立评审意见；评审结论 needs_rework → 本版逐条修正）
范围：设计与决策，不含实现代码
日期：2026-09-11

> v0.1 → v0.2 变更摘要（对应评审 4 blocking / 12 major / 10 minor）
> - 新增 §3.3「每会话 ACP 连接持有者」，回答"start 与 send 之间谁持有 stdio"（blocking 1）
> - `mutation_status` 改为五态，判定绑定到写入边界，去掉 30s 时间窗（blocking 2）
> - ACP 客户端补 `-32601`、`$/cancel_request`、未知 update 容错、id 宽松匹配（blocking 3）
> - 新增协议版本协商规则，只接受 v1（blocking 4）
> - §2.4 事实表重写为"规范 / SDK / Paseo 实现观察"三类并修正 5 处错误引用
> - 回执新增 `stop_reason` 透传、`side_effects`、`failed_tools`、`context_usage`、`final_text` 上限
> - 重写 stop 序列、macOS 兼容、tree-kill、残留进程报告
> - schema 字段改 `schema_version: 3`，`snapshot_id` 在 acp 下为 null，新增 `event_cursor`，定义 `mutation_performed` 映射
> - manifest 保持 flat 前缀键，列出模板变量
> - 会话记录含 repo；补环境变量白名单、日志轮转、自宿主递归风险
> - 默认通道：PoC 前仅 Grok / Kimi 为 acp
> - 补 `key escape → cancel`、`--continue → session/list`、`pending_permissions[]`、`decision_id → request_id` 映射

---

## 0. 一句话结论

Runner v2 向 orchestrator 同时暴露两条通道——**`acp`** 与 **`pty`（现有 tmux/nested-PTY relay）**——共用同一套会话身份、命令面与回执 schema。Runner 只负责"通道能力事实 + 机械传输 + 事件精简"，通道的**选择权**归 orchestrator；Runner 通过默认值与成本事实提示引导它用最少 token 完成任务。PoC 阶段 Grok / Kimi 默认 acp，其余四平台默认 pty 但报告 acp 可用性。

---

## 1. 目标与非目标

### 1.1 目标

| 编号 | 目标 | 度量 |
| --- | --- | --- |
| G1 | orchestrator 每轮控制一个 CLI 所消耗的 token 显著下降 | PoC 记录字节数 + 固定 tokenizer token 数、命令调用次数、推理轮数 |
| G2 | Runner 更轻：ACP 路径不需要 tmux、屏幕 snapshot、pane revision、控制字过滤、按键旁路；**但每个 acp 会话有一个连接持有者进程**（形态同现有 relay，见 §3.3） | 行数、模块数、live smoke 步骤数 |
| G3 | 保留六平台与现有 tmux 能力，不做破坏性迁移 | `kaola-tmux.sh` 现有命令面全部可用且回执不变（仅新增字段） |
| G4 | 保持 Runner 原则：只报事实、不设 hardgate、不替 orchestrator 做语义判断 | 设计审查 |
| G5 | 借鉴 Paseo 的 ACP 思路与 quirk 知识，不引入 Paseo 源码、全局 daemon、桌面/移动端、relay、voice | 依赖清单 |

### 1.2 非目标

- 不做**全局**常驻 daemon、多客户端、workspace/worktree 管理。
- 不实现 Workflow、heartbeat、cadence、完成策略（AGENTS.md 约束）。
- 不承诺 token 下降倍数；PoC 量化后再报告。
- 不在同一 CLI 进程上同时开两条通道（§5）。
- 不支持 ACP v2（draft）；只协商 v1（§7.2）。

---

## 2. 现状与问题定位

### 2.1 现状架构（v1）

```text
Controlling Agent (orchestrator)
    -> communication-only Skill
        -> platform adapter (platforms/*.yaml + scripts/adapters/*.sh)
            -> tmux pane leader: managed relay (kaola-pane-relay.py, Unix socket)
                -> nested-PTY runtime child
```

命令面：`preflight / start / observe / status / capture / send / key / answer / stop`。
回执：`schema_version: 2`，含 `raw_current_frame`、`snapshot_id`（由 hard_evidence/relay/frame 计算的 opaque digest，仅 relay managed 时非 null）、`pane_revision`、relay 事实、Git 事实、`mutation_performed: true|false|null`，以及 advisory 的 `activity_hint / editor_state / native_approval / decision_id`。
会话身份三元组：platform + session + repo（tmux env marker + pane path）。
`stop` 语义：先送 `quit_text` 等待 10s → `quit-pending` → `--force`。

### 2.2 token 成本从哪来

1. `observe` 携带整块 raw frame。
2. 不知何时完成，只能重复 observe/capture。
3. orchestrator 用推理 token 判断忙/等审批/卡住/完成。
4. 权限确认靠屏幕识别 + `key` 逐键 + 再 observe。

### 2.3 复杂度从哪来

lease/fence、snapshot 关联、pane revision、控制字过滤、bracketed-paste、PTY 指纹、legacy relay 升级、Kimi trust UI 按键旁路、Cursor 坐标问题——全部派生自"屏幕文本是唯一事实来源"。

### 2.4 ACP 事实清单（按来源分三类）

#### A. 六平台 ACP 启动命令

| 平台 | 命令 | 来源类型 | 备注 |
| --- | --- | --- | --- |
| Grok | `grok agent stdio` | Paseo catalog（`packages/app/src/data/acp-provider-catalog.ts`） | Paseo 生产路径 |
| Kimi CLI | `kimi acp` | Paseo `KimiACPAgentClient` | Paseo 生产路径 |
| Cursor CLI | `cursor-agent acp` | Paseo `getCursorACPCommand`（`provider-registry.ts`） | Paseo 生产路径 |
| Devin CLI | `devin acp` | Paseo catalog | Paseo 生产路径 |
| OpenCode | `opencode acp` | OpenCode 官方文档 | **Paseo 未以 ACP 驱动 OpenCode**（走 HTTP）；`/undo /redo` 不支持 |
| Claude Code | `npx --yes @agentclientprotocol/claude-agent-acp@<pin>`（需 `CLAUDE_CODE_EXECUTABLE`） | Paseo `acp-wrapper-smoke.test.ts`（pin 0.31.4） | **Paseo 生产路径是 Claude Agent SDK 直连，非 ACP**；wrapper 仅 smoke 验证 |

#### B. 协议规范事实（agentclientprotocol.com, v1）

- 传输：client 以子进程方式 spawn agent 并独占其 stdin/stdout；newline-delimited JSON-RPC。
- 方法：`initialize`、`authenticate`（可选，`authMethods` 可为空）、`session/new`、`session/load`（gated by `agentCapabilities.loadSession`）、`session/resume`（gated by `sessionCapabilities.resume`）、`session/list`（gated by `sessionCapabilities.list`）、`session/prompt`、`session/cancel`（通知）、`session/close`（gated）、`session/set_mode`、`session/set_config_option`。
- 通知：`session/update`，变体含 `agent_message_chunk`、`agent_thought_chunk`、`tool_call`、`tool_call_update`、`plan`、`available_commands_update`、`current_mode_update`、`config_option_update`、`usage_update`、`user_message_chunk`。
- agent→client 请求：`session/request_permission`、`fs/read_text_file`、`fs/write_text_file`、`terminal/*`、`elicitation/create`、`$/cancel_request`。
- **cancel 有确认**：agent 收到 `session/cancel` 后 MUST 以 `stopReason: cancelled` 响应原 `session/prompt`。
- `stopReason` 取值：`end_turn | max_tokens | max_turn_requests | refusal | cancelled`。
- 省略的 `clientCapabilities` 视为 UNSUPPORTED；默认 `fs:{false,false}, terminal:false`。
- 一个 session 同时只允许一个 prompt turn。
- client 在 cancel/stop 时必须对所有 pending permission 回 `cancelled`。
- `session/prompt` 无协议级超时。
- 未知方法应按 JSON-RPC 返回 `-32601`；被取消的请求返回 `-32800`。
- v2（draft）已发布：prompt 响应不再结束 turn、`session/load` 移除、`fs/terminal/set_mode` 移除。**v2 不在本设计范围。**

#### C. Paseo 实现观察（SDK `@agentclientprotocol/sdk@^0.17.1`）

- `BASE_ACP_CLIENT_CAPABILITIES = { fs:{false,false}, terminal:true }`，并实现全部 terminal 方法。
- 未调用 `authenticate`；用 `NO_BROWSER=true` 抑制探测期登录。
- 进程空闲时退出不告警、只有 active turn 才发 `turn_failed`——这是 Paseo 的选择，不是协议事实。
- `max_tokens / refusal / max_turn_requests` 一律映射为 `turn_completed`（对 orchestrator 是信息丢失，v2 不照抄）。
- 对 id 为数字字符串的响应做规范化（JSON-RPC id 类型不一致是现实问题）。
- SDK 方法 `unstable_resumeSession` / `unstable_setSessionModel` / `unstable_closeSession` 对应规范 `session/resume` / `session/set_config_option` / `session/close`。
- Devin CLI resume 需同时传 `sessionId + cwd + mcpServers`。
- Cursor：slash 命令异步发布（Paseo 等待 ≤10s）；对"ACP 报 0 模型"有防御分支。v2 不做目录探测，不受影响。
- Kimi：thinking 选项需逐模型切换后读取；仅影响目录探测。

---

## 3. 总体架构（v2）

```text
Controlling Agent (orchestrator)
    -> communication-only Skill（新增：通道事实、成本提示、fallback 规则）
        -> platform manifest (platforms/*.yaml，新增 acp_* flat 键)
            -> transport = acp                          | transport = pty (现有，不变)
               kaola-acp.py (CLI, socket client)       | kaola-tmux.sh (CLI)
               kaola-acp-holder.py (每会话持有者进程)   | kaola-pane-relay.py (tmux pane leader)
               spawn CLI --acp / stdio JSON-RPC        | nested PTY
               事件精简层 + JSONL 事件日志              | frame/snapshot 层
        -> 统一回执 schema_version 3（v2 超集）
```

### 3.1 组件职责

| 组件 | 职责 | 不负责 |
| --- | --- | --- |
| Skill 模板 | 告诉 orchestrator：默认通道、通道能力事实、成本事实、fallback 规则 | 任何自动决策 |
| platform manifest | `default_transport`、`acp_command`、`acp_client_capabilities`、`acp_quirks`、`acp_verified_versions`、`acp_env_allowlist`、`acp_login_requires_pty` | 运行时探测结果 |
| `kaola-acp.py`（CLI） | 解析命令、连接持有者 socket、格式化回执 | 持有 stdio |
| `kaola-acp-holder.py`（每会话持有者，纯 Python 3） | spawn、stdio JSON-RPC、读线程、事件日志、pending permission、权限应答、cancel、stop 序列 | 判断任务完成、是否 fallback |
| `kaola-tmux.sh` + relay | 不变 | — |
| 回执 schema v3 | 两通道共用字段 + `transport` 段 + `mutation_status` | — |

### 3.2 会话身份与记录

- 会话名仍为 `--session NAME`，正则不变；身份仍是 platform + session + repo 三元组。
- 会话记录目录：`${XDG_RUNTIME_DIR:-${TMPDIR:-/tmp}}/kaola-<uid>/<platform>/<session>/<sha256(repo)[:16]>/`，含 `record.json`、`holder.sock`、`events.jsonl`、`stderr.log`。
- `record.json` 字段：`transport`、`platform`、`repo`、`holder_pid`、`agent_pid/pgid`、`acp_session_id`、`protocol_version`、`agent_info{name,version}`、`created_at`、`last_prompt{fingerprint, written_at, transport, mutation_status, stop_reason}`、`pending_permissions[]`。
- **一个会话名 + repo 同一时刻只绑定一条通道。** `start` 前同时查 tmux（pty）与记录目录（acp）；对已存在会话使用另一通道 → 回执 `transport-mismatch{other_transport, other_pid, other_repo}`（事实，不是 hardgate）。
- 记录由持有者进程写；持有者死亡时 `status/observe` 依据 `holder_pid` 不存活 + 记录内容推导（见 §5.3）。

### 3.3 每会话 ACP 连接持有者（v0.2 新增，回应 blocking 1）

ACP stdio 归属于 spawn 它的进程；`start` 与 `send` 之间必须有人持有管道并持续读事件。两条路：

| 方案 | 说明 | 结论 |
| --- | --- | --- |
| A. 每会话持有者进程 | `start` fork 出 `kaola-acp-holder.py`（`start_new_session=True`），持有 agent stdio，监听 Unix socket；`send/wait/permit/cancel/observe/capture/stop` 都是 socket 客户端 | **采用**。与现有 relay 同构，"无全局 daemon"仍成立 |
| B. 每次命令重新 spawn + `session/load` | 无常驻，但依赖 `loadSession` 能力（各家不一），每轮重放历史抵消 token 收益 | 否决 |

持有者规则：

- 生命周期与一个 agent 进程一一对应；agent 退出后持有者写终态记录、保留 socket 直到 `stop` 或 `observe` 读到 `process_exited` 后自行退出（默认 10 分钟空闲）。
- 持有者崩溃/被 kill：`record.json` 中 `holder_pid` 不存活 → CLI 回执 `holder-lost`；若 `last_prompt.written_at` 存在且无 `stop_reason` → `mutation_status: unknown`（绝不推导为 `not_started`）。agent 子进程此时可能仍存活，`stop --force` 用记录中的 `agent_pgid` 清理并报 `residual_pids`。
- 持有者与 CLI 之间的协议是本地 JSON 行，不是 ACP；CLI 超时（连不上 socket）报 `holder-unreachable`。

---

## 4. 命令面（统一）

全局参数 `--transport acp|pty`，默认来自 manifest `default_transport`。

| 命令 | acp 行为 | pty 行为（现有） | 备注 |
| --- | --- | --- | --- |
| `preflight` | 检查二进制 → 短生命周期探测：`initialize`（记录 `protocolVersion`、`agentCapabilities`、`authMethods`、`agentInfo.version`）→ 试探 `session/new`（`auth_required` 错误 → `login_required:true`）→ `session/close`（有能力时）→ 退出 | 现有 | 探测进程用 `NO_BROWSER=true`；结果写入回执 `transport.capabilities` |
| `start [--continue \| --resume ID]` | fork 持有者 → spawn → `initialize` → 版本校验（§7.2）→ `session/new` / `session/load` / `session/resume`；`--continue` 需 `sessionCapabilities.list` → `session/list` 取最近 → resume；能力缺失回执 `resume-unsupported` / `continue-unsupported`，不自动新建 | 现有 | 返回 `acp_session_id` |
| `send --text/stdin [--wait \| --no-wait] [--timeout S]` | `session/prompt`；默认 `--wait` 阻塞到 `stopReason` 或超时；turn 进行中再次 send → `prompt-in-progress`（事实，不排队） | 现有（不等待） | §6 |
| `wait [--timeout S]` | 等待当前 turn 终态 | `wait-unsupported` | 新命令 |
| `observe` | 会话状态摘要：进程/持有者/最后 turn/`pending_permissions[]`/`context_usage`，无 raw frame | 现有 | 两者都是 schema v3 |
| `capture [--tools \| --since CURSOR \| --full \| --lines N]` | L0–L3 分级（§6.3）；`--lines` 映射为最近 N 个事件 | 现有 | — |
| `permit --request-id ID --option ID` | 应答 `session/request_permission`；多个 pending 时必须指定 ID | `permit-unsupported`（用 `key`） | 新命令 |
| `key` | 仅 `escape` 映射为 `cancel`；其他 → `key-unsupported` | 现有 | — |
| `answer --replace-editor [--decision-id ID]` | `answer-unsupported`；文档指引：等价于新 `send`，`--decision-id` 对应 `permit --request-id` | 现有 | — |
| `cancel` | `session/cancel` → 等待 `stopReason: cancelled` ≤N 秒 → 否则 `cancel-unconfirmed` | `cancel-unsupported`（用 `key escape`） | 新命令 |
| `stop [--force]` | §7.6 序列 | 现有 | 非 force：走完协议序列等待退出；force：跳过等待直接信号 |
| `status` | 持有者/agent 进程/记录/最后事件 | 现有 | — |

`send`、`stop` 依旧不消费 advisory 字段做 gate。

---

## 5. 通道选择模型

### 5.1 第一层：Runner 给出默认与能力事实（preflight / start 回执）

```text
transport:
  selected: acp
  default: acp                     # 来自 manifest
  alternatives: [pty]
  reason: manifest-default         # manifest-default | caller-override
  protocol_version: 1
  agent_info: {name, version}
  verified_version_match: true | false | unknown
  capabilities:
    prompt: true
    cancel: true
    permission: true
    load_session: false
    resume: false
    list: false
    close: true
    set_config_option: true
  login_required: false | true | unknown
  self_hosting_risk: false         # 父进程链含同一 CLI 二进制时为 true
  quirks: [...]                    # 来自 manifest
```

### 5.2 第二层：orchestrator 选择（Skill 合同中的事实与成本提示）

| 场景 | 通常适合 | 事实依据 |
| --- | --- | --- |
| 普通 prompt、等待完成、读最终回复、权限应答、resume | acp | 回执已含终态与权限结构，无需 observe/capture 循环 |
| 首次登录、trust 目录、OAuth 浏览器流程 | pty | preflight `login_required:true`；`authenticate` 各家实现未验证 |
| 人类旁观或接管 TUI | pty | acp 无可视界面 |
| 需要原生按键（方向键、菜单） | pty | acp 无按键概念（仅 escape→cancel） |
| preflight 报二进制/`initialize`/版本不支持，或任务所需 capability 缺失 | pty | 事实驱动 |
| acp 会话连续出现 `process_exited` / `prompt_timeout` | orchestrator 判断 | Runner 只报事实 |
| `self_hosting_risk:true` | 换平台或 pty | 避免同一 CLI 驱动自身 |

措辞原则：Skill 模板只陈述事实与成本（"acp 回执已含终态，不需要再 observe"），不写"必须给出理由"之类的审计式要求。

### 5.3 第三层：失败后的 fallback 边界（重复执行防护，v0.2 重写）

1. **Runner 永不自动 fallback、永不自动重发。**
2. `mutation_status` 五态，判定绑定到可观测的写入边界：

| 状态 | 判定 | 另一通道重发同一 prompt 是否安全 |
| --- | --- | --- |
| `not_started` | spawn/initialize 失败，或 `session/prompt` 帧尚未 `write()` 成功 | 安全 |
| `in_progress` | 帧写入成功，尚未收到本 turn 任何 update | **不安全**（agent 可能已开始执行） |
| `accepted` | 收到本 turn 第一条 `session/update` 或 `session/request_permission` | 不安全 |
| `completed` | 收到 `stopReason`（任意值） | 不应重发；看 `stop_reason` 决定是否续 prompt |
| `unknown` | 持有者丢失 / 连接断且记录有 `written_at` 无 `stop_reason` | 不安全；先 `observe`/`capture --since`，必要时 `stop` |

   与 v1 `mutation_performed` 映射：`completed|accepted|in_progress → true`，`not_started → false`，`unknown → null`。
3. 切通道 = 新会话：`stop` 旧会话后在新通道 `start`。平台支持 `resume` 且 ACP session ID 与 CLI 原生 session ID 同源时可 `--resume`（Grok/Kimi/Devin 在 PoC 验证）；否则 Skill 明示上下文会丢失。
4. `duplicate-prompt-warning`：对同 platform + session + repo 的 `last_prompt.fingerprint` 做**无时限**比对，回执同时给出上次的 `transport`、`written_at`、`mutation_status`、`stop_reason`。事实，不阻断。

---

## 6. 低 token 事件精简层（acp 通道核心）

### 6.1 原则

- 事件替代轮询：`send --wait` / `wait` 阻塞到终态。
- 摘要默认、全量按需。
- 终态优先；`stop_reason` 原样透传，不折叠。
- thinking、工具 chunk、stderr 默认只给计数/摘要；失败时自动附 stderr 尾部。

### 6.2 默认 `send --wait` 回执（L0）

```text
receipt:
  schema_version: 3
  transport: {selected: acp, ...}
  acp_session_id: ...
  prompt_fingerprint: sha256:...
  outcome: turn_completed | turn_failed | turn_canceled | permission_requested | prompt_timeout | process_exited | holder_lost
  stop_reason: end_turn | max_tokens | max_turn_requests | refusal | cancelled | <未知值原样透传> | null
  mutation_status: <五态>
  mutation_performed: true | false | null
  duration_ms: ...
  final_text: "<assistant 最终回复>"           # 默认上限 4000 字符（--max-final-chars）
  final_text_truncated: false                  # true 时附 events.jsonl 路径
  tool_calls: {count: 7, kinds: {edit: 3, execute: 4}, failed: 0}
  side_effects: {files_changed: 3, commands_run: 4}   # 由 tool_call kind 推导
  failed_tools: [{title, kind, error_head}]           # 最多 3 条
  thinking_chars: 12840
  context_usage: {used, size} | null                  # 来自 usage_update
  pending_permissions: [{request_id, title, options: [{id, kind, label}]}]
  error: {code, message, stderr_tail: [...]}          # 仅失败时
  git: {...}                                          # 现有 Git 事实
  event_cursor: 143                                   # 供 capture --since
  event_log_bytes: 88213
```

Skill 模板注明：`refusal / max_tokens / max_turn_requests` 不等于任务完成。

### 6.3 `capture` 分级

| 级别 | 参数 | 内容 |
| --- | --- | --- |
| L0 | 默认 | 最近一个 turn 的 §6.2 摘要 |
| L1 | `--tools` | 工具调用列表：名称、参数摘要（截断）、状态、耗时 |
| L2 | `--since CURSOR` | 自游标起的原始 `session/update`（含未知变体） |
| L3 | `--full` | 默认只返回 `events.jsonl` 路径与大小；`--inline` 才内联 |

事件日志按 10 MB 轮转（保留 3 个），stderr 环形缓冲 64 KB + 落盘轮转；已知敏感键名（`*_API_KEY`、`*TOKEN*`、`Authorization`）在日志中脱敏。

### 6.4 pty 通道对应优化（可选，不阻塞 v2）

`observe --compact`：去 ANSI、去空行、只保留变化区域。默认行为不变。

### 6.5 Skill 合同中的成本提示（写入模板）

> acp 通道的 `send --wait` 回执已包含终态、最终回复和待处理权限；再次 `observe` 不会带来新信息。`capture --tools/--since` 用于失败排查或审计；`capture --full` 默认只返回文件路径。pty 通道每次 `observe` 都会返回整块屏幕，成本随会话增长。

---

## 7. ACP 持有者（`kaola-acp-holder.py`）设计要点

### 7.1 进程与连接

- `subprocess.Popen(..., start_new_session=True)`（不用外部 `setsid`，兼容 macOS）；stdin/stdout 管道；stderr 独立读线程。
- 环境：默认透传当前环境，manifest `acp_env_allowlist` 非空时只透传白名单 + 系统必需变量；探测进程额外注入 `NO_BROWSER=true`。
- JSON-RPC：newline-delimited；一个读线程分发 response / notification / agent→client request；非 JSON 行与半行按字节缓冲、计数并落盘，不报错。
- response id 与 request id 宽松匹配（数字 ↔ 数字字符串）。
- `cwd` 传 `--repo` 解析后的 Git top-level；与 v1 相同校验。

### 7.2 生命周期与版本协商

```text
spawn -> initialize(protocolVersion=1, clientCapabilities=manifest 值)
      -> 若 agent 返回 protocolVersion != 1 -> 回执 acp-protocol-version-unsupported{agent_version}，走 stop 序列并退出
         （客观 transport 不可能，允许拒绝）
      -> [authenticate 仅当 session/new 返回 auth_required 且 authMethods 非空且 manifest 允许]
      -> session/new(cwd, mcpServers=[]) | session/load | session/resume | session/list→resume
      -> [session/set_config_option: 模型/effort，configId 来自 manifest acp_model_config_id]
      -> loop: session/prompt -> stream session/update -> response.stopReason
      -> stop: §7.6
```

`agent_info.version` 缺失时回落 `binary --version`，两者都记入回执。

### 7.3 agent→client 请求处理（v0.2 补全）

| 请求 | 处理 |
| --- | --- |
| `session/request_permission` | 写入 `pending_permissions[]`（Map，支持多个并发），`mutation_status → accepted`；`permit` 应答；`cancel`/`stop` 时全部回 `cancelled` |
| `$/cancel_request` | 对被取消的 pending 请求返回 `-32800`，从 `pending_permissions` 移除 |
| `fs/*`、`terminal/*` | 默认 `clientCapabilities = {fs:{false,false}, terminal:false}`（规范默认，**非** Paseo 取值——Paseo 为 `terminal:true`）。仍被调用时返回 `-32601`。若某平台 wrapper（如 claude-agent-acp）需要 client terminal，在 manifest `acp_client_capabilities` 按平台开启并实现最小 terminal 服务（PoC 决定） |
| `elicitation/create` 及任何未知方法 | 返回 `-32601`，事件日志记录 |
| 未知 `sessionUpdate` 变体 | 计数、落盘，不报错 |

### 7.4 超时与死进程

- `--timeout S` 到期 → `prompt_timeout` 事实，**不自动 cancel**。
- stdout EOF / 进程退出：无论是否有 active turn 都记录 `process_exited{code, signal}`；有 active turn 时 `outcome: process_exited`，`mutation_status` 依写入边界保持（不降级为 not_started）。
- `cancel`：等待 `stopReason: cancelled` ≤N 秒；超时 → `cancel-unconfirmed`。`cancel` 与 `end_turn` 竞态：以先到的 `stopReason` 为准，回执透传。
- stderr 高速输出：独立线程持续读，避免管道填满阻塞 agent。

### 7.5 平台 quirk 承载位置

全部放在 manifest `acp_quirks` 与持有者的平台钩子，不进入 Skill 模板与 orchestrator 视野。初始清单：

- cursor：commands/models 异步发布；v2 不等待目录。
- kimi：不做模型目录探测；`--model/--effort` 通过 `acp_model_config_id` 下发（PoC 记录实际 configId）。
- devin：resume 必传 `sessionId + cwd + mcpServers`。
- claude-code：wrapper pin；需 `CLAUDE_CODE_EXECUTABLE`；npx 首次下载可能超时 → preflight 报 `wrapper-fetch-timeout`；可能需要 `terminal:true`。
- 所有平台：`acp_verified_versions` 记录已验证的 CLI 版本与协商到的 `protocolVersion`；preflight 报 `verified_version_match`（事实）。

### 7.6 stop 序列（v0.2 重写）

```text
非 force：
  1. 所有 pending permission 回 cancelled
  2. 有 active turn → session/cancel，等 stopReason ≤ N 秒
  3. sessionCapabilities.close → session/close
  4. 关闭 agent stdin（EOF），等进程退出 ≤ N 秒
  5. SIGTERM 进程组，等 ≤ N 秒
  6. SIGKILL 进程组
  7. 扫描进程组内残留（含 npx→node→claude→shell 子链），回执 residual_pids[]（事实）
  8. 写终态记录，持有者退出，socket 清理
force：从第 5 步开始，仍执行 1（best effort，不等待）与 7、8
```

macOS：不依赖 `/proc`；进程枚举用 `ps -o pid,pgid`（现有 `PS_BIN` 覆盖机制）。

---

## 8. 回执 schema v3

- 字段名 `schema_version: 3`（与 v1 `schema_version: 2` 同一字段；不使用 `protocol_version`，避免与 ACP 的 `protocolVersion` 混淆）。
- schema v2 全部字段保留且语义不变。pty 通道输出 = v1 输出 + `transport` 段 + `mutation_status`。
- acp 通道下：`raw_current_frame`、`pane_*`、`relay` 为 `null`；**`snapshot_id: null`**（不复用）；新增 `event_cursor`（整数）配合 `capture --since`。
- `mutation_performed` 保留，按 §5.3 映射。
- advisory 映射：`native_approval` 在 acp 下为 null，`decision_id` → `pending_permissions[].request_id`；`activity_hint` 在 acp 下由 `outcome` 派生（`in_progress/accepted → busy`，`completed → idle`，`permission_requested → waiting`）。
- 新增字段（两通道通用）：`transport`、`mutation_status`、`stop_reason`、`pending_permissions`、`event_cursor`。

---

## 9. 文件与仓库影响（仅列出，不实现）

| 变更 | 类型 | 说明 |
| --- | --- | --- |
| `scripts/kaola-acp.py` | 新增 | CLI / socket 客户端 |
| `scripts/kaola-acp-holder.py` | 新增 | 每会话持有者 |
| `scripts/kaola-tmux.sh` | 修改 | `--transport` 分发；pty 回执加 `transport`、`mutation_status` |
| `platforms/*.yaml` | 修改 | **保持 flat 解析器**，新增前缀键（值均为 JSON 字符串）：`default_transport`、`acp_command`、`acp_client_capabilities`、`acp_quirks`、`acp_verified_versions`、`acp_env_allowlist`、`acp_login_requires_pty`、`acp_model_config_id`、`acp_wrapper_pin` |
| `scripts/render-skills.py` | 修改 | 读取上述键并校验；`--check` 覆盖 |
| `templates/SKILL.md.tmpl` | 修改 | 新增变量：`{{DEFAULT_TRANSPORT}}`、`{{ACP_COMMAND}}`、`{{ACP_QUIRKS}}`、`{{ACP_LOGIN_REQUIRES_PTY}}`；通道事实段、成本提示段、fallback 规则段 |
| `templates/references/transport.md.tmpl` | 修改 | 改名语义为 pty 通道说明 |
| `templates/references/acp.md.tmpl` | 新增 | acp 通道命令、回执字段、`mutation_status` 表 |
| `tests/contract/mock-acp-agent.py` | 新增 | 纯 Python mock agent：可脚本化延迟、半行、崩溃、多 permission、`$/cancel_request`、拒绝版本、未知方法调用 |
| `tests/contract/test-acp-contract.py` | 新增 | 启动 mock，覆盖 §7.3/§7.4/§7.6 全部分支 |
| `scripts/validate.sh` | 修改 | 接入上述合同测试（离线、快速） |
| `docs/architecture.md`、`docs/api.md` | 修改 | — |
| `templates/grok-golden/` | **不动** | Grok 默认 acp 只影响 `skills/grok-*` 渲染输出，不影响 golden |
| `skills/` | 生成 | 不手编 |

---

## 10. PoC 与验收

### 10.1 PoC 范围

平台：Grok（原生 ACP、最简单）+ Kimi（有 trust UI，验证 pty 兜底）。其余四平台 `default_transport: pty`，preflight 报告 acp 事实。

live 场景：

1. 普通 prompt → `send --wait` → `final_text`、`stop_reason: end_turn`。
2. 触发权限请求 → `pending_permissions` → `permit`。
3. 长任务 → `wait --timeout` → `prompt_timeout` → `cancel` → `stopReason: cancelled`。
4. `stop` 非 force → 进程组零残留（`residual_pids: []`）。
5. `--resume` 成功 / `resume-unsupported`；`--continue` 有/无 `session/list`。
6. 未登录 → preflight `login_required:true` → pty 登录 → acp。
7. acp spawn 失败 → `mutation_status: not_started` → pty 重发。
8. pty 完成后误用 acp 重发同一 prompt → `duplicate-prompt-warning`（含上次 transport/时间/状态）。
9. turn 进行中再次 `send` → `prompt-in-progress`。
10. 持有者被 kill → `observe` 回执 `holder-lost`、`mutation_status: unknown` → `stop --force` 清理。
11. `--repo` 非 canonical git root → 与 v1 相同的拒绝事实。
12. 同名会话跨两个 repo 并发 → 记录互不覆盖。
13. Grok/Kimi 的 `configOptions` 实际 id 记录到 manifest。

mock 合同场景（validate.sh，离线）：permission pending 时 agent 死亡；半行/非 JSON 行；stderr 高速输出；`cancel` 与 `end_turn` 竞态；`$/cancel_request` 级联；`protocolVersion: 2`；agent 调用 `fs/*`/`elicitation/create` → `-32601`；数字字符串 id；多 permission 并发。

### 10.2 度量（同一任务，acp vs pty 各 ≥5 次，报中位数）

- 送入 orchestrator 的 UTF-8 字节数 + 固定 tokenizer（cl100k）token 数。
- Runner 命令调用次数。
- orchestrator 推理轮数。
- 端到端时长。
- 失败恢复次数及 `mutation_status` 准确率。

### 10.3 验收标准

- `./scripts/validate.sh`、`render-skills.py --check` 全绿；pty live smoke 与 v1 一致（仅新增字段）。
- mock 合同测试覆盖 §7.3、§7.4、§7.6 全部分支。
- Grok/Kimi live：§10.1 十三个场景全部产出预期回执。
- Claude Code：当前无有效账号，live 验收标 `PRECONDITION-NOT-MET`，条件通过；条件为账号可用后跑通场景 1–4。
- token 度量报告出具后，再决定其余四平台是否切默认 acp。

---

## 11. 风险清单

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| 各家 ACP 实现随版本漂移 | 行为突变 | `acp_verified_versions` + mock 合同测试 + CHANGELOG COMPAT 标记 |
| ACP v2 协议迁移 | v1 客户端失效 | 只协商 v1，版本不符明确拒绝；跟踪 v2 稳定后另立设计 |
| 持有者进程崩溃 | 状态丢失 | 记录由持有者持续写入；`holder-lost` + `unknown` 口径；`stop --force` 按记录清理 |
| `session/prompt` 无超时 | 挂死 | `--timeout` 事实 + `cancel`；orchestrator 决定 `stop` |
| resume 与 CLI 原生 session 不同源 | 切通道丢上下文 | PoC 验证；`resume-unsupported` 明示 |
| 双通道重复执行 | 重复改代码 | 五态 `mutation_status` 绑定写入边界 + 无时限 `duplicate-prompt-warning` |
| 事件流原样透传导致 token 反升 | 违背 G1 | L0 默认；`final_text` 上限；`--full` 只给路径 |
| Claude 依赖 npx wrapper | 供应链/离线 | pin 版本；`wrapper-fetch-timeout` 事实；无账号时条件验收 |
| 未声明 `fs/terminal` 导致 wrapper 功能退化 | 工具不可用 | 规范默认值 + `-32601`；按平台在 manifest 开启 |
| 事件日志含敏感信息 | 泄露 | 已知键名脱敏；日志轮转与大小上限；`acp_env_allowlist` |
| 同一 CLI 驱动自身（Devin/Codex 递归） | 凭据/工作区冲突 | preflight `self_hosting_risk` 事实；Skill 提示 |
| tree-kill 不彻底（npx→node→shell 子链） | 残留进程 | 进程组信号 + 残留扫描 + `residual_pids` 报告 |
| macOS 兼容 | 运行失败 | 不依赖 `/proc`、`setsid`、`XDG_RUNTIME_DIR` |
| orchestrator 习惯性选 pty | 收益落空 | 默认 acp + 成本事实提示；`transport.reason` 可审计 |
| 与 v1 relay 并存增加维护面 | 复杂度 | pty 层冻结；新增只在 acp 层 |

---

## 12. 评审结论与已采纳决定

独立评审（ultra 模式子 session）对 v0.1 结论为 needs_rework；v0.2 已采纳全部 blocking/major 建议与绝大多数 minor 建议。对 v0.1 §12 七个待评审问题的最终决定：

1. `mutation_status` → 五态，`not_started` 仅指帧未写入；持有者丢失一律 `unknown`。
2. `clientCapabilities` → 显式声明规范默认值，未知请求回 `-32601`；按平台可开启 terminal。
3. `snapshot_id` → acp 下 null；新增 `event_cursor`；版本字段 `schema_version: 3`。
4. `send --wait` → 保留，属协议原生请求-响应，不是策略层；Skill 措辞改为成本事实提示。
5. Claude Code → 走 `claude-agent-acp` wrapper（pin），不引入 `stream-json` 第三 transport。
6. 默认通道 → PoC 前仅 Grok/Kimi 为 acp。
7. 命令等价物 → `key escape → cancel`；`decision_id → request_id`；`--continue → session/list`；`--lines → 事件数`。

未采纳/保留意见：无。

下一步：用户确认 v0.2 后进入 PoC（Grok + Kimi），PoC 报告出具后再决定其余四平台默认通道与正式实现排期。
