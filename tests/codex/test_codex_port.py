from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = load_module("codex_runtime", ROOT / "hooks" / "codex_runtime.py")
installer = load_module("install_codex_plugin", ROOT / "scripts" / "install_codex_plugin.py")


class HookRuntimeTests(unittest.TestCase):
    def test_apply_patch_is_adapted_per_file(self) -> None:
        payload = {
            "tool_name": "apply_patch",
            "tool_input": {
                "command": "*** Begin Patch\n*** Update File: .codex/config.toml\n+token = 'x'\n*** Add File: note.md\n+hello\n*** End Patch"
            },
        }
        adapted = runtime._payloads_for_profile(payload, "write")
        self.assertEqual([item["tool_input"]["file_path"] for item in adapted], [".codex/config.toml", "note.md"])
        self.assertTrue(all(item["tool_name"] == "Write" for item in adapted))

    def test_legacy_allow_is_neutral(self) -> None:
        decision, reason = runtime._decision_from({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            }
        })
        self.assertEqual((decision, reason), ("allow", ""))

    def test_secret_in_codex_mcp_command_is_denied(self) -> None:
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "codex mcp add demo --env TOKEN=ghp_abcdefghijklmnopqrstuvwxyz -- demo"},
            "cwd": str(ROOT),
        }
        completed = subprocess.run(
            [sys.executable, str(ROOT / "hooks" / "codex_runtime.py"), "PreToolUse", "shell"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        output = json.loads(completed.stdout)
        specific = output["hookSpecificOutput"]
        self.assertEqual(specific["permissionDecision"], "deny")
        self.assertIn("secret", specific["permissionDecisionReason"].lower())

    def test_secret_in_codex_config_patch_is_denied(self) -> None:
        payload = {
            "tool_name": "apply_patch",
            "tool_input": {
                "command": "*** Begin Patch\n*** Update File: .codex/config.toml\n+token = 'ghp_abcdefghijklmnopqrstuvwxyz'\n*** End Patch"
            },
            "cwd": str(ROOT),
        }
        completed = subprocess.run(
            [sys.executable, str(ROOT / "hooks" / "codex_runtime.py"), "PreToolUse", "write"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        output = json.loads(completed.stdout)
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("secret", output["hookSpecificOutput"]["permissionDecisionReason"].lower())

    def test_session_context_handler_emits_codex_payload(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "hooks" / "session-start-context.py")],
            input=json.dumps({"hook_event_name": "SessionStart", "cwd": str(ROOT)}),
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        output = json.loads(completed.stdout)
        specific = output["hookSpecificOutput"]
        self.assertEqual(specific["hookEventName"], "SessionStart")
        self.assertIn("AGENTS.md", specific["additionalContext"])

    def test_unknown_event_is_silent(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "hooks" / "codex_runtime.py"), "UnknownEvent"],
            input="{}",
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "")


class InstallerTests(unittest.TestCase):
    def test_installer_preserves_existing_marketplace_entries_and_backs_up(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            source = base / "source"
            (source / ".codex-plugin").mkdir(parents=True)
            (source / ".codex-plugin" / "plugin.json").write_text(
                json.dumps({"name": installer.PLUGIN_NAME}), encoding="utf-8"
            )
            (source / "payload.txt").write_text("v1", encoding="utf-8")
            target = base / "plugins" / installer.PLUGIN_NAME
            marketplace = base / ".agents" / "plugins" / "marketplace.json"
            marketplace.parent.mkdir(parents=True)
            marketplace.write_text(json.dumps({
                "name": "personal",
                "interface": {"displayName": "My Plugins"},
                "plugins": [{
                    "name": "existing",
                    "source": {"source": "local", "path": "./plugins/existing"},
                    "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                    "category": "Productivity",
                }],
            }), encoding="utf-8")

            args = ["--source", str(source), "--target", str(target), "--marketplace", str(marketplace)]
            self.assertEqual(installer.main(args), 0)
            value = json.loads(marketplace.read_text(encoding="utf-8"))
            self.assertEqual(value["interface"]["displayName"], "My Plugins")
            self.assertEqual([p["name"] for p in value["plugins"]], ["existing", installer.PLUGIN_NAME])
            self.assertEqual((target / "payload.txt").read_text(encoding="utf-8"), "v1")

            (source / "payload.txt").write_text("v2", encoding="utf-8")
            self.assertEqual(installer.main(args), 0)
            self.assertEqual((target / "payload.txt").read_text(encoding="utf-8"), "v2")
            self.assertEqual(len(list(marketplace.parent.glob("marketplace.json.bak-*"))), 2)
            self.assertTrue(any(target.parent.glob(f".{installer.PLUGIN_NAME}.backup-*")))

    def test_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            source = base / "source"
            (source / ".codex-plugin").mkdir(parents=True)
            (source / ".codex-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
            target = base / "plugins" / installer.PLUGIN_NAME
            marketplace = base / "marketplace.json"
            self.assertEqual(installer.main([
                "--source", str(source),
                "--target", str(target),
                "--marketplace", str(marketplace),
                "--dry-run",
            ]), 0)
            self.assertFalse(target.exists())
            self.assertFalse(marketplace.exists())


class DiagnoseTests(unittest.TestCase):
    def test_healthy_minimal_vault_has_no_red_findings(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            vault = Path(raw)
            (vault / "AGENTS.md").write_text("# Brain\n\n## Vault Map\n- Home\n", encoding="utf-8")
            (vault / "⚙️ Meta" / "scripts").mkdir(parents=True)
            (vault / "⚙️ Meta" / "rules").mkdir(parents=True)
            completed = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "diagnose_codex.py"), str(vault), "--json"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertIn(completed.returncode, (0, 1), completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertNotIn("red", {row["status"] for row in payload["findings"]})

    def test_missing_agents_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            completed = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "diagnose_codex.py"), raw, "--json"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 2)
            payload = json.loads(completed.stdout)
            agents = [row for row in payload["findings"] if row["check"] == "AGENTS.md"]
            self.assertEqual(agents[0]["status"], "red")


if __name__ == "__main__":
    unittest.main()
