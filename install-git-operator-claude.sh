#!/usr/bin/env bash
# Installs git-operator rules into ~/.claude/CLAUDE.md (Claude Code global memory)
set -e

CLAUDE_DIR="$HOME/.claude"
CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"

mkdir -p "$CLAUDE_DIR"

# If file already has the git-operator section, skip
if grep -q "## Git Operator — Dual Identity" "$CLAUDE_MD" 2>/dev/null; then
  echo "✅ git-operator rules already present in $CLAUDE_MD — nothing to do."
  exit 0
fi

cat >> "$CLAUDE_MD" << 'EOF'

---

## Git Operator — Dual Identity (macOS)

Whenever doing any Git operation (push, commit, PR, remote setup), behave as an autonomous Git operator:

### Identities
- **Personal**: username `sagarpahwa`, SSH host `github.com-personal`, remote `git@github.com-personal:<owner>/<repo>.git`
- **Work/CARS24**: username `sagarpahwacars24`, SSH host `github.com`, remote `git@github.com:<owner>/<repo>.git`

Critical: `git@github.com` → sagarpahwacars24; `git@github.com-personal` → sagarpahwa. Personal repos FAIL if they use `github.com`.

### Pre-Push Workflow (run every time before first push)
1. `git remote -v && git branch --show-current && git status --short`
2. Parse owner from remote URL
3. If owner == sagarpahwa → use `github.com-personal`; if work/CARS24/Cloud24 → use `github.com`
4. If host is wrong: `git remote set-url origin git@<correct-host>:<owner>/<repo>.git`
5. Verify: `ssh -T git@github.com-personal || true` and `ssh -T git@github.com || true`
6. Push: no upstream → `git push -u origin <branch>`; else `git push`

### Default Branch + Feature Branch Rules
- Always check for a default branch first; if missing on remote, create and push `main` first
- Always work on a feature branch — never commit directly to default
- After pushing, always open a PR to the default branch with `gh pr create`

### Error Handling (retry once)
- "denied to sagarpahwacars24" on personal repo → switch to `github.com-personal` and retry
- "denied to sagarpahwa" on work repo → switch to `github.com` and retry
- Still failing → report exact root cause with command evidence

### Safety
- Never `git reset --hard`, force push, or `checkout --` without explicit request
- Preserve all user changes; prefer SSH remotes

### Completion Report
Always report: final origin URL, identity used, branch pushed, tracking status (`git branch -vv`), fix applied, PR URL.
EOF

echo "✅ git-operator rules installed to $CLAUDE_MD"
