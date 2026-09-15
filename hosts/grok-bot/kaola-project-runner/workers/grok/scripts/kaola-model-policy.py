#!/usr/bin/env python3
"""Resolve and verify per-run main-model facts without changing CLI config."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


def digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_probe(runtime: str, repo: str, argv: list[str]) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [runtime, *argv], cwd=repo, text=True, capture_output=True,
            timeout=float(os.environ.get("KAOLA_MODEL_PROBE_TIMEOUT", "5")), check=False,
        )
        output = (result.stdout + result.stderr).strip()
        return {
            "command": [Path(runtime).name, *argv],
            "returncode": result.returncode,
            "output": output,
            "output_digest": digest(output),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "command": [Path(runtime).name, *argv],
            "returncode": None,
            "output": "",
            "output_digest": None,
            "error": type(exc).__name__,
        }


def entry_supports_fast(details: Any) -> bool:
    if not isinstance(details, dict):
        return False
    tiers = details.get("service_tiers")
    if isinstance(tiers, list):
        for tier in tiers:
            label = tier.get("id") or tier.get("name") if isinstance(tier, dict) else tier
            if isinstance(label, str) and ("fast" in label.lower() or "priority" in label.lower()):
                return True
    extra = details.get("additional_speed_tiers")
    if isinstance(extra, list) and any("fast" in str(item).lower() for item in extra):
        return True
    return False


def collect_json_models(value: Any, found: dict[str, str], fast_ids: set[str] | None = None) -> None:
    if isinstance(value, dict):
        models = value.get("models")
        if isinstance(models, dict):
            for model_id, details in models.items():
                if isinstance(model_id, str):
                    display = details.get("displayName", model_id) if isinstance(details, dict) else model_id
                    found[model_id] = str(display)
                    if fast_ids is not None and entry_supports_fast(details):
                        fast_ids.add(model_id)
        elif isinstance(models, list):
            for details in models:
                if isinstance(details, dict):
                    model_id = details.get("id") or details.get("slug")
                    if isinstance(model_id, str):
                        found[model_id] = str(
                            details.get("name") or details.get("display_name")
                            or details.get("displayName") or model_id
                        )
                        if fast_ids is not None and entry_supports_fast(details):
                            fast_ids.add(model_id)
        model_id = value.get("id") or value.get("slug")
        if isinstance(model_id, str):
            found[model_id] = str(
                value.get("name") or value.get("display_name") or value.get("displayName") or model_id
            )
            if fast_ids is not None and entry_supports_fast(value):
                fast_ids.add(model_id)
        for child in value.values():
            collect_json_models(child, found, fast_ids)
    elif isinstance(value, list):
        for child in value:
            collect_json_models(child, found, fast_ids)


def models_from_output(output: str) -> tuple[dict[str, str], set[str]]:
    found: dict[str, str] = {}
    fast_ids: set[str] = set()
    try:
        collect_json_models(json.loads(output), found, fast_ids)
    except (json.JSONDecodeError, TypeError):
        pass
    for line in output.splitlines():
        stripped = line.strip()
        pipe = stripped.split("|")
        if len(pipe) >= 2 and pipe[1].strip():
            found[pipe[1].strip()] = pipe[0].strip() or pipe[1].strip()
        match = re.match(r"^(?:[*+-]\s*)?([a-z0-9][a-z0-9._:/-]+)(?:\s+\(default\))?(?:\s+-\s+(.+))?$", stripped, re.I)
        if match and ("/" in match.group(1) or "-" in match.group(1)):
            found[match.group(1)] = (match.group(2) or match.group(1)).strip()
        # Devin-style catalog: "  model-id  Display Name  [pricing]" or
        # single-token IDs like "adaptive" followed by a display name and
        # a bracketed pricing/context block.  Require the bracket content
        # to contain a pricing or context indicator ($ or "context") so
        # CLI help lines like "list  List sessions  [aliases: ls]" are
        # not falsely parsed as models.
        catalog_match = re.match(
            r"^([a-z0-9][a-z0-9._:/-]*)\s{2,}(\S.+?)\s+\[([^\]]*)\]",
            stripped, re.I,
        )
        if catalog_match and re.search(r"\$|context|Free", catalog_match.group(3)):
            found[catalog_match.group(1)] = catalog_match.group(2).strip()
    # Claude currently exposes aliases through help rather than a catalog command.
    for alias in re.findall(r"['\"](fable|opus|sonnet)['\"]", output, re.I):
        found[alias.lower()] = alias.title()
    for model_id in found:
        if model_id.endswith(("-fast", "-priority")):
            fast_ids.add(model_id)
    return found, fast_ids


def probes_for(platform: str) -> list[list[str]]:
    return {
        "grok": [["models"], ["inspect", "--json"], ["--help"]],
        "claude-code": [["--help"]],
        "opencode": [["models"], ["--help"]],
        "kimi-cli": [["provider", "list", "--json"], ["models"], ["doctor"], ["--help"]],
        "cursor-cli": [["--list-models"], ["models"], ["--help"]],
        "devin": [["models", "list"], ["--help"]],
        # `codex debug models` is a read-only catalog dump; it carries slugs,
        # supported reasoning levels, and per-model fast service tiers.
        "codex": [["debug", "models"], ["--help"]],
    }[platform]


def public_probe(probe: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in probe.items() if key != "output"}


# Platforms whose live TUI evidence parser reports the fast flag; only those
# get "fast" added to resolved_parameters for verify() to compare.
FAST_OBSERVABLE_PLATFORMS = {"cursor-cli"}


def resolve(args: argparse.Namespace) -> dict[str, Any]:
    probes = [run_probe(args.runtime_bin, args.repo, argv) for argv in probes_for(args.platform)]
    available: dict[str, str] = {}
    fast_capable: set[str] = set()
    for probe in probes:
        if probe.get("returncode") == 0:
            found, fast_ids = models_from_output(str(probe.get("output", "")))
            available.update(found)
            fast_capable.update(fast_ids)

    # The catalog is an evidence source, not a model picker.  Keep the exact
    # candidate supplied by the Agent (or by the adapter's declared default) as
    # the launch identifier even when a readable catalog omits it.  In
    # particular, never rewrite a literal through a display-name match: doing
    # so would silently select a different runtime model.
    candidate = args.candidate_id
    resolved = candidate
    catalog_readable = bool(available)

    suffixes = [item for item in (args.fast_suffixes or "").split(",") if item]
    is_fast_id = bool(candidate) and any(candidate.endswith(item) for item in suffixes)
    fast_requested = {"true": "on", "false": "off"}.get(args.fast, "unknown")
    fast_block: dict[str, Any] = {
        "requested": fast_requested,
        "mechanism": args.fast_mechanism,
    }
    resolved_fast = "unknown"
    if args.fast_mechanism == "model-suffix":
        fast_block["support"] = "model-variant"
        if fast_requested == "on":
            if is_fast_id:
                resolved_fast = "on"
                fast_block["detail"] = "explicit fast model ID"
            elif candidate:
                variant = next(
                    (candidate + item for item in suffixes if (candidate + item) in available),
                    None,
                )
                if variant:
                    resolved = variant
                    resolved_fast = "on"
                    fast_block["detail"] = f"catalog fast variant {variant}"
                elif catalog_readable:
                    resolved_fast = "unsupported"
                    fast_block["detail"] = "no advertised fast variant for resolved model"
                else:
                    resolved_fast = "unknown"
                    fast_block["detail"] = "catalog unreadable; fast variant availability unknown"
            else:
                resolved_fast = "unknown"
                fast_block["detail"] = "no resolved model to attach a fast variant"
        elif fast_requested == "off":
            if is_fast_id:
                resolved_fast = "on"
                fast_block["conflict"] = "explicit fast model ID supplied with --fast off"
            else:
                resolved_fast = "off"
        else:
            resolved_fast = "on" if is_fast_id else "unknown"
    elif args.fast_mechanism == "config":
        fast_block["support"] = "config"
        if fast_requested in ("on", "off"):
            resolved_fast = fast_requested
            if candidate:
                fast_block["model_support"] = (
                    candidate in fast_capable if fast_capable else "unknown"
                )
        else:
            resolved_fast = "unknown"
    elif args.fast_mechanism == "settings":
        # A process-scoped launch setting (e.g. claude --settings
        # '{"fastMode": ...}') carries the request verbatim. Whether the
        # model honors it is the native CLI's determination — no Runner-side
        # capability inference; effective stays unknown without native
        # evidence.
        fast_block["support"] = "settings"
        if fast_requested in ("on", "off"):
            resolved_fast = fast_requested
            fast_block["detail"] = "applied via launch settings; native support determined by the CLI"
        else:
            resolved_fast = "unknown"
    else:
        fast_block["support"] = "none"
        if fast_requested == "on":
            resolved_fast = "unsupported"
            fast_block["detail"] = "no native Fast mechanism; request reported unsupported"
        elif fast_requested == "off":
            resolved_fast = "off"
            fast_block["detail"] = "no native Fast mechanism; nothing to enable"

    if not candidate:
        resolution_state = (
            "resume-preserved" if args.source == "resume-preserved" else "native-default"
        )
    elif candidate in available:
        resolution_state = "resolved"
    elif catalog_readable:
        resolution_state = "catalog-missing-declared-candidate"
    else:
        resolution_state = "catalog-unknown-declared-candidate"

    parameters: dict[str, Any] = {}
    if args.effort:
        parameters["effort"] = args.effort
    if (
        resolved_fast in ("on", "off")
        and args.fast_mechanism == "model-suffix"
        and args.platform in FAST_OBSERVABLE_PLATFORMS
    ):
        parameters["fast"] = resolved_fast == "on"
    display = available.get(resolved, args.requested_name)
    option_text = "\n".join(str(item.get("output", "")) for item in probes)
    supported_options = sorted(
        option for option in ("--effort", "--reasoning-effort", "--variant")
        if option in option_text
    )
    provenance = {
        "requested": {"source": args.source, "name": args.requested_name},
        "selection": {"source": args.source, "tier": args.tier or None},
        "catalog_probe": {
            "probes": [public_probe(item) for item in probes],
            "available_model_count": len(available),
            "candidate_present": candidate in available,
            "state": "readable" if catalog_readable else "unknown",
        },
        "resolution": {
            "state": resolution_state,
            "candidate_id": candidate or None,
            "resolved_id": resolved or None,
            "display_name": display or None,
            "supported_options": supported_options,
        },
        "fast": fast_block,
    }
    if resolved != candidate:
        provenance["resolution"]["fast_variant_applied"] = resolved
    return {
        "requested_model_source": args.source,
        "requested_model_name": args.requested_name,
        "requested_tier": args.tier or None,
        "requested_fast": fast_requested,
        "resolved_runtime_model_id": resolved,
        "resolved_runtime_model_display": display or None,
        "resolved_parameters": parameters,
        "resolved_fast": resolved_fast,
        "actual_runtime_model_id": None,
        "actual_parameters": None,
        "model_verified": "unknown",
        "model_mismatch_reason": "actual-model-evidence-not-yet-read",
        "model_evidence_provenance": provenance,
    }


def marker_evidence(frame: str) -> tuple[str | None, dict[str, Any] | None, str | None]:
    matches = re.findall(r"KPR_MODEL_EVIDENCE\s+(\{[^\n]+\})", frame)
    if matches:
        try:
            value = json.loads(matches[-1])
            return value.get("model_id"), value.get("parameters") or {}, str(value.get("source") or "runtime-marker")
        except json.JSONDecodeError:
            pass
    matches = re.findall(
        r"Active model:\s*([^|\n]+?)\s*\|\s*effort=([^|\s]+)\s*\|\s*fast=(true|false)",
        frame, re.I,
    )
    if matches:
        model_id, effort, fast = matches[-1]
        return model_id.strip(), {"effort": effort.lower(), "fast": fast.lower() == "true"}, "main-tui"
    return None, None, None


def real_surface_evidence(platform: str, frame: str) -> tuple[str | None, dict[str, Any] | None, str | None]:
    if "Active model evidence unavailable" in frame:
        return None, None, None
    model_id, parameters, source = marker_evidence(frame)
    if model_id:
        return model_id, parameters, source
    # Only runtime-owned TUI text may establish actual model identity.  Shell
    # launch preambles contain the requested argv and are resolution evidence,
    # not proof of what the child actually selected.
    anchors = {
        "claude-code": "Claude Code",
        "codex": "OpenAI Codex",
        "cursor-cli": "Cursor Agent",
        "opencode": "OpenCode",
        "kimi-cli": "Kimi Code",
    }
    anchor = anchors.get(platform)
    runtime_frame = frame
    if anchor:
        if anchor not in frame:
            # Some TUIs keep a distinctive model footer after their header has
            # scrolled away.  These footer forms cannot occur in launch argv.
            if platform == "cursor-cli" and "Cursor Grok 4.6" in frame:
                runtime_frame = frame
            elif platform == "kimi-cli" and re.search(r"\byolo\s+K3\s+thinking:\s*(?:low|high|max)\b", frame, re.I):
                runtime_frame = frame
            elif platform == "opencode" and re.search(r"\b(?:Build|Plan)\s+·\s+GLM[- ]?5\.3\b", frame, re.I):
                runtime_frame = frame
            elif platform == "codex" and re.search(
                r"^\s*[a-z0-9][a-z0-9._:/-]+\s+(?:low|medium|high|xhigh|max|ultra)\s+·\s+\S",
                frame, re.I | re.M,
            ):
                runtime_frame = frame
            else:
                return None, None, None
        else:
            runtime_frame = frame[frame.rfind(anchor):]

    if platform == "claude-code":
        matches = re.findall(r"\b(Opus|Sonnet|Fable)\s+\d+(?:\.\d+)?\s*\|\s*(low|medium|high|xhigh|max) effort", runtime_frame, re.I)
        if matches:
            family, effort = matches[-1]
            return family.lower(), {"effort": effort.lower()}, "claude-main-tui"
        families = re.findall(r"\b(Opus|Sonnet|Fable)\s+\d+(?:\.\d+)?\b", runtime_frame, re.I)
        efforts = re.findall(r"\b(low|medium|high|xhigh|max)\b(?:\s+effort|\s*·\s*/effort)", runtime_frame, re.I)
        if families and efforts:
            return families[-1].lower(), {"effort": efforts[-1].lower()}, "claude-main-tui"
    elif platform == "cursor-cli":
        matches = re.findall(r"Cursor Grok 4\.6(?:\s*[—|-]?\s*)?(Extra High|High|Medium|Low)(?:\s+(Fast))?", runtime_frame, re.I)
        if matches:
            effort_label, fast_label = matches[-1]
            effort = {"extra high": "xhigh", "high": "high", "medium": "medium", "low": "low"}[effort_label.lower()]
            suffix = "-fast" if fast_label else ""
            return f"cursor-grok-4.6-{effort}{suffix}", {"effort": effort, "fast": bool(fast_label)}, "cursor-main-tui"
    elif platform == "grok":
        model_effort = re.findall(
            r"\bGrok\s+(4\.[0-9]+)\s*\((low|medium|high|xhigh|max|extra high)\)",
            runtime_frame,
            re.I,
        )
        if model_effort:
            version, effort_label = model_effort[-1]
            effort = effort_label.lower().replace("extra high", "xhigh")
            return f"grok-{version.lower()}", {"effort": effort, "fast": False}, "grok-main-tui"
        models = re.findall(r"\bgrok-4\.[0-9]+\b", runtime_frame, re.I)
        efforts = re.findall(r"\b(low|medium|high|xhigh|max|extra high)\b", runtime_frame, re.I)
        if models and efforts:
            effort = efforts[-1].lower().replace("extra high", "xhigh")
            return models[-1].lower(), {"effort": effort, "fast": False}, "grok-main-tui"
    elif platform == "opencode":
        if re.search(r"\b(?:Build|Plan)\s+·\s+GLM[- ]?5\.3\b", runtime_frame, re.I):
            efforts = re.findall(r"\b(low|high|max)\b", runtime_frame, re.I)
            if efforts:
                return "zhipuai-coding-plan/glm-5.3", {"effort": efforts[-1].lower()}, "opencode-main-tui"
            return "zhipuai-coding-plan/glm-5.3", {}, "opencode-main-tui"
    elif platform == "kimi-cli":
        if "Trust this folder?" in runtime_frame:
            return None, None, None
        footer = re.findall(r"\byolo\s+K3\s+thinking:\s*(low|high|max)\b", runtime_frame, re.I)
        if footer:
            return "kimi-code/k3", {"effort": footer[-1].lower()}, "kimi-main-tui"
    elif platform == "codex":
        # Codex TUI header row:  "model:       gpt-6-astra medium   /model to change"
        # Codex TUI footer row:  "  gpt-6-astra medium · /private/tmp"
        header = re.findall(
            r"\bmodel:\s*([a-z0-9][a-z0-9._:/-]*)\s+(low|medium|high|xhigh|max|ultra)\b",
            runtime_frame, re.I,
        )
        if header:
            model_id, effort = header[-1]
            return model_id.lower(), {"effort": effort.lower()}, "codex-main-tui"
        footer = re.findall(
            r"^\s*([a-z0-9][a-z0-9._:/-]+)\s+(low|medium|high|xhigh|max|ultra)\s+·\s+\S",
            runtime_frame, re.I | re.M,
        )
        if footer:
            model_id, effort = footer[-1]
            return model_id.lower(), {"effort": effort.lower()}, "codex-main-tui"
    elif platform == "devin":
        # Devin TUI footer shape: the model display name followed by 2+
        # spaces and one of the known trailing annotations:
        #   "Adaptive                         Context: 14k tokens"
        #   "Adaptive                         Type @ to mention files ..."
        # Require this concrete shape so capitalized non-model lines
        # (e.g. "Max · 97% remaining", "Done", ordinary output) are
        # never falsely classified as model evidence.
        footer_re = re.compile(
            r"^(.+?)\s{2,}(?:Context:\s*\d+k?\s*tokens|Type\s+@\s|Press\s+Ctrl|Alt\+Enter\s)",
            re.I,
        )
        for line in reversed(runtime_frame.splitlines()):
            m = footer_re.match(line.strip())
            if m:
                display = m.group(1).strip()
                if display and re.match(r"[A-Z]", display):
                    return display, {}, "devin-footer"
    return None, None, None


def verify(args: argparse.Namespace) -> dict[str, Any]:
    policy = json.loads(args.policy_json)
    frame = Path(args.frame_file).read_text(encoding="utf-8")
    prior_actual_id = policy.get("actual_runtime_model_id")
    prior_actual_parameters = policy.get("actual_parameters")
    actual_id, actual_parameters, actual_source = real_surface_evidence(args.platform, frame)
    provenance = policy.setdefault("model_evidence_provenance", {})
    latest_observation = {
        "source": actual_source or "unreadable",
        "frame_digest": digest(frame),
        "model_id": actual_id,
        "parameters": actual_parameters,
    }
    provenance["latest_observation"] = latest_observation
    if not actual_id and prior_actual_id:
        # Preserve the last runtime-owned confirmation.  A later frame that has
        # scrolled past the model footer is new unreadable evidence, not proof
        # that the already-confirmed session model changed.
        policy["actual_runtime_model_id"] = prior_actual_id
        policy["actual_parameters"] = prior_actual_parameters
        return policy
    # Devin footer returns a display name (e.g. "Adaptive"), not a model ID.
    # Resolve it to the policy's model ID by comparing against the resolved
    # display name; attribute the resolved ID only on exact match.
    if actual_source == "devin-footer" and actual_id:
        expected_display = policy.get("resolved_runtime_model_display")
        if expected_display and actual_id == expected_display:
            actual_id = policy.get("resolved_runtime_model_id")
    policy["actual_runtime_model_id"] = actual_id
    policy["actual_parameters"] = actual_parameters
    provenance["actual"] = {
        **latest_observation,
        "model_id": actual_id,
        "parameters": actual_parameters,
    }
    if not actual_id:
        policy["model_verified"] = "unknown"
        policy["model_mismatch_reason"] = "actual-model-evidence-unreadable"
        return policy
    expected_id = policy.get("resolved_runtime_model_id")
    if not expected_id:
        # No Runner model override was resolved (native default or preserved
        # resume state).  The actual observation is still reported, but it is
        # not comparable to a Runner-selected target.
        policy["model_verified"] = "unknown"
        state = (provenance.get("resolution") or {}).get("state")
        policy["model_mismatch_reason"] = (
            "resume-preserved-actual-not-comparable"
            if state == "resume-preserved"
            else "native-default-model-not-comparable"
        )
        return policy
    if actual_id != expected_id:
        policy["model_verified"] = False
        policy["model_mismatch_reason"] = f"actual-model-mismatch:{actual_id}"
        return policy
    expected_parameters = policy.get("resolved_parameters") or {}
    for key, expected in expected_parameters.items():
        if actual_parameters is None or key not in actual_parameters:
            policy["model_verified"] = "unknown"
            policy["model_mismatch_reason"] = f"actual-{key}-evidence-unreadable"
            return policy
        if actual_parameters[key] != expected:
            policy["model_verified"] = False
            policy["model_mismatch_reason"] = f"actual-{key}-mismatch:{actual_parameters[key]}"
            return policy
    policy["model_verified"] = True
    policy["model_mismatch_reason"] = None
    return policy


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    resolving = sub.add_parser("resolve")
    resolving.add_argument("--platform", required=True)
    resolving.add_argument("--runtime-bin", required=True)
    resolving.add_argument("--repo", required=True)
    resolving.add_argument(
        "--source",
        choices=("user", "runner-default", "runner-upgrade", "resume-preserved"),
        required=True,
    )
    resolving.add_argument("--requested-name", required=True)
    resolving.add_argument("--candidate-id", required=True)
    resolving.add_argument("--effort", default="")
    resolving.add_argument("--fast", choices=("true", "false", "unknown"), default="unknown")
    resolving.add_argument("--tier", choices=("default", "upgrade"), default="default")
    resolving.add_argument(
        "--fast-mechanism", choices=("none", "config", "model-suffix", "settings"), default="none"
    )
    resolving.add_argument("--fast-suffixes", default="-fast,-priority")
    verifying = sub.add_parser("verify")
    verifying.add_argument("--platform", required=True)
    verifying.add_argument("--policy-json", required=True)
    verifying.add_argument("--frame-file", required=True)
    args = parser.parse_args()
    value = resolve(args) if args.command == "resolve" else verify(args)
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
