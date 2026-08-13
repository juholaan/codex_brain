---
type: rule
purpose: Restore ~/.codex/hooks.json and hook scripts to a known-good state when a recent change breaks the session.
trigger: "hooks are broken" / "nothing is firing" / "rollback" / "revert the last change" / "restore settings"
---

# Rollback runbook

When a recent change to hooks, settings, or plugin config breaks the session, follow this order. Cheapest first, nuclear last.

## 0. Diagnose before reverting

1. `cat ~/.codex/hooks.json | python3 -m json.tool` — is it valid JSON?
2. `tail -20 ~/.codex/hooks/*.log` — any error entries?
3. `ls ~/.codex/hooks/sync.*.lock 2>/dev/null` — stuck sync lock?
4. If plugin-related: check plugin hooks JSON parses correctly

If settings.json is invalid, Codex ignores the entire hooks block silently. Fix JSON first.

## 1. Revert settings.json

Keep dated backups at `~/.codex/hooks.json.bak-*`. List newest first:

```bash
ls -t ~/.codex/hooks.json.bak-*
cp ~/.codex/hooks.json.bak-<newest-known-good> ~/.codex/hooks.json
python3 -m json.tool < ~/.codex/hooks.json >/dev/null && echo "JSON OK"
```

Name your backups before making risky changes:
```bash
cp ~/.codex/hooks.json ~/.codex/hooks.json.bak-$(date +%Y%m%d-%H%M%S)-pre-<change>
```

## 2. Revert a hook script

If a specific hook started behaving wrong:

```bash
mv ~/.codex/hooks/<script>.py ~/.codex/hooks/<script>.py.broken
cp ~/.codex/hooks/<script>.py.bak-<date> ~/.codex/hooks/<script>.py
```

Then verify the settings.json hook entry still points to the right path.

## 3. Clear stuck sync lock

If SessionStart/SessionEnd hangs on sync:

```bash
rm -rf ~/.codex/hooks/sync.*.lock
tail -5 ~/.codex/hooks/sync-*.log
```

## 4. Disable all custom hooks (nuclear)

Rename `~/.codex/hooks.json` → `settings.json.disabled`. Codex falls back to defaults. Good for isolating "is the problem in my hooks or in Codex itself?"

## 5. Plugin sandbox

Disable a plugin via `~/.codex/hooks.json` `enabledPlugins` block — set to `false` instead of `true`. Kills that plugin's hooks only, leaves yours.

## 6. Codex update rollback

If a Codex version update broke something, the binary handles its own downgrade:

```bash
claude --version
# Check the changelog: https://github.com/anthropics/claude-code/releases
```

For version-specific breakage, pin with `CLAUDE_CODE_VERSION=` env var or reinstall an older tag.

## After any rollback

1. Start a new session and verify hooks fire.
2. Document the failure mode — what broke, what fixed it.
3. If the root cause is a Codex bug, log it against `anthropics/claude-code` issues after grepping for duplicates.

## Never

- Never `rm -rf ~/.codex/` as a first move. State is recoverable; plugins re-download.
- Never edit settings.json with a hook still holding a lock — race condition.
- Never skip Step 0 diagnosis. Rolling back a working change wastes time.
