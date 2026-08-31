# Kaola Project Runner

Kaola Project Runner 是一组面向 Codex 的 CLI 通信驱动 Skill。每个 Skill 只负责在所有权可验证的
tmux 主会话中启动指定 CLI、读取输出、传递控制 Agent 选择的提示词或原生按键、读取真实回复，
以及结束这个精确会话。

`templates/grok-golden/` 保留已经实跑验证的历史 Grok Workflow 提示词与协议字节，作为兼容和
回归证据；它们不再是 active Skill 强制执行的编排规则。五个平台的 active Skill 都从同一份
通信模板生成。是否发送 `workflow-next`、选择什么命令、是否创建 heartbeat、如何编排、重试和
收口，全部由读过现场证据的控制 Agent 决定。

每个新会话由一个受管 nested-PTY relay 承载：relay 是 tmux pane leader，目标 CLI 是其 nested-PTY
子进程。Runner 采集 raw frame、tmux/process/relay、输入输出、仓库与 Workflow 事实；控制 agent
解释这些证据并决定何时输入、如何读取回复以及如何处理运行中的问题。Skill 只发现、传递和回读，
不定义状态也不阻止 agent 选择的动作。坐标、固定文案、snapshot 变化、`activity`、editor/approval
标签、worker 计数、Git 和 Workflow 解释都不是写操作的 hardgate。

## 支持的平台

| Platform | Codex Skill | CLI | Runner 默认主模型 | runtime-native recurring |
|---|---|---|---|---|
| Grok CLI | `$grok-kaola-project-runner` | `grok` | Grok 4.6, xhigh, non-FAST | supported，需显式请求 |
| Claude Code | `$claude-code-kaola-project-runner` | `claude` | Opus 5, high | unsupported |
| OpenCode | `$opencode-kaola-project-runner` | `opencode` | GLM 5.3, max | unsupported |
| Kimi CLI | `$kimi-cli-kaola-project-runner` | `kimi` | K3, max | unsupported |
| Cursor CLI | `$cursor-cli-kaola-project-runner` | `cursor-agent` | Cursor Grok 4.6, xhigh, non-FAST | unsupported |

裸调用统一表示：使用当前目录所在的 canonical Git repository，启动或恢复该平台的精确
tmux session 并返回可读证据。它不会隐式发送 `workflow-next`、materialize 项目文件、创建
15 分钟 heartbeat、选择任务模式或启动循环。

## 本地安装

```bash
./scripts/render-skills.py --write
./scripts/render-skills.py --check
./scripts/install-local.sh
```

默认安装全部五个平台，也可以选择一个或多个：

```bash
./scripts/install-local.sh --platform grok,opencode
./scripts/install-local.sh --platform claude-code
./scripts/install-local.sh --uninstall
```

安装目标是 `${CODEX_HOME:-$HOME/.codex}/skills/<skill-name>`。旧的
`grok-kaola-project-runner -> <repository-root>` 只有在 canonical target 精确等于当前仓库根
时才会迁移。其他 symlink、普通文件、目录和 dangling link 均拒绝覆盖；卸载也只移除精确指向
本仓库生成目录的 owned symlink。

## 快速使用

```text
$grok-kaola-project-runner
$claude-code-kaola-project-runner
$opencode-kaola-project-runner
$kimi-cli-kaola-project-runner
$cursor-cli-kaola-project-runner
```

控制 Agent 负责理解输出并选择下一条输入；目标 CLI 负责执行收到的输入；当 Agent 选择使用
Kaola Workflow 时，Workflow 才负责 claim、mission list、finalize、Issue/PR、archive 和 sink。
Runner 本身不设默认 heartbeat，也不解释 `HUMAN_DECISION_REQUIRED`；它只提供读写通道。

## 控制接口

```bash
scripts/kaola-tmux.sh grok preflight \
  --repo /absolute/path/to/repo --session grok-kaola-example

scripts/kaola-tmux.sh opencode start \
  --repo /absolute/path/to/repo --session opencode-kaola-example

scripts/kaola-tmux.sh opencode start \
  --repo /absolute/path/to/repo --session opencode-user-model \
  --model zhipuai-coding-plan/glm-5.3 --effort max

scripts/kaola-tmux.sh cursor-cli status \
  --repo /absolute/path/to/repo --session cursor-cli-kaola-example

scripts/kaola-tmux.sh opencode send \
  --repo /absolute/path/to/repo --session opencode-kaola-example \
  --text 'continue'

scripts/kaola-tmux.sh kimi-cli key \
  --repo /absolute/path/to/repo --session kimi-cli-kaola-example \
  --key up
```

