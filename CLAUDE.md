# CLAUDE.md — Vaani Engineering Contract

This is the first file you read before writing any code. It is the authoritative contract for how development works in this repository. It evolves with the product — updating CLAUDE.md is a required part of every PR that introduces a new pattern, service, or workflow.

---

## The Vision

Vaani is building the world's largest public-speaking company. The product scope will grow into areas not yet conceived. The codebase today is a data foundation. It will gain a mobile app, a coaching AI, a real-time feedback engine, microservices, and more.

Because AI drives development here, the quality system must be self-enforcing. Every principle below is backed by an automated check that fails the build if violated. This ensures quality degrades only by deliberate human decision, never by accident.

---

## The Five Principles

These are immutable. Every design decision flows from them.

1. **Convention Over Configuration** — File placement and naming determine what CI runs. A new Python script in `scripts/python/` is automatically linted, tested, and measured. No manual workflow changes needed.

2. **Ratcheting Quality Bar** — Coverage and quality metrics only move forward. The baseline is committed in `quality-baseline.json`. CI fails if coverage drops. The baseline is only updated upward via `make coverage-update-baseline`.

3. **CLAUDE.md Is the Contract** — This file governs the codebase. Updating it when introducing new patterns is enforced by the `docs-freshness` CI job. If you add files to `scripts/`, `schemas/`, `services/`, `api/`, or `app/` without updating CLAUDE.md, the build fails.

4. **Tests Are the Feature** — A function without a test is incomplete code. Coverage gates enforce this. Never commit code without co-located tests. The pattern: write the test alongside the code, commit both, CI verifies both pass.

5. **The Pipeline Is Observable** — Coverage, dependency vulnerabilities, secret drift, and build times are tracked. The weekly security scan catches CVEs before they ship.

---

## Repository Architecture

```
vaani/
├── scripts/
│   ├── node/               # DB admin (Node.js 18+ ES modules)
│   │   ├── db_init.js      # Creates 12 collections with JSON Schema validators
│   │   ├── create_indexes.js  # ~50 indexes across all collections
│   │   └── verify.js       # Verification queries + health checks
│   ├── python/             # Data pipeline (Python 3.11+)
│   │   ├── seed_speakers.py
│   │   ├── seed_taxonomies.py
│   │   ├── ingest_wikidata.py
│   │   └── utils/
│   │       ├── slugify_utils.py
│   │       └── wikidata.py
│   └── ci/                 # CI quality scripts
│       ├── check_claude_md.py   # CLAUDE.md freshness gate
│       ├── ratchet_coverage.py  # Coverage ratchet check
│       └── update_baseline.py   # Raise the coverage floor
├── schemas/                # MongoDB JSON Schema validators (12 files)
├── seed/                   # Authoritative seed data (committed to git)
│   ├── speakers_100.json   # 102 verified speakers
│   ├── capability_taxonomy.json  # 25 capabilities
│   └── profession_taxonomy.json  # 22 professions
├── tests/
│   ├── unit/               # Fast, no Docker, <5s total
│   └── integration/        # Require running MongoDB (@pytest.mark.integration)
├── .github/
│   ├── workflows/
│   │   ├── ci.yml          # Every push: lint + syntax + JSON + unit tests + secrets
│   │   ├── integration.yml # PRs to main: Docker MongoDB + full seed + verify
│   │   └── security.yml    # Weekly: pip-audit + npm audit + secret scan
│   └── dependabot.yml      # Automated dependency updates
├── quality-baseline.json   # Committed coverage floor — only moves up
├── Makefile                # Universal developer interface
├── docker-compose.yml      # MongoDB 7.0 + mongo-express
├── pyproject.toml          # Python project config, pytest, coverage, ruff, black
└── package.json            # Node.js config + npm scripts
```

### The 12 MongoDB Collections

| Collection | Upsert key | Seeded from |
|---|---|---|
| `speakers` | `slug` (unique index) | `seed/speakers_100.json` |
| `candidate_speakers` | `external_ids.wikidata` (unique sparse) | `ingest_wikidata.py` |
| `capability_taxonomy` | `capability_id` (unique) | `seed/capability_taxonomy.json` |
| `profession_taxonomy` | `profession_id` (unique) | `seed/profession_taxonomy.json` |
| `speeches` | `speaker_id + title` | future pipeline |
| `transcripts` | `speech_id` (unique) | future pipeline |
| `sources` | `url` (unique) | future pipeline |
| `evidence_items` | `speaker_id + claim_type` | future pipeline |
| `speaker_scores` | `speaker_id + scoring_version` | future pipeline |
| `extraction_runs` | `run_type + started_at` | `ingest_wikidata.py` |
| `media_assets` | `speech_id + speaker_id` | future pipeline |
| `practice_drills` | `capability_id + difficulty` | future seed |

