#!/usr/bin/env bash
# Issue #126 M0 (sequential; attempt 1 ran the three in parallel and all hit acp-initialize-timeout on cold npx): A = discovery, C = $kaola-project-runner entry + new-build anchor, N = negative control.
E="$(cd "$(dirname "$0")" && pwd)"
A='Do not use any tool and do not read any file in this turn. Using only the skill and command lists already present in your context, list every skill or command name that contains kaola-project-runner, each with the exact prefix character it is invoked with. Reply with those names separated by single spaces, or reply NONE.'
C='$kaola-project-runner
In this turn do not call any tool except one whose only purpose is to load a skill. Quote verbatim the third sentence of the first paragraph under the heading "Hosts" of the loaded Project Runner Skill body and nothing else; if that Skill body is not in your context, reply exactly SKILL-NOT-LOADED.'
N='In this turn do not call any tool at all. Quote verbatim the third sentence of the first paragraph under the heading "Hosts" of the Project Runner Skill body if that body is already in your context, and nothing else; if it is not in your context, reply exactly SKILL-NOT-LOADED.'
python3 "$E/probe.py" codex codex-KPR-i126-discover "$A" > "$E/A-codex.json"
python3 "$E/probe.py" codex codex-KPR-i126-kpr "$C" > "$E/C-codex.json"
python3 "$E/probe.py" codex codex-KPR-i126-neg "$N" > "$E/N-codex.json"

echo "sequential rc=0 $(date +%FT%T)" > "$E/run-m0.exit"
