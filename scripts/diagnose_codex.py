#!/usr/bin/env python3
"""Read-only health check for a Codex Brain Starter vault."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Finding:
    status: str
    check: str
    detail: str


def add(rows: list[Finding], status: str, check: str, detail: str) -> None:
    rows.append(Finding(status, check, detail))


def check_plugin(rows: list[Finding]) -> None:
    try:
        manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        name = manifest.get("name")
        version = manifest.get("version")
        if name != "codex-brain-starter" or not version:
            raise ValueError("identity fields are missing")
        for relative in ("skills/setup-brain/SKILL.md", "hooks/hooks.json", "hooks/codex_runtime.py"):
            if not (ROOT / relative).is_file():
                raise ValueError(f"missing {relative}")
        add(rows, "green", "plugin", f"Codex Brain Starter {version} is structurally present")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        add(rows, "red", "plugin", f"Plugin installation is incomplete: {exc}")


def check_vault(rows: list[Finding], vault: Path) -> None:
    agents = vault / "AGENTS.md"
    if not agents.is_file():
        add(rows, "red", "AGENTS.md", f"Missing at vault root: {agents}")
    else:
        text = agents.read_text(encoding="utf-8-sig", errors="replace")
        if "Vault Map" not in text:
            add(rows, "yellow", "AGENTS.md", "Present, but no Vault Map section was found")
        else:
            add(rows, "green", "AGENTS.md", "Present with a Vault Map")

    meta = vault / "⚙️ Meta"
    missing = [name for name in ("scripts", "rules") if not (meta / name).is_dir()]
    if not meta.is_dir():
        add(rows, "red", "Meta layer", f"Missing folder: {meta}")
    elif missing:
        add(rows, "yellow", "Meta layer", "Missing subfolders: " + ", ".join(missing))
    else:
        add(rows, "green", "Meta layer", "Metadata, scripts, and rules folders are present")


def check_hooks(rows: list[Finding], vault: Path) -> None:
    try:
        config = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        if not isinstance(config.get("hooks"), dict):
            raise ValueError("plugin hook map is missing")
        add(rows, "green", "plugin hooks", "Bundled hook declaration is valid JSON")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        add(rows, "red", "plugin hooks", str(exc))

    project = vault / ".codex" / "hooks.json"
    if not project.exists():
        add(rows, "green", "vault hooks", "No project hooks file; plugin hooks remain available")
        return
    try:
        value = json.loads(project.read_text(encoding="utf-8-sig"))
        if not isinstance(value.get("hooks"), dict):
            raise ValueError("root hooks object is missing")
        add(rows, "green", "vault hooks", f"Project hook file parses: {project}")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        add(rows, "red", "vault hooks", f"Invalid {project}: {exc}")


def check_journal_index(rows: list[Finding], vault: Path) -> None:
    index = vault / "⚙️ Meta" / "journal-index.json"
    if not index.exists():
        add(rows, "yellow", "journal index", "Not built yet; run the Phase 18 index builder after journals exist")
        return
    try:
        json.loads(index.read_text(encoding="utf-8-sig"))
        age_days = (datetime.now(timezone.utc).timestamp() - index.stat().st_mtime) / 86400
        if age_days > 14:
            add(rows, "yellow", "journal index", f"Valid JSON but {age_days:.0f} days old")
        else:
            add(rows, "green", "journal index", f"Valid and {age_days:.1f} days old")
    except (OSError, json.JSONDecodeError) as exc:
        add(rows, "red", "journal index", f"Malformed: {exc}")


def check_tools(rows: list[Finding]) -> None:
    for tool in ("git",):
        path = shutil.which(tool)
        add(rows, "green" if path else "red", tool, path or f"{tool} is not on PATH")
    if sys.version_info >= (3, 10):
        add(rows, "green", "python", f"{sys.version.split()[0]} at {sys.executable}")
    else:
        add(rows, "red", "python", f"Python 3.10+ required; found {sys.version.split()[0]}")


def check_git(rows: list[Finding], vault: Path) -> None:
    result = subprocess.run(
        ["git", "-C", str(vault), "rev-parse", "--is-inside-work-tree"],
        text=True,
        capture_output=True,
        check=False,
    ) if shutil.which("git") else None
    if result and result.returncode == 0:
        add(rows, "green", "vault history", "Vault is in a Git worktree")
    else:
        add(rows, "yellow", "vault history", "Vault is not Git-tracked; local snapshot history is optional but recommended")


def check_powershell_files(rows: list[Finding], vault: Path) -> None:
    failures = []
    for path in vault.rglob("*.ps1"):
        try:
            if not path.read_bytes().startswith(b"\xef\xbb\xbf"):
                failures.append(str(path.relative_to(vault)))
        except OSError:
            failures.append(str(path))
    if failures:
        add(rows, "red", "PowerShell encoding", "Missing UTF-8 BOM: " + ", ".join(failures[:5]))
    else:
        add(rows, "green", "PowerShell encoding", "All vault .ps1 files use UTF-8 BOM, or none exist")


def check_codex_config(rows: list[Finding], vault: Path) -> None:
    configs = [vault / ".codex" / "config.toml", Path.home() / ".codex" / "config.toml"]
    found = 0
    for path in configs:
        if not path.is_file():
            continue
        found += 1
        try:
            with path.open("rb") as handle:
                tomllib.load(handle)
            add(rows, "green", "Codex config", f"Valid TOML: {path}")
        except (OSError, tomllib.TOMLDecodeError) as exc:
            add(rows, "red", "Codex config", f"Invalid TOML at {path}: {exc}")
    if not found:
        add(rows, "green", "Codex config", "No project/user config file found; defaults are valid")


def check_location(rows: list[Finding], vault: Path) -> None:
    lowered = str(vault).lower()
    providers = [name for name in ("onedrive", "dropbox", "google drive", "icloud") if name in lowered]
    if providers:
        add(rows, "yellow", "vault location", f"Path appears cloud-synced ({providers[0]}); avoid putting Codex worktrees inside the watched vault")
    else:
        add(rows, "green", "vault location", "No common consumer cloud-sync segment detected")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vault", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    vault = args.vault.expanduser().resolve()
    rows: list[Finding] = []
    check_plugin(rows)
    check_vault(rows, vault)
    check_hooks(rows, vault)
    check_journal_index(rows, vault)
    check_tools(rows)
    check_git(rows, vault)
    check_powershell_files(rows, vault)
    check_codex_config(rows, vault)
    check_location(rows, vault)
    rank = {"green": 0, "yellow": 1, "red": 2}
    exit_code = max((rank[row.status] for row in rows), default=0)
    if args.as_json:
        # Keep machine-readable output ASCII-safe so redirected Windows consoles
        # using legacy code pages cannot crash on Unicode vault folder names.
        print(json.dumps({"vault": str(vault), "status": ("green", "yellow", "red")[exit_code], "findings": [asdict(row) for row in rows]}, indent=2, ensure_ascii=True))
    else:
        icon = {"green": "[OK]", "yellow": "[WARN]", "red": "[FAIL]"}
        for row in rows:
            print(f"{icon[row.status]} {row.check}: {row.detail}")
        overall = ("green", "yellow", "red")[exit_code]
        print(f"Overall: {overall}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
