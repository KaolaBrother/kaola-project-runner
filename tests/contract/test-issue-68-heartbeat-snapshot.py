#!/usr/bin/env python3
"""Issue #68 acceptance: the heartbeat carries only the currently effective constraints.

Three real before -> compacted-snapshot -> next-action scenarios are replayed against
executable invariants (superseded values gone, current values in force, in-flight
locators and unfinished close-out duties kept, no unauthorized platform, no invented
cancel). Every scenario also carries wrong snapshots that the same invariants must
reject, so a green run means the checks discriminate instead of matching keywords.
The generated surfaces are then checked for the obligation itself: the per-host
heartbeat definition, the per-beat subtraction, and the absence of any new mechanism.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
ORCHESTRATOR = PROJECT / "skills" / "kaola-project-runner"
SKILL = ORCHESTRATOR / "SKILL.md"
SKELETON = ORCHESTRATOR / "references" / "heartbeat-skeleton.md"
BUDGETS = PROJECT / "templates" / "budgets.json"


# --------------------------------------------------------------------------
# The rule, as executable invariants over a produced snapshot.
#
# A scenario is one heartbeat beat: the prompt that arrived (`before`), what the
# human confirmed during it (`event`), the prompt written back for the next beat
# (`after`), and the work the beat actually launched (`next_action`).
# --------------------------------------------------------------------------


class Snapshot:
    def __init__(self, name, before, event, after, next_action):
        self.name = name
        self.before = before
        self.event = event
        self.after = after
        self.next_action = next_action


def superseded_dropped(scenario, superseded, **_):
    """A value the human replaced may not survive anywhere in the written-back prompt."""
    return [f"superseded value still present: {token!r}" for token in superseded if token in scenario.after]


def current_in_force(scenario, current, **_):
    """Every currently authorized value has to be readable from the snapshot alone."""
    return [f"current value missing: {token!r}" for token in current if token not in scenario.after]


def no_contradictory_pair(scenario, contradictions, **_):
    """"New rule wins" appended next to the old quota is exactly the failure to catch."""
    return [
        f"both {old!r} and {new!r} are stated as effective"
        for old, new in contradictions
        if old in scenario.after and new in scenario.after
    ]


def in_flight_kept(scenario, in_flight, **_):
    """A lowered quota or a platform swap never erases where live work is."""
    return [f"in-flight locator dropped: {token!r}" for token in in_flight if token not in scenario.after]


def duties_kept(scenario, duties, **_):
    """Unfinished delivery/acceptance/sync/cleanup duties outlive the beat that made them."""
    return [f"unfinished duty dropped: {token!r}" for token in duties if token not in scenario.after]


def history_compacted(scenario, obsolete, **_):
    """Inert history leaves the prompt; it stays in the records the pointer names."""
    return [f"obsolete project message retained: {token!r}" for token in obsolete if token in scenario.after]


def recovery_pointer_kept(scenario, pointers, **_):
    """Subtraction is not amnesia: the minimum pointer back to the evidence stays."""
    return [f"recovery pointer dropped: {token!r}" for token in pointers if token not in scenario.after]


def acts_on_current_constraint(scenario, acts_on, **_):
    """The beat that learned the new constraint is the beat that works under it."""
    return [] if any(re.search(p, scenario.next_action) for p in acts_on) else [
        "next action does not act under the new constraint in this beat"
    ]


def no_unauthorized_move(scenario, forbidden_moves, **_):
    """Platform substitution and cancelling live work need the human, not a quota reading.

    The patterns carry a `(?<![不未])` guard because the correct next action says the
    same words in the negative ("不 stop", "不丢弃"): only the affirmative move counts.
    """
    return [
        f"next action takes an unauthorized move: {pattern!r}"
        for pattern in forbidden_moves
        if re.search(pattern, scenario.next_action)
    ]


INVARIANTS = (
    superseded_dropped,
    current_in_force,
    no_contradictory_pair,
    in_flight_kept,
    duties_kept,
    history_compacted,
    recovery_pointer_kept,
    acts_on_current_constraint,
    no_unauthorized_move,
)


def violations(scenario, spec):
    found = []
    for invariant in INVARIANTS:
        found.extend(f"{invariant.__name__}: {problem}" for problem in invariant(scenario, **spec))
    return found


# --------------------------------------------------------------------------
# Scenario 1 - the authorized quota ran out and the human approved a substitute.
# --------------------------------------------------------------------------

S1_BEFORE = """PROJECT_RUNNER_HEARTBEAT_V2
CLI、模型、并发、额度及能力限制：Codex ×2（账户额度本周剩余 20%），并发 2，Claude Code 未授权
现场入口：codex worker kpr-issue-101 在 .kw/worktrees/issue-101，Issue #101
项目约束与停止条件：#101 交付后仍需 review 与合并；#98 的 worktree 清理未做
上一拍记录：Codex 第 1 次 429 限流后重试成功
上上拍记录：Cursor 模型不匹配（cursor-grok-4.6-xhigh 显示为默认），已记入 Issue #99
计划 A（已废弃）：用 Codex ×2 并行跑 #101 与 #104
"""

S1_AFTER = """PROJECT_RUNNER_HEARTBEAT_V2
CLI、模型、并发、额度及能力限制：Claude Code ×1（用户 2026-09-18 确认），并发 1
现场入口：codex worker kpr-issue-101 在 .kw/worktrees/issue-101，Issue #101（在飞，用户未要求取消）
项目约束与停止条件：#101 仍需 review 与合并；#98 的 worktree 清理未做
"""

S1_NEXT = """本拍即按 Claude Code ×1 安排工作：先接 #101 的 review 收尾。
不再按 Codex 额度派任何新工作；在飞的 codex worker kpr-issue-101 保留，不 stop、不丢弃它的收尾职责。
"""

S1_SPEC = {
    "superseded": ["Codex ×2", "账户额度本周剩余 20%", "并发 2", "Claude Code 未授权"],
    "current": ["Claude Code ×1", "并发 1"],
    "contradictions": [("Codex ×2", "Claude Code ×1")],
    "in_flight": ["kpr-issue-101", ".kw/worktrees/issue-101"],
    "duties": ["#101 仍需 review 与合并", "#98 的 worktree 清理未做"],
    "obsolete": ["429 限流后重试成功", "Cursor 模型不匹配", "计划 A（已废弃）"],
    "pointers": ["Issue #101"],
    "acts_on": [r"本拍即按 Claude Code ×1"],
    "forbidden_moves": [
        r"(?<![不未])stop .{0,20}kpr-issue-101",
        r"改用 (?:Cursor|Grok|Kimi)",
        r"(?<![不未])丢弃",
    ],
}

# The same beat, done wrong.
S1_WRONG = {
    "appends the new platform under the old quota": Snapshot(
        "s1-append",
        S1_BEFORE,
        "",
        S1_BEFORE + "新规则优先：Claude Code ×1（用户 2026-09-18 确认），并发 1\n",
        S1_NEXT,
    ),
    "drops the in-flight worker together with its platform": Snapshot(
        "s1-drop-in-flight",
        S1_BEFORE,
        "",
        """PROJECT_RUNNER_HEARTBEAT_V2
