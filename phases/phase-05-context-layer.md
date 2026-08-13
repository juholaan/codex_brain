## Phase 5: Build the Context Layer

"Now I'm creating three small notes that let me orient myself in 10 seconds every session."

> **Platform note — read before running any shell command in this phase.** The
> file and folder operations below are written as Mac/Linux bash (`cp`, `mkdir -p`,
> `chmod`). **On Windows those error** — `cp`/`chmod` don't exist and `mkdir -p`
> isn't valid — and the vault silently ends up missing `⚙️ Meta/scripts`,
> `⚙️ Meta/Sessions`, `⚙️ Meta/Decisions`, and the hook scripts. So on Windows,
> perform the SAME operations with your native file tools instead: create each
> folder, and write/copy each file, directly (no bash). The `.sh` scripts are
> still written to disk — they run under Git Bash/WSL if present — and `chmod +x`
> is a Mac/Linux-only no-op you skip on Windows. The end state must be identical
> on every OS: the folders exist and every file is in place. Verify with a
> directory listing before moving on.

Create these files in the Meta/ folder:

**00 Start Here.md:**
```markdown
---
creationDate: [today]
type: meta
---
# Start Here

Read these in order at the start of every session:
1. [[AGENTS]] — who I am, how to behave
2. [[Current Priorities]] — what matters right now
3. [[Open Loops]] — what's unresolved
4. [[Last Session]] — what happened last time
```

**Current Priorities.md** — Ask them: "What are your top 5 priorities right now? Across work, life, everything." Build the note from their answer with headlines and bullet points.

**Open Loops.md** — Ask them: "What are you waiting on from other people? What do you need to do but haven't? What decisions are you sitting on?" Organize into three sections: Waiting On Others, Needs Action, Decisions Pending.

**⚙️ Meta/topic-map.json** — Copy `templates/topic-map.json` from this repo to `⚙️ Meta/topic-map.json` in their vault, then personalize it with them.

This file is what makes the vault-context hook routes *their* important files (not just generic examples) into context when they ask about the topics that matter to them. Without it, the hook only injects Current Priorities and Open Loops.

Ask them: "When you ask Codex about certain topics, which vault files should auto-load? For example, when you say 'raise' or 'investor,' we can pull your raise dashboard. When you say 'client' or 'pipeline,' we can pull your sales tracker."

For each of their top 4-6 focus areas, capture:
- A short name (e.g. `fundraising`, `writing`, `sales-pipeline`)
- 4-8 trigger keywords they'd actually type
- The 1-3 vault files that matter most for that topic

Replace the example entries in `topic-map.json` with their answers. Remove anything they don't need. If they want to redefine what counts as a "strategic" question, edit the `_signals` array at the top — otherwise leave the defaults.

**Last Session.md:**
```markdown
---
creationDate: [today]
type: meta
---
# Last Session

## [today's date] — Initial Setup
- Created vault structure
- Built AGENTS.md
- Set up context layer
- [add what else was done]

## Still Pending
- [anything not finished]
```

### Create a portable agent-memory area

Create `⚙️ Meta/Agent Memory/` inside the vault and add it to the Vault Map in
the root `AGENTS.md`. Instruct Codex to write durable user-approved discoveries
there as ordinary Markdown notes. Do not symlink or migrate hidden Codex
application state: its format and lifecycle are host-owned and may change.

Tell the user plainly: "Done — durable brain memories will live as readable
notes in `⚙️ Meta/Agent Memory/`, so they stay visible in Obsidian and travel
with your vault. Codex's own app state remains separate."

### Verify the plugin SessionStart context

The plugin already bundles a native `SessionStart` hook through
`hooks/hooks.json`. It loads the session protocol and reminds Codex to read the
vault's `AGENTS.md`, `⚙️ Meta/Last Session.md`, and
`⚙️ Meta/Current Priorities.md`. Do not duplicate it in the vault.

Confirm the user reviewed the plugin hook in `/hooks`. If they declined it,
leave trust unchanged and explain that the same behavior still exists as
instructions in the vault's `AGENTS.md`, but automatic context injection is
off.

The plugin also bundles prompt routing, frontmatter validation, note-secret
guards, MCP-secret guards, and session-close detection. All commands flow
through `hooks/codex_runtime.py`; they are not copied into `~/.codex/hooks`.
Run the port verifier if any handler appears missing:

