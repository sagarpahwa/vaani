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
├── services/               # POC backend layer (FastAPI) — see "POC" section below
│   └── api/                # Coaching API: app, config, db, domain, providers, routes, tests
├── app/                    # POC universal frontend (Expo + Expo Router; web + Android)
├── tests/
│   ├── unit/               # Fast, no Docker, <5s total
│   └── integration/        # Require running MongoDB (@pytest.mark.integration)
├── .github/
│   ├── workflows/
│   │   ├── ci.yml          # Every push: lint + syntax + JSON + unit tests + secrets + api + app
│   │   ├── reusable-python-api.yml  # Reusable: services/api lint + test + coverage gate
│   │   ├── reusable-node-app.yml    # Reusable: app/ (Expo) lint + test
│   │   ├── integration.yml # PRs to main: Docker MongoDB + full seed + verify
│   │   └── security.yml    # Weekly: pip-audit + npm audit + secret scan
│   └── dependabot.yml      # Automated dependency updates
├── quality-baseline.json   # Committed coverage floor — only moves up
├── Makefile                # Universal developer interface (incl. isolated `poc-*` targets)
├── docker-compose.yml      # MongoDB 7.0 + mongo-express (real DB, port 27017)
├── docker-compose.poc.yml  # Isolated POC stack: vaani_poc_mongo (27018) + optional MinIO
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
| `api-tests` | Every push | `services/api` ruff/black violations, FastAPI test failures, coverage < 70% | `make poc-api-lint && make poc-api-test` |
| `app-tests` | Every push | `app/` (Expo) lint/type/test failures | `make poc-app-test` |
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

## POC: Universal Coaching App (`services/api` + `app`)

The POC is a real public-speaking coach (Mode A: system-guided script; Mode B: user-provided
script). It is built on layers added via the New Layer Protocol above. **Implementation progress
is tracked in [`docs/plans/poc-implementation-progress.md`](docs/plans/poc-implementation-progress.md)
— that file is the resumable source of truth.**

### Hard isolation rules (never violate)

The POC must never disturb the data-foundation dev environment:

- **DB:** the POC uses an isolated MongoDB — `docker-compose.poc.yml` → container `vaani_poc_mongo`
  on **port 27018**, database `public_speaking_intelligence_mock`. The real DB
  (`public_speaking_intelligence`, `vaani_mongo`, port 27017) is never touched.
- **Python env:** the backend uses a separate **`.venv-poc`** (created by `make poc-api-install`),
  never `.venv` / `.venv311`.
- **Audio:** never stored in Mongo documents. Use the `ObjectStore` abstraction
  (LocalFS adapter by default at `.poc-storage/`; MinIO/S3 adapter pluggable via `OBJECT_STORE`).
- **Config:** `.env.poc` (copy from `.env.poc.example`). All POC settings are `POC_*` / `PROVIDER_*`.

### Backend (`services/api`, FastAPI)

```
services/api/
├── app.py            # create_app() factory
├── config.py         # pydantic-settings (reads .env.poc; mock defaults)
├── main.py           # uvicorn entry: services.api.main:app
├── db/               # mock-DB init + seed (targets public_speaking_intelligence_mock)
├── domain/           # pure logic: text, types, versions, goal_signature, pipeline
├── providers/        # base (ABCs), object_store, analysis (align/features/score),
│                     #   mock_ai (STT/TTS/feedback), registry (build_providers)
├── routes/           # API routers (sessions, scripts, utterances, retry, audio, ws)
├── models.py         # Pydantic request/response models (carry *_version fields)
├── requirements.txt  # installed into .venv-poc
└── tests/            # pytest (unit + @pytest.mark.integration), .coveragerc gate ≥70%
```

Rules:
1. AI is accessed only through `providers/` interfaces. Default impls are deterministic mocks so
   the app runs and tests pass with no cloud credentials. Real providers swap in via `PROVIDER_*`.
2. Every scored/feedback output carries version fields: `rubric_version`, `scoring_model_version`,
   `feature_extractor_version`, `prompt_version` (see `domain/versions.py`).
3. Separate pure logic (testable) from DB/IO. Co-locate tests in `services/api/tests`.
4. Run: `make poc-db-up && make poc-db-setup && make poc-api-run` → http://localhost:8090/docs.

### POC Data Model (10 collections, mock DB only)

POC schemas live in **`services/api/db/schemas/`** (deliberately NOT the shared `schemas/`), so the
data-foundation Node scripts (`scripts/node/*`) and the real DB can never pick them up.
`services/api/db/init_mock_db.py` creates them with `$jsonSchema` validators + indexes in the mock
DB; `services/api/db/seed_mock.py` seeds demo data from `services/api/db/seed_data/`. Both refuse to
run unless the target database name ends in `_mock` and the URI is not on port 27017
(`assert_mock_target` guard).

| Collection | Upsert key | Purpose |
|---|---|---|
| `users` | `user_id` | POC demo accounts |
| `learner_profiles` | `user_id` | per-user Goal Signature defaults + capability levels |
| `guided_scripts` | `script_id` | Mode A scripts (seeded from `seed_data/guided_scripts.json`) |
| `practice_sessions` | `session_id` | one coaching session (Mode A/B); carries the four `*_version` fields |
| `session_utterances` | `utterance_id` | per-utterance transcript + `audio_key` (object store, not raw audio) |
| `coaching_feedback` | `feedback_id` | generated feedback + read-aloud text + capability scores |
| `audio_corrections` | `correction_id` | A/B pairs: user vs ideal-voice `*_audio_key` |
| `progress_snapshots` | `snapshot_id` | per-user score history + deltas |
| `model_eval_runs` | `run_id` | golden-dataset regression results |
| `release_health_events` | `event_id` | telemetry / SLO events |

Every document carries `created_at` / `updated_at` / `schema_version` (same core data-model rules as
the data foundation).

### Frontend (`app`, Expo + Expo Router)

One universal codebase for **web + Android** (iOS best-effort for the POC). Audio capture/playback
via `expo-audio`; full-feedback read-aloud via `expo-speech`. API base URL from app config.
Run: `make poc-app-install && make poc-app-web`.

### Adding POC code

- New backend module in `services/api/`: keep pure logic separate, co-locate a test, keep
  `make poc-api-lint` + `make poc-api-test` green (coverage ≥70% via `services/api/.coveragerc`).
- New collection for the POC: add a `services/api/db/schemas/<name>.json` (NOT the shared
  `schemas/`), register it in `COLLECTION_SPECS` in `services/api/db/init_mock_db.py`, add it to
  the POC Data Model table above, and add a case to `services/api/tests/test_schemas_poc.py`.
- New screen in `app/`: co-locate a component/logic test; keep `make poc-app-test` green.

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
