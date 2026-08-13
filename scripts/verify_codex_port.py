#!/usr/bin/env python3
"""Static completion checks for the Codex-native distribution."""
from __future__ import annotations

import ast
import importlib.util
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_EVENTS = {
    "PreToolUse",
    "PermissionRequest",
    "PostToolUse",
    "PreCompact",
    "PostCompact",
    "UserPromptSubmit",
    "SubagentStop",
    "Stop",
    "SessionStart",
    "SubagentStart",
    "SessionEnd",
}
ARCHIVED = {
    Path("docs/upstream/README.md"),
    Path("docs/upstream/SKILL.md"),
    Path("docs/CHANGELOG.md"),
    Path("docs/CODEX_PORT.md"),
}
STALE_PATTERNS = (
    re.compile(r"(?:~[/\\]|[/\\])\.claude(?:[/\\]|$)", re.IGNORECASE),
    re.compile(r"\bCLAUDE\.md\b"),
    re.compile(r"\.claude-plugin", re.IGNORECASE),
    re.compile(r"\bClaude Code\b", re.IGNORECASE),
    re.compile(r"\bclaude\s+(?:--print|mcp|--version)\b", re.IGNORECASE),
    re.compile(r"claude\.ai|claude-sonnet|AnthropicCodex|@anthropic-ai/claude-code", re.IGNORECASE),
)


class VerificationError(Exception):
    pass


def check(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationError(f"invalid JSON at {path.relative_to(ROOT)}: {exc}") from exc
    check(isinstance(value, dict), f"JSON root must be an object: {path.relative_to(ROOT)}")
    return value


def verify_manifest() -> None:
    manifest = load_json(ROOT / ".codex-plugin" / "plugin.json")
    check(manifest.get("name") == "codex-brain-starter", "manifest name mismatch")
    check(re.fullmatch(r"\d+\.\d+\.\d+", str(manifest.get("version", ""))) is not None, "manifest version is not semver")
    for key in ("description", "skills", "mcpServers", "interface"):
        check(key in manifest, f"manifest missing {key}")
    for key in ("skills", "mcpServers"):
        value = manifest[key]
        check(isinstance(value, str) and value.startswith("./"), f"manifest {key} path must start with ./")
        check((ROOT / value).exists(), f"manifest {key} target is missing: {value}")


def verify_hooks() -> None:
    config = load_json(ROOT / "hooks" / "hooks.json")
    hooks = config.get("hooks")
    check(isinstance(hooks, dict) and hooks, "hooks.json has no hooks")
    check(set(hooks) <= ALLOWED_EVENTS, f"unsupported hook events: {set(hooks) - ALLOWED_EVENTS}")
    for event, groups in hooks.items():
        check(isinstance(groups, list), f"{event} hooks must be a list")
        for group in groups:
            check(isinstance(group, dict), f"{event} hook group must be an object")
            for handler in group.get("hooks", []):
                check(handler.get("type") == "command", f"{event} has a non-command hook")
                command = str(handler.get("command", ""))
                windows = str(handler.get("commandWindows", ""))
                check("${PLUGIN_ROOT}" in command, f"{event} command does not use PLUGIN_ROOT")
                check("%PLUGIN_ROOT%" in windows, f"{event} Windows command does not use PLUGIN_ROOT")
    runtime = ROOT / "hooks" / "codex_runtime.py"
    check(runtime.is_file(), "Codex hook runtime is missing")
    ast.parse(runtime.read_text(encoding="utf-8"), filename=str(runtime))


def parse_frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    check(lines and lines[0].strip() == "---", f"missing frontmatter: {path.relative_to(ROOT)}")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise VerificationError(f"unterminated frontmatter: {path.relative_to(ROOT)}") from exc
    result: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" in line:
            key, value = line.split(":", 1)
            value = value.strip()
            if value.startswith('"') and value.endswith('"'):
                value = json.loads(value)
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1].replace("''", "'")
            result[key.strip()] = value
    return result