```bash
python3 ~/plugins/codex-brain-starter/scripts/verify_codex_port.py
```

Do not install an automatic `git pull` hook. Marketplace installs are copied
snapshots and may not have a Git checkout. Updates happen through the Plugins
Directory or by rerunning `scripts/install_codex_plugin.py` from a newer source.

### Optional vault-specific guards

The general plugin guards work without knowing the vault path. Add a
project-scoped `.codex/hooks.json` only for behavior that genuinely needs this
vault's concrete path, such as the session-end and post-write scripts below.
Codex loads project hooks only in trusted projects, and the user must review
them in `/hooks`.

For large Git-backed vaults, the repository also contains optional
`block-raw-vault-git.py` and `block-vault-git-fullwalk.py` guards. Read each
file before opting in, wire it from the project hook file with an absolute path,
and set `VAULT_ROOT`. Never install these guards silently because they change
which Git commands Codex may run.

Tell the user: "Done. The plugin now loads your session protocol automatically.
The vault-specific close and write hooks are next; Codex will show them for
review before trusting them."

Also create the **session-end-hook.sh** script. This script writes a per-worktree session stub (never to the shared `Last Session.md`) and then runs the aggregator. This design is race-safe against concurrent worktrees — see the "Why per-worktree writes" note below the script for the full explanation.

