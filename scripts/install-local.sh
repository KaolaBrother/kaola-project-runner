#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd "$script_dir/.." && pwd -P)"
mode=install
method=copy
runtime_alias=""
skills_dir=""
bin_links_request=""
selection=()
platform_given=false
install_orchestrator=true
orchestrator_skill_name="kaola-project-runner"
external_skill_name="kaola-delegator"
installer_python="${PYTHON_BIN:-python3}"

command -v "$installer_python" >/dev/null 2>&1 || {
  printf 'python3 executable not found: %s\n' "$installer_python" >&2
  exit 1
}

usage() {
  printf '%s\n' \
    'Usage: ./scripts/install-local.sh [--runtime NAME | --skills-dir ABS_PATH]' \
    '                                  [--method link|copy] [--platform ID[,ID...]]' \
    '                                  [--no-orchestrator]' \
    '                                  [--bin-links | --no-bin-links] [--uninstall]' \
    '' \
    'Consuming runtimes (verified native skill directories):' \
    '  codex        ${CODEX_HOME:-$HOME/.codex}/skills' \
    '  claude-code  ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills' \
    '  cursor       $HOME/.cursor/skills' \
    '  devin        ${DEVIN_CONFIG_DIR:-$HOME/.config/devin}/skills' \
    '  zcode        $HOME/.zcode/skills (ZCode Host install; verified default' \
    '               discovery roots are the workspace .zcode/skills and' \
    '               .agents/skills — --skills-dir covers either — and the' \
    '               user-level ~/.zcode/skills and ~/.agents/skills; configured' \
    '               skills.roots/plugins.dirs roots also scan — docs/zcode-host.md)' \
    '  grok-cli     $HOME/.grok/skills (Grok CLI Host)' \
    '  droid        $HOME/.factory/skills' \
    '  opencode     $HOME/.config/opencode/skills' \
    '  kimi-cli     $HOME/.agents/skills (shared with dsh; see referrers below)' \
    '  dsh          $HOME/.agents/skills (shared with kimi-cli)' \
    'Each root above was measured as a Skill root of that CLI (Issue #119,' \
    'host-entry-matrix.md in the Project Runner Skill).' \
    'Grok Bot is a bridge host, not an installer destination: the account holds one' \
    'thin generated Skill (hosts/grok-bot/kaola-delegator.md) that loads the' \
    'Kaola-Delegator Skill from this checkout on the bound execution target' \
    'through the device-local locator kaola-project-runner-locate' \
    '(scripts/kaola-locate.py register --target local|cloud, which validates the' \
    'checkout, links the command, and writes its registration receipt beside the' \
    'link; a bare --bin-links link carries no receipt). See docs/grok-bot-host.md.' \
    'Grok CLI worker uses --platform grok, not --runtime grok; a Grok CLI Host' \
    'installs with --runtime grok-cli.' \
    'ZCode is both a worker platform (--platform zcode) and a native' \
    'skill-directory Host (--runtime zcode installs to $HOME/.zcode/skills; a' \
    'workspace .zcode/skills or .agents/skills destination goes through' \
    '--skills-dir; see docs/zcode-host.md).' \
    '' \
    '--skills-dir installs into any explicit destination parent (including' \
    'project-local paths) and is mutually exclusive with --runtime.' \
    '--method copy (default) installs a standalone copy tracked by a per-Skill' \
    'receipt. --method link is an explicit development choice that symlinks each' \
    'Skill to this checkout. An owned source link migrates to a copy on a default' \
    'or --method copy reinstall.' \
    'Platforms: grok, claude-code, opencode, kimi-cli, cursor-cli, devin, codex, zcode, droid, dsh' \
    '--platform filters worker Skills only. The main Skill kaola-project-runner' \
    '(display name Project Runner) is installed for every destination unless' \
    '--no-orchestrator is passed. Codex and generic destinations also plan' \
    'kaola-delegator as control-plane unless that flag is passed: a first install' \
    'requires zcode in this --platform (or no --platform); an already-installed' \
    'Delegator stays in the plan on later reinstall/uninstall even when this' \
    '--platform omits zcode, so it is not left stale. Neither control-plane Skill' \
    'is a platform ID.' \
    'With no --platform, installs all ten worker Skills plus the control-plane' \
    'Skills for that destination (unless skipped). With no destination flags the' \
    'legacy Codex destination is used. Existing foreign paths are never replaced.' \
    'Installed Skills are shared blocks counted by reference: each receipt lists' \
    'the runtimes that use that Skill. Installing the same build another runtime' \
    'already installed only records a reference (refer); another build updates the' \
    'one shared copy and keeps every referrer. --uninstall withdraws only this' \
    'runtime'"'"'s reference and removes a Skill only when no referrer is left (kept).' \
    '--bin-links also manages the $HOME/.local/bin/kaola-acp* helper links and the' \
    'kaola-project-runner-locate locator link; it is on by default only for the' \
    'Codex runtime destination. Uninstall never removes bin' \
    'links unless --bin-links is passed explicitly. The links are counted the same' \
    'way in $HOME/.local/bin/.kaola-project-runner-bin-links.json (runtime and' \
    'checkout): an existing link to a usable executable is referenced, not' \
    'replaced; a dangling one is refused. Uninstall keeps a link while another' \
    'referrer remains, and keeps the locator link while its registration receipt' \
    'exists (the installer never writes that receipt).' \
    'The Codex runtime destination (--runtime codex, or no destination flag) also' \
    'installs one Runner-owned user-level SessionStart(compact) recovery entry in' \
    '${CODEX_HOME:-$HOME/.codex}/hooks.json (id kaola-project-runner:user-compact-context,' \
    'assets under ${CODEX_HOME:-$HOME/.codex}/kaola-project-runner/hooks/) whenever' \
    'the control-plane Skills are in the plan; --no-orchestrator skips it, and' \
    '--uninstall removes only that entry and those assets. Foreign hook entries are' \
    'never changed. --skills-dir never touches any hooks.json. Codex still asks you' \
    'to review and trust the new entry in /hooks, and hooks load at session start,' \
    'so recovery is not active in the session that ran the install.'
}

