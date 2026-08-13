# Codex Brain Starter — Repository Instructions

This is the Codex-native distribution of Mycelium AI's `ai-brain-starter`.
It is a public template used by people with unrelated vaults and identities.

## Public-repository safety

- Never add real names, private vault paths, live credentials, meeting content,
  company context, or personal anecdotes to reusable files.
- Use fictional examples or explicit placeholders.
- Never put secrets in `.codex/config.toml`, `.codex/config.toml`, hook commands, tests,
  or documentation. Refer to environment-variable names instead.
- Preserve attribution in `LICENSE`, `docs/CHANGELOG.md`, and the archived
  upstream documents.

## Native Codex surfaces

- `.codex-plugin/plugin.json` is the plugin manifest.
- `skills/<name>/SKILL.md` contains plugin skills. Keep frontmatter limited to
  `name` and `description`; put UI metadata in `agents/openai.yaml`.
- `skills/setup-brain/SKILL.md` is the progressive-disclosure setup router.
  It must point to the phase files rather than embedding them.
- `hooks/hooks.json` is the trusted-hook declaration.
- `hooks/codex_runtime.py` is the only command invoked directly by Codex hooks.
  It may delegate to existing Python guards, but a neutral result must never
  auto-approve a tool call.
- `.codex/config.toml` declares bundled MCP servers. Keep optional servers disabled
  until their executable dependencies are installed.
- User vault instructions belong in `AGENTS.md`, never `AGENTS.md`.
- User-installed standalone skills belong under `~/.agents/skills`.
- Codex state and hook configuration belong under `~/.codex`.

## Editing rules

- Inspect the existing phase, template, skill, or hook before creating a new
  one. Extend the modular structure instead of duplicating it.
- Keep `skills/setup-brain/SKILL.md` below 500 lines and load phase files only
  when their phase begins.
- On Windows, keep `.ps1` files UTF-8 with BOM.
- In large Obsidian vaults, never run unscoped `git add -A`, `git add .`, or
  unscoped `git status`; use explicit paths.
- Do not delete or overwrite a user's vault file during setup. Back up before
  migration and add missing sections instead of replacing personal content.

## Verification

Run these from the repository root after changing native surfaces:

```powershell
python scripts/verify_codex_port.py
python -m unittest discover -s tests/codex -p "test_*.py"
```

Also validate the plugin with the current Codex plugin validator before
shipping. Treat passing tests as evidence only for the behavior they cover.