def verify_skills() -> None:
    skill_root = ROOT / "skills"
    count = 0
    names: set[str] = set()
    for directory in sorted(skill_root.iterdir()):
        if not directory.is_dir() or directory.name.startswith("_"):
            continue
        skill_file = directory / "SKILL.md"
        check(skill_file.is_file(), f"skill directory has no SKILL.md: {directory.name}")
        metadata = parse_frontmatter(skill_file)
        name = metadata.get("name", "")
        check(name == directory.name, f"skill name/folder mismatch: {directory.name} != {name}")
        check(bool(metadata.get("description")), f"skill has no description: {name}")
        check(set(metadata) == {"name", "description"}, f"unsupported frontmatter keys in {name}: {set(metadata) - {'name', 'description'}}")
        check(name not in names, f"duplicate skill name: {name}")
        names.add(name)
        count += 1
    check(count >= 30, f"expected the full skill bundle, found only {count}")
    setup = ROOT / "skills" / "setup-brain" / "SKILL.md"
    check(len(setup.read_text(encoding="utf-8-sig").splitlines()) < 500, "setup-brain exceeds progressive-disclosure limit")
    for ref in re.findall(r"`(phases/[^`]+\.md)`", setup.read_text(encoding="utf-8-sig")):
        check((ROOT / ref).is_file(), f"setup-brain points to missing phase: {ref}")


def verify_python() -> None:
    checked = 0
    for path in ROOT.rglob("*.py"):
        if any(part in {"__pycache__", "vendor"} for part in path.parts):
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except (SyntaxError, UnicodeError) as exc:
            raise VerificationError(f"Python parse failed at {path.relative_to(ROOT)}: {exc}") from exc
        checked += 1
    check(checked >= 300, f"expected full Python surface, parsed only {checked} files")


def verify_native_references() -> None:
    suffixes = {".md", ".py", ".sh", ".ps1", ".json", ".yaml", ".yml", ".toml"}
    files: set[Path] = {
        ROOT / "AGENTS.md",
        ROOT / "README.md",
        ROOT / "bootstrap.sh",
        ROOT / "bootstrap.ps1",
        ROOT / ".mcp.json",
        ROOT / ".codex-plugin" / "plugin.json",
        ROOT / "hooks" / "hooks.json",
        ROOT / "hooks" / "codex_runtime.py",
        ROOT / "scripts" / "install_codex_plugin.py",
    }
    for directory in (ROOT / "skills", ROOT / "phases", ROOT / "templates" / "generated"):
        files.update(path for path in directory.rglob("*") if path.is_file() and path.suffix.lower() in suffixes)
    runtime_path = ROOT / "hooks" / "codex_runtime.py"
    spec = importlib.util.spec_from_file_location("codex_runtime_verify", runtime_path)
    check(spec is not None and spec.loader is not None, "cannot load Codex hook runtime")
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    files.update(ROOT / relative for handlers in runtime.HANDLERS.values() for relative in handlers)
    failures: list[str] = []
    for path in sorted(files):
        check(path.is_file(), f"active file is missing: {path.relative_to(ROOT)}")
        rel = path.relative_to(ROOT)
        if rel in ARCHIVED:
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if any(pattern.search(text) for pattern in STALE_PATTERNS):
            failures.append(str(rel))
    check(not failures, "active files retain stale Claude references: " + ", ".join(failures[:12]))
    check(not (ROOT / "CLAUDE.md").exists(), "legacy CLAUDE.md remains at plugin root")
    check(not (ROOT / ".claude-plugin").exists(), "legacy .claude-plugin remains")
    check((ROOT / "AGENTS.md").is_file(), "root AGENTS.md is missing")


def verify_mcp() -> None:
    config = load_json(ROOT / ".mcp.json")
    servers = config.get("mcpServers")
    check(isinstance(servers, dict) and "health" in servers, "Health MCP declaration missing")
    check(servers["health"].get("command") == "codex-brain-health-mcp", "Health MCP command mismatch")
    pyproject = (ROOT / "services" / "health-mcp" / "pyproject.toml").read_text(encoding="utf-8")
    check('codex-brain-health-mcp = "main:run"' in pyproject, "Health MCP executable entry point missing")


def verify_bootstrap() -> None:
    check((ROOT / "bootstrap.sh").is_file(), "bootstrap.sh missing")
    ps1 = ROOT / "bootstrap.ps1"
    check(ps1.read_bytes().startswith(b"\xef\xbb\xbf"), "bootstrap.ps1 must be UTF-8 with BOM")


def main() -> int:
    checks = (
        verify_manifest,
        verify_hooks,
        verify_skills,
        verify_python,
        verify_native_references,
        verify_mcp,
        verify_bootstrap,
    )
    try:
        for function in checks:
            function()
            print(f"PASS {function.__name__}")
    except VerificationError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    print(f"Codex port verified: {len(checks)} check groups passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
