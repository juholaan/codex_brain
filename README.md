# Codex Brain Starter

A Codex-native port of
[Mycelium AI's AI Brain Starter](https://github.com/mycelium-hq/ai-brain-starter):
an interactive system for building and operating an Obsidian second brain.

## Upstream credit

This project is derived from
[mycelium-hq/ai-brain-starter](https://github.com/mycelium-hq/ai-brain-starter)
by **Mycelium AI**. It retains the upstream project's MIT license and preserves
the original README, setup skill, tests, and GitHub automation under
[`docs/upstream/`](docs/upstream/) for attribution and comparison. Codex Brain
Starter adapts the active plugin, skills, hooks, installer, and CI surfaces for
Codex; it is not an official Mycelium AI release.

This distribution keeps the upstream journaling, meeting, insight, knowledge
graph, health, and team workflows while replacing the active Codex surfaces
with Codex equivalents:

- `AGENTS.md` for durable vault and repository guidance
- plugin skills under `skills/`, invoked as `$setup-brain`, `$daily-journal`,
  `$insights`, `$graphify`, and the other bundled skills
- `.codex-plugin/plugin.json` for Codex and ChatGPT plugin packaging
- lifecycle hooks using Codex event payloads and `PLUGIN_ROOT`
- optional bundled Health MCP configuration
- a non-destructive personal-marketplace installer

The original repository's README and setup skill are preserved under
`docs/upstream/` for attribution and comparison.

## Install

Unzip or clone this repository, then run the wrapper for your platform from
the repository root.

macOS or Linux:

```bash
bash bootstrap.sh
```

Windows PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\bootstrap.ps1
```

The installer copies the plugin to `~/plugins/codex-brain-starter` and merges
one entry into `~/.agents/plugins/marketplace.json`. Existing marketplace
entries are preserved and the previous file is backed up before a change.

Preview the install without writing anything:

```bash
python scripts/install_codex_plugin.py --dry-run
```

After installation:

1. Restart the ChatGPT desktop app or Codex host.
2. Open the Plugins Directory, select the personal marketplace, and enable
   **Codex Brain Starter**.
3. Run `/hooks`, review the bundled commands, and trust them only if the paths
   and behavior match this repository.
4. Start with: `Use $setup-brain to set up my Obsidian second brain.`

Codex does not automatically trust plugin hooks. Declining them leaves the
skills usable; only the automatic context and guard behavior is disabled.

## Optional Health MCP

The plugin declares the Health MCP server but leaves it disabled until its
Python dependencies and command are installed:

```bash
python scripts/install_codex_plugin.py --with-health-mcp
```

Then enable the `health` server in Codex's plugin settings. Health data remains
local unless you separately configure an external provider. Review every MCP
server before enabling it because MCP tools can read or modify external data.

## Architecture

```text
Codex / ChatGPT host
  └─ codex-brain-starter plugin
      ├─ skills/                 conversational workflows
      ├─ phases/                 progressive setup phases
      ├─ templates/              generated vault files and rules
      ├─ hooks/hooks.json        Codex lifecycle declarations
      ├─ hooks/codex_runtime.py  compatibility and safety adapter
      ├─ scripts/                deterministic setup and maintenance tools
      └─ services/health-mcp/    optional local MCP server
```

The setup skill reads one phase at a time. Hooks are fail-open for internal
errors but preserve explicit security denials. Neutral PreToolUse results emit
no approval decision, so normal Codex permission policy still applies.

## Validate

```bash
python scripts/verify_codex_port.py
python -m unittest discover -s tests/codex -p "test_*.py"
```

See `docs/CODEX_PORT.md` for the conversion map and known compatibility
boundaries. This port is derived from upstream under the MIT license; see
`LICENSE`.

## GitHub automation

The active workflows under `.github/workflows/` verify the Codex package on
Linux and Windows and publish versioned source archives for `v*` tags. The
original Claude-oriented repository automation is preserved under
`docs/upstream/github/` for reference and is not executed by this port.