skill_name_for() {
  case "$1" in
    grok) printf '%s\n' 'grok-kaola-project-runner' ;;
    claude-code) printf '%s\n' 'claude-code-kaola-project-runner' ;;
    opencode) printf '%s\n' 'opencode-kaola-project-runner' ;;
    dsh) printf '%s\n' 'dsh-kaola-project-runner' ;;
    kimi-cli) printf '%s\n' 'kimi-cli-kaola-project-runner' ;;
    cursor-cli) printf '%s\n' 'cursor-cli-kaola-project-runner' ;;
    devin) printf '%s\n' 'devin-kaola-project-runner' ;;
    codex) printf '%s\n' 'codex-kaola-project-runner' ;;
    zcode) printf '%s\n' 'zcode-kaola-project-runner' ;;
    droid) printf '%s\n' 'droid-kaola-project-runner' ;;
    *) return 1 ;;
  esac
}

runtime_skills_dir() {
  case "$1" in
    codex) printf '%s\n' "${CODEX_HOME:-$HOME/.codex}/skills" ;;
    claude-code) printf '%s\n' "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills" ;;
    cursor) printf '%s\n' "$HOME/.cursor/skills" ;;
    devin) printf '%s\n' "${DEVIN_CONFIG_DIR:-$HOME/.config/devin}/skills" ;;
    zcode) printf '%s\n' "$HOME/.zcode/skills" ;;
    # Issue #119: user roots measured live for each non-ZCode Host platform
    # (templates/orchestrator/references/host-entry-matrix.md).
    grok-cli) printf '%s\n' "$HOME/.grok/skills" ;;
    droid) printf '%s\n' "$HOME/.factory/skills" ;;
    opencode) printf '%s\n' "$HOME/.config/opencode/skills" ;;
    kimi-cli|dsh) printf '%s\n' "$HOME/.agents/skills" ;;
    *) return 1 ;;
  esac
}

append_selection() {
  local raw="$1" item
  IFS=',' read -r -a items < <(printf '%s\n' "$raw")
  for item in "${items[@]}"; do
    skill_name_for "$item" >/dev/null || {
      printf 'unknown platform: %s\n' "$item" >&2
      exit 2
    }
    selection+=("$item")
  done
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform)
      [[ $# -ge 2 ]] || { printf '%s\n' '--platform needs a value' >&2; exit 2; }
      append_selection "$2"
      platform_given=true
      shift 2
      ;;
    --runtime)
      [[ $# -ge 2 ]] || { printf '%s\n' '--runtime needs a value' >&2; exit 2; }
      if [[ "$2" == grok ]]; then
        printf 'unknown runtime: grok\nGrok CLI is worker platform id grok (--platform grok); a Grok CLI Host installs with --runtime grok-cli ($HOME/.grok/skills). Grok Bot is a bridge host with no installer destination (see docs/grok-bot-host.md).\n' >&2
        exit 2
      fi
      if [[ "$2" == grok-bot || "$2" == grokbot ]]; then
        printf 'unknown runtime: %s\nGrok Bot is a bridge host, not an installer destination: save hosts/grok-bot/kaola-delegator.md on the account and register the locator with scripts/kaola-locate.py register on the execution target (see docs/grok-bot-host.md). --platform grok is the Grok CLI worker.\n' "$2" >&2
        exit 2
      fi
      runtime_skills_dir "$2" >/dev/null || { printf 'unknown runtime: %s\n' "$2" >&2; exit 2; }
      [[ -z "$runtime_alias" ]] || { printf '%s\n' '--runtime may be given once' >&2; exit 2; }
      runtime_alias="$2"
      shift 2
      ;;
    --skills-dir)
      [[ $# -ge 2 ]] || { printf '%s\n' '--skills-dir needs a value' >&2; exit 2; }
      [[ -z "$skills_dir" ]] || { printf '%s\n' '--skills-dir may be given once' >&2; exit 2; }
      skills_dir="$2"
      shift 2
      ;;
    --method)
      [[ $# -ge 2 ]] || { printf '%s\n' '--method needs a value' >&2; exit 2; }
      case "$2" in link|copy) ;; *) printf 'unknown method: %s\n' "$2" >&2; exit 2 ;; esac
      method="$2"
      shift 2
      ;;
    --no-orchestrator) install_orchestrator=false; shift ;;
    --bin-links) bin_links_request=on; shift ;;
    --no-bin-links) bin_links_request=off; shift ;;
    --uninstall) mode=uninstall; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -n "$runtime_alias" && -n "$skills_dir" ]]; then
  printf '%s\n' '--runtime and --skills-dir are mutually exclusive' >&2
  exit 2