CLI、模型、并发、额度及能力限制：Claude Code ×1（用户 2026-09-18 确认），并发 1
项目约束与停止条件：#101 仍需 review 与合并；#98 的 worktree 清理未做
""",
        S1_NEXT,
    ),
    "reads the exhausted quota as a licence to cancel": Snapshot(
        "s1-cancel",
        S1_BEFORE,
        "",
        S1_AFTER,
        "Codex 额度用尽，stop 会话 kpr-issue-101 并丢弃其未完成交付，改用 Claude Code ×1。\n",
    ),
}

# --------------------------------------------------------------------------
# Scenario 2 - concurrency raised, then lowered again while three workers run.
# --------------------------------------------------------------------------

S2_BEFORE = """PROJECT_RUNNER_HEARTBEAT_V2
CLI、模型、并发、额度及能力限制：Codex ×3，并发 4（用户 2026-09-17 上调），token 预算 本周 8M
优先级：Issue #107 (P0) 先于 #103 (P2)
现场入口：worker A=#107 .kw/worktrees/issue-107；worker B=#103 .kw/worktrees/issue-103；worker C=#111 .kw/worktrees/issue-111
项目约束与停止条件：#103 的验收证据未补；#107 合并后需通知其他 worker 同步
上一拍记录：并发从 2 上调到 4 之后已补派 worker C
"""

S2_EVENT = "用户确认：并发降回 2，其他不变。"

S2_AFTER = """PROJECT_RUNNER_HEARTBEAT_V2
CLI、模型、并发、额度及能力限制：Codex ×3，并发 2（用户 2026-09-18 确认），token 预算 本周 8M
优先级：Issue #107 (P0) 先于 #103 (P2)
现场入口：worker A=#107 .kw/worktrees/issue-107；worker B=#103 .kw/worktrees/issue-103；worker C=#111 .kw/worktrees/issue-111（3 个在飞，超出新并发上限，按用户新指令范围处理，未被取消）
项目约束与停止条件：#103 的验收证据未补；#107 合并后需通知其他 worker 同步
"""

S2_NEXT = """本拍起按并发 2 安排：不再新派第 4 个 worker，也不按并发 4 找活。
已在飞的 A/B/C 三个继续跑到各自交付，自然收敛到 2；#107 (P0) 优先复核。
并发下调不等于取消在飞任务，未取得用户指示前不 stop A/B/C。
"""

S2_SPEC = {
    "superseded": ["并发 4", "用户 2026-09-17 上调", "并发从 2 上调到 4"],
    "current": ["并发 2", "Codex ×3", "token 预算 本周 8M", "Issue #107 (P0) 先于 #103 (P2)"],
    "contradictions": [("并发 4", "并发 2")],
    "in_flight": [".kw/worktrees/issue-107", ".kw/worktrees/issue-103", ".kw/worktrees/issue-111"],
    "duties": ["#103 的验收证据未补", "#107 合并后需通知其他 worker 同步"],
    "obsolete": ["已补派 worker C"],
    "pointers": ["Issue #107"],
    "acts_on": [r"本拍起按并发 2"],
    "forbidden_moves": [
        r"(?<![不未])stop worker C",
        r"(?<![不未])取消 .{0,10}在飞",
        r"(?<![不未])按并发 4",
    ],
}

S2_WRONG = {
    "keeps the raised concurrency beside the lowered one": Snapshot(
        "s2-contradiction",
        S2_BEFORE,
        S2_EVENT,
        S2_AFTER.replace("token 预算 本周 8M", "token 预算 本周 8M；上一拍并发 4 的安排继续有效"),
        S2_NEXT,
    ),
    "waits for the next beat instead of re-planning now": Snapshot(
        "s2-deferred",
        S2_BEFORE,
        S2_EVENT,
        S2_AFTER,
        "记下并发降回 2，下一拍再按新并发重新安排；本拍继续按并发 4 派活。\n",
    ),
    "auto-cancels the worker that exceeds the new limit": Snapshot(
        "s2-autocancel",
        S2_BEFORE,
        S2_EVENT,
        S2_AFTER,
        "本拍起按并发 2 安排：立即 stop worker C 以符合新上限。\n",
    ),
}

# --------------------------------------------------------------------------
# Scenario 3 - an ordinary beat: clear obsolete project messages only.
# --------------------------------------------------------------------------

S3_BEFORE = """PROJECT_RUNNER_HEARTBEAT_V2
CLI、模型、并发、额度及能力限制：Claude Code ×1，并发 1
现场入口：claude worker kpr-issue-112 在 .kw/worktrees/issue-112，Issue #112
项目约束与停止条件：#112 候选待外层验收；#109 的 archive/sink 未完成
上一拍记录：#109 已合并到 main，validate 通过
上上拍记录：tmux 会话一次性失联，重连后恢复
再上一拍记录：#109 已合并到 main，validate 通过
计划 B（已被 #112 的新方案替代）：先改 renderer 再改模板
项目说明：本项目是 Runner 通信驱动（第三次重复叙述）
"""

S3_AFTER = """PROJECT_RUNNER_HEARTBEAT_V2
CLI、模型、并发、额度及能力限制：Claude Code ×1，并发 1
现场入口：claude worker kpr-issue-112 在 .kw/worktrees/issue-112，Issue #112
项目约束与停止条件：#112 候选待外层验收；#109 的 archive/sink 未完成
"""

S3_NEXT = """本拍按 Claude Code ×1 继续：推进 #112 的验收补证，并收尾 #109 的 archive/sink。
被删掉的合并与故障叙述留在 Issue #109 与既有运行记录里，不重抄进本篇。
"""

S3_SPEC = {
    "superseded": [],
    "current": ["Claude Code ×1", "并发 1"],
    "contradictions": [],
    "in_flight": ["kpr-issue-112", ".kw/worktrees/issue-112"],
    "duties": ["#112 候选待外层验收", "#109 的 archive/sink 未完成"],
    "obsolete": [
        "已合并到 main，validate 通过",
        "tmux 会话一次性失联",
        "计划 B（已被 #112 的新方案替代）",
        "第三次重复叙述",
    ],
    "pointers": ["Issue #112"],
    "acts_on": [r"本拍按 Claude Code ×1 继续"],
    "forbidden_moves": [r"(?<![不未])stop .{0,20}kpr-issue-112", r"(?<![不未])放弃 #109"],
}

S3_WRONG = {
    "compacts by dropping the unfinished close-out duty": Snapshot(
        "s3-lost-duty",
        S3_BEFORE,
        "",
        """PROJECT_RUNNER_HEARTBEAT_V2
