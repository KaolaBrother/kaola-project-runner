# Kaola Project Runner v2 设计文档：ACP 优先、tmux 兜底的双通道架构

状态：v0.3 实施基线（PoC #15 已验证；本版按实测事实修正并锁定生产实现范围）
范围：设计与决策；PoC 代码已在仓库（§9 标注"已有 / 待做"）
日期：2026-09-11

> v0.2 → v0.3 变更摘要（依据 `docs/poc-acp-transport-2026-09-11.md`）
> - 默认通道决定：原生 ACP 五平台（Grok / Kimi / Cursor / Devin / OpenCode）`default_transport: acp`，Claude Code 保持 `pty`（§5.1、§12）
> - `--continue` 改为 `session/load` 最近记录的 `acp_session_id`；`session/list` / `session/resume` / `session/close` 在 Grok/Kimi 上均不存在（§4、§7.2）
> - permission 流程在实跑中未触发（Grok `always-approve`；Kimi `mode=default` 亦不发 `request_permission`）：`permit` 机制保留（mock 覆盖），live 验收改为条件项（§10.3）
> - 持有者 socket 改为 `$TMPDIR/kaola-<uid>-acp/<hash>.sock`，记录目录内 `holder.sock` 为 symlink（§3.2）
> - `configOptions` 落在 `session/new` 结果，记入 `session_meta`；manifest `acp_model_config_id` 取实测 id（§7.5）
> - Grok 不发 `agentInfo` / `usage_update`，`session_info_update` 为 Grok 私有变体（§7.3、§7.5）
> - 跨通道 `duplicate-prompt-warning` 需 pty 侧 journal `last_prompt`（issue #18，§5.3）
> - §9 文件影响表按"PoC 已有 / 生产待做"重排；§10 以 PoC 结论替换 PoC 计划，新增生产验收
>
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

Runner v2 向 orchestrator 同时暴露两条通道——**`acp`** 与 **`pty`（现有 tmux/nested-PTY relay）**——共用同一套会话身份、命令面与回执 schema。Runner 只负责"通道能力事实 + 机械传输 + 事件精简"，通道的**选择权**归 orchestrator；Runner 通过默认值与成本事实提示引导它用最少 token 完成任务。PoC 实测 acp 比 pty 少约 12× 字节 / token（§10.2）；据此原生 ACP 五平台默认 acp，Claude Code（npx wrapper）默认 pty 但报告 acp 可用性。

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
| platform manifest | `default_transport`、`acp_command`、`acp_client_capabilities`、`acp_quirks`、`acp_verified_versions`、`acp_env_allowlist`、`acp_login_requires_pty`、`acp_model_config_id`、`acp_effort_config_id`、`acp_wrapper_pin`（完整表见 §9.2） | 运行时探测结果 |
| `kaola-acp.py`（CLI） | 解析命令、连接持有者 socket、格式化回执 | 持有 stdio |
| `kaola-acp-holder.py`（每会话持有者，纯 Python 3） | spawn、stdio JSON-RPC、读线程、事件日志、pending permission、权限应答、cancel、stop 序列 | 判断任务完成、是否 fallback |
| `kaola-tmux.sh` + relay | 不变 | — |
| 回执 schema v3 | 两通道共用字段 + `transport` 段 + `mutation_status` | — |

### 3.2 会话身份与记录