```bash
#!/bin/bash
# Save to: [VAULT_PATH]/⚙️ Meta/scripts/session-end-hook.sh
# chmod +x this file after creating it
#
# NO STUBS: Codex writes session files directly during session close
# (see ⚙️ Meta/rules/session-end-cascade.md Phase 2). This hook only:
#   1. Appends a timestamp to Session Log
#   2. Cleans up: deletes stubs >7d old, archives substantive files >7d old
#   3. Runs the aggregator to refresh Last Session.md
#   4. Emits the session-close prompt for Codex
#
# PER-WORKTREE META WRITES: each session gets its own file in
# ⚙️ Meta/Sessions/ named by timestamp + worktree. The aggregator
# rebuilds Last Session.md deterministically — concurrent runs are safe
# (same sorted input → same bytes). See issue #5.
#
# Prior versions wrote a "stub" file every hook invocation, expecting
# Codex to fill it in. In practice most sessions end without running
# the full protocol, and stubs piled up (one user had 966 of 1,046
# files as empty stubs). This version trusts Codex to write the real
# file during session close and never creates stubs.

VAULT="[VAULT_PATH]"
META_DIR="$VAULT/⚙️ Meta"
SESSIONS_DIR="$META_DIR/Sessions"
ARCHIVE_DIR="$SESSIONS_DIR/Archive"
SESSION_LOG="$META_DIR/Session Log.md"
ERROR_LOG="$META_DIR/hook-errors.log"
AGGREGATE_SESSIONS="$META_DIR/scripts/aggregate-sessions.py"
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M)
TIMESTAMP_FILE=$(date +%Y-%m-%dT%H-%M)

# Cutoff for retention (7 days back). BSD date (macOS) uses -v, GNU uses -d.
if date -v-7d +%Y-%m-%d >/dev/null 2>&1; then
  CUTOFF=$(date -v-7d +%Y-%m-%d)
else
  CUTOFF=$(date -d '7 days ago' +%Y-%m-%d)
fi

# GUARD: fail loudly, never silently. If the Meta dir doesn't exist, bubble an error
# into the Codex hook context so the user sees it. This honors the NEVER fail silently rule.
if [ ! -d "$META_DIR" ]; then
  MSG="session-end-hook: Meta directory not found at '$META_DIR'. Vault may use a different folder name than '⚙️ Meta' — update this script's META_DIR. No session context saved."
  mkdir -p "$VAULT" 2>/dev/null && echo "$DATE $TIME — $MSG" >> "$VAULT/hook-errors.log"
  echo "{\"continue\":true,\"stopReason\":\"session-end-error\",\"systemMessage\":\"HOOK ERROR: $MSG Tell the user immediately and help fix the path.\"}"
  exit 0
fi

# Derive worktree name. Try three methods in order:
#   1. pwd matches .../.codex/worktrees/{name}/... → use {name}
#   2. Read the .git file if we're inside a git worktree
#   3. Fall back to "main-$$" (PID) so two concurrent fallback sessions
#      never collide on the same filename
WORKTREE_NAME=""
PWD_PATH="$(pwd)"
case "$PWD_PATH" in
  *"/.codex/worktrees/"*)
    WORKTREE_NAME=$(echo "$PWD_PATH" | sed -n 's|.*/\.codex/worktrees/\([^/]*\).*|\1|p')
    ;;
esac
if [ -z "$WORKTREE_NAME" ] && [ -f "$PWD_PATH/.git" ]; then
  GITDIR=$(grep -o 'worktrees/[^ ]*' "$PWD_PATH/.git" 2>/dev/null | head -1)
  if [ -n "$GITDIR" ]; then
    WORKTREE_NAME=$(echo "$GITDIR" | sed 's|worktrees/||' | tr -d '[:space:]')
  fi
fi
[ -z "$WORKTREE_NAME" ] && WORKTREE_NAME="main-$$"

SESSION_FILE="$SESSIONS_DIR/${TIMESTAMP_FILE}-${WORKTREE_NAME}.md"

mkdir -p "$SESSIONS_DIR" 2>>"$ERROR_LOG"
mkdir -p "$ARCHIVE_DIR" 2>>"$ERROR_LOG"

# Step 1: Always write a timestamp entry to Session Log (guaranteed, no Codex involvement).
# Append-only, small writes are atomic on local filesystems so this is safe under concurrency.
if ! echo "- $DATE $TIME — session ended ($WORKTREE_NAME)" >> "$SESSION_LOG" 2>>"$ERROR_LOG"; then
  echo "{\"continue\":true,\"stopReason\":\"session-end-error\",\"systemMessage\":\"HOOK ERROR: Could not append to Session Log at '$SESSION_LOG'. Check '$ERROR_LOG' for details and tell the user.\"}"
  exit 0
fi

# Step 2: Retention cleanup — delete stubs >7d old, archive substantive >7d old.
# Runs every hook invocation but only touches files past the cutoff (fast + idempotent).
# Keeps the Sessions folder from growing unbounded while preserving the last week
# of context for /weekly reviews and the aggregator's Last Session.md rebuild.
for f in "$SESSIONS_DIR"/*.md; do
  [ -f "$f" ] || continue
  fname=$(basename "$f")
  fdate="${fname:0:10}"
  # Skip files that don't start with a date pattern
  [[ "$fdate" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || \
  [[ "$fdate" =~ ^[0-9]{8} ]] || continue
  # Normalize YYYYMMDD to YYYY-MM-DD for comparison
  if [[ "$fdate" =~ ^[0-9]{8}$ ]]; then
    fdate="${fdate:0:4}-${fdate:4:2}-${fdate:6:2}"
  fi
  # Skip if within retention window
  [[ "$fdate" > "$CUTOFF" || "$fdate" == "$CUTOFF" ]] && continue
  # Old file: delete if legacy stub, archive if substantive
  if grep -q 'session_label: "update pending"' "$f" 2>/dev/null; then
    rm "$f"
  else
    mv "$f" "$ARCHIVE_DIR/"
  fi
done

# Step 3: Run the aggregator to refresh Last Session.md from Sessions/.
# Deterministic output → safe even if another worktree's hook is running
# the same aggregator at the same moment (both write identical bytes).
if [ -f "$AGGREGATE_SESSIONS" ]; then
  VAULT_ROOT="$VAULT" python3 "$AGGREGATE_SESSIONS" >/dev/null 2>>"$ERROR_LOG" || true
fi

# Step 4: Ask Codex to run session close protocol and log any decisions.
cat <<EOF
{"continue":true,"stopReason":"session-end-cascade","systemMessage":"SESSION ENDING (${DATE} ${TIME}, worktree: ${WORKTREE_NAME}): Run session close protocol (⚙️ Meta/rules/session-end-cascade.md). Write session file to '${SESSION_FILE}' — do NOT write to Last Session.md directly (auto-generated by aggregate-sessions.py). VERBATIM RULE: for commitments made during this session, capture the EXACT words used. For any decisions, create per-decision files at '${META_DIR}/Decisions/${TIMESTAMP_FILE}-{slug}.md' with frontmatter (type: decision, worktree, decision_date). After writing, run: VAULT_ROOT='${VAULT}' python3 '${AGGREGATE_SESSIONS}' && VAULT_ROOT='${VAULT}' python3 '${META_DIR}/scripts/aggregate-decisions.py'. Also save any non-obvious technical discoveries as memory files (type: discovery)."}
EOF
```