CLI、模型、并发、额度及能力限制：Claude Code ×1，并发 1
现场入口：claude worker kpr-issue-112 在 .kw/worktrees/issue-112，Issue #112
项目约束与停止条件：#112 候选待外层验收
""",
        S3_NEXT,
    ),
    "keeps appending the same finished history": Snapshot(
        "s3-append",
        S3_BEFORE,
        "",
        S3_BEFORE,
        S3_NEXT,
    ),
}

SCENARIOS = (
    (Snapshot("s1", S1_BEFORE, "用户确认：Codex 额度用尽，改用 Claude Code ×1，其他不变。", S1_AFTER, S1_NEXT), S1_SPEC, S1_WRONG),
    (Snapshot("s2", S2_BEFORE, S2_EVENT, S2_AFTER, S2_NEXT), S2_SPEC, S2_WRONG),
    (Snapshot("s3", S3_BEFORE, "（无新指令的普通一拍）", S3_AFTER, S3_NEXT), S3_SPEC, S3_WRONG),
)


class HeartbeatSnapshotBehavior(unittest.TestCase):
    def test_compacted_snapshots_satisfy_every_invariant(self) -> None:
        for scenario, spec, _ in SCENARIOS:
            with self.subTest(scenario=scenario.name):
                self.assertEqual([], violations(scenario, spec))

    def test_wrong_snapshots_are_rejected(self) -> None:
        """Without this the invariants above could be vacuously true."""
        for scenario, spec, wrong in SCENARIOS:
            for label, broken in wrong.items():
                with self.subTest(scenario=scenario.name, wrong=label):
                    self.assertNotEqual([], violations(broken, spec), f"{label} was accepted")

    def test_before_snapshots_would_fail_the_same_invariants(self) -> None:
        """The inputs are real: each `before` is exactly what the rule has to fix."""
        for scenario, spec, _ in SCENARIOS:
            with self.subTest(scenario=scenario.name):
                stale = Snapshot(scenario.name, scenario.before, scenario.event, scenario.before, scenario.next_action)
                self.assertNotEqual([], violations(stale, spec))


class HeartbeatGuidanceObligation(unittest.TestCase):
    """The generated surfaces must instruct the behavior the scenarios exercise."""

    def setUp(self) -> None:
        self.skill = SKILL.read_text(encoding="utf-8")
        self.skeleton = SKELETON.read_text(encoding="utf-8")

    def test_heartbeat_is_defined_per_host_without_a_shared_implementation(self) -> None:
        # Codex and Grok Bot: their own timer. ZCode Host: worker return / worker event.
        self.assertRegex(self.skeleton, r"Codex 与 Grok Bot 由各自定时系统触发投递")
        self.assertRegex(self.skeleton, r"ZCode Host 由每次 Worker 返回或既有 Worker 事件触发投递")
        self.assertRegex(self.skeleton, r"不要求各平台同路径同 schema")
        self.assertRegex(self.skeleton, r"不给 ZCode 加定时器")
        self.assertRegex(self.skeleton, r"不把 Codex/Grok Bot 改成事件触发")
        self.assertRegex(
            self.skill,
            re.compile(
                r"heartbeat is the working prompt itself.{0,200}own timer.{0,120}"
                r"worker return or event.{0,120}host-native\s+carriers",
                re.S,
            ),
        )

    def test_each_beat_subtracts_while_keeping_live_work(self) -> None:
        step = self.skeleton.split("7. ", 1)[1].split("\nPR ", 1)[0]
        drop, keep = step.split("保留：", 1)
        for token in ("已被替代的额度", "已作废的计划", "重复叙述", "无后续影响的已完成事项", "暂态故障"):
            self.assertIn(token, drop, f"per-beat drop list is missing {token!r}")
        for token in ("当前有效的项目约束", "在飞任务的定位", "未完成的交付", "恢复所需的最小指针"):
            self.assertIn(token, keep, f"per-beat keep list is missing {token!r}")
        self.assertIn("不得同时存在两个互相矛盾的额度或优先级", step)
        self.assertIn("从本篇移除不等于删除证据", step)
        self.assertRegex(self.skill, r"effective-now snapshot, not a\s+log")
        self.assertRegex(self.skill, r"replacing superseded quota, priority and\s+plans")
        self.assertRegex(self.skill, r"keeping in-flight locators and unfinished duties")

    def test_a_confirmed_change_takes_effect_in_the_same_beat(self) -> None:
        self.assertRegex(self.skeleton, r"立即替换旧值，并在本拍就按新约束重新安排可执行工作")
        self.assertRegex(self.skeleton, r"不再按已被替代的额度派工")
        self.assertRegex(self.skill, r"A confirmed change\s+applies in that beat")

    def test_exhaustion_neither_switches_platform_nor_cancels_in_flight(self) -> None:
        self.assertRegex(self.skeleton, r"平台故障或实测额度耗尽只是证据，本身不扩大换平台的授权")
        self.assertRegex(self.skeleton, r"额度下调也不等于取消或丢弃在飞任务")
        self.assertRegex(self.skeleton, r"保留其定位与剩余收尾职责")
        self.assertRegex(self.skill, r"a lowered quota alone\s+cancels nothing")

    def test_quota_units_are_not_fused_into_one_number(self) -> None:
        self.assertRegex(self.skeleton, r"保留用户表达的单位与含义")
        self.assertRegex(self.skeleton, r"并发数、账户额度、token 预算分别记，不合成一个数")

    def test_carriers_stay_host_native_and_no_new_mechanism_is_introduced(self) -> None:
        carrier = self.skeleton.split("载体按本宿主现有机制：", 1)[1].split("\n", 1)[0]
        self.assertIn(".kaola/heartbeat-prompt.json", carrier)
        self.assertIn("`body`", carrier)  # Issue #66 defect reporting survives, scoped to ZCode
        self.assertIn("Codex 与 Grok Bot 更新各自定时系统已有的提示词载体", carrier)
        self.assertIn("不新建 schema、额度账本、调度器或清理脚本", carrier)
        for invented in ("cron", "crontab", "Routine 定时器", "配额执行器", "quota ledger"):
            self.assertNotIn(invented, self.skeleton, f"heartbeat skeleton invented {invented!r}")

    def test_budgets_are_not_raised(self) -> None:
        limits = json.loads(BUDGETS.read_text(encoding="utf-8"))
        self.assertLessEqual(limits["main_skill_bytes"], 17408)
        self.assertLessEqual(limits["reference_bytes"], 8192)
        self.assertLessEqual(len(SKILL.read_bytes()), limits["main_skill_bytes"])
        self.assertLessEqual(len(SKELETON.read_bytes()), limits["reference_bytes"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
