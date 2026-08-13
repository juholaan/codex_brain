# Codex port map

## Active-surface mapping

| Upstream surface | Codex-native surface |
|---|---|
| `CLAUDE.md` | `AGENTS.md` |
| root `SKILL.md` / slash command | `skills/setup-brain/SKILL.md` / `$setup-brain` |
| `.claude-plugin/plugin.json` | `.codex-plugin/plugin.json` |
| `~/.claude/skills` | `~/.agents/skills` or bundled plugin skills |
| `.claude/settings.json` hooks | `hooks/hooks.json`, reviewed with `/hooks` |
| `.mcp.json` / Claude MCP config | plugin `.mcp.json` or `.codex/config.toml` |
| `claude --print` automation | `codex exec` automation |

## Hook compatibility

`hooks/codex_runtime.py` is the boundary between Codex and the upstream Python
guards. It:

- translates Codex `apply_patch` payloads into per-file write-shaped payloads;
- supplies both Codex and legacy plugin-root environment variables;
- combines context from multiple guards into one supported hook result;
- preserves explicit `deny` or exit-code-2 blocks;
- ignores legacy neutral `allow` output so it cannot bypass Codex approvals;
- drops unsupported `suppressOutput` fields;
- times out individual guards and fails open on internal errors.

Vault-generated shell hooks that require a concrete vault path are installed
during `$setup-brain`; they are not hardcoded in the distributable plugin.
Destructive worktree cleanup and automatic self-update hooks are intentionally
not enabled by default. Their scripts remain available for an administrator to
review and opt into.

## MCP compatibility

The local Health MCP is bundled as an optional server. The manifest expects the
`codex-brain-health-mcp` executable, installed by the bootstrap's
`--with-health-mcp` option. The server remains disabled until installation.
Other upstream integrations such as Granola, calendars, email, Slack, or CRM
are configured interactively during setup because authentication and connector
availability vary by user and workspace.

## Historical material

`docs/upstream/README.md`, `docs/upstream/SKILL.md`, and the narrative changelog
are retained as upstream records. They may mention Codex-specific behavior and
are not executable Codex instructions.