### Core Data Model Rules

1. Every document has `created_at` (set once on insert via `$setOnInsert`), `updated_at` (set on every upsert), and `schema_version` (string `"1.0"`).
2. All bulk writes use `upsert=True` with `$setOnInsert: {created_at: NOW}` — never overwrite creation timestamps.
3. All scripts call `sys.exit(1)` on fatal errors. No unhandled exceptions at the top level.
4. Score fields are always `float` in `[0.0, 1.0]`. Validate before writing.
5. Slugs match `^[a-z0-9-]+$`. Always generate with `make_slug()` from `scripts/python/utils/slugify_utils.py`.
6. Module-level pattern: `ROOT = Path(__file__).parents[N]`, `load_dotenv(ROOT / ".env")`, then env var reads with defaults.

---

## What Every CI Check Validates

| Job | Triggers | What it catches | Fix locally in |
|---|---|---|---|
| `python-lint` | Every push | `black` format violations, `ruff` rule violations | `make lint-fix` |
| `node-syntax` | Every push | JavaScript syntax errors in `scripts/node/*.js` | `node --check scripts/node/file.js` |
| `json-validate` | Every push | Malformed JSON in `schemas/` or `seed/`; duplicate slugs/IDs; seed count minimums | `python3 -c "import json; json.load(open('file.json'))"` |
| `unit-tests` | Every push | Test failures; coverage < 70% | `make test` |
| `secret-scan` | Every push | Credentials or API keys committed | Remove the secret, rotate it |
| `docs-freshness` | PRs only | New source files without CLAUDE.md update | Update this file |
| `integration-tests` | PRs to main | DB init/seed/verify cycle; idempotency; index enforcement | `make db-up && make db-setup && make test-integration` |
| `python-audit` | Weekly | Python CVEs | `pip-audit` locally |
| `node-audit` | Weekly | Node.js CVEs | `npm audit` locally |

---

## Development Workflow

```
1. git checkout -b feat/your-feature
2. Write tests first (or alongside), then implementation
3. make test         ← must be green before pushing
4. make lint         ← must be clean
5. git add <specific files>   ← never git add -A
6. git commit -m "feat(scope): description"
7. git push origin feat/your-feature
8. Open PR to main → CI runs automatically
9. All checks green → merge (no human review required)
```

Branch naming: `feat/`, `fix/`, `chore/`, `test/`, `ci/`, `docs/`

### Commit Conventions

Format: `type(scope): short description`

Types: `feat` `fix` `chore` `docs` `test` `refactor` `ci` `build` `perf`

Scopes (examples): `seed` `schema` `ingest` `db-init` `indexes` `verify` `tests` `ci` `deps`

Breaking changes: `feat(schema)!: rename field`

Examples:
```
feat(seed): add 10 speakers to speakers_100.json
fix(ingest): retry on Wikidata 503 with backoff
test(validation): cover capability strength_score edge cases
ci: add coverage ratchet to unit-tests job
chore(deps): bump pymongo to 4.8
```

---

## Writing Tests for New Code

### For a new Python data script

Create `tests/unit/test_<script_name>.py`. Rules:
- Import only the pure functions (validation, parsing, building docs). Do NOT call `main()`.
- Use the `db` fixture (mongomock) for any function that takes a PyMongo collection.
- Test: happy path, empty/zero input, at least one validation error path.
- Never `time.sleep()`. Never make real network calls — mock `requests`, `SPARQLWrapper`.

Pattern for a seeder:
```python
from seed_speakers import upsert_speakers, validate_record

def test_upsert_inserts_new(db, valid_speaker):
    ins, upd = upsert_speakers(db, [valid_speaker])
    assert ins == 1
    assert db.speakers.count_documents({}) == 1
```

### For a new schema file

Add tests to `tests/unit/test_schemas_json.py`:
- Assert the file parses as valid JSON.
- Assert `$jsonSchema` key exists.
- Assert the `required` list contains expected fields.
- Assert any enum fields contain expected values.

### For integration tests

Add `@pytest.mark.integration` to the test. Use `MONGO_URI` from environment. Never hardcode credentials. Place in `tests/integration/`.

### Coverage requirement

Unit tests must keep ≥70% line coverage on `scripts/python/`. Run `make test` to check. The baseline in `quality-baseline.json` sets the floor — coverage only moves up.

---

## How to Add New Code

### New Python script in `scripts/python/`

