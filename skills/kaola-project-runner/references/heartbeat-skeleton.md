# Heartbeat skeleton

Starting point for a project-specific heartbeat. Not a second copy of this Skill's policy. Render from current authorization and project instructions; replace the same heartbeat when those change. Do not hard-code host tool names.

```text
PROJECT_RUNNER_HEARTBEAT_V2
你是主编排者。每拍按已加载主 Skill 的授权、职责、执行循环、汇报与停止规则做一次完整处理；固定方法只在 Skill 与本参考里，body 只写本项目当前状态，不复述 Skill 规则。

Host（任一有 host_skill_entry 的平台）由 Worker 事件触发投递；非 Host 的 Codex 监督者由其定时系统触发投递。载体沿用本宿主现有机制，不要求各平台同路径同 schema，不给 Host 加定时器。Grok Bot 不加载本 Skill。
body 是 state 工具生成的 Host 视图，不手写；未知字段只显示定位，不进入正文。无标题、Skill 正文、ledger、测试清单或历史，空节省略。当前字段：
- project：repo（canonical 根；启动时一次 export KAOLA_PROJECT_RUNNER_CANONICAL_REPO=<根>，之后派工省略 --repo），code（本项目短码与仓库身份：稳定 ASCII 短码，例如 KaolaTerminal 用 KT，属项目策略，不每次派工另猜），goal（已授权目标），stop（交付/停止边界），requirements_source（AGENTS.md 用户区或原始目标来源的简短指针，不复制要求、Skill 或采纳历史）。
- authorization：只存当前 owner 授予的精确 id 或 preset_ids、count、state、lifetime/expires、该 grant/group 的 model_switch 与 owner special_requirements；默认值省略。保留用户表达的单位与含义：并发数、账户额度、token 预算分别记，不合成一个数。共享组一行、一 count、一组允许选择；逐选择限制可用 special_requirements 的 preset-id 键。允许的 choices 不等于允许运行中切换。classes、profile、默认 model/effort 来自版本匹配的 catalog/templates；工具从授予、默认 Worker 池、exclusions、当前 holds 和实际 availability 生成候选与 capability，不另存摘要或完整档案。未知 availability 明示 unknown。state 的 paused 保留当前理由与重开路径；撤销/到期项离开授权，默认 Worker 的排除保留为 exclusions。未尽 stop/handoff/reclaim 留在具体当前 duty。只用 grant/group 一处 pause/switch 权限，不另存 paused/revoked/model_switches。Droid 共享组 count 取 owner 实数；Worker 池不变，Host/Sideagent 不消耗 worker seat。总量与可用量由有效 grant/shared count 和核实占用推导，不写 elite_cap/total_cap/worker_pool_cap 或改名等价字段。旧总量或 switch 冲突须原始证据与 owner 决策，不静默扩权。special_requirements 只留显式 owner 偏差（model、effort、task_scope），不复制默认 profile；不能应用时报告不匹配，不回退相近 id。
Owner-confirmed availability replaces stale exhaustion. Removed Elite grants do not restore themselves.
- tasks：state.tasks 按稳定 id 记录当前工作；stage 为 todo/doing/review/closeout/done，goal、next、wait 与 verdict 保留交付目标和当前决定。视图生成数组；dispatch、session、holder、candidate 与原始证据按需读取，不复制工人表。
- holds、alerts、decisions、attention：当前例外、待决定项和需 Host 判定的输入。没有工人时，未完成 QA、集成、验收或收尾仍是当前 task；Issue 关闭不把未运行 QA 变成 PASS。
- recovery：只写非标准恢复指针，如旧会话的原始 --repo 与 --expected-holder-instance-id、非标准会话名；标准的 Runner status/回执、Workflow 记录与 Issue/PR 不必列。

例：{"project":{"repo":"/abs/kaolaterminal","code":"KT","goal":"关闭已授权的开放 Issue","stop":"backlog 清空并收尾","requirements_source":"AGENTS.md 用户区"},"authorization":{"grants":[{"preset_ids":["droid/default","droid/opus","droid/core"],"count":2,"state":"granted","model_switch":false},{"id":"devin/default","count":1,"state":"granted"}]},"tasks":[{"id":"i12","stage":"doing","goal":"关闭 Issue 12","next":"验收原始结果"},{"id":"integration","stage":"todo","goal":"集成 QA","wait":"发布前仍需运行"}]}

读写时机：新回合或恢复按需加载紧凑当前状态，同一回合已读的不重复读；Runner 返回用关联回执，不每次重读完整 body。认领、派工、采纳或验收时，只取影响决定的新事实（含相关待采纳 owner 变更）；细节档案与历史按需读取。当前事实或义务改变时才写回，不每次写后回读。v2 只经 state 工具写（lifecycle-state.md）：Host 记决定与派发，Sideagent 节点核对流程；Delegator 自己保留并确认待采纳变更。详见 duty-reconcile.md。写回：按已确认的新事实替换旧值。确认的变更同拍替换全部冲突值；收到用户明确暂停要求时，立即暂停所指动作并更新现有状态；无关的已授权工作继续。Delegator 通过 delegator view/update/migrate 工具维护自己的 `.kaola/delegator-heartbeat.json`；先执行不写入的迁移计划并核对未解授权与职责，再 --write；Host 文件只经 state 工具写。Delegator 的当日收工（pause_new_claims_keep_inflight）只暂停新 Issue 认领：带来源记入 authorization；Delegator 核对采纳与认领证据，此后到重新开放前不认领新 Issue；在飞任务与工人照常，不是停止 Host 或完成任务。
删除：已被替代的额度、优先级和平台/模型选择，已作废的计划，重复叙述，无后续影响的已完成事项（已完成且无未尽义务的工作离开 tasks），暂态故障和调配历史。
保留：本项目短码与仓库身份，当前有效的项目约束，在飞任务的定位（会话、worktree、Issue/PR），未完成的交付、验收、同步、清理义务与待办 QA/文档核对及其责任人（跨 Issue 的 QA 保留为当前 task，直到 Host 据证据作出判定），尚待决定事项，恢复所需的最小指针，当前实质性失败交接（task-failure.md）。
写回后 body 不得同时存在两个互相矛盾的额度或优先级，也不能只追加一句「新规则优先」就留着旧值；从本篇移除不等于删除证据，更不改写已完成 Mission 的 result。
载体按本宿主现有机制：Host 更新项目根 `.kaola/heartbeat-prompt.json`（v2 的 `body` 是 state 生成的 Host 视图，放在名为 `body` 的非空字符串字段，该字符串必须再解析为单一 JSON 对象；字段名错或为空则投递缺失报告而非你的状态）；非 Host 的 Codex 更新其定时系统已有的提示词载体（Skill 入口加同样的 JSON 对象）。不新建 schema、额度账本、调度器或清理脚本。投递时载体自带首行 Skill 入口（`host_skill_entry`；ZCode 为 `/kaola-project-runner`）与事件信封，本篇只写 `body` 正文：不重复入口行，也不复制 Skill 正文。
```
