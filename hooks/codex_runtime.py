#!/usr/bin/env python3
"""Codex lifecycle-hook adapter for the upstream AI Brain guard scripts.

Codex and Codex hooks share many event concepts but not every input/output
detail. This adapter keeps the proven Python guards, normalizes Codex tool
payloads, and emits only fields supported by Codex. Neutral guards never
auto-approve a tool call; the normal Codex permission policy still applies.
"""
from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(os.environ.get("PLUGIN_ROOT", Path(__file__).resolve().parents[1])).resolve()
DEBUG = os.environ.get("CODEX_BRAIN_DEBUG_HOOKS") == "1"

HANDLERS: dict[tuple[str, str], tuple[str, ...]] = {
    ("SessionStart", ""): (
        "hooks/session-start-context.py",
        "hooks/inject-instinct-context.py",
        "hooks/first-week-checkin.py",
        "hooks/surface-stranded-session-artifacts.py",
        "hooks/surface-orphan-worktree-snapshots.py",
        "hooks/worktree-footprint-signal.py",
        "hooks/warn-vault-session-in-worktree.py",
        "hooks/surface-backup-status.py",
        "hooks/enforce-worktree-cap.py",
        "hooks/remediate-runaway-procs.py",
        "hooks/context-budget-measure.py",
        "hooks/surface-connector-liveness.py",
        "hooks/relocate-watch-surface.py",
        "hooks/dev-hub-refresh-on-session-start.py",
    ),
    ("UserPromptSubmit", ""): (
        "hooks/detect-closing-signal.py",
        "hooks/warn-vault-session-in-worktree.py",
        "hooks/log-skill-usage.py",
        "hooks/inject-love-language-context.py",
        "hooks/inject-meeting-workflow-on-trigger.py",
    ),
    ("PreToolUse", "shell"): (
        "hooks/warn-vault-session-in-worktree.py",
        "hooks/warn-journal-saved-without-context.py",
        "hooks/warn-chained-state-command-truncated.py",
        "hooks/check-cd-outside-worktree.py",
        "hooks/block-git-mutation-mid-operation.py",
        "hooks/block-codex-mcp-inline-secret.py",
        "hooks/observe-tool-calls.py",
    ),
    ("PreToolUse", "write"): (
        "hooks/lint-vault-frontmatter.py",
        "hooks/validate-skill-frontmatter.py",
        "hooks/block-secret-in-note.py",
        "hooks/validate-handoff-frontmatter.py",
        "hooks/block-populated-public-skill.py",
        "hooks/warn-learning-to-tool-private-memory.py",
        "hooks/warn-workflow-call-permission-elevation.py",
        "hooks/warn-journal-saved-without-context.py",
        "hooks/block-mcp-config-inline-secret.py",
        "hooks/observe-tool-calls.py",
    ),
    ("PreToolUse", "observe"): ("hooks/observe-tool-calls.py",),
    ("PostToolUse", ""): ("hooks/post-tool-use-learnings.py",),
    ("PreCompact", ""): ("hooks/pre-compact-context.py",),
    ("Stop", ""): (
        "hooks/snapshot-pending-work-on-stop.py",
        "hooks/coach-auto-prescribe-on-journal.py",
        "hooks/verify-session-close-cascade.py",
        "hooks/check-fabricated-verification.py",
        "hooks/check-fabricated-hook-attribution.py",
    ),
}

PATCH_PATH = re.compile(r"^\*\*\* (?:Update|Add|Delete) File: (.+)$", re.MULTILINE)


def _debug(message: str) -> None:
    if DEBUG:
        print(f"[codex-brain-hook] {message}", file=sys.stderr)


def _payloads_for_profile(payload: dict[str, Any], profile: str) -> list[dict[str, Any]]:
    adapted = copy.deepcopy(payload)
    tool_name = str(adapted.get("tool_name") or adapted.get("tool") or "")
    tool_input = adapted.get("tool_input") or {}
    if profile == "shell" and tool_name in {"exec_command", "shell", "Bash"}:
        adapted["tool_name"] = "Bash"
        return [adapted]
    if profile != "write" or tool_name != "apply_patch":
        return [adapted]

    patch = str(tool_input.get("command") or tool_input.get("patch") or "")
    paths = PATCH_PATH.findall(patch) or [""]
    result: list[dict[str, Any]] = []
    for path in paths:
        item = copy.deepcopy(adapted)
        item["tool_name"] = "Write"
        item["tool_input"] = {
            "file_path": path.strip(),
            "path": path.strip(),
            "content": patch,
            "new_string": patch,
            "edits": [{"new_string": patch}],
            "codex_original_tool_input": tool_input,
        }
        result.append(item)
    return result


