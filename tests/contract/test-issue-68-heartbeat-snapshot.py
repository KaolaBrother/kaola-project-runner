#!/usr/bin/env python3
"""Issue #68 contract: the generated surfaces instruct a current-effective heartbeat.

This suite checks only what a contract check can honestly check — that the rendered
main Skill and heartbeat skeleton state the obligation, scope the carrier per host,
and add no new mechanism. It deliberately does NOT assert over hand-written "after"
snapshots: those constants are written by the same worker that wrote the template, so
they prove nothing about behavior.

The behavioral record lives with the run, not here: one isolated ACP session read this
candidate cold and produced its own compacted heartbeats from three raw inputs, in
kaola-workflow/issue-68/evidence/sentinel/ (and the readable walk-through in
kaola-workflow/issue-68/evidence/heartbeat-snapshot-scenarios.md).
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


class HeartbeatGuidanceObligation(unittest.TestCase):
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
