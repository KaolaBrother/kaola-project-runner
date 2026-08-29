# Kaola Project Runner

Kaola Project Runner 是一组面向 Codex 的外层调度 Skill。每个 Skill 在一个所有权可验证的
tmux 主会话中启动指定 CLI，再让该 CLI 使用已经安装的 Kaola Workflow 完成 Issue 选择、
claim、mission list、执行和最终收口。

现有 Grok Skill 是已经实跑验证的 golden contract：四种任务模式、项目与 PR 提示词、claim
handoff、15 分钟 heartbeat、foreground scheduler 和关闭协议保持原文、原语义。其他平台从这份
完整契约机械对齐，只把 executable、启动/恢复、preflight、TUI/activity 和尚未实证的 recurring
能力放进 adapter。本仓库不安装或改写 Kaola Workflow，也不修改目标 CLI 的用户配置。

## 支持的平台

| Platform | Codex Skill | CLI | Recurring |
|---|---|---|---|
| Grok CLI | `$grok-kaola-project-runner` | `grok` | supported，需显式请求 |
| Claude Code | `$claude-code-kaola-project-runner` | `claude` | unsupported |
| OpenCode | `$opencode-kaola-project-runner` | `opencode` | unsupported |
| Kimi CLI | `$kimi-cli-kaola-project-runner` | `kimi` | unsupported |
| Cursor CLI | `$cursor-cli-kaola-project-runner` | `cursor-agent` | unsupported |

裸调用统一表示：使用当前目录所在的 canonical Git repository，启动或恢复该平台的精确
tmux session，让当前可见的 `workflow-next` 自行选择最合适的 coherent Issue batch，完成后
finalize 并停止。不会预先限制为单个 Issue，也不会隐式启动循环。

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

每个运行保留三层边界：Codex 外层负责精确会话控制和监督；目标 CLI 主会话负责项目接单和
执行；Kaola Workflow 负责 claim、mission list、finalize、Issue/PR、archive 和 sink。
Codex heartbeat 只监督，不是执行循环。`HUMAN_DECISION_REQUIRED` 必须回到用户，并且只有在
精确 runtime session 已证明 idle 后才能把答案送回。

## 控制接口

```bash
scripts/kaola-tmux.sh grok preflight \
  --repo /absolute/path/to/repo --session grok-kaola-example

scripts/kaola-tmux.sh opencode start \
  --repo /absolute/path/to/repo --session opencode-kaola-example

scripts/kaola-tmux.sh cursor-cli status \
  --repo /absolute/path/to/repo --session cursor-cli-kaola-example
```

命令为 `preflight`、`start`、`status`、`capture`、`send`、`stop`。复用、捕获、发送和停止前
都必须证明 exact session、单 pane、Runner owner、platform、canonical repo、pane cwd 和
runtime TUI；TUI 身份同时要求当前 pane process 在 argv[0] 或解释器 argv[1] 绑定 exact resolved
runtime binary，不能只信任 scrollback 或后续参数文本。发送和普通停止还要求 activity 为 idle，
待人工决定会话会被保留。prompt 使用 tmux buffer 传输，不经过 shell 求值。

`scripts/grok-tmux.sh` 是 frozen Grok surface 的兼容包装器，等价于
`scripts/kaola-tmux.sh grok ...`，并保留旧 marker 与 `grok_tui` 状态字段。

Cursor CLI 的 `preflight` 保持只读；首次 `start` 会在创建 tmux 前调用当前 Kaola Cursor
authority 的正式 `--ensure-target <repo>`，验证 receipt 后物化项目级 commands。任何 unmanaged
collision 都会在 session 创建前失败关闭。本仓库不复制或自行改写这些 Workflow commands。

## 仓库结构

- `templates/grok-golden/`：已实跑验证、字节冻结的 Grok 协议和提示词；
- `platforms/*.yaml`：五个平台的固定事实与能力声明；
- `templates/agents/`、`templates/references/platform.md.tmpl`：UI 与 adapter facts 模板；
- `scripts/adapters/`：binary、preflight、启动、TUI/activity 和退出差异；
- `scripts/kaola-tmux.sh`：平台中立、安全默认关闭的会话核心；
- `skills/`：确定性生成并提交的五个自包含 Skill；
- `tests/contract/`：golden compatibility、renderer、安装迁移和控制面验收。

修改 golden contract 需要真实 Grok 再验证和明确授权；通常的新平台工作只能改 manifest、adapter
和机械 renderer。修改后运行 `--write` 并提交生成产物，`--check` 会拒绝任何 drift。

## 验证

```bash
./scripts/validate.sh
```

离线测试使用临时 Git repository、fake CLI、隔离 Codex home 和独立 tmux session。真实验收按
五个平台分别启动 exact tmux 主会话并交付完整 Grok-aligned `workflow-next` 提示词。Claude Code
当前无账号时，只把 TUI/命令接收作为通过证据，认证后的执行阻断会单独记录，不声称 Workflow
成功运行。

详细边界见 [架构](docs/architecture.md)、[命令契约](docs/api.md) 和
[开发约定](docs/conventions.md)。五个平台的真实 tmux 验收、Claude 认证边界和零会话残留见
[2026-08-29 live smoke](docs/live-smoke-2026-08-29.md)。