def _parse_output(stdout: str) -> tuple[dict[str, Any] | None, str]:
    stripped = stdout.strip()
    if not stripped:
        return None, ""
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        return None, stripped
    return (value if isinstance(value, dict) else None), ""


def _context_from(data: dict[str, Any] | None, plain: str) -> str:
    if plain:
        return plain
    if not data:
        return ""
    specific = data.get("hookSpecificOutput")
    if isinstance(specific, dict):
        value = specific.get("additionalContext")
        if isinstance(value, str):
            return value.strip()
    value = data.get("additionalContext")
    return value.strip() if isinstance(value, str) else ""


def _decision_from(data: dict[str, Any] | None) -> tuple[str, str]:
    if not data:
        return "", ""
    specific = data.get("hookSpecificOutput")
    if isinstance(specific, dict):
        decision = str(specific.get("permissionDecision") or "").lower()
        reason = str(specific.get("permissionDecisionReason") or "")
        if decision:
            return decision, reason
    decision = str(data.get("decision") or "").lower()
    reason = str(data.get("reason") or "")
    return decision, reason


def _run_handler(relative: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any] | None, str, str]:
    script = (ROOT / relative).resolve()
    if ROOT not in script.parents or not script.is_file():
        _debug(f"missing handler: {relative}")
        return 0, None, "", ""
    env = os.environ.copy()
    cwd = str(payload.get("cwd") or os.getcwd())
    env.setdefault("PLUGIN_ROOT", str(ROOT))
    env.setdefault("PLUGIN_DATA", str(Path.home() / ".codex" / "plugin-data" / "codex-brain-starter"))
    env.setdefault("CLAUDE_PLUGIN_ROOT", env["PLUGIN_ROOT"])
    env.setdefault("CLAUDE_PLUGIN_DATA", env["PLUGIN_DATA"])
    env.setdefault("CODEX_PROJECT_DIR", cwd)
    env.setdefault("CODEX_CWD", cwd)
    env.setdefault("CLAUDE_PROJECT_DIR", cwd)
    env.setdefault("CLAUDE_CWD", cwd)
    try:
        completed = subprocess.run(
            [sys.executable, str(script)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=cwd if Path(cwd).is_dir() else None,
            env=env,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _debug(f"{relative}: {exc}")
        return 0, None, "", ""
    data, plain = _parse_output(completed.stdout)
    return completed.returncode, data, plain, completed.stderr.strip()


def _emit_block(event: str, reason: str) -> int:
    reason = reason or "A Codex Brain safety guard blocked this action."
    if event == "PreToolUse":
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    else:
        output = {"decision": "block", "reason": reason}
    print(json.dumps(output))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    if not args:
        print("usage: codex_runtime.py EVENT [PROFILE]", file=sys.stderr)
        return 2
    event = args[0]
    profile = args[1] if len(args) > 1 else ""
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    contexts: list[str] = []
    for handler in HANDLERS.get((event, profile), ()):
        for adapted in _payloads_for_profile(payload, profile):
            code, data, plain, stderr = _run_handler(handler, adapted)
            decision, reason = _decision_from(data)
            if code == 2 or decision in {"deny", "block"}:
                return _emit_block(event, reason or stderr or plain)
            if event == "PreToolUse" and decision in {"ask", "prompt"}:
                print(json.dumps({
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "ask",
                        "permissionDecisionReason": reason,
                    }
                }))
                return 0
            if code not in {0, 2}:
                _debug(f"{handler} exited {code}: {stderr}")
            context = _context_from(data, plain)
            if context:
                contexts.append(context)

    combined = "\n\n".join(dict.fromkeys(contexts))
    if not combined:
        return 0
    if event in {"SessionStart", "UserPromptSubmit"}:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": event,
                "additionalContext": combined,
            }
        }))
    elif event == "PreCompact":
        print(combined)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
