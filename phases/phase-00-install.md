# Phase 0 — Verify the Codex installation

This phase starts after the user has enabled the Codex Brain Starter plugin and
invoked `$setup-brain`. The plugin already contains every bundled skill. Do not
clone the repository again and do not copy skills into `~/.agents/skills`.

## 0.0 Explain approvals before tools run

Tell the user, in their language:

> I’m checking the local tools your brain uses. Codex may show a permission box
> before a command runs. Read the command and approve it if it matches what I
> described. The brain’s automatic hooks have a separate trust review in
> `/hooks`; enabling the plugin does not silently trust them.

When a missing dependency requires installing software, explain what will be
installed and why before requesting approval. Never put an API key or password
in a command, hook, `.mcp.json`, or `.codex/config.toml`.

## 0.1 Verify the plugin itself

Resolve the plugin root from `PLUGIN_ROOT` when available. Otherwise use the
directory containing this skill (`skills/setup-brain/../..`). Run:

```bash
python3 "$PLUGIN_ROOT/scripts/verify_codex_port.py"
```

On Windows use the available Python launcher and a native path. A failed check
is blocking: show the exact failing check and repair or reinstall the plugin
before continuing.

Confirm that the following are present:

- `.codex-plugin/plugin.json`
- `skills/setup-brain/SKILL.md`
- `hooks/hooks.json`
- `hooks/codex_runtime.py`
- `.mcp.json`

## 0.2 Check hook review state

Ask Codex to open `/hooks` if the host has not already shown the review. Explain
that these bundled commands all call one file, `hooks/codex_runtime.py`, using
`PLUGIN_ROOT`. The user may decline; setup continues, but automatic session
context, close detection, and write-time guards remain off until trusted.

Never edit Codex’s trust state behind the user’s back.

## 0.3 Check local prerequisites

Detect before asking or installing:

| Tool | Required now | Purpose |
|---|---:|---|
| Python 3.10+ | yes | hook runtime, indexes, graph scripts |
| Git | yes | backups, change tracking, optional updates |
| Obsidian | yes | the vault interface |
| Node.js | later, if selected | specific connector or media tools |
| `gh` | later, if selected | GitHub ingestion and issue workflows |
| `pipx` | only for Health MCP | isolated MCP installation |

Use `python3 --version` (or `py -3 --version` on Windows), `git --version`, and
platform-appropriate Obsidian detection. If Python or Git is missing, install it
with the platform package manager only after explaining the command. If
Obsidian is missing, offer the platform package-manager install and complete it
after approval. Do not ask the user to visit several download pages.

If a package manager is unavailable or requires an interactive administrator
password Codex cannot supply, give the user exactly one command to run in a
terminal, explain the expected password prompt, and resume when it succeeds.

## 0.4 Verify bundled skills

The plugin bundles the skills under `skills/`; they do not need a second
installation. Confirm at least these core skills are present:

- `$daily-journal`
- `$insights`
- `$meeting-todos`
- `$graphify`
- `$patterns`
- `$diagnose`
- `$setup-vault-types`
- `$health-setup`

Do not register legacy slash-command files. Codex discovers skills from the
enabled plugin and invokes them with `$skill-name`.

## 0.5 Optional MCP dependencies

The bundled `.mcp.json` declares `health` but leaves it disabled. Do not install
or enable it unless the user chooses health ingestion in Phase 12. At that
point run the installer with `--with-health-mcp`, review the executable and its
data paths, then let the user enable the server.

Email, calendar, Slack, CRM, Granola, and other external systems are configured
in Phase 11. Prefer supported Codex plugins or reviewed MCP servers. Never
invent a connector, silently enable external egress, or store a token inline.

## 0.6 Record progress and continue

Append the phase telemetry event and update
`~/.codex/.ai-brain-starter-progress.json` with phase `0`. Then continue directly
to Phase 1. Do not stop after saying the plugin is installed; installation is
only the entry point to the interview.