- 会话名仍为 `--session NAME`，正则不变；身份仍是 platform + session + repo 三元组。
- 会话记录目录：`${KAOLA_ACP_RECORD_ROOT:-${XDG_RUNTIME_DIR:-${TMPDIR:-/tmp}}/kaola-<uid>}/<platform>/<session>/<sha256(repo)[:16]>/`，含 `record.json`、`holder.sock`、`events.jsonl`、`stderr.log`。
- **socket 真身**在 `$TMPDIR/kaola-<uid>-acp/<sha256(record_dir)[:24]>.sock`（macOS AF_UNIX `sun_path` 约 104 字节，记录目录路径可能超长）；记录目录内的 `holder.sock` 是指向它的 symlink（PoC 实测修正）。
- `record.json` 字段：`transport`、`platform`、`repo`、`holder_pid`、`agent_pid/pgid`、`acp_session_id`、`protocol_version`、`agent_info{name,version}`、`session_meta`（`session/new` 结果，含 `configOptions`）、`created_at`、`last_prompt{fingerprint, written_at, transport, mutation_status, stop_reason}`、`pending_permissions[]`。
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
| `start [--continue \| --resume ID]` | fork 持有者 → spawn → `initialize` → 版本校验（§7.2）→ `session/new` / `session/load` / `session/resume`；`--resume ID` 优先 `session/resume`（有能力时），否则 `session/load`；`--continue` 读取同一 platform + session + repo 记录中的上一个 `acp_session_id` 并按同样规则恢复，无记录 → `continue-empty`；能力缺失回执 `resume-unsupported` / `continue-unsupported`，不自动新建 | 现有 | 返回 `acp_session_id`。PoC 实测 Grok/Kimi 仅有 `loadSession`，无 `session/list`，故 `--continue` 不再依赖 `session/list` |
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

manifest `default_transport`（v0.3 决定）：

| 平台 | default_transport | 依据 |
| --- | --- | --- |
| Grok | `acp` | PoC live 11/13 PASS，Part C 12× |
| Kimi CLI | `acp` | PoC live 11/13 PASS |
| Cursor CLI | `acp` | 原生 `cursor-agent acp`（Paseo 生产路径）；生产实现中以 preflight + 场景 1/3/4/7 实跑补证据 |
| Devin CLI | `acp` | 原生 `devin acp`；同上；`self_hosting_risk` 在 Devin 驱动 Devin 时为 true |
| OpenCode | `acp` | 原生 `opencode acp`（官方文档）；同上 |
| Claude Code | `pty` | 依赖 npx wrapper（供应链、首次下载超时、可能需要 `terminal:true`）且当前无有效账号；preflight 仍报告 acp 事实 |

任一平台若在实跑中 preflight `initialize` 失败或版本不支持，回执事实即可让 orchestrator 选 pty；不为此改 manifest 默认值。

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
4. `duplicate-prompt-warning`：对同 platform + session + repo 的 `last_prompt.fingerprint` 做**无时限**比对，回执同时给出上次的 `transport`、`written_at`、`mutation_status`、`stop_reason`。事实，不阻断。PoC 只验证了 acp→acp；pty→acp 需要 `kaola-tmux.sh send` 把 `last_prompt{transport: pty}` journal 到同一身份记录（issue #18，生产实现项）。

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
      -> session/new(cwd, mcpServers=[]) | session/resume(有能力) | session/load(记录中的 acp_session_id)
      -> [session/set_config_option: 模型/effort，configId 来自 manifest acp_model_config_id]
      -> loop: session/prompt -> stream session/update -> response.stopReason
      -> stop: §7.6