命令为 `preflight`、`start`、`observe`、`status`、`capture`、`send`、`key`、`answer`、`stop`。`observe`
返回 schema-v2 `raw_current_frame`、`hard_evidence`、进程/approval/decision 提示、relay byte revisions
和 opaque snapshot。它们只供 agent 参考，不定义平台状态，也不授权或阻断普通 `send`/`stop`。
snapshot 是可选的证据关联：若传入，紧凑回执只在 `based_on_snapshot` 原样返回，不把它变成
freshness gate。prompt 通过 relay
literal/bracketed-paste transport 传输，不经过 shell 求值。
每次 `start` 都先解析主模型：当前请求显式传入的 `--model/--effort` 优先，否则使用上表的
Runner default；不会把 CLI 保存的 picker/config 冒充默认值。模型不可读或不匹配只作为 Agent
的事实输入，不会封锁已有会话的普通通信；Runner 也从不自动发送 `workflow-next`。
CR、ESC、DEL 与其他终端 C0/C1 控制字会在任何子 PTY 写入前被拒绝；LF/TAB 只有在 CLI 已明确
启用 bracketed paste 时才允许。跨出原 child PGID 的后代会在只读 observation 中按启动指纹
登记，供 force-stop 终态证明使用；它们不会因此暂停或阻断普通发送。send 回执记录实际传输的
payload fingerprint；语义是否合适、如何处理
retained draft、approval、login/trust 或 active output，都由读过完整 frame 的 agent 判断，Skill
不把任何一种观察转成阻止动作的规则。

`key --key <name>` 传递 Agent 明确选择的 `up/down/left/right/enter/escape/tab/backtab/space`，
不附加 Enter、不解释选项语义，并回报 exact byte fingerprint。这取代了 Kimi 实跑历史里为通过
trust UI 而不得不使用的 raw `tmux send-keys Up Enter` 旁路。

发送后必须再次 `observe`/`capture` 读取真实回复，不能把 Enter 回执当成功。Workflow 启动要从
`workflow-state.md`、`mission-list.md`、branch/worktree 与 forge claim 验证；收口还要验证 sink、
Issue/PR、claim cleanup、archive 和零 Runner residue。普通通信不建立 lease、恢复事务或
later-output barrier；无法确认是否发生部分写入时，回执把 `mutation_performed` 报告为 `null`。

`answer --replace-editor` 是经过实测的 whole-editor transport capability；目前只有 Claude Code
adapter 支持，其余平台会如实报告 `answer-unsupported`，由 agent 选择其他路线。decision ID、
snapshot 与已有 later-output barrier 都是关联证据，不是后续动作 hardgate。旧 relay session
仍可读取；发送时会精确报告 `relay-upgrade-required`，由 agent 在安全边界决定是否只重启该精确
会话，Runner 不会自动迁移或终止它。

`scripts/grok-tmux.sh` 是 frozen Grok surface 的兼容包装器，等价于
`scripts/kaola-tmux.sh grok ...`，并保留旧 marker 与 `grok_tui` 状态字段。

Cursor CLI 的 `preflight` 与 `start` 都不物化或改写项目文件。已安装的 Workflow commands、
authority receipt 和项目级 commands 只作为证据报告；需要 materialize 时由控制 Agent 显式选择
相应工具，而不是 Runner 启动 CLI 的前置 hardgate。

## 仓库结构

- `templates/SKILL.md.tmpl`：五个平台共用的 active 通信驱动合同；
- `templates/grok-golden/`：已实跑验证、字节冻结的历史 Grok Workflow 协议和提示词证据；
- `platforms/*.yaml`：五个平台的固定事实与能力声明；
- `templates/agents/`、`templates/references/platform.md.tmpl`：UI 与 adapter facts 模板；
- `scripts/adapters/`：binary、preflight、启动、TUI/editor/approval 事实和退出差异；
- `scripts/kaola-tmux.sh`：平台中立、安全默认关闭的会话与 guarded-action 核心；
- `scripts/kaola-pane-relay.py`、`kaola-relay-client.py`：nested PTY、直接输入 transport 和旧协议兼容；
- `scripts/kaola-observation.py`：schema-v2 canonical facts、revision、snapshot 与 receipt；
- `scripts/kaola-model-policy.py`：只读 catalog 解析、per-run 主模型选择与实际模型证据比较；
- `skills/`：确定性生成并提交的五个自包含 Skill；
- `tests/contract/`：golden compatibility、renderer、安装迁移和控制面验收。

golden bytes 保持冻结；active Skill、manifest、adapter 或 renderer 修改后运行 `--write` 并提交
生成产物，`--check` 会拒绝任何 drift。

## 验证

```bash
./scripts/validate.sh
```

默认离线验证只检查渲染一致性、Skill 格式、shell 语法、冻结 Grok bytes 和最小通信合同；不再
运行耗时的 fake-runtime 历史矩阵。真实验收按五个平台分别证明 start/read/send/read-back/stop；
原生选择界面还要证明 Agent-selected `key`。Claude Code 当前无有效账号，只把提示词传输与登录
错误回读作为通过证据，不声称认证后的模型执行成功。

详细边界见 [架构](docs/architecture.md)、[命令契约](docs/api.md) 和
[开发约定](docs/conventions.md)。五个平台的真实 tmux 验收、Claude 认证边界和零会话残留见
[2026-08-29 live smoke](docs/live-smoke-2026-08-29.md)。
Issue #7 的无 hardgate 交互验收和五平台权限边界见
[2026-08-30 evidence-first live smoke](docs/live-smoke-evidence-first-2026-08-30.md)。
Issue #8 的逐 runtime 模型选择、`workflow-next` 通信和精确会话关闭证据见
[2026-08-30 model-policy live smoke](docs/live-smoke-model-policy-2026-08-30.md)。
Issue #9 的最小五平台通信实跑见
[2026-08-31 minimal live smoke](docs/live-smoke-issue-9-2026-08-31.md)。
