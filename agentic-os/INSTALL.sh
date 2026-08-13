#!/usr/bin/env bash
#
# agentic-os/INSTALL.sh - drop the agentic-OS kernel + agents + contexts + rules +
# data scaffold into a target repo. One command, idempotent, no network.
#
#   bash agentic-os/INSTALL.sh [TARGET_DIR]      (default: current directory)
#
# Lands:
#   TARGET/AGENTS.md                       the kernel (orchestrator)        [*]
#   TARGET/.claude/agents/*.md             pinned specialist agents
#   TARGET/.claude/contexts/*.md           posture modes
#   TARGET/.claude/rules/<lang>/hooks.md   paths-scoped per-language rules
#   TARGET/.codex/hooks/*.py              the validator + paths-scoped hook
#   TARGET/data/                           durable project-memory scaffold
#
# [*] An existing TARGET/AGENTS.md is NOT overwritten; the kernel is written to
#     TARGET/CLAUDE.agentic-os.md for you to merge by hand.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TARGET="${1:-.}"
mkdir -p "$TARGET"
TARGET="$(cd "$TARGET" && pwd)"

echo "agentic-os: installing into $TARGET"

mkdir -p \
  "$TARGET/.claude/agents" \
  "$TARGET/.claude/contexts" \
  "$TARGET/.claude/rules" \
  "$TARGET/.codex/hooks" \
  "$TARGET/data"

# Kernel - never clobber an existing AGENTS.md.
if [ -e "$TARGET/AGENTS.md" ]; then
  cp "$SRC/kernel/AGENTS.md" "$TARGET/CLAUDE.agentic-os.md"
  echo "  note: TARGET/AGENTS.md exists - kernel written to CLAUDE.agentic-os.md (merge by hand)"
else
  cp "$SRC/kernel/AGENTS.md" "$TARGET/AGENTS.md"
  echo "  + AGENTS.md (kernel)"
fi

# Agents (pinned model + tool surface).
cp "$SRC"/agents/*.md "$TARGET/.claude/agents/"
echo "  + .claude/agents/"

# Contexts (posture modes).
cp "$SRC"/contexts/*.md "$TARGET/.claude/contexts/"
echo "  + .claude/contexts/"

# Rules (one dir per language; copy each lang's hooks.md).
for lang_dir in "$SRC"/rules/*/; do
  [ -d "$lang_dir" ] || continue
  lang="$(basename "$lang_dir")"
  mkdir -p "$TARGET/.claude/rules/$lang"
  cp "${lang_dir}hooks.md" "$TARGET/.claude/rules/$lang/hooks.md"
done
echo "  + .claude/rules/"

# Hooks - the validator + the paths-scoped-rules auto-apply hook.
cp "$SRC/bin/validate_agents.py" "$TARGET/.codex/hooks/validate_agents.py"
cp "$SRC/bin/paths_scoped_rules.py" "$TARGET/.codex/hooks/paths_scoped_rules.py"
chmod +x "$TARGET/.codex/hooks/validate_agents.py" "$TARGET/.codex/hooks/paths_scoped_rules.py"
echo "  + .codex/hooks/"

# Data scaffold (includes README.md + .gitkeep).
cp -R "$SRC"/data/. "$TARGET/data/"
echo "  + data/"

# Settings snippet to wire the paths-scoped-rules hook (PostToolUse on Write|Edit).
cat >"$TARGET/.claude/settings.agentic-os.json" <<'JSON'
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
          { "type": "command", "command": "python3 .codex/hooks/paths_scoped_rules.py" }
        ]
      }
    ]
  }
}
JSON
echo "  + .claude/settings.agentic-os.json"

cat <<'EOF'

agentic-os installed. Next:
  1. Merge .claude/settings.agentic-os.json into .claude/settings.json
     (wires paths_scoped_rules as a PostToolUse hook so rules auto-apply on edit).
  2. Validate the agent tool-surface boundary:
       python3 .codex/hooks/validate_agents.py .claude/agents
  3. Replace the placeholder mission line at the bottom of AGENTS.md with yours.
EOF
