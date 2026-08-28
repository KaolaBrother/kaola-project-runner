# Grok Kaola Project Runner

一个仅面向 Codex 的 Skill：让 Codex 在精确的 tmux session 中操作 Grok CLI 主会话，并使用
Kaola Workflow 启动、恢复、推进和收口具体项目。

默认模式是一次性、可恢复的项目运行。loop 或 scheduler 只有在用户明确要求周期执行时才启用。
每个活动项目都会由 Codex 在当前线程建立一个 15 分钟 heartbeat，用来检查状态并向用户汇报；
它与可选的 Grok 执行 scheduler 是两套不同机制。

裸调用不需要任何参数或补充提示词：Codex 会把当前工作目录所在的 Git repo 作为 workspace，
选择一次性 Workflow 项目模式，并立即在 Grok 主会话调用 `workflow-next`。额外提示词只用于更
准确地说明目标、Issue、PR 或模式，不是启动前提。

## 能力边界

- Grok 主会话负责接单和保留需要用户决定的问题。
- `workflow-next` 负责 claim、mission list 和项目推进。
- `kaola-workflow-finalize` 负责最终验证、文档、Issue、归档与 sink。
- `scripts/grok-tmux.sh` 只操作带有本项目所有权标记的精确 tmux session。
- Codex 线程 heartbeat 每 15 分钟检查 Grok、Git、Kaola 和远端状态，终态后删除。
- Grok 循环执行必须在同一个 main orchestrator 中使用 `foreground: true` scheduler。
- 不根据历史记忆假定仓库指令、Grok 版本或 Kaola Workflow 安装位置。

## 本地安装

```bash
./scripts/install-local.sh
```

安装器会创建：

```text
~/.codex/skills/grok-kaola-project-runner -> 当前项目目录
```

如果目标已被其他文件或目录占用，安装器会停止，不会覆盖。

## 快速使用

在 Codex 中：

```text
$grok-kaola-project-runner
```

默认含义是：在当前 Git repo 中，使用 `grok-kaola-<repo-name>` tmux session，立即启动或恢复
一个由 `workflow-next` 选择的项目。只有明确要求循环时才创建 Grok scheduler。

Skill 向 Codex 暴露四种任务能力：

1. 完整做一次 Workflow 项目。
2. 循环做 Workflow 项目。
3. 完整做一次 PR 审核、合并与 finalize。
4. 循环做 PR 审核、合并与 finalize。

这是 Skill 路由，不是四个业务 CLI 子命令。Codex 根据 Skill 选择模式，再像现有
Automation 一样自行检查状态、操作 tmux/Grok CLI、发送提示词并监管结果。两个循环模式都要求
Grok 使用同一个 Main orchestrator 中的 `foreground: true` scheduler，绝不使用 detached
`/loop` General subagent。

PR 模式始终调用 `workflow-next`。调用前先检查 linked Issue 的远端 claim；当 PR head 与同一
claim project 匹配时，把冲突解释为作者 PR-sink run 的正常 review handoff，并明确要求
`workflow-next` 忽略该冲突对 PR 审核的阻断。忽略的只是“不能审核”这一结论，不是 Issue 或
作者 run 的 ownership：审阅者不得重复 claim、接管或重建作者的 workflow 状态。

底层控制 helper 示例：

```bash
scripts/grok-tmux.sh preflight \
  --repo /absolute/path/to/repo \
  --session my-project-grok

scripts/grok-tmux.sh start \
  --repo /absolute/path/to/repo \
  --session my-project-grok

scripts/grok-tmux.sh status \
  --repo /absolute/path/to/repo \
  --session my-project-grok
```

通常应由 Agent 根据 Skill 契约操作这些命令，而不是让用户手工驱动整个流程。

## 验证

```bash
./scripts/validate.sh
```

测试使用隔离临时 Git 仓库、假的 Grok TUI 和独立 tmux session；不会接触已有 session。
