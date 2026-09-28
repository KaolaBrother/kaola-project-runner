# Heartbeat skeleton

Starting point for a project-specific heartbeat. Not a second copy of this Skill's policy. Render from current authorization and project instructions; replace the same heartbeat when those change. Do not hard-code host tool names.

```text
PROJECT_RUNNER_HEARTBEAT_V2
上一行是本心跳契约名（投递信封按它要求一次完整处理），不写进 body。你是本项目的主编排者。每拍按已加载主 Skill 的授权、职责、执行循环、汇报与停止规则做一次完整处理；固定方法只在 Skill 与本参考里，body 只写本项目现在有效的状态，不复述 Skill 规则。平台 Runner 只负责运输，工人执行仓库工作。

heartbeat 就是投递给你的工作提示词：载体自带的 Skill 入口与事件信封，加上 body 里的一个 JSON 状态对象。Host（任一有 host_skill_entry 的平台）由 Worker 事件触发投递；非 Host 的 Codex 监督者由其定时系统触发投递。载体沿用本宿主现有机制，不要求各平台同路径同 schema，不给 Host 加定时器。Grok Bot 不加载本 Skill。
body 是「当前有效状态快照」，不是变更日志：恰好一个紧凑 JSON 对象，没有标题行、说明文字、Skill 正文、完整 mission ledger、测试清单或历史；某节为空就省略。历史留在 Workflow、Issue 和既有运行记录里。字段：
- project：repo（canonical 根；启动时一次 export KAOLA_PROJECT_RUNNER_CANONICAL_REPO=<根>，之后派工省略 --repo），code（本项目短码与仓库身份：稳定 ASCII 短码，例如 KaolaTerminal 用 KT，属项目策略，不每次派工另猜），goal（已授权目标），stop（交付/停止边界），可选 rules（仍约束本项目的用户要求与非默认选择）。
- authorization：当前有效的授予、排除与额度。按最新授权保留用户表达的单位与含义；并发数、账户额度、token 预算分别记，不合成一个数；授予、暂停或撤销的席位以档案行的精确 preset id（<platform>/<tier>，如 cursor-cli/default、grok/default、claude-code/default 与 claude-code/sonnet）指名，平台名单独不指名席位；数量、Class 授予期限、并发上限、配额单位、席位身份与切换授权各自分开记。含 Elite 授予、获批 Expert 任务、Worker 池排除项（点名精确 preset id）、模型/preset 限制与切换授权，只记相关已授权档案行或其指针；六个 Worker preset 保持默认授权，不逐席重复列条目。每项只有一个当前值。仅当 owner 确实给出偏差时，该授权项才带可选 special_requirements（如 {"effort":"high"} 或 {"task_scope":"visual QA"}）：缺省即省略该键——tier 默认、profile 文本或 Host 的每次派工判断都不是 owner 要求；effort 只改 effort，task_scope 只收窄覆盖；无法应用时报告不匹配，不静默回退，也不就近取相近 id。
- active：数组，每个在飞或可立即行动的 Issue/任务一项，同一 Issue 的多名工人各一项：ref，session（精确会话名、平台/preset、holder；已停席不列 live），candidate（需要时的 worktree、分支、提交或 PR），next，evidence（证据指针）。
- pending：数组，未了结的 Host 义务（集成 QA、文档核对、验收、finalize、同步、清理或人工决定）：duty，scope，owner，evidence（指针或具体缺口），boundary（交付点）。没有在飞工人时照样保留；Issue 关闭不把未运行的 QA 变成 PASS。
- recovery：只写非标准恢复指针，如旧会话的原始 --repo 与 --expected-holder-instance-id、非标准会话名；标准的 Runner status/回执、Workflow 记录与 Issue/PR 不必列。

例：{"project":{"repo":"/abs/kaolaterminal","code":"KT","goal":"关闭已授权的开放 Issue","stop":"backlog 清空并收尾"},"authorization":{"pool":"默认 Worker 池","elite":"cursor-cli/opus 1 席","limits":"并发 4；token 预算未给"},"active":[{"ref":"#12","session":"codex-KT-i12-fix","next":"idle 后验收","evidence":".kw/worktrees/issue-12"}],"pending":[{"duty":"集成 QA","scope":"#12+#13 CLI/README","owner":"Host","evidence":"未运行","boundary":"发布前"}]}

写回：每个自然拍（有意义的 Worker 事件或责任人变化）后，用新鲜的 Forge/Workflow/Runner 事实与当前授权核对，再用新对象整体替换 body，不追加；写回前先做减法。用户或 Delegator 的变更以单独消息到达，确认后写进对应字段；Delegator 自己的 `.kaola/delegator-heartbeat.json` 不归你写。Delegator 的当日收工（pause_new_claims_keep_inflight）只暂停新 Issue 认领：回复确认并记入 authorization，此后到重新开放前不认领新 Issue；在飞任务与工人照常，不是停止 Host 或完成任务。
   删除：已被替代的额度、优先级和平台/模型选择，已作废的计划，重复叙述，无后续影响的已完成事项（已关闭 Issue 离开 active），暂态故障和调配历史。
   保留：本项目短码与仓库身份，当前有效的项目约束，在飞任务的定位（会话、worktree、Issue/PR），未完成的交付、验收、同步、清理义务与待办 QA/文档核对及其责任人（跨 Issue 的 QA 留在 pending，直到 Host 据证据作出判定），尚待决定事项，恢复所需的最小指针。
   写回后 body 不得同时存在两个互相矛盾的额度或优先级，也不能只追加一句「新规则优先」就留着旧值；从本篇移除不等于删除证据，更不改写已完成 Mission 的 result。
   载体按本宿主现有机制：Host 更新项目根 `.kaola/heartbeat-prompt.json`（JSON 对象，状态对象序列化后放在名为 `body` 的非空字符串字段；字段名错或为空则投递缺失报告而非你的状态）；非 Host 的 Codex 更新其定时系统已有的提示词载体（Skill 入口加同样的 JSON 对象）。不新建 schema、额度账本、调度器或清理脚本。投递时载体自带首行 Skill 入口（`host_skill_entry`；ZCode 为 `/kaola-project-runner`）与事件信封，本篇只写 `body` 正文：不重复入口行，也不复制 Skill 正文。
```