fi

if [[ -n "$skills_dir" ]]; then
  [[ "$skills_dir" == /* ]] || { printf '%s\n' '--skills-dir must be an absolute path' >&2; exit 2; }
  target_parent="$skills_dir"
  resolved_runtime=generic
elif [[ -n "$runtime_alias" ]]; then
  target_parent="$(runtime_skills_dir "$runtime_alias")"
  resolved_runtime="$runtime_alias"
else
  target_parent="${CODEX_HOME:-$HOME/.codex}/skills"
  resolved_runtime=codex
fi
receipts_dir="$target_parent/.kaola-install-receipts"

# Issue #123: this install's reference id, and who a pre-ledger receipt in this
# root counts as referenced by (every runtime mapped to the same root, e.g.
# kimi-cli and dsh for $HOME/.agents/skills).
self_ref="$resolved_runtime"
canonical_dir() { (cd "$1" 2>/dev/null && pwd -P) || printf '%s\n' "$1"; }
target_key="$(canonical_dir "$target_parent")"
legacy_referrers=""
for known_runtime in codex claude-code cursor devin zcode grok-cli droid opencode kimi-cli dsh; do
  [[ "$(canonical_dir "$(runtime_skills_dir "$known_runtime")")" == "$target_key" ]] \
    && legacy_referrers="${legacy_referrers:+$legacy_referrers,}$known_runtime"
done
[[ -n "$legacy_referrers" ]] || legacy_referrers="$self_ref"

if [[ "$mode" == install ]]; then
  if [[ "$bin_links_request" == on || ( -z "$bin_links_request" && "$resolved_runtime" == codex ) ]]; then
    want_bin_links=true
  else
    want_bin_links=false
  fi
else
  # Uninstall leaves shared helper links alone unless removal was explicitly
  # requested; they may belong to another installation.
  [[ "$bin_links_request" == on ]] && want_bin_links=true || want_bin_links=false
fi

if [[ ${#selection[@]} -eq 0 ]]; then
  selection=(grok claude-code opencode kimi-cli cursor-cli devin codex zcode droid dsh)
fi

deduped=()
for item in "${selection[@]}"; do
  duplicate=false
  for seen in "${deduped[@]:-}"; do
    [[ "$seen" == "$item" ]] && duplicate=true
  done
  [[ "$duplicate" == true ]] || deduped+=("$item")
done
selection=("${deduped[@]}")

canonical_existing_target() {
  local target="$1" raw
  raw="$(readlink "$target")" || return 1
  if [[ "$raw" == /* ]]; then
    [[ -e "$raw" ]] || return 1
    (cd "$raw" 2>/dev/null && pwd -P)
  else
    [[ -e "$(dirname "$target")/$raw" ]] || return 1
    (cd "$(dirname "$target")/$raw" 2>/dev/null && pwd -P)
  fi
}

tree_digest() {
  "$installer_python" -c 'import hashlib, os, sys
root = sys.argv[1]
entries = []
for dirpath, dirnames, filenames in os.walk(root):
    # Python may cache imported helpers inside an installed Skill. These are
    # runtime byproducts, not generated payload bytes or ownership evidence.
    dirnames[:] = [name for name in dirnames if name != "__pycache__"]
    dirnames.sort()
    for name in dirnames + [name for name in filenames if not name.endswith((".pyc", ".pyo"))]:
        entries.append(os.path.join(dirpath, name))
digest = hashlib.sha256()
for path in sorted(entries, key=lambda p: os.path.relpath(p, root)):
    rel = os.path.relpath(path, root).replace(os.sep, "/")
    if os.path.islink(path):
        digest.update(b"L" + rel.encode() + b"=" + os.readlink(path).encode() + b"\n")
    elif os.path.isdir(path):
        digest.update(b"D" + rel.encode() + b"\n")
    else:
        with open(path, "rb") as handle:
            content = hashlib.sha256(handle.read()).hexdigest()
        digest.update(b"F" + rel.encode() + b"=" + content.encode() + b"\n")
print(digest.hexdigest())' "$1"
}

receipt_digest() {
  # Print the recorded content hash when $1 is an exact-owned receipt for $2.
  "$installer_python" -c 'import json, sys
path, skill = sys.argv[1], sys.argv[2]
try:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
except (OSError, ValueError):
    sys.exit(0)
if (
    data.get("receipt") == "kaola-project-runner-install/1"
    and data.get("skill") == skill
    and data.get("method") == "copy"
    and isinstance(data.get("content_sha256"), str)
):
    sys.stdout.write(data["content_sha256"])' "$1" "$2"
}

# Issue #123: an installed Skill and the $HOME/.local/bin helper links are
# shared blocks, counted by reference. A Skill receipt lists the runtimes that
# reference that Skill ("referrers"; copy and link installs both write one). A
# receipt without the field predates the ledger and counts as referenced by
# every runtime mapped to that root, so an unknown owner is never assumed gone.
# The helper links keep their referrers in a separate sidecar beside them; the
# locator registration receipt written by kaola-locate.py is never written
# here, and its presence counts as one more reference to the locator link.
refs_program='import json, os, sys, time
op, args = sys.argv[1], sys.argv[2:]
RECEIPT = "kaola-project-runner-install/1"
LEDGER = ".kaola-project-runner-bin-links.json"
LEDGER_SCHEMA = "kaola-project-runner-bin-links/1"
REGISTRATION = ".kaola-project-runner-locate.json"
LOCATOR = "kaola-project-runner-locate"

def load(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None

def write_json(path, data):
    temp = "%s.part.%d" % (path, os.getpid())
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temp, path)

def names(raw):
    return sorted(set(item for item in raw.split(",") if item))

def receipt_for(path, skill):
    data = load(path)
    if (isinstance(data, dict) and data.get("receipt") == RECEIPT
            and data.get("skill") == skill and data.get("method") in ("copy", "link")):
        return data
    return None

if op == "skill-refs":
    # Print the referrers of skill $2 as a comma list: the recorded list, the
    # legacy list $3 for a receipt (or an owned link, $4 = 1) without one, or
    # nothing when this skill has no receipt.
    path, skill, legacy, linked = args
    data = receipt_for(path, skill)
    if data is not None and isinstance(data.get("referrers"), list):
        print(",".join(names(",".join(str(item) for item in data["referrers"]))))
    elif data is not None or linked == "1":
        print(legacy)
    else:
        print("")
elif op == "write-receipt":
    path, skill, method, source, digest, refs = args
    data = {"receipt": RECEIPT, "skill": skill, "method": method, "source": source,
            "referrers": names(refs),
            "installed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if method == "copy":
        data["content_sha256"] = digest
    write_json(path, data)
elif op == "set-referrers":
    path, skill, refs = args
    data = receipt_for(path, skill)
    if data is None:
        sys.exit("set-referrers: no owned receipt at %s" % path)
    data["referrers"] = names(refs)
    write_json(path, data)
elif op == "owned":
    sys.exit(0 if receipt_for(args[0], args[1]) is not None else 1)
elif op == "bin-plan":
    # Plan every helper link and print one "action|source|target|note" row per
    # link, then "ledger|<json>" with the sidecar as it must read afterwards.
    # A refusal exits 1 before anything is written.
    mode, bin_dir, runtime, checkout = args[:4]
    ledger = load(os.path.join(bin_dir, LEDGER))
    links = {}
    if isinstance(ledger, dict) and ledger.get("schema") == LEDGER_SCHEMA and isinstance(ledger.get("links"), dict):
        links = {k: v for k, v in ledger["links"].items() if isinstance(v, dict)}
    registered = os.path.isfile(os.path.join(bin_dir, REGISTRATION))
    me = {"runtime": runtime, "checkout": checkout}
    rows = []
    def creator(path):
        # A link made before the ledger belongs to the checkout it resolves into.
        parent = os.path.dirname(path)
        return os.path.dirname(parent) if os.path.basename(parent) == "scripts" else parent
    def label(ref):
        return "%s@%s" % (ref.get("runtime"), ref.get("checkout"))
    for spec in args[4:]:
        name, source = spec.split("=", 1)
        target = os.path.join(bin_dir, name)
        entry = links.get(name)
        refs = [r for r in (entry or {}).get("referrers") or [] if isinstance(r, dict)]
        is_link = os.path.islink(target)
        raw = os.readlink(target) if is_link else ""
        ours = is_link and os.path.exists(target) and os.path.exists(source) and os.path.samefile(target, source)
        if is_link and entry is None and not ours:
            refs = [{"runtime": "legacy", "checkout": creator(os.path.realpath(target))}]
        if mode == "install":
            if is_link:
                usable = os.path.isfile(target) and os.access(target, os.X_OK)
                if not (ours or usable):
                    sys.stderr.write("refusing to replace existing symlink: %s -> %s (target missing or not executable)\n" % (target, raw))
                    sys.exit(1)
                known = me in refs
                if not known:
                    refs.append(me)
                links[name] = {"target": raw, "referrers": refs}
                if ours:
                    rows.append(("already", source, target, ""))
                else:
                    rows.append(("already" if known else "refer", source, target,
                                 ", ".join(label(r) for r in refs)))
            elif os.path.lexists(target):
                sys.stderr.write("refusing to replace existing path: %s\n" % target)
                sys.exit(1)
            else:
                if me not in refs:
                    refs.append(me)
                links[name] = {"target": source, "referrers": refs}
                rows.append(("install", source, target, ""))
        else:
            remaining = [r for r in refs if not (r.get("checkout") == checkout
                                                 and r.get("runtime") in (runtime, "legacy"))]
            holders = [label(r) for r in remaining]
            if name == LOCATOR and registered:
                holders.append("Grok Bot locator registration " + os.path.join(bin_dir, REGISTRATION))
            if remaining:
                links[name] = {"target": (entry or {}).get("target") or raw, "referrers": remaining}
            else:
                links.pop(name, None)
            if is_link:
                if holders:
                    rows.append(("keep", source, target, "still referenced by " + ", ".join(holders)))
                elif ours or (entry is not None and raw == entry.get("target")):
                    rows.append(("uninstall", source, target, ""))
                else:
                    rows.append(("keep", source, target, "not linked by this checkout"))
            elif os.path.lexists(target):
                sys.stderr.write("refusing to remove non-symlink path: %s\n" % target)
                sys.exit(1)
            else:
                rows.append(("absent", source, target, ""))
    for row in rows:
        print("|".join(row))
    print("ledger|" + json.dumps({"schema": LEDGER_SCHEMA, "links": links}, sort_keys=True))
elif op == "bin-write":
    bin_dir, text = args
    path = os.path.join(bin_dir, LEDGER)
    data = json.loads(text)
    if data["links"]:
        write_json(path, data)
    elif os.path.lexists(path):
        os.unlink(path)
'
refs_tool() { "$installer_python" -c "$refs_program" "$@"; }

write_receipt() {
  # $1 skill name, $2 source dir, $3 method, $4 content digest (copy), $5 referrers
  mkdir -p "$receipts_dir"
  refs_tool write-receipt "$receipts_dir/$1.json" "$1" "$3" "$2" "$4" "$5"
}

drop_owned_receipt() {
  # Remove $1's receipt only when it parses as an exact-owned receipt for $1.
  local path="$receipts_dir/$1.json"
  [[ -f "$path" ]] || return 0
  refs_tool owned "$path" "$1" && rm -f "$path" || true
}

set_skill_referrers() {
  # $1 skill name, $2 source dir, $3 referrers. A legacy owned link has no
  # receipt yet; it gets a link receipt carrying the referrers.
  if refs_tool owned "$receipts_dir/$1.json" "$1"; then
    refs_tool set-referrers "$receipts_dir/$1.json" "$1" "$3"
  else
    write_receipt "$1" "$2" link "" "$3"
  fi
}

has_ref() { [[ ",$1," == *",$2,"* ]]; }
add_ref() {
  if [[ -z "$1" ]]; then printf '%s\n' "$2"
  elif has_ref "$1" "$2"; then printf '%s\n' "$1"
  else printf '%s\n' "$1,$2"; fi
}
drop_ref() {
  local out="" item
  local -a items=()
  [[ -z "$1" ]] || IFS=',' read -r -a items < <(printf '%s\n' "$1")
  for item in ${items[@]+"${items[@]}"}; do
    [[ "$item" == "$2" ]] || out="${out:+$out,}$item"
  done
  printf '%s\n' "$out"
}
skill_refs() {
  # $1 skill name; $2 is 1 when the target is this checkout's own symlink.
  refs_tool skill-refs "$receipts_dir/$1.json" "$1" "$legacy_referrers" "${2:-0}"
}

stage_copy() {
  "$installer_python" -c 'import shutil, sys
shutil.copytree(sys.argv[1], sys.argv[2], symlinks=True,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))' "$1" "$2"
}

place_staged() {
  # Move $1 into place at $2; an existing $2 is set aside at $3. Keep $3 on
  # managed drift so an Agent can inspect or restore the previous bytes.
  # If the staged rename fails, the previous target is restored from backup;
  # if restoration itself fails, the backup is retained and its recovery path
  # is reported instead of being deleted.
  "$installer_python" -c 'import os, shutil, sys
staged, target, backup, keep_previous = sys.argv[1:5]
moved = False
if os.path.lexists(target):
    try:
        os.replace(target, backup)
        moved = True
    except OSError as exc:
        sys.exit("place_staged: could not set aside %s -> %s: %s" % (target, backup, exc))
try:
    os.replace(staged, target)
except OSError as exc:
    if not moved:
        sys.exit("place_staged: rename %s -> %s failed: %s" % (staged, target, exc))
    try:
        os.replace(backup, target)
    except OSError as rb_exc:
        sys.exit(
            "place_staged: rename %s -> %s failed: %s; rollback failed: %s; "
            "previous installation retained at %s" % (staged, target, exc, rb_exc, backup)
        )
    sys.exit(
        "place_staged: rename %s -> %s failed: %s; previous installation restored from %s"
        % (staged, target, exc, backup)
    )
if os.path.lexists(backup) and keep_previous != "1":
    if os.path.isdir(backup) and not os.path.islink(backup):
        shutil.rmtree(backup)
    else:
        os.unlink(backup)' "$1" "$2" "$3" "${4:-0}"
}

# Plan every action before any write; a refusal anywhere aborts the whole run.
# $1 is the generated Skill directory name. $2 is the worker platform id, or
# empty for the main orchestrator Skill (not a platform id). Every row ends
# with the Skill's referrers as they must read after the action (Issue #123).
plan_skill() {
  local name="$1"
  local platform="${2-}"
  local source="$repo_root/skills/$name"
  local target="$target_parent/$name"
  local refs remaining

  if [[ "$mode" == install ]]; then
    [[ -f "$source/SKILL.md" && -f "$source/.generated-by-kaola-project-runner" ]] || {
      printf 'generated Skill is missing; run ./scripts/render-skills.py --write: %s\n' "$source" >&2
      exit 1
    }
    if [[ "$method" == link ]]; then
      if [[ -L "$target" ]]; then
        current="$(canonical_existing_target "$target" || true)"
        if [[ -n "$current" && "$current" -ef "$source" ]]; then
          refs="$(skill_refs "$name" 1)"
          if has_ref "$refs" "$self_ref"; then
            actions+=("already|$name|$source|$target|$refs")
          else
            actions+=("refer|$name|$source|$target|$(add_ref "$refs" "$self_ref")")
          fi
        elif [[ "$platform" == grok && -n "$current" && "$current" -ef "$repo_root" ]]; then
          actions+=("migrate|$name|$source|$target|$(add_ref "$(skill_refs "$name" 1)" "$self_ref")")
        else
          printf 'refusing to replace existing symlink: %s -> %s\n' "$target" "$(readlink "$target")" >&2
          exit 1
        fi
      elif [[ -d "$target" ]]; then
        recorded="$(receipt_digest "$receipts_dir/$name.json" "$name")"
        actual="$(tree_digest "$target")"
        refs="$(add_ref "$(skill_refs "$name")" "$self_ref")"
        if [[ -n "$recorded" && "$actual" == "$recorded" ]]; then
          actions+=("relink|$name|$source|$target|$refs")
        elif [[ -n "$recorded" ]]; then
          actions+=("relink-drift|$name|$source|$target|$refs")
        else
          printf 'refusing to replace foreign directory without ownership receipt: %s\n' "$target" >&2
          exit 1
        fi
      elif [[ -e "$target" ]]; then
        printf 'refusing to replace existing path: %s\n' "$target" >&2
        exit 1
      else
        actions+=("install|$name|$source|$target|$(add_ref "$(skill_refs "$name")" "$self_ref")")
      fi
    else
      if [[ -L "$target" ]]; then
        current="$(canonical_existing_target "$target" || true)"
        if [[ -n "$current" && ( "$current" -ef "$source" || ( "$platform" == grok && "$current" -ef "$repo_root" ) ) ]]; then
          actions+=("copy-over-link|$name|$source|$target|$(add_ref "$(skill_refs "$name" 1)" "$self_ref")")
        else
          printf 'refusing to replace existing symlink: %s -> %s\n' "$target" "$(readlink "$target")" >&2
          exit 1
        fi
      elif [[ -d "$target" ]]; then
        recorded="$(receipt_digest "$receipts_dir/$name.json" "$name")"
        if [[ -z "$recorded" ]]; then
          printf 'refusing to replace foreign directory without ownership receipt: %s\n' "$target" >&2
          exit 1
        fi
        refs="$(skill_refs "$name")"
        actual="$(tree_digest "$target")"
        if [[ "$actual" != "$recorded" ]]; then
          actions+=("repair|$name|$source|$target|$(add_ref "$refs" "$self_ref")")
        elif [[ "$actual" == "$(tree_digest "$source")" ]]; then
          # Same build already in place: reference it instead of reinstalling.
          if has_ref "$refs" "$self_ref"; then
            actions+=("already|$name|$source|$target|$refs")
          else
            actions+=("refer|$name|$source|$target|$(add_ref "$refs" "$self_ref")")
          fi
        else
          # Another build: update the one shared copy, keeping every referrer.
          actions+=("update|$name|$source|$target|$(add_ref "$refs" "$self_ref")")
        fi
      elif [[ -e "$target" ]]; then
        printf 'refusing to replace existing path: %s\n' "$target" >&2
        exit 1
      else
        actions+=("install|$name|$source|$target|$(add_ref "$(skill_refs "$name")" "$self_ref")")
      fi
    fi
  else
    # Uninstall only withdraws this runtime's reference; the Skill and its
    # receipt are removed only when no other referrer remains.
    if [[ -L "$target" ]]; then
      current="$(canonical_existing_target "$target" || true)"
      if [[ -n "$current" && ( "$current" -ef "$source" || ( "$platform" == grok && "$current" -ef "$repo_root" ) ) ]]; then
        remaining="$(drop_ref "$(skill_refs "$name" 1)" "$self_ref")"
        if [[ -n "$remaining" ]]; then
          actions+=("release|$name|$source|$target|$remaining")
        else
          actions+=("uninstall|$name|$source|$target|")
        fi
      else
        printf 'refusing to remove foreign symlink: %s -> %s\n' "$target" "$(readlink "$target")" >&2
        exit 1
      fi
    elif [[ -d "$target" ]]; then
      recorded="$(receipt_digest "$receipts_dir/$name.json" "$name")"
      if [[ -z "$recorded" ]]; then
        printf 'refusing to remove foreign directory without ownership receipt: %s\n' "$target" >&2
        exit 1
      fi
      remaining="$(drop_ref "$(skill_refs "$name")" "$self_ref")"
      if [[ -n "$remaining" ]]; then
        actions+=("release|$name|$source|$target|$remaining")
      else
        if [[ "$(tree_digest "$target")" != "$recorded" ]]; then
          printf 'refusing to remove modified installed copy (user edits preserved): %s\n' "$target" >&2
          exit 1
        fi
        actions+=("uninstall-copy|$name|$source|$target|")
      fi
    elif [[ -e "$target" ]]; then
      printf 'refusing to remove non-symlink path: %s\n' "$target" >&2
      exit 1
    else
      remaining="$(drop_ref "$(skill_refs "$name")" "$self_ref")"
      if [[ -n "$remaining" ]]; then
        actions+=("release|$name|$source|$target|$remaining")
      else
        actions+=("absent|$name|$source|$target|")
      fi
    fi
  fi
}

actions=()
for platform in "${selection[@]}"; do
  plan_skill "$(skill_name_for "$platform")" "$platform"
done
if [[ "$install_orchestrator" == true ]]; then
  plan_skill "$orchestrator_skill_name"
  if [[ "$resolved_runtime" == "codex" || "$resolved_runtime" == "generic" ]]; then
    zcode_selected=false
    for item in "${selection[@]}"; do
      [[ "$item" == zcode ]] && zcode_selected=true
    done
    if [[ "$zcode_selected" == true ]]; then
      plan_skill "$external_skill_name"
    elif [[ -e "$target_parent/$external_skill_name" || -L "$target_parent/$external_skill_name" ]]; then
      # Already installed: keep it in this control-plane plan so a filtered
      # reinstall updates it and a filtered uninstall removes it.
      plan_skill "$external_skill_name"
    else
      printf 'skipping %s: needs the ZCode worker Skill (not in --platform)\n' "$external_skill_name"
    fi
  fi
fi

bin_dir="$HOME/.local/bin"
bin_specs=(
  "kaola-acp|$script_dir/kaola-acp.py"
  "kaola-acp-holder|$script_dir/kaola-acp-holder.py"
  "kaola-project-runner-locate|$script_dir/kaola-locate.py"
)
bin_actions=()
bin_ledger=""
if [[ "$want_bin_links" == true ]]; then
  # Issue #123: the helper links are shared blocks counted in the sidecar
  # ledger beside them; an existing link to a usable target is referenced,
  # not refused, and uninstall keeps a link while anything still refers to it.
  bin_plan="$(refs_tool bin-plan "$mode" "$bin_dir" "$self_ref" "$repo_root" \
    "${bin_specs[@]/|/=}")" || exit 1
  while IFS= read -r row; do
    if [[ "$row" == ledger\|* ]]; then
      bin_ledger="${row#ledger|}"
    else
      bin_actions+=("$row")
    fi
  done < <(printf '%s\n' "$bin_plan")
fi

# Issue #97: the Codex runtime destination owns one user-level
# SessionStart(compact) recovery entry beside the control-plane Skills. The
# hook tool refuses a malformed user hooks.json before any write, so that
# refusal is planned here, before the first Skill write, and aborts the run.
# A generic --skills-dir destination is never a Codex user-level install.
hook_tool="$script_dir/kaola-codex-compact-hook.py"
codex_home="${CODEX_HOME:-$HOME/.codex}"
want_user_hook=false
if [[ "$resolved_runtime" == codex && "$install_orchestrator" == true ]]; then
  want_user_hook=true
  if [[ -d "$codex_home" ]]; then
    hook_status="$("$installer_python" "$hook_tool" user-status --codex-home "$codex_home")" || {
      printf 'refusing: Codex user-level hooks.json cannot be merged: %s\n' "$hook_status" >&2
      exit 1
    }
    if [[ "$mode" == install ]]; then
      hook_blockers="$("$installer_python" -c 'import json,sys; print("\n".join(json.loads(sys.argv[1]).get("install_blockers") or []))' "$hook_status")"
      [[ -z "$hook_blockers" ]] || {
        printf 'refusing: Codex user-level compact-recovery hook cannot be installed:\n%s\n' "$hook_blockers" >&2
        exit 1
      }
    fi
  elif [[ "$mode" == uninstall ]]; then
    want_user_hook=false
  fi
fi

[[ "$mode" == install ]] && mkdir -p "$target_parent"
[[ "$want_bin_links" == true && "$mode" == install ]] && mkdir -p "$bin_dir"

for row in "${actions[@]}"; do
  IFS='|' read -r action name source target refs < <(printf '%s\n' "$row")
  case "$action" in
    already)
      printf 'already installed: %s\n' "$target"
      ;;
    refer)
      set_skill_referrers "$name" "$source" "$refs"
      printf 'refer: %s (same build already installed; referrers: %s)\n' "$target" "$refs"
      ;;
    release)
      set_skill_referrers "$name" "$source" "$refs"
      printf 'kept: %s (still referenced by %s)\n' "$target" "$refs"
      ;;
    install|update|copy-over-link|repair)
      temp="$target_parent/.${name}.tmp.$$"
      keep_previous=0
      if [[ "$action" == repair ]]; then
        backup="$target_parent/.${name}.drift.$$"
        keep_previous=1
      else
        backup="$target_parent/.${name}.old.$$"
      fi
      [[ ! -e "$temp" && ! -L "$temp" && ! -e "$backup" && ! -L "$backup" ]] || {
        printf 'temporary path exists: %s\n' "$temp" >&2; exit 1; }
      if [[ "$method" == copy ]]; then
        if ! stage_copy "$source" "$temp"; then
          rm -rf "$temp" 2>/dev/null || true
          printf 'staging copy failed: %s\n' "$source" >&2
          exit 1
        fi
        new_digest="$(tree_digest "$temp")"
      else
        ln -s "$source" "$temp"
      fi
      if ! place_staged "$temp" "$target" "$backup" "$keep_previous"; then
        rm -rf "$temp" 2>/dev/null || true
        printf 'atomic replacement failed: %s\n' "$target" >&2
        exit 1
      fi
      if [[ "$method" == copy ]]; then
        write_receipt "$name" "$source" copy "$new_digest" "$refs"
      else
        write_receipt "$name" "$source" link "" "$refs"
      fi
      if [[ "$action" == repair ]]; then
        printf 'repair: %s (managed drift; previous copy: %s; edit repo templates/manifests, not installed Skills)\n' "$target" "$backup"
      else
        printf '%s: %s\n' "$action" "$target"
      fi
      ;;
    migrate|relink|relink-drift)
      temp="$target_parent/.${name}.tmp.$$"
      keep_previous=0
      if [[ "$action" == relink-drift ]]; then
        backup="$target_parent/.${name}.drift.$$"
        keep_previous=1
      else
        backup="$target_parent/.${name}.old.$$"
      fi
      [[ ! -e "$temp" && ! -L "$temp" && ! -e "$backup" && ! -L "$backup" ]] || {
        printf 'temporary path exists: %s\n' "$temp" >&2; exit 1; }
      ln -s "$source" "$temp"
      if ! place_staged "$temp" "$target" "$backup" "$keep_previous"; then
        rm -rf "$temp" 2>/dev/null || true
        printf 'atomic replacement failed: %s\n' "$target" >&2
        exit 1
      fi
      write_receipt "$name" "$source" link "" "$refs"
      if [[ "$action" == relink-drift ]]; then
        printf 'repair: %s -> %s (managed drift; previous copy: %s; edit repo templates/manifests, not installed Skills)\n' "$target" "$source" "$backup"
      else
        printf '%s: %s -> %s\n' "$action" "$target" "$source"
      fi
      ;;
    uninstall)
      unlink "$target"
      drop_owned_receipt "$name"
      printf 'uninstalled: %s\n' "$target"
      ;;
    uninstall-copy)
      rm -rf "$target"
      drop_owned_receipt "$name"
      printf 'uninstalled: %s\n' "$target"
      ;;
    absent)
      drop_owned_receipt "$name"
      printf 'already absent: %s\n' "$target"
      ;;
  esac
done
[[ "$mode" == uninstall ]] && rmdir "$receipts_dir" 2>/dev/null || true

if [[ "$want_user_hook" == true ]]; then
  if [[ "$mode" == install ]]; then
    hook_receipt="$("$installer_python" "$hook_tool" user-install --codex-home "$codex_home")" || {
      printf 'Codex user-level compact-recovery hook install failed: %s\n' "$hook_receipt" >&2
      exit 1
    }
    printf 'codex user hook: %s\n' "$hook_receipt"
    printf 'codex user hook: review and trust the new entry in /hooks; it loads from the next Codex session\n'
  else
    hook_receipt="$("$installer_python" "$hook_tool" user-uninstall --codex-home "$codex_home")" || {
      printf 'Codex user-level compact-recovery hook uninstall failed: %s\n' "$hook_receipt" >&2
      exit 1
    }
    printf 'codex user hook: %s\n' "$hook_receipt"
  fi
fi

for row in ${bin_actions[@]+"${bin_actions[@]}"}; do
  IFS='|' read -r action source target note < <(printf '%s\n' "$row")
  case "$action" in
    already)
      printf 'already installed: %s -> %s\n' "$target" "$(readlink "$target")"
      ;;
    refer)
      printf 'refer: %s -> %s (existing usable link kept; referrers: %s)\n' "$target" "$(readlink "$target")" "$note"
      ;;
    keep)
      printf 'kept: %s (%s)\n' "$target" "$note"
      ;;
    install)
      temp="$bin_dir/.${target##*/}.tmp.$$"
      [[ ! -e "$temp" && ! -L "$temp" ]] || { printf 'temporary path exists: %s\n' "$temp" >&2; exit 1; }
      ln -s "$source" "$temp"
      if ! "$installer_python" -c 'import os, sys
os.replace(sys.argv[1], sys.argv[2])' "$temp" "$target"
      then
        unlink "$temp" 2>/dev/null || true
        printf 'atomic symlink replacement failed: %s\n' "$target" >&2
        exit 1
      fi
      printf 'install: %s -> %s\n' "$target" "$source"
      ;;
    uninstall)
      unlink "$target"
      printf 'uninstalled: %s\n' "$target"
      ;;
    absent)
      printf 'already absent: %s\n' "$target"
      ;;
  esac
done
[[ -z "$bin_ledger" ]] || refs_tool bin-write "$bin_dir" "$bin_ledger"
