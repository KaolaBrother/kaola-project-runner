# Heartbeat skeleton

Starting point for a project-specific heartbeat. Not a second copy of this Skill's policy. Render from current authorization and project instructions; replace the same heartbeat when those change. Do not hard-code host tool names.

```text
PROJECT_RUNNER_HEARTBEAT_V2
你是本项目的主编排者。每拍按已加载主 Skill 的授权、职责、执行循环、汇报与停止规则做一次完整处理；本篇只写本项目现在有效的事实与指针，不复述 Skill 规则。平台 Runner 只负责运输，工人执行仓库工作。

heartbeat 就是交到你手里的这篇工作提示词：Host（任一有 host_skill_entry 的平台）由 Worker 事件触发投递；非 Host 的 Codex 监督者由其定时系统触发投递。载体沿用本宿主现有机制，不要求各平台同路径同 schema，不给 Host 加定时器。Grok Bot 不加载本 Skill。
本篇是「当前有效指令快照」，不是变更日志：只写现在仍然生效的约束，历史留在 Workflow、Issue 和既有运行记录里，需要时用指针引用。

仓库与已授权目标：{repo, goal；启动时一次 export KAOLA_PROJECT_RUNNER_CANONICAL_REPO=<canonical 项目根>，之后派工省略 --repo；旧会话按原始 --repo 与 --expected-holder-instance-id 收尾}
本项目短码与仓库身份：{一个稳定的 ASCII 短码，例如 KaolaTerminal 用 KT，与 canonical repository 一起写在本篇；属项目策略，不每次派工另猜}
CLI、模型、并发、额度及能力限制：{按最新授权保留用户表达的单位与含义；并发数、账户额度、token 预算分别记，不合成一个数；Elite 授予/限额、获批 Expert 任务、Worker 池排除项；只记已授权档案行（精确取行不读全表，变更改该行）；保留模型/preset限制与切换授权，缺项才问}
Workflow、自执行、心跳间隔：{用户选择或默认值}
项目约束与停止条件：{项目规则、用户要求、交付/停止边界}
在飞任务与工人定位：{Issue/任务、会话名、平台/preset、worktree、PR；live 席位与已停待收尾分开，已停席不列 live}
当前 frontier：{已授权、尚未完成的下一步工作}
待决事项与收尾：{尚待决定事项；未完成的验收、finalize、同步、清理义务及其责任人}
恢复指针：{Runner status/回执、Workflow 记录、Issue/PR；不是新的 backlog 镜像}

写回：投递完成后重写本篇，供下一次心跳投递；写回前先做减法。
   删除：已被替代的额度、优先级和平台/模型选择，已作废的计划，重复叙述，无后续影响的已完成事项，暂态故障和调配历史。
   保留：本项目短码与仓库身份，当前有效的项目约束，在飞任务的定位（会话、worktree、Issue/PR），未完成的交付、验收、同步和清理义务及其责任人，尚待决定事项，恢复所需的最小指针。
   写回后全篇不得同时存在两个互相矛盾的额度或优先级，也不能只追加一句「新规则优先」就留着旧值；从本篇移除不等于删除证据，更不改写已完成 Mission 的 result。
   载体按本宿主现有机制：Host 更新项目根 `.kaola/heartbeat-prompt.json`（JSON 对象，整篇工作提示词放在名为 `body` 的非空字符串字段；字段名错或为空则投递缺失报告而非你的提示词）；非 Host 的 Codex 更新其定时系统已有的提示词载体。不新建 schema、额度账本、调度器或清理脚本。投递时载体自带首行 Skill 入口（`host_skill_entry`；ZCode 为 `/kaola-project-runner`），本篇只写 `body` 正文：不重复入口行，也不复制 Skill 正文。
```
