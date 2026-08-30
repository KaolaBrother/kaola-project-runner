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


def collect_json_models(value: Any, found: dict[str, str]) -> None:
    if isinstance(value, dict):
        models = value.get("models")
        if isinstance(models, dict):
            for model_id, details in models.items():
                if isinstance(model_id, str):
                    display = details.get("displayName", model_id) if isinstance(details, dict) else model_id
                    found[model_id] = str(display)
        model_id = value.get("id")
        if isinstance(model_id, str):
            found[model_id] = str(value.get("name") or value.get("displayName") or model_id)
        for child in value.values():
            collect_json_models(child, found)
    elif isinstance(value, list):
        for child in value:
            collect_json_models(child, found)


def models_from_output(output: str) -> dict[str, str]:
    found: dict[str, str] = {}
    try:
        collect_json_models(json.loads(output), found)
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
    # Claude currently exposes aliases through help rather than a catalog command.
    for alias in re.findall(r"['\"](fable|opus|sonnet)['\"]", output, re.I):
        found[alias.lower()] = alias.title()
    return found


def probes_for(platform: str) -> list[list[str]]:
    return {
        "grok": [["models"], ["inspect", "--json"], ["--help"]],
        "claude-code": [["--help"]],
        "opencode": [["models"], ["--help"]],
        "kimi-cli": [["provider", "list", "--json"], ["models"], ["doctor"], ["--help"]],
        "cursor-cli": [["--list-models"], ["models"], ["--help"]],
    }[platform]


def public_probe(probe: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in probe.items() if key != "output"}


def resolve(args: argparse.Namespace) -> dict[str, Any]:
    probes = [run_probe(args.runtime_bin, args.repo, argv) for argv in probes_for(args.platform)]
    available: dict[str, str] = {}
    for probe in probes:
        if probe.get("returncode") == 0:
            available.update(models_from_output(str(probe.get("output", ""))))

    candidate = args.candidate_id
    resolved = candidate if candidate in available else None
    if resolved is None:
        folded = args.requested_name.casefold()
        matches = [model_id for model_id, name in available.items() if name.casefold() == folded]
        if len(matches) == 1:
            resolved = matches[0]

    # A partial help-only surface can establish documented Claude aliases. If a
    # legacy/fake runtime has no readable catalog at all, retain the declared
    # exact candidate as unknown catalog evidence so communication remains usable.
    catalog_readable = bool(available)
    if resolved is None and not catalog_readable:
        resolved = candidate
        resolution_state = "catalog-unknown-declared-candidate"
    elif resolved is None:
        resolution_state = "unavailable"
    else:
        resolution_state = "resolved"

    parameters: dict[str, Any] = {}
    if args.effort:
        parameters["effort"] = args.effort
    if args.fast != "unknown":
        parameters["fast"] = args.fast == "true"
    display = available.get(resolved or "", args.requested_name if resolved else "")
    option_text = "\n".join(str(item.get("output", "")) for item in probes)
    supported_options = sorted(
        option for option in ("--effort", "--reasoning-effort", "--variant")
        if option in option_text
    )
    provenance = {
        "requested": {"source": args.source, "name": args.requested_name},
        "catalog_probe": {
            "probes": [public_probe(item) for item in probes],
            "available_models": sorted(available),
            "state": "readable" if catalog_readable else "unknown",
        },
        "resolution": {
            "state": resolution_state,
            "candidate_id": candidate,
            "resolved_id": resolved,
            "display_name": display or None,
            "supported_options": supported_options,
        },
    }
    return {
        "requested_model_source": args.source,
        "requested_model_name": args.requested_name,
        "resolved_runtime_model_id": resolved,
        "resolved_runtime_model_display": display or None,
        "resolved_parameters": parameters,
        "actual_runtime_model_id": None,
        "actual_parameters": None,
        "model_verified": "unknown" if resolved else False,
        "model_mismatch_reason": "actual-model-evidence-not-yet-read" if resolved else "requested-model-unavailable",
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
    resolving.add_argument("--source", choices=("user", "runner-default"), required=True)
    resolving.add_argument("--requested-name", required=True)
    resolving.add_argument("--candidate-id", required=True)
    resolving.add_argument("--effort", default="")
    resolving.add_argument("--fast", choices=("true", "false", "unknown"), default="unknown")
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
