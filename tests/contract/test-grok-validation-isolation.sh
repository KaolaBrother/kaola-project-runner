#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
legacy_test="$project_root/tests/test-grok-tmux.sh"
tmp_root="$(mktemp -d "${TMPDIR:-/tmp}/grok-validation-isolation.XXXXXX")"
tmux_bin="$(command -v tmux)"
user_socket="gkpr-user-$$-${RANDOM}"
user_tmux="$tmp_root/user-tmux"
keeper="gkpr-user-keeper-$$"

cat >"$user_tmux" <<'TMUX_SHIM'
#!/usr/bin/env bash
set -euo pipefail
exec "$GROK_ISOLATION_TMUX_BIN" -L "$GROK_ISOLATION_TMUX_SOCKET" "$@"
TMUX_SHIM
chmod +x "$user_tmux"
export GROK_ISOLATION_TMUX_BIN="$tmux_bin"
export GROK_ISOLATION_TMUX_SOCKET="$user_socket"

cleanup() {
  "$user_tmux" kill-session -t "$keeper" 2>/dev/null || true
  "$user_tmux" kill-server 2>/dev/null || true
  rm -rf "$tmp_root"
}
trap cleanup EXIT

# Model the user's/default server separately from the legacy test's private
# server. The only server visible through TMUX_BIN is deliberately 1-based.
"$user_tmux" new-session -d -s "$keeper" -c "$tmp_root"
"$user_tmux" set-option -g base-index 1
"$user_tmux" set-window-option -g pane-base-index 1
user_base_index="$("$user_tmux" show-options -gqv base-index)"
user_pane_base_index="$("$user_tmux" show-window-options -gv pane-base-index)"

set +e
legacy_output="$(TMUX_BIN="$user_tmux" bash "$legacy_test" 2>&1)"
legacy_rc=$?
set -e

if [[ "$legacy_rc" -ne 0 ]]; then
  printf 'RED: test_legacy_grok_validation_is_independent_of_user_tmux — expected legacy validation to pass, got rc=%s\n' "$legacy_rc" >&2
  printf '%s\n' "$legacy_output" >&2
  exit 1
fi

"$user_tmux" has-session -t "=$keeper" || {
  printf 'RED: test_legacy_grok_validation_preserves_user_server — user/default server was not preserved\n' >&2
  exit 1
}
user_base_index_after="$("$user_tmux" show-options -gqv base-index)"
user_pane_base_index_after="$("$user_tmux" show-window-options -gv pane-base-index)"
[[ "$user_base_index" == 1 && "$user_pane_base_index" == 1 && \
   "$user_base_index_after" == "$user_base_index" && \
   "$user_pane_base_index_after" == "$user_pane_base_index" ]] || {
  printf 'RED: test_legacy_grok_validation_preserves_user_server — numbering options changed from %s/%s to %s/%s\n' \
    "$user_base_index/$user_pane_base_index" "$user_base_index_after/$user_pane_base_index_after" >&2
  exit 1
}

printf 'Grok validation isolation acceptance: PASS\n'
