---
name: "diagnose"
description: "Use when a Codex Brain vault needs a health check, Codex is not following AGENTS.md, journal insights are stale, hooks are not firing, MCP configuration may be malformed, Obsidian is unstable, or Windows scripts fail. Also use after a major $setup-brain update. This is a read-only vault-install audit, not a general code debugger."
---

# Diagnose a Codex Brain vault

Resolve this skill's plugin root as `{SKILL_DIR}/../..`. Run the read-only
diagnostic with the vault root:

```bash
python3 "{SKILL_DIR}/../../scripts/diagnose_codex.py" "/path/to/vault"
```

On Windows, invoke the available Python 3 launcher with the same script and
path. Use `--json` only when another tool needs structured output.

The script checks:

- plugin manifest, core skills, and native hook files;
- vault `AGENTS.md` and its Vault Map;
- `⚙️ Meta`, scripts, and rules folders;
- plugin and project hook JSON;
- journal-index validity and age;
- Python, Git, and optional vault Git history;
- UTF-8 BOM on vault PowerShell files;
- user/project Codex TOML configuration;
- common cloud-sync path risks.

Translate the result into plain language:

- Green: say the vault is healthy.
- Yellow: list the cleanup items and offer the exact safe fix.
- Red: name the broken invariant and propose a fix. Get confirmation before
  changing files or installing software.

Do not modify the vault, fetch the network, publish the report, or treat an
optional email, connector, MCP server, or Git repository as mandatory.
