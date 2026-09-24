#!/usr/bin/env python3
"""Issue #86: an unspecified token quota is not an extra Delegator start gate.

Issue #74 requires a new ZCode Host to have current authorization before
``start``: goal and remaining work, authorized worker platforms/members, counts
and concurrency, the quota the user gave, priority, and the delivery/stop
boundary. It also forbids fusing quota units.

The pre-fix shared Delegator prompt turned "do not fuse units" into "all three
quota units are mandatory figures". An outer Agent that had been given worker
platforms, counts, concurrency, an account quota, priority, the stop boundary,
and the canonical project path still refused to ``start`` for want of a
separate token cap. That is an extra hard gate, not unit hygiene.

This suite pins the difference. The removed sentences are asserted absent, the
replacement rule is asserted present, and the four properties that must survive
the fix — unit non-fusion, no invented unlimited quota, still-ask on a genuinely
missing or ambiguous value, and no re-ask on a live Host — are asserted too.

Isolated behavioral evidence for the same five scenarios (pre-fix legs and
post-fix legs over the frozen rendered text) lives in
``kaola-workflow/issue-86/evidence/``; it is not reproduced here.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXTERNAL = ROOT / "skills" / "kaola-delegator"
SKILL_TMPL = ROOT / "templates" / "kaola-delegator" / "SKILL.md.tmpl"
HANDOFF_TMPL = ROOT / "templates" / "kaola-delegator" / "references" / "handoff.md.tmpl"
BUDGETS = json.loads((ROOT / "templates" / "budgets.json").read_text(encoding="utf-8"))

CHECKS: list[str] = []


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    CHECKS.append(label)


def one_line(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def main() -> int:
    skill = (EXTERNAL / "SKILL.md").read_text(encoding="utf-8")
    handoff = (EXTERNAL / "references" / "handoff.md").read_text(encoding="utf-8")
    skill_one = one_line(skill)
    handoff_one = one_line(handoff)
    both_one = skill_one + " " + handoff_one
    readme_one = one_line((ROOT / "README.md").read_text(encoding="utf-8"))

    # --- the removed gate -------------------------------------------------
    # Each of these made a separate token figure mandatory before `start`.
    check("quota as separate concurrency, account, and token figures" not in skill_one,
          "Skill no longer demands three separate quota figures at extraction")
    check("account and token quota as separate figures" not in handoff_one,
          "new-Host authorization no longer demands account and token as separate figures")
    check("stay three numbers" not in handoff_one,
          "handoff text no longer requires three quota numbers")
    check("quota_concurrency=<n>" not in handoff,
          "the concurrency slot no longer demands a number")

    # --- the replacement rule ---------------------------------------------
    check("the quota the user actually gave, each figure in its own unit" in skill_one,
          "Skill collects the quota the user actually gave, each figure in its own unit")
    # Issue #157 (KD-R3): handoff step 4 no longer restates the set; it points
    # at SKILL §Extract once, which keeps every rule below.
    check("authorization per SKILL §Extract once, confirmed with the user" in handoff_one,
          "new-Host authorization is the SKILL §Extract once set")
    check("A quota unit the user never gave is not a missing key value" in skill_one,
          "Skill: an ungiven quota unit is not a missing key value")
    check("carry it as unspecified and start" in skill_one,
          "Skill: an ungiven quota unit is carried as unspecified rather than blocking start")
    check("A unit the user never gave is none of those" not in handoff_one,
          "handoff step 4 does not restate the SKILL quota rule")
    for slot in ("quota_concurrency=<as given>", "quota_account=<as given>",
                 "quota_token=<as given>"):
        check(slot in handoff, f"the handoff carries what the user gave ({slot})")

    # --- an unspecified quota is never reported as unlimited ---------------
    check("`unspecified` is not unlimited" in handoff_one,
          "handoff text says an unspecified quota is not an unlimited one")
    check("treat an unspecified quota as unlimited" in skill_one,
          "Skill forbids reading an unspecified quota as unlimited")
    check("quota_token=unlimited" not in handoff and "quota_account=unlimited" not in handoff,
          "no quota slot is ever rendered unlimited")
    check("Missing authorization stays missing" in handoff_one,
          "the Host prompt still forbids the inner engine expanding authorization")

    # --- properties that must survive the fix ------------------------------
    check("fuse quota units" in skill_one, "unit non-fusion survives")
    check("quota units never merge" in handoff_one, "handoff still forbids merging units")
    check("a quota whose unit is unclear is, so ask" in skill_one,
          "an ambiguous quota unit is still a missing key value and still asks")
    check("missing, conflicting, or expired key values must be confirmed before `start`"
          in skill_one,
          "a genuinely missing key value still asks and still refuses start")
    check("reuse a stale quota" in skill_one,
          "a new Host still does not guess or reuse a stale quota")
    check("Do not open a blank Host" in handoff_one and "Do not open a blank Host" in skill_one,
          "a blank Host is still refused")
    check("raise quota" in skill_one and "expand authorization" in skill_one,
          "quota is still never raised and authorization never expanded")
    check("apply only the user's latest change" in handoff_one
          and "apply only the user's latest change" in skill_one,
          "a live Host A to B attach still does not re-ask the full authorization set")
    check("A live Host A→B attach is not a new session: do not re-ask the full set"
          in handoff_one,
          "the live-Host exemption is still stated inside the new-Host step")
    check("authorization **before** `start`" in handoff_one,
          "a new Host still needs current authorization before start")

    # --- no unit is ever derived from another ------------------------------
    for fused in ("quota_token=<quota_account", "quota_account=<quota_token",
                  "derive the token", "convert the account quota"):
        check(fused not in handoff_one, f"no quota unit is derived from another ({fused})")

    # --- no new engine, schema, state file, or transport gate --------------
    for invented in ("quota-engine", "quota.json", "quota-state", ".kaola/quota",
                     "quota_ledger", "--quota", "quota registry"):
        check(invented not in handoff and invented not in skill,
              f"no new quota mechanism is introduced ({invented})")

    # --- README states the same rule ---------------------------------------
    check("only after current authorization is complete" in readme_one,
          "README keeps the Issue #74 complete-authorization contract")
    check("carried as unspecified and does not block the start" in readme_one,
          "README states that an ungiven quota unit does not block a new Host")
    check("not as unlimited" in readme_one,
          "README states an ungiven quota unit is not reported as unlimited")
    check("a unit whose meaning is unclear is ambiguous, so ask" in readme_one,
          "README keeps the ask-on-ambiguous-unit rule")

    # --- progressive disclosure still holds --------------------------------
    skill_bytes = len((EXTERNAL / "SKILL.md").read_bytes())
    handoff_bytes = len((EXTERNAL / "references" / "handoff.md").read_bytes())
    check(skill_bytes <= BUDGETS["external_skill_bytes"],
          f"external Skill stays within budget ({skill_bytes} <= {BUDGETS['external_skill_bytes']})")
    check(handoff_bytes <= BUDGETS["reference_bytes"],
          f"handoff stays within budget ({handoff_bytes} <= {BUDGETS['reference_bytes']})")

    # --- generated output is the renderer's, not hand-edited ---------------
    check(SKILL_TMPL.is_file() and HANDOFF_TMPL.is_file(),
          "both shared Delegator templates exist")
    skill_tmpl = one_line(SKILL_TMPL.read_text(encoding="utf-8"))
    handoff_tmpl = one_line(HANDOFF_TMPL.read_text(encoding="utf-8"))
    check("A quota unit the user never gave is not a missing key value" in skill_tmpl,
          "the Skill rule comes from the shared template, not a hand-edited skills/ file")
    check("authorization per SKILL §Extract once" in handoff_tmpl,
          "the handoff pointer comes from the shared template, not a hand-edited skills/ file")

    print(f"PASS test-issue-86-delegator-quota.py ({len(CHECKS)} checks)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print(f"FAIL test-issue-86-delegator-quota.py: {exc}", file=sys.stderr)
        for done in CHECKS:
            print(f"  ok: {done}", file=sys.stderr)
        sys.exit(1)
