#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  Vaani — Full DB Setup + Git Fix
#  Run this ONCE from your Mac Terminal inside ~/code/25/vaani/
#
#  What it does:
#    1. Fixes the git staging mess (stale index.lock + wrongly staged files)
#    2. Creates all 12 collections with JSON Schema validators
#    3. Creates ~50 indexes
#    4. Seeds capability_taxonomy (25 docs)
#    5. Seeds profession_taxonomy (22 docs)
#    6. Seeds speakers (102 docs)
#    7. Verifies everything in DB
#    8. Commits + pushes to origin
# ─────────────────────────────────────────────────────────────────────────────
set -e
cd "$(dirname "$0")"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }
err()  { echo -e "${RED}✗${NC} $*"; }

echo ""
echo "══════════════════════════════════════════════"
echo "  Vaani DB Setup"
echo "══════════════════════════════════════════════"
echo ""

# ── 1. Preflight ─────────────────────────────────────────────────────────────
echo "▶ Preflight checks…"

if ! command -v node &>/dev/null; then
  err "node not found. Install Node.js >= 18 first."; exit 1
fi
if ! command -v python3 &>/dev/null; then
  err "python3 not found."; exit 1
fi

NODE_VER=$(node -e "console.log(process.version.slice(1).split('.')[0])")
if [ "$NODE_VER" -lt 18 ]; then
  err "Node.js >= 18 required (found v$NODE_VER)"; exit 1
fi

# Ping MongoDB
PING=$(mongosh "mongodb://vaani_admin:vaani_secret@localhost:27017/public_speaking_intelligence?authSource=admin" --quiet --eval "db.runCommand({ping:1}).ok" 2>/dev/null || echo "0")
if [ "$PING" != "1" ]; then
  err "MongoDB not reachable at localhost:27017"
  warn "Is docker-compose running? Try: docker-compose up -d"
  exit 1
fi
ok "MongoDB is up"

# ── 2. Fix git index.lock if stale ───────────────────────────────────────────
echo ""
echo "▶ Fixing git state…"

if [ -f .git/index.lock ]; then
  warn "Removing stale .git/index.lock"
  rm -f .git/index.lock
fi

# Unstage everything that's wrongly staged (the deleted files + .env)
git restore --staged . 2>/dev/null || true
ok "Staging area cleaned"

# ── 3. npm install ───────────────────────────────────────────────────────────
echo ""
echo "▶ Installing Node dependencies…"
npm install --silent
ok "node_modules ready"

# ── 4. Python venv + deps ────────────────────────────────────────────────────
echo ""
echo "▶ Installing Python dependencies…"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install --quiet pymongo python-dotenv
ok "Python deps ready"

# ── 5. Create DB collections + validators ────────────────────────────────────
echo ""
echo "▶ Initialising database (creating collections + validators)…"
node scripts/node/db_init.js
ok "Collections created"

# ── 6. Create indexes ────────────────────────────────────────────────────────
echo ""
echo "▶ Creating indexes…"
node scripts/node/create_indexes.js
ok "Indexes created"

# ── 7. Seed taxonomies ───────────────────────────────────────────────────────
echo ""
echo "▶ Seeding capability_taxonomy + profession_taxonomy…"
.venv/bin/python3 scripts/python/seed_taxonomies.py
ok "Taxonomies seeded"

# ── 8. Seed speakers ─────────────────────────────────────────────────────────
echo ""
echo "▶ Seeding 102 speakers…"
.venv/bin/python3 scripts/python/seed_speakers.py
ok "Speakers seeded"

# ── 9. Verify ────────────────────────────────────────────────────────────────
echo ""
echo "▶ Running verification…"
node scripts/node/verify.js

# ── 10. Git commit + push ────────────────────────────────────────────────────
echo ""
echo "▶ Committing + pushing…"

git add PROGRESS.md docker-compose.yml docs/ package.json package-lock.json \
        pyproject.toml schemas/ scripts/ seed/ setup_db.sh 2>/dev/null || true
# Never add .env, logs/, or node_modules/

DIRTY=$(git diff --cached --name-only | wc -l | tr -d ' ')
if [ "$DIRTY" -gt 0 ]; then
  git commit -m "chore(setup): add setup_db.sh + fix staging area"
  ok "Committed"
else
  ok "Nothing new to commit"
fi

git push origin feat/vaani-db-foundation
ok "Pushed to origin"

echo ""
echo "══════════════════════════════════════════════"
echo -e "  ${GREEN}All done!${NC}"
echo "  Open MongoDB Compass → localhost:27017"
echo "  DB: public_speaking_intelligence"
echo "  Auth: vaani_admin / vaani_secret"
echo "  Auth DB: admin"
echo "══════════════════════════════════════════════"
echo ""
