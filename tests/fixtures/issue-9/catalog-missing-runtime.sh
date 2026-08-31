#!/usr/bin/env bash
set -euo pipefail

runtime_name="${FAKE_ISSUE9_RUNTIME_NAME:?}"
argv_log="${FAKE_ISSUE9_ARGV_LOG:?}"

printf 'event=argv\targs=' >>"$argv_log"
printf '%s ' "$@" >>"$argv_log"
printf '\n' >>"$argv_log"

if [[ "${1:-}" == --version || "${1:-}" == version ]]; then
  printf '%s\n' "$runtime_name issue-9-catalog-fixture 1.0.0"
  exit 0
fi

emit_catalog() {
  # The requested/default model is intentionally absent, while a readable
  # catalog proves that the absence is a catalog classification rather than a
  # probe failure.
  python3 - "$runtime_name" <<'PY'
import json
import sys

runtime = sys.argv[1]
print(json.dumps({
    "version": "issue-9-catalog-fixture 1.0.0",
    "grokVersion": "issue-9-catalog-fixture 1.0.0",
    "models": [{"id": f"known/{runtime}", "name": "Known fixture model"}],
    "skills": [{"name": "workflow-next"}, {"name": "kaola-workflow-finalize"}],
}))
PY
}

case "${1:-}" in
  inspect|models|model-list|list-models|catalog|schema|--list-models)
    emit_catalog
    exit 0
    ;;
  provider)
    if [[ "${2:-}" == list || "${2:-}" == --json ]]; then
      emit_catalog
      exit 0
    fi
    ;;
  doctor)
    emit_catalog
    exit 0
    ;;
  --help|-h|help)
    printf '%s\n' \
      '--model <model>' \
      '--effort <low|medium|high|xhigh|max>' \
      '--reasoning-effort <low|medium|high|xhigh|max>' \
      '--variant <low|high|max>'
    exit 0
    ;;
esac

selected=""
effort=""
args=("$@")
index=0
while (( index < ${#args[@]} )); do
  argument="${args[$index]}"
  case "$argument" in
    --model|-m)
      index=$((index + 1))
      selected="${args[$index]:-}"
      ;;
    --model=*) selected="${argument#--model=}" ;;
    --effort|--reasoning-effort|--variant)
      index=$((index + 1))
      effort="${args[$index]:-}"
      ;;
    --effort=*|--reasoning-effort=*|--variant=*) effort="${argument#*=}" ;;
  esac
  index=$((index + 1))
done

[[ -n "$selected" ]] || {
  printf 'catalog fixture: Runner omitted the selected model\n' >&2
  exit 64
}

printf 'event=launch\tselected=%s\teffort=%s\n' "$selected" "$effort" >>"$argv_log"
python3 - "$runtime_name" "$selected" "$effort" <<'PY'
import json
import sys

runtime, selected, effort = sys.argv[1:]
title = {
    "grok": "grok",
    "claude-code": "Claude Code",
    "opencode": "OpenCode",
    "kimi-cli": "Kimi Code",
    "cursor-cli": "Cursor Agent",
}.get(runtime, runtime)
print(f"\033]0;{title}\007", end="")
print(f"{title} Issue #9 catalog fixture")
print(f"CLI accepted catalog-missing model: {selected}")
print("KPR_MODEL_EVIDENCE " + json.dumps({
    "model_id": selected,
    "parameters": {"effort": effort, "fast": False} if effort else {"fast": False},
    "source": "runtime-marker",
}, ensure_ascii=False))
print("❯ ", end="", flush=True)
PY

while IFS= read -r line; do
  if [[ "$line" == /exit || "$line" == /quit ]]; then
    exit 0
  fi
  printf 'ECHO:%s\n❯ ' "$line"
done