```

`agent_info.version` 缺失时回落 `binary --version`，两者都记入回执（PoC 实测 Grok 1.0.25 不返回 `agentInfo`，此回落是必需路径）。
`session/new` 结果中的 `configOptions` 原样记入 `session_meta`，回执 `transport.config_options` 只给 `[{id, current}]` 摘要。

### 7.3 agent→client 请求处理（v0.2 补全）

| 请求 | 处理 |
| --- | --- |
| `session/request_permission` | 写入 `pending_permissions[]`（Map，支持多个并发），`mutation_status → accepted`；`permit` 应答；`cancel`/`stop` 时全部回 `cancelled` |
| `$/cancel_request` | 对被取消的 pending 请求返回 `-32800`，从 `pending_permissions` 移除 |
| `fs/*`、`terminal/*` | 默认 `clientCapabilities = {fs:{false,false}, terminal:false}`（规范默认，**非** Paseo 取值——Paseo 为 `terminal:true`）。仍被调用时返回 `-32601`。若某平台 wrapper（如 claude-agent-acp）需要 client terminal，在 manifest `acp_client_capabilities` 按平台开启并实现最小 terminal 服务（PoC 决定） |
| `elicitation/create` 及任何未知方法 | 返回 `-32601`，事件日志记录 |
| 未知 `sessionUpdate` 变体 | 计数、落盘，不报错（实测：Grok 发私有 `session_info_update`；Grok 不发 `usage_update`，Kimi 发） |

### 7.4 超时与死进程

- `--timeout S` 到期 → `prompt_timeout` 事实，**不自动 cancel**。
- stdout EOF / 进程退出：无论是否有 active turn 都记录 `process_exited{code, signal}`；有 active turn 时 `outcome: process_exited`，`mutation_status` 依写入边界保持（不降级为 not_started）。
- `cancel`：等待 `stopReason: cancelled` ≤N 秒；超时 → `cancel-unconfirmed`。`cancel` 与 `end_turn` 竞态：以先到的 `stopReason` 为准，回执透传。
- stderr 高速输出：独立线程持续读，避免管道填满阻塞 agent。

### 7.5 平台 quirk 承载位置

全部放在 manifest `acp_quirks` 与持有者的平台钩子，不进入 Skill 模板与 orchestrator 视野。初始清单：

- grok（实测 1.0.25）：`configOptions` = `model`{grok-4.6, grok-4.5} + `reasoning_effort`{xhigh, high, medium, low}；无 `agentInfo`、无 `usage_update`、私有 `session_info_update`；无 approval configOption，`always-approve`；仅 `loadSession`。`acp_model_config_id: "model"`，effort 走 `reasoning_effort`。
- kimi（实测 0.41.0）：`configOptions` = `model`{kimi-for-coding, kimi-for-coding-highspeed, k3, k3-256k} + `thinking`{low, high, max} + `mode`{default, plan, auto, yolo}；`mode=default` 实测不发 `request_permission`；仅 `loadSession`。`acp_model_config_id: "model"`，effort 走 `thinking`。不做模型目录探测。
- cursor：commands/models 异步发布；v2 不等待目录。
- devin：resume 必传 `sessionId + cwd + mcpServers`。
- claude-code：wrapper pin；需 `CLAUDE_CODE_EXECUTABLE`；npx 首次下载可能超时 → preflight 报 `wrapper-fetch-timeout`；可能需要 `terminal:true`。
- 所有平台：`acp_verified_versions` 记录已验证的 CLI 版本与协商到的 `protocolVersion`；preflight 报 `verified_version_match`（事实）。Cursor / Devin / OpenCode / Claude Code 的 configOption id 在生产实现 preflight 实跑后补入。

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

## 9. 文件与仓库影响

### 9.1 PoC 已有（commit `13b5770`，issue #15）

| 文件 | 状态 | 说明 |
| --- | --- | --- |
| `scripts/kaola-acp.py` | 已有 | CLI / socket 客户端；平台 → ACP 命令目前**硬编码** `DEFAULT_COMMANDS = {grok, kimi-cli}`（生产待改为读 manifest） |
| `scripts/kaola-acp-holder.py` | 已有 | 每会话持有者；§3.3 / §7 全部分支 |
| `tests/contract/mock-acp-agent.py` | 已有 | 12 场景 mock agent |
| `tests/contract/test-acp-contract.py` | 已有 | 13 测试，接入 `validate.sh` |
| `scripts/validate.sh` | 已有 | 已调用 acp 合同测试 |

### 9.2 生产待做（issue #17 拆分项）

| 变更 | 类型 | 说明 | 归属 |
| --- | --- | --- | --- |
| `platforms/*.yaml` | 修改 | **保持 flat 解析器**，新增前缀键（值均为 JSON 字符串）：`default_transport`、`acp_command`、`acp_client_capabilities`、`acp_quirks`、`acp_verified_versions`、`acp_env_allowlist`、`acp_login_requires_pty`、`acp_model_config_id`、`acp_effort_config_id`、`acp_wrapper_pin` | A |
| `scripts/render-skills.py` | 修改 | `REQUIRED` 纳入上述键并校验取值；`--check` 覆盖 | A |
| `templates/SKILL.md.tmpl` | 修改 | 新增变量：`{{DEFAULT_TRANSPORT}}`、`{{ACP_COMMAND}}`、`{{ACP_QUIRKS}}`、`{{ACP_LOGIN_REQUIRES_PTY}}`；通道事实段、成本提示段（§6.5）、fallback 规则段（§5.3） | A |
| `templates/references/transport.md.tmpl` | 修改 | 语义收窄为 pty 通道说明 | A |
| `templates/references/acp.md.tmpl` | 新增 | acp 通道命令、回执字段、`mutation_status` 表 | A |
| `tests/contract/test-generated-skills.py` | 修改 | 断言六个 Skill 渲染出通道段与正确默认值 | A |
| `scripts/kaola-acp.py` | 修改 | 删除 `DEFAULT_COMMANDS` 硬编码，从 `platforms/<id>.yaml` 读取 `acp_command` 等键（与 `kaola-tmux.sh` 同一解析口径） | B |
| `scripts/kaola-tmux.sh` | 修改 | 全局 `--transport acp\|pty`，默认取 manifest；acp → exec `kaola-acp.py`；pty 回执加 `transport` 段与 `mutation_status`（schema v3 超集） | B |
| `scripts/kaola-observation.py` | 修改 | pty 回执 `schema_version: 3`、`transport`、`mutation_status` 映射（§8） | B |
| `scripts/kaola-tmux.sh send` | 修改 | 向同一身份记录 journal `last_prompt{transport: pty}`（issue #18） | B |
| `scripts/render-skills.py`、`scripts/install-local.sh` | 修改 | 生成的 `skills/*/scripts/` 打包 `kaola-acp.py` + `kaola-acp-holder.py`；安装迁移测试覆盖 | B |
| `docs/architecture.md`、`docs/api.md`、`README.md` | 修改 | 双通道命令面、schema v3 | A/B 各自 dock |
| `platforms/*.yaml acp_verified_versions` | 修改 | Cursor / Devin / OpenCode / Claude Code 实跑 preflight + 场景 1/3/4/7 后写入版本与 configOption id | C |
| `templates/grok-golden/` | **不动** | Grok 默认 acp 只影响 `skills/grok-*` 渲染输出，不影响 golden | — |
| `skills/` | 生成 | 不手编 | — |

---

## 10. PoC 结论与生产验收

### 10.1 PoC 结论（issue #15，详见 `docs/poc-acp-transport-2026-09-11.md`）

平台：Grok 1.0.25 + Kimi 0.41.0。十三个 live 场景：

| # | 场景 | 结果 |
| --- | --- | --- |
| 1 | prompt → `send --wait` → `final_text` / `end_turn` | PASS × 2 |
| 2 | 权限请求 → `pending_permissions` → `permit` | **未触发**：两家默认自动批准；仅 mock 覆盖 |
| 3 | `prompt_timeout` → `cancel` → `cancelled` | PASS × 2 |
| 4 | `stop` 非 force → `residual_pids: []` | PASS × 2 |
| 5 | `--resume` / `--continue` | `session/load` 成功、上下文保留；`session/list` 缺失 → 改为记录内 `acp_session_id`（§4） |
| 6 | 未登录 → `login_required:true` | PRECONDITION-NOT-MET（凭据已缓存） |
| 7 | spawn 失败 → `not_started` → pty 重发 | PASS |
| 8 | 跨通道 `duplicate-prompt-warning` | acp→acp PASS；pty→acp 需 #18 |
| 9 | `prompt-in-progress` | PASS × 2 |
| 10 | 持有者 kill → `holder_lost` / `unknown` → `stop --force` | PASS × 2 |
| 11 | 非 canonical `--repo` 拒绝 | PASS × 2 |
| 12 | 同名会话跨 repo 记录独立 | PASS × 2 |
| 13 | `configOptions` id | 已记入 §7.5 |

离线合同（`test-acp-contract.py`）：13/13，覆盖 §7.3 / §7.4 / §7.6 全部分支。

### 10.2 度量结果（"reply PONG"，5 次中位数）

| 指标 | acp | pty | 比值 |
| --- | --- | --- | --- |
| 送入 orchestrator 字节 | 2,453 | 29,982 | 12.2× less |
| cl100k token | 791 | 9,313 | 11.8× less |
| Runner 调用次数 | 3 | 6 | 2× fewer |
| observe 读取 | 0 | 3 | 轮询消除 |
| 端到端 | 7.9 s | 13.1 s | 1.7× faster |

### 10.3 生产验收标准

- `./scripts/validate.sh`、`render-skills.py --check` 全绿；`templates/grok-golden/` 字节不变。
- pty 通道 live smoke 与 v1 行为一致，回执仅新增 `transport`、`mutation_status`（schema v3 超集）。
- 六个生成 Skill 均含通道事实段、成本提示段、fallback 规则段，`default_transport` 与 §5.1 表一致。
- `kaola-tmux.sh <platform> --transport acp` 与直接调用 `kaola-acp.py` 回执一致；`skills/*/scripts/` 打包 acp 脚本，`install-local.sh` 安装后可用。
- Cursor / Devin / OpenCode：各自 live 跑通场景 1 / 3 / 4 / 7，`acp_verified_versions` 写入实测版本与 configOption id。
- Claude Code：无有效账号时 preflight 报 acp 事实（wrapper 可拉取 / `wrapper-fetch-timeout`），live 标 `PRECONDITION-NOT-MET`，条件为账号可用后跑通场景 1–4。
- 权限流程：至少在一个平台的严格模式（候选：Kimi `mode=plan`）下尝试触发 `session/request_permission`；触发则跑通场景 2，不触发则记录事实，`permit` 继续以 mock 为准。
- pty→acp `duplicate-prompt-warning`（#18）live 复现一次。

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
6. 默认通道 → PoC 前仅 Grok/Kimi 为 acp。（v0.3 更新，见下）
7. 命令等价物 → `key escape → cancel`；`decision_id → request_id`；`--continue → session/list`（v0.3 改为 `session/load`）；`--lines → 事件数`。

未采纳/保留意见：无。

### v0.3 决定（PoC 后，用户确认 2026-09-11）

1. **默认通道**：原生 ACP 五平台（Grok / Kimi / Cursor / Devin / OpenCode）`default_transport: acp`；Claude Code `pty`。依据：12× token 实测；五家 ACP 入口均为 CLI 原生子命令，Claude 依赖第三方 npx wrapper 且无账号可验。
2. **`--continue`**：不再依赖 `session/list`；读取同一身份记录的上一个 `acp_session_id` 走 `session/load`（或 `session/resume`）。
3. **permission**：`permit` / `pending_permissions` 机制按 v0.2 保留，生产验收改为条件项（§10.3）；不为"未触发"引入新 gate。
4. **socket 路径**：短路径真身 + 记录目录 symlink（§3.2）。
5. **模型下发**：manifest 拆 `acp_model_config_id` 与 `acp_effort_config_id`（Grok `model`/`reasoning_effort`，Kimi `model`/`thinking`），对应现有 `--model/--effort` 语义。
6. **实施拆分**：§9.2 归属 A（manifest / 模板 / renderer 合同）、B（`kaola-tmux.sh --transport` 分发、pty schema v3、去硬编码、打包安装、#18）、C（Cursor / Devin / OpenCode / Claude Code 实跑与 `acp_verified_versions`、permission 严格模式探测）。A 与 B 可并行，C 依赖 A + B。

下一步：按 §9.2 A / B / C 建立 issue，用 Kaola-Workflow 逐个跑通；§10.3 全部满足后本设计转为 `docs/architecture.md` / `docs/api.md` 的正式内容。
