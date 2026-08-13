#!/bin/bash
# run-insights.sh -- Generate weekly or monthly journal insight reports via Codex CLI
# Usage: ./run-insights.sh weekly   (Monday mornings via cron)
#        ./run-insights.sh monthly  (2nd of each month via cron)
#
# Auto-detects vault root from script location (⚙️ Meta/scripts/ -> 2 levels up).
# Override with VAULT_ROOT env var if needed.

PERIOD="${1:-weekly}"

# Auto-detect vault root from script location
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VAULT_DIR="${VAULT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
LOG_FILE="$SCRIPT_DIR/.insights-cron.log"

# Find the Codex CLI (path changes with version updates)
CODEX_BASE="$HOME/Library/Application Support/Codex/claude-code"
CODEX_BIN=$(find "$CODEX_BASE" -name "claude" -path "*/MacOS/claude" 2>/dev/null | sort -V | tail -1)

if [ -z "$CODEX_BIN" ]; then
  echo "$(date): ERROR -- Codex CLI not found in $CODEX_BASE" >> "$LOG_FILE"
  exit 1
fi

echo "$(date): Starting $PERIOD insights generation..." >> "$LOG_FILE"

cd "$VAULT_DIR" || exit 1

"$CODEX_BIN" --print \
  --model claude-sonnet-4-6 \
  --allowedTools "Read,Write,Edit,Glob,Grep,Bash" \
  --permission-mode acceptEdits \
  "Run the /insights skill for a $PERIOD report. Read the skill at ~/.agents/skills/insights/SKILL.md first, then follow its instructions exactly. Read all journal entries for the $PERIOD calendar period and generate the full report. Save it to the correct folder." \
  >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
echo "$(date): Finished $PERIOD insights (exit code: $EXIT_CODE)" >> "$LOG_FILE"