**Why per-worktree writes (the failure mode this design prevents):** if a user runs multiple Codex sessions in parallel worktrees, and each session follows the session-end cascade rule to write to the shared `Last Session.md` and `Decision Log.md`, the writes will race. Each session reads the file, constructs a new version with its entry, writes it back. Last write wins. Earlier sessions' entries are silently clobbered. The per-worktree split eliminates the race: unique filenames in `Sessions/` and `Decisions/` prevent contention at the write layer, and the aggregator scripts produce deterministic output from sorted input — so even concurrent aggregator runs can clobber each other without data loss, because they write the same bytes. Reported and fixed at [mycelium-hq/ai-brain-starter#5](https://github.com/mycelium-hq/ai-brain-starter/issues/5).

**Companion scripts** (Phase 5 also installs these — see `scripts/aggregate-sessions.py` and `scripts/aggregate-decisions.py` in this repo):

```bash
# Copy the two aggregator scripts into the vault's Meta folder
cp ~/plugins/codex-brain-starter/scripts/aggregate-sessions.py "[VAULT_PATH]/⚙️ Meta/scripts/"
cp ~/plugins/codex-brain-starter/scripts/aggregate-decisions.py "[VAULT_PATH]/⚙️ Meta/scripts/"
chmod +x "[VAULT_PATH]/⚙️ Meta/scripts/aggregate-sessions.py" "[VAULT_PATH]/⚙️ Meta/scripts/aggregate-decisions.py"

# Create the source-of-truth folders
mkdir -p "[VAULT_PATH]/⚙️ Meta/Sessions" "[VAULT_PATH]/⚙️ Meta/Decisions"
```

Also create the **write-hook.sh** script that fires after every Write tool call. It auto-triggers meeting-todos extraction when a meeting note is saved:

```bash
#!/bin/bash
# Save to: [VAULT_PATH]/⚙️ Meta/scripts/write-hook.sh
# chmod +x this file after creating it

INPUT=$(cat)

# GUARD: if python3 is missing, fail loudly. Honors NEVER fail silently rule.
if ! command -v python3 >/dev/null 2>&1; then
  echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PostToolUse\",\"additionalContext\":\"HOOK ERROR: write-hook.sh needs python3 but it's not on PATH. Tell the user and help them install it.\"}}"
  exit 0
fi

FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    path = d.get('tool_input', {}).get('file_path', '')
    print(path)
except Exception as e:
    sys.stderr.write(f'write-hook.sh JSON parse error: {e}\n')
    print('')
")
PARSE_EXIT=$?

# If python parsing itself errored, surface it — don't pretend nothing happened
if [ $PARSE_EXIT -ne 0 ]; then
  echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PostToolUse\",\"additionalContext\":\"HOOK ERROR: write-hook.sh could not parse the tool input JSON. Check your Codex version and tell the user.\"}}"
  exit 0
fi

if echo "$FILE_PATH" | grep -qi "Meeting Notes/\|Meeting-Notes/"; then
  BASENAME=$(basename "$FILE_PATH" .md)
  echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PostToolUse\",\"additionalContext\":\"Meeting note saved: '$BASENAME'. Run $meeting-todos on this file now — extract action items, show the user a preview, and add confirmed tasks to the to-do file. Do this automatically without waiting to be asked.\"}}"
else
  echo "{}"
fi
```

Replace the Stop hook path in `.codex/hooks.json` to point to this script:
```json
"Stop": [{"hooks": [{"type": "command", "command": "bash '[VAULT_PATH]/⚙️ Meta/scripts/session-end-hook.sh'", "statusMessage": "Saving session context..."}]}]
```

And add the PostToolUse hook:
```json
"PostToolUse": [{"matcher": "Write", "hooks": [{"type": "command", "command": "bash '[VAULT_PATH]/⚙️ Meta/scripts/write-hook.sh'", "statusMessage": "Checking write triggers..."}]}]
```

After creating both scripts, run: `chmod +x "[VAULT_PATH]/⚙️ Meta/scripts/session-end-hook.sh" "[VAULT_PATH]/⚙️ Meta/scripts/write-hook.sh"`

**Note:** If the user was already set up with `originals-hook.sh`, migrate by copying its contents into `write-hook.sh` and updating the hook path in `.codex/hooks.json`.

### Context-Routing Hooks

Install everything below as written. These are the hooks that fire on every prompt to route the right graph context and panel voices into the conversation — the connective tissue that makes the vault feel like a second brain instead of a notes folder.

