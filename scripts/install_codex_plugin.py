#!/usr/bin/env python3
"""Install Codex Brain Starter into a personal Codex marketplace safely."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PLUGIN_NAME = "codex-brain-starter"
EXCLUDES = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", "node_modules"}


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _load_marketplace(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"name": "personal", "interface": {"displayName": "Personal"}, "plugins": []}
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot parse existing marketplace {path}: {exc}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("plugins", []), list):
        raise RuntimeError(f"Marketplace has an unsupported shape: {path}")
    value.setdefault("name", "personal")
    value.setdefault("interface", {"displayName": "Personal"})
    value.setdefault("plugins", [])
    return value


def _plugin_entry() -> dict[str, Any]:
    return {
        "name": PLUGIN_NAME,
        "source": {"source": "local", "path": f"./plugins/{PLUGIN_NAME}"},
        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        "category": "Productivity",
    }


def _write_marketplace(path: Path, value: dict[str, Any], *, dry_run: bool) -> Path | None:
    plugins = value["plugins"]
    entry = _plugin_entry()
    for index, current in enumerate(plugins):
        if isinstance(current, dict) and current.get("name") == PLUGIN_NAME:
            plugins[index] = entry
            break
    else:
        plugins.append(entry)
    if dry_run:
        print(f"DRY RUN: would merge {PLUGIN_NAME} into {path}")
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    backup: Path | None = None
    if path.exists():
        backup = path.with_name(f"{path.name}.bak-{_timestamp()}")
        shutil.copy2(path, backup)
    fd, raw_tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp = Path(raw_tmp)
    try:
        tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
    return backup


def _copy_plugin(source: Path, target: Path, *, dry_run: bool) -> Path | None:
    if source == target:
        print(f"Plugin already runs from {target}; skipping copy.")
        return None
    if dry_run:
        print(f"DRY RUN: would install {source} -> {target}")
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.parent / f".{PLUGIN_NAME}.staging-{os.getpid()}"
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(source, staging, ignore=shutil.ignore_patterns(*EXCLUDES))
    backup: Path | None = None
    try:
        if target.exists():
            backup = target.parent / f".{PLUGIN_NAME}.backup-{_timestamp()}"
            target.replace(backup)
        staging.replace(target)
    except Exception:
        if not target.exists() and backup and backup.exists():
            backup.replace(target)
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return backup


def _install_health_mcp(target: Path, *, dry_run: bool) -> None:
    source = target / "services" / "health-mcp"
    pipx = shutil.which("pipx")
    if not pipx:
        raise RuntimeError("pipx is required for --with-health-mcp. Install pipx, then rerun.")
    command = [pipx, "install", "--force", str(source)]
    if dry_run:
        print("DRY RUN: would run " + " ".join(command))
        return
    subprocess.run(command, check=True)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--target", type=Path, default=Path.home() / "plugins" / PLUGIN_NAME)
    parser.add_argument(
        "--marketplace",
        type=Path,
        default=Path.home() / ".agents" / "plugins" / "marketplace.json",
    )
    parser.add_argument("--with-health-mcp", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    source = args.source.expanduser().resolve()
    target = args.target.expanduser().resolve()
    marketplace = args.marketplace.expanduser().resolve()
    manifest = source / ".codex-plugin" / "plugin.json"
    if not manifest.is_file():
        print(f"ERROR: plugin manifest not found: {manifest}", file=sys.stderr)
        return 2
    if target == Path.home() or target.parent == target:
        print(f"ERROR: refusing unsafe target: {target}", file=sys.stderr)
        return 2
    try:
        market = _load_marketplace(marketplace)
        plugin_backup = _copy_plugin(source, target, dry_run=args.dry_run)
        market_backup = _write_marketplace(marketplace, market, dry_run=args.dry_run)
        if args.with_health_mcp:
            _install_health_mcp(target if not args.dry_run else source, dry_run=args.dry_run)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("Codex Brain Starter install complete." if not args.dry_run else "Dry run complete; no files changed.")
    if plugin_backup:
        print(f"Previous plugin preserved at: {plugin_backup}")
    if market_backup:
        print(f"Marketplace backup: {market_backup}")
    if not args.dry_run:
        print("Restart Codex, enable Codex Brain Starter, review /hooks, then invoke $setup-brain.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
