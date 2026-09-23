#!/usr/bin/env python3
"""Verify the recorded, accepted #149 measurement without rerunning ACP."""
import json
import subprocess
from pathlib import Path

here = Path(__file__).resolve().parent
read = lambda name: json.loads((here / name).read_text())
versions = read('versions-and-verdict.json')
assert versions['codex_cli'] == '0.156.1'
assert versions['codex_acp'] == '1.13.0'
assert versions['checkout_commit'] == 'd62ab082c23f84cc54b2d1b9b50ee3c199181a5e'
assert versions['shadow_auth_exit'] == 0
assert (here / 'auth-status.txt').read_text().strip() == 'Logged in using ChatGPT'
assert read('installed-hook-original.json')['hooks']['SessionStart'][0]['matcher'] == 'compact'
assert 'logging-wrapper.py' in read('installed-hook-observable.json')['hooks']['SessionStart'][0]['hooks'][0]['command']
assert read('acp-summary.json')['compact_prompt']['result']['stopReason'] == 'end_turn'
assert read('acp-followup-summary.json')['followup_prompt']['result']['stopReason'] == 'end_turn'
assert read('acp-followup-summary.json')['method'] == 'session/load, no session/new'
assert any(e.get('status') == 'completed' and e.get('contextCompaction') for e in read('acp-compact-events.json'))
assert {e['type'] for e in read('codex-rollout-compact-events.json')} == {'compacted', 'item_completed'}
assert not (here / 'hook-firings.jsonl').exists()
controls = [json.loads(s) for s in (here / 'hook-firings-control.jsonl').read_text().splitlines()]
assert len(controls) == 1 and controls[0]['parsed_stdin']['source'] == 'compact'
assert (here / 'shadow-cleanup.txt').is_file()
assert (here / 'render-check.exit').read_text().strip() == '1'
assert (here / 'validate.exit').read_text().strip() == '1'
assert 'kaola-workflow/release/validate-v0559.log' in (here / 'render-check.log').read_text()
assert 'kaola-workflow/release/validate-v0559.log' in (here / 'validate.log').read_text()
changed = subprocess.check_output(['git', 'diff', '--name-only', 'main...HEAD'], text=True).splitlines()
assert changed and all(p.startswith('kaola-workflow/issue-149/') for p in changed)
print('PASS: authenticated shadow, completed ACP compaction, absent hook firing, positive control, baseline pin failure, and #149-only scope')
