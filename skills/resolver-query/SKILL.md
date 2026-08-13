---
name: "resolver-query"
description: "Use when an operator invokes $resolver-query with a question, asks which rule or policy governs pricing exceptions, deploys, refunds, or hiring, or wants to look up the matching rule in Meta/RESOLVER.md without reading the whole index by hand. Also trigger on 'which rule applies', 'what's our policy on X', or 'does a rule cover this'. Not for writing or editing rules (read-only) and not for rebuilding RESOLVER.md (use resolver-build.py)."
---

# $resolver-query

Look up which rule in `Meta/RESOLVER.md` applies to a natural-language question. The skill itself does NOT call an LLM. It reads RESOLVER.md, parses every rule row, and returns either a decisive match, a ranked candidate list, or "no rule matches." The host Codex session does the natural-language understanding on top of the structured output.

## When to run

- An operator wonders which rule governs a recurring question (pricing, deploy, refund, hiring exception).
- A new teammate wants to find the policy for a scenario without reading the full resolver index.
- Any time the resolver layer should answer a query and the operator wants the structured candidate set in one call.

## How it works

1. The skill reads `Meta/RESOLVER.md` from the vault root.
2. It parses the YAML frontmatter for the build timestamp and counts.
3. It parses every row of the `## Rules` table into a structured record.
4. It runs a deterministic match against the question:
   a. Tokenize the question (lowercase, drop stopwords, keep stems).
   b. For each rule, score by token overlap against `rule_id`, source path, skill link, and source-file H1/topic when available.
   c. If exactly one rule scores >= the decisive threshold, return that rule directly.
   d. Otherwise return up to `--limit` rules ranked by score.
   e. If no rule scores above zero, return `no rule matches this query`.
5. The host session then reads the structured output and frames the answer to the operator.

## Step 1: Run the skill

```bash
python3 skills/resolver-query/query.py "How do we handle pricing exceptions?" \
    --vault-root <vault>
```

Output is a JSON document on stdout with shape:

```json
{
  "question": "...",
  "vault_root": "...",
  "resolver_built_at": "...",
  "rule_count": 17,
  "match_kind": "decisive | ranked | none",
  "matched_rules": [
    {
      "rule_id": "...",
      "type": "decision | workflow | exception | fact",
      "status": "active | stale | superseded | under-review | unknown",
      "last_verified": "...",
      "source_path": "...",
      "skill_link": "...",
      "score": 0.0
    }
  ],
  "summary": "..."
}
```

## Step 2: Read the matched rule

If the match kind is `decisive`, the host session opens the rule's source file (`source_path`). If `ranked`, the host session presents the top candidates to the operator and lets them pick. If `none`, the host session tells the operator no rule applies and offers to draft one manually.

## Rules

- The skill is read-only. It NEVER writes to `RESOLVER.md` or any source file.
- The skill makes no external network calls. No LLM API is invoked from inside `query.py`.
- The matching algorithm is deterministic and stdlib-only. The host Codex session is the natural-language layer on top.
- When `match_kind == none`, the skill returns the empty `matched_rules` list and the host session tells the operator no rule matches; it does not invent one.

## Boundary

- Adjacent skills:
  - `scripts/resolver-build.py` rebuilds `RESOLVER.md`.
  - `scripts/resolver-conflict-report.py` surfaces conflicts in JSON.
  - `scripts/resolver-branch-merge-prompt.py` drafts merge prompts.
- This skill READS the rendered index. It does not refresh, edit, or rewrite it.