1. Follow the module-level pattern (ROOT, load_dotenv, env vars, SCHEMA_VERSION, NOW).
2. Separate pure logic functions from DB-touching functions from `main()`.
3. Add `try/except BulkWriteError` for bulk operations; `sys.exit(1)` on fatal errors.
4. Create `tests/unit/test_<name>.py` with ≥1 test per exported function.
5. Update this CLAUDE.md under "Repository Architecture" if it introduces a new pattern.

### New schema in `schemas/`

1. Create `schemas/<collection_name>.json` with `$jsonSchema` at root.
2. Add the collection to `COLLECTIONS` in `scripts/node/db_init.js`.
3. Add required indexes to `scripts/node/create_indexes.js`.
4. Add a count check to `scripts/node/verify.js`.
5. Add to `TestSchemaFiles` in `tests/unit/test_schemas_json.py`.
6. Update the "12 MongoDB Collections" table above.

### New seed data

**New speakers in `seed/speakers_100.json`:**
- Each speaker must pass `validate_record()` — run `make test` to verify.
- `slug` must be unique within the file and match `^[a-z0-9-]+$`.
- All scores in `[0.0, 1.0]`.
- Commit with: `feat(seed): add <n> speakers`

**New capabilities in `seed/capability_taxonomy.json`:**
- `capability_id` must be unique and match `^[a-z_]+$`.
- Run `make test` — `test_no_duplicate_capability_ids` catches duplication.

**New professions in `seed/profession_taxonomy.json`:**
- `profession_id` must be unique.

### New service layer (FastAPI, React Native, ML pipeline, Go microservice…)

Follow the **New Layer Protocol** (see below).

---

## New Layer Protocol

When adding any new technology or service, follow these steps **before writing any feature code**:

1. **Scaffold the directory** (`services/<name>/`, `api/`, `app/`, etc.) with a minimal structure.
2. **Create a reusable workflow** `.github/workflows/reusable-<language>.yml` covering: install, lint, format-check, test, coverage-gate.
3. **Wire it into `ci.yml`** with `uses: ./.github/workflows/reusable-<language>.yml`.
4. **Add Makefile targets** for the new layer's install/lint/test/run commands.
5. **Update this CLAUDE.md**: add the new directory to the architecture map, add its CI job to the "What Every CI Check Validates" table, add instructions to "How to Add New Code".
6. **Write at least one test** before any feature code. The coverage gate enforces no regression from day one.

This is the mechanism: new layers inherit the full quality system at scaffolding time, before features exist.

---

## Quality Baseline Management

`quality-baseline.json` stores the current coverage floor. It is committed to git.

**To see current coverage:**
```bash
make test   # prints coverage report with missing lines
```

**When coverage naturally improves** (you added tests), update the baseline:
```bash
make test                           # get new coverage.json
make coverage-update-baseline       # raises the floor
git add quality-baseline.json
git commit -m "chore: raise coverage baseline to X%"
```

**When CI fails with "coverage dropped":** add tests for the uncovered lines. Run `make test` to see exactly which lines are missing. Do not lower the baseline.

---

## Environment Setup (one-shot bootstrap)

```bash
# 1. Copy env (fill in values if using non-default credentials)
cp .env.example .env

# 2. Install all deps + git hooks
make install
make pre-commit-install

# 3. Start MongoDB
make db-up

# 4. Initialize + seed DB (first time only)
make db-setup

# 5. Verify everything works
make test
```

**Environment variables** (see `.env.example` for all):
- `MONGO_URI` — full connection string including auth
- `MONGO_DB` — database name (`public_speaking_intelligence`)
- `LOG_LEVEL` — `INFO` or `DEBUG`
- `WIKIDATA_REQUEST_DELAY_SECONDS` — rate limit delay (default `1.5`)

Never commit `.env`. It is blocked by pre-commit hooks.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: seed_speakers` | pytest can't find scripts/python | `pip install -e ".[dev]"` |
| `ModuleNotFoundError: mongomock` | dev deps not installed | `pip install -e ".[dev]"` |
| `black: reformatted X files` (CI fails) | Uncommitted formatting | `make format && git add -u && git commit --amend` |
| `ruff: X errors` | Lint violations | `make lint-fix` |
| `Coverage X% < 70%` | New code without tests | Run `make test` to see missing lines; add tests |
| `MongoDB connection refused` | Docker not running | `make db-up` |
| `BulkWriteError` in integration tests | Missing indexes | `make db-indexes` |
| `verify.js exits non-zero` | Collections not seeded | `make db-seed` |
| `docs-freshness fails` | New source files, CLAUDE.md not updated | Update CLAUDE.md then push |
| Slug validation error in tests | Slug contains uppercase/spaces/special chars | Use `make_slug()` to generate slugs |