**graph-context-hook.sh (install if the user has graphify installed).**

If the vault uses `$graphify` to build a knowledge graph, install the **graph-context-hook.sh** companion. It's a `UserPromptSubmit` hook that fires on every prompt, regex-matches the prompt against routing keywords, and (on match) injects `additionalContext` pointing the assistant at the right `GRAPH_REPORT.md` with a freshness note. Silent passthrough on no match.

Why: telling Codex in AGENTS.md to "always read the graph first" works some of the time. Injecting a routing reminder AT the moment of the matching prompt — with the file's mtime so staleness is visible — is more reliable, especially in long sessions where the static reminder fires only once.

Copy `scripts/graph-context-hook.sh` from this repo into `[VAULT_PATH]/⚙️ Meta/scripts/`, then **edit the CONFIG block at the top of the file**: set `VAULT_ROOT`, set `PRIMARY_GRAPH` and `PRIMARY_PATTERN` (regex of keywords for the main graph), and either configure `SECONDARY_GRAPH`/`SECONDARY_PATTERN` for a sub-folder graph (e.g. a separate work/team graph) or set `SECONDARY_GRAPH=""` if you only have one. Test with:

```bash
echo '{"hook_event_name":"UserPromptSubmit","prompt":"<your test phrase>"}' | bash "[VAULT_PATH]/⚙️ Meta/scripts/graph-context-hook.sh"
```

A matching prompt should print a `hookSpecificOutput` JSON; a non-matching prompt should be silent. Register it as a project `UserPromptSubmit` hook in `.codex/hooks.json`; the plugin's SessionStart protocol remains separate.

**Design rule:** the hook does NOT pin specific god-node names in its message text. God-node names go stale every graphify run. The stable signal is the path + freshness date — let the model open the report to see the actual current top nodes. If you need a hand-curated snapshot, put it in AGENTS.md (with an "as of YYYY-MM-DD" tag), not in the hook.

The plugin-wide lifecycle definitions live in `hooks/hooks.json`. Vault-specific `Stop` and `PostToolUse` commands live in the vault's `.codex/hooks.json` because only that file can contain the resolved vault path. Review both with `/hooks` after an update.

**Hook performance note for large vaults (5,000+ files):** PostToolUse hooks fire on every tool call. In code repos this is fine. In large Obsidian vaults (5,000+ files), a PostToolUse hook that scans files or runs scripts can become overwhelming, firing hundreds of times in a session. If you notice slowdowns or excessive hook output, consider moving the hook logic to a cron-based approach (check every N minutes) instead of per-tool-call. The Write-matcher pattern above is scoped narrowly (only fires on Write, not Read/Grep/etc.) which keeps it manageable.

**Sync philosophy for auto-updates:** when auto-updating files (skills, scripts, templates), always back up the existing file before overwriting. Never skip an update because the user might have customized the file. The right pattern is: copy the existing file to `<name>.bak-YYYY-MM-DD-HHMM`, then overwrite with the new version. This way the update always lands AND local customizations are recoverable from the backup. Missing an update is invisible; a backup is always recoverable.

**Decision Log.md:**
```markdown
---
creationDate: [today]
type: meta
---
# Decision Log

| Date | Decision | Why | Outcome |
|------|----------|-----|---------|
| [today] | Set up AI-powered vault | Want a connected second brain | In progress |
```

**Vault Changelog.md:**
```markdown
---
creationDate: [today]
type: meta
---
# Vault Changelog

*Everything we've built, improved, or automated — in order. Check here before building something new.*

## [today's date] — Initial Setup
- Created vault structure with [X] folders
- Built AGENTS.md with personal context
- Set up context layer (priorities, open loops, session tracking)
- Installed session protocol hook
- **Impact:** AI orients itself in 10 seconds instead of 15 minutes
```

**Content Drafts.md** (for auto-capture of sharp insights during conversations):
```markdown
---
creationDate: [today]
type: meta
---
# Content Drafts

*Sharp insights, standalone observations, and ideas that surface during conversations. Batch-captured at end of sessions.*

## Ready to Use
```

**Idea Quarantine.md** (only create if the user has a business/project):
```markdown
---
creationDate: [today]
type: meta
---
# Idea Quarantine

*New ideas go here to cool off before getting attention. Main project first. Ideas are welcome — but they go in quarantine, not into action.*

## Ideas
```
