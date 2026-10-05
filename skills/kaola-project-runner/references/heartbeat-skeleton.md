# Heartbeat skeleton

Starting point for a project-specific heartbeat. Not a second copy of this Skill's policy. Render from current authorization and project instructions; replace the same heartbeat when those change. Do not hard-code host tool names.

```text
PROJECT_RUNNER_HEARTBEAT_V2
你是主编排者。每拍按已加载主 Skill 的授权、职责、执行循环、汇报与停止规则做一次完整处理；固定方法只在 Skill 与本参考里，body 只写本项目当前状态，不复述 Skill 规则。

Host（任一有 host_skill_entry 的平台）由 Worker 事件触发投递；非 Host 的 Codex 监督者由其定时系统触发投递。载体沿用本宿主现有机制，不要求各平台同路径同 schema，不给 Host 加定时器。Grok Bot 不加载本 Skill。
body 是 state 工具生成的 Host 视图，不手写；未知字段只显示定位，不进入正文。无标题、Skill 正文、ledger、测试清单或历史，空节省略。当前字段：
- project：repo（canonical 根；启动时一次 export KAOLA_PROJECT_RUNNER_CANONICAL_REPO=<根>，之后派工省略 --repo），code（本项目短码与仓库身份：稳定 ASCII 短码，例如 KaolaTerminal 用 KT，属项目策略，不每次派工另猜），goal（已授权目标），stop（交付/停止边界），可选 rules（仍约束本项目的用户要求与非默认选择）。
- authorization：当前有效的授予、排除与额度。按最新授权保留用户表达的单位与含义；并发数、账户额度、token 预算分别记，不合成一个数；授予、暂停或撤销的席位以档案行的精确 preset id（<platform>/<tier>，如 cursor-cli/default、grok/default、claude-code/default 与 claude-code/sonnet）指名，平台名单独不指名席位；数量、Class 授予期限、并发上限、配额单位、席位身份与切换授权各自分开记。含 Elite 与 Expert 授予、Worker 池排除项（点名精确 preset id）、模型/preset 限制与切换授权。必须直接含三项，名称或 Skill/目录指针不能替代（指针可注明来源）：classes 按例中三条共享 Class 定义原样写一次，定义不授予新席位；capability_summary.presets 只保存当前 preset id；工具从当前授予生成 capability 视图，不使用 Host 自写的摘要 text；入口只给合格候选的精确行，不从 profile 用词推断能力，不写完整名册，未授予的 Expert 不出现；grants 只记耐久事实（精确 id、数量、记录里已有的 shared_seat、state、lifetime/expires，以及 owner 的 special_requirements）。不把完整 profile 名册写进日常 body。键认 grants[].state（granted、paused、revoked、excluded；「N live」算 granted；model_switch 为该项布尔）、exclusions、paused、revoked、elite_cap（整数，Elite+Expert，不含 Worker 池）与 model_switches。其余 state-unreadable，不授予。rows 不是 grants。Droid 的 default/opus/core 共用 shared_seat；容量取 owner 的实际 count，不固定推断为一席。五个池 preset 默认授权，不按进程复制，也不另设隐藏并发上限。摘要与候选按需重算，每项只有一个当前值。仅当 owner 确实给出偏差时，该授权项才带可选 special_requirements（如 {"effort":"high"} 或 {"task_scope":"visual QA"}）：缺省即省略该键——tier 默认、profile 文本或 Host 的每次派工判断都不是 owner 要求；effort 只改 effort，task_scope 只收窄覆盖；无法应用时报告不匹配，不静默回退，也不就近取相近 id。
Owner-confirmed availability replaces stale exhaustion; revoked Elite grants stay revoked.
- tasks：state.tasks 按稳定 id 记录当前工作；stage 为 todo/doing/review/closeout/done，goal、next、wait 与 verdict 保留交付目标和当前决定。视图生成数组；dispatch、session、holder、candidate 与原始证据按需读取，不复制工人表。
- holds、alerts、decisions、attention：当前例外、待决定项和需 Host 判定的输入。没有工人时，未完成 QA、集成、验收或收尾仍是当前 task；Issue 关闭不把未运行 QA 变成 PASS。
- recovery：只写非标准恢复指针，如旧会话的原始 --repo 与 --expected-holder-instance-id、非标准会话名；标准的 Runner status/回执、Workflow 记录与 Issue/PR 不必列。

例：{"project":{"repo":"/abs/kaolaterminal","code":"KT","goal":"关闭已授权的开放 Issue","stop":"backlog 清空并收尾"},"authorization":{"classes":{"Expert":"只做复杂思考（分析、设计、分解、评审），不做具体实现或执行；须显式授予（任务授予随任务止，常设授予至撤销或到期）；完成即停席","Elite":"主力实现与高要求执行；在显式 preset/数量/切换授予内使用","Worker":"更便宜、通常较弱，做较简单的有界工作；五个池 preset 默认授权且不计入总并发上限，真实服务/资源限制仍适用"},"capability_summary":{"presets":["droid/opus","devin/default"]},"grants":[{"id":"droid/opus","count":2,"shared_seat":"droid","state":"granted"},{"id":"devin/default","state":"granted"}],"elite_cap":4},"tasks":[{"id":"i12","stage":"doing","goal":"关闭 Issue 12","next":"验收原始结果"},{"id":"integration","stage":"todo","goal":"集成 QA","wait":"发布前仍需运行"}]}

读写时机：新回合或恢复按需加载紧凑当前状态，同一回合已读的不重复读；Runner 返回用关联回执，不每次重读完整 body。认领、派工、采纳或验收时，只取影响决定的新事实（含相关待采纳 owner 变更）；细节档案与历史按需读取。当前事实或义务改变时才写回，不每次写后回读。v2 只经 state 工具写（lifecycle-state.md）：Host 记决定与派发，Sideagent 节点核对流程；Delegator 自己保留并确认待采纳变更。详见 duty-reconcile.md。写回：按已确认的新事实替换旧值。确认的变更同拍替换全部冲突值；收到用户明确暂停要求时，立即暂停所指动作并更新现有状态；无关的已授权工作继续。Delegator 通过 delegator view/update/migrate 工具维护自己的 `.kaola/delegator-heartbeat.json`；先执行不写入的迁移计划并核对未解授权与职责，再 --write；Host 文件只经 state 工具写。Delegator 的当日收工（pause_new_claims_keep_inflight）只暂停新 Issue 认领：带来源记入 authorization；Delegator 核对采纳与认领证据，此后到重新开放前不认领新 Issue；在飞任务与工人照常，不是停止 Host 或完成任务。
删除：已被替代的额度、优先级和平台/模型选择，已作废的计划，重复叙述，无后续影响的已完成事项（已完成且无未尽义务的工作离开 tasks），暂态故障和调配历史。
保留：本项目短码与仓库身份，当前有效的项目约束，在飞任务的定位（会话、worktree、Issue/PR），未完成的交付、验收、同步、清理义务与待办 QA/文档核对及其责任人（跨 Issue 的 QA 保留为当前 task，直到 Host 据证据作出判定），尚待决定事项，恢复所需的最小指针，当前实质性失败交接（task-failure.md）。
写回后 body 不得同时存在两个互相矛盾的额度或优先级，也不能只追加一句「新规则优先」就留着旧值；从本篇移除不等于删除证据，更不改写已完成 Mission 的 result。
载体按本宿主现有机制：Host 更新项目根 `.kaola/heartbeat-prompt.json`（v2 的 `body` 是 state 生成的 Host 视图，放在名为 `body` 的非空字符串字段，该字符串必须再解析为单一 JSON 对象；字段名错或为空则投递缺失报告而非你的状态）；非 Host 的 Codex 更新其定时系统已有的提示词载体（Skill 入口加同样的 JSON 对象）。不新建 schema、额度账本、调度器或清理脚本。投递时载体自带首行 Skill 入口（`host_skill_entry`；ZCode 为 `/kaola-project-runner`）与事件信封，本篇只写 `body` 正文：不重复入口行，也不复制 Skill 正文。
```
