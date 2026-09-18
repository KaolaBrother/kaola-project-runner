# 输入：三拍 heartbeat 原始记录

下面是同一个项目在三个不同时刻收到的 heartbeat 工作提示词原文，以及该拍内用户给出的确认。
它们是原始输入，没有经过任何整理。

---

## 场景 1

### 本拍收到的 heartbeat 原文

```
PROJECT_RUNNER_HEARTBEAT_V2
CLI、模型、并发、额度及能力限制：Codex ×2（账户额度本周剩余 20%），并发 2，Claude Code 未授权
现场入口：codex worker kpr-issue-101 在 .kw/worktrees/issue-101，Issue #101
项目约束与停止条件：#101 交付后仍需 review 与合并；#98 的 worktree 清理未做
上一拍记录：Codex 第 1 次 429 限流后重试成功
上上拍记录：Cursor 模型不匹配（cursor-grok-4.6-xhigh 显示为默认），已记入 Issue #99
计划 A（已废弃）：用 Codex ×2 并行跑 #101 与 #104
```

### 本拍内用户的确认

> Codex 额度用尽，改用 Claude Code ×1，其他不变。

---

## 场景 2

### 本拍收到的 heartbeat 原文

```
PROJECT_RUNNER_HEARTBEAT_V2
CLI、模型、并发、额度及能力限制：Codex ×3，并发 4（用户 2026-09-17 上调），token 预算 本周 8M
优先级：Issue #107 (P0) 先于 #103 (P2)
现场入口：worker A=#107 .kw/worktrees/issue-107；worker B=#103 .kw/worktrees/issue-103；worker C=#111 .kw/worktrees/issue-111
项目约束与停止条件：#103 的验收证据未补；#107 合并后需通知其他 worker 同步
上一拍记录：并发从 2 上调到 4 之后已补派 worker C
```

### 本拍内用户的确认

> 并发降回 2，其他不变。

---

## 场景 3

### 本拍收到的 heartbeat 原文

```
PROJECT_RUNNER_HEARTBEAT_V2
CLI、模型、并发、额度及能力限制：Claude Code ×1，并发 1
现场入口：claude worker kpr-issue-112 在 .kw/worktrees/issue-112，Issue #112
项目约束与停止条件：#112 候选待外层验收；#109 的 archive/sink 未完成
上一拍记录：#109 已合并到 main，validate 通过
上上拍记录：tmux 会话一次性失联，重连后恢复
再上一拍记录：#109 已合并到 main，validate 通过
计划 B（已被 #112 的新方案替代）：先改 renderer 再改模板
项目说明：本项目是 Runner 通信驱动（第三次重复叙述）
```

### 本拍内用户的确认

> （本拍用户没有新指令。）
