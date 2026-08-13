#!/usr/bin/env python3
"""PreToolUse Write/Edit hook: block writes to MCP config files when the new
content contains a secret in an `env` block.

Closes the gap from block-codex-mcp-inline-secret.py, which only catches
`codex mcp add` Bash commands. The 2026-05-19 + 2026-05-23 GitHub PAT leaks
were both regressions where a token got back into ~/.codex.json's
mcpServers.<name>.env.<KEY> via direct file edit (not via `codex mcp add`).

Triggers on Write or Edit when path matches:
  - ~/.codex/config.toml
  - **/.codex/config.toml
  - plugin .mcp.json files

AND the would-be-written content contains a secret pattern.

Bypass: MCP_CONFIG_SECRET_BYPASS=1.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

SECRET_PATTERNS = [
    r"sk-ant-[A-Za-z0-9_\-]+",
    r"sk-[A-Za-z0-9_\-]{20,}",
    r"github_pat_[A-Za-z0-9_]+",
    r"ghp_[A-Za-z0-9]+",
    r"ghs_[A-Za-z0-9]+",
    r"gho_[A-Za-z0-9]+",
    r"pat-[a-z0-9_\-]+",
    r"xoxb-[0-9A-Za-z\-]+",
    r"xoxp-[0-9A-Za-z\-]+",
    r"xoxc-[0-9A-Za-z\-]+",
    r"glpat-[A-Za-z0-9_\-]+",
    r"Bearer\s+[A-Za-z0-9_\-\.]+",
    r"AKIA[0-9A-Z]{16}",
    r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+",  # JWT
]

SECRET_RE = re.compile("|".join(SECRET_PATTERNS))

MCP_CONFIG_BASENAMES = {".mcp.json", "config.toml"}


def _is_mcp_config_path(path_str: str) -> bool:
    """True if the path is a Codex/MCP config file we want to guard."""
    p = Path(path_str)
    name = p.name
    if name not in MCP_CONFIG_BASENAMES:
        return False
    if name == "config.toml":
        return ".codex" in p.parts
    return name == ".mcp.json"


def _content_has_inline_secret(content: str) -> tuple[bool, str | None]:
    """Quick scan: secret-pattern match anywhere in content. Returns (hit, pattern)."""
    m = SECRET_RE.search(content)
    if not m:
        return False, None
    return True, m.group(0)[:20] + "..."  # truncated for the error message


def main() -> int:
    if os.environ.get("MCP_CONFIG_SECRET_BYPASS") == "1":
        return 0

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    tool = payload.get("tool_name") or payload.get("tool", "")
    if tool not in ("Write", "Edit", "MultiEdit"):
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if not file_path or not _is_mcp_config_path(file_path):
        return 0

    # Pull the would-be-written content depending on the tool
    if tool == "Write":
        content = tool_input.get("content") or ""
    elif tool == "Edit":
        content = tool_input.get("new_string") or ""
    elif tool == "MultiEdit":
        edits = tool_input.get("edits") or []
        content = "\n".join((e.get("new_string") or "") for e in edits)
    else:
        return 0

    hit, snippet = _content_has_inline_secret(content)
    if not hit:
        return 0

    print(
        f"BLOCK: would-be-written content for {file_path} contains a secret "
        f"pattern ({snippet}) in an MCP config file.\n\n"
        f"Pattern this prevents: inlining a secret into mcpServers.<name>.env "
        f"causes every Codex child spawn to bake the secret into a "
        f"--mcp-config argv string. Past incidents: 2026-05-19 + 2026-05-23 "
        f"github PAT leaks via this exact path.\n\n"
        f"Correct pattern: put the value in a protected environment variable "
        f"or operating-system credential store and reference only the variable "
        f"name from Codex configuration.\n\n"
        f"Bypass: MCP_CONFIG_SECRET_BYPASS=1",
        file=sys.stderr,
    )
    return 2  # exit-2 is a blocking hook error in Codex


if __name__ == "__main__":
    sys.exit(main())
