# POC Implementation Progress Tracker

> **THIS IS THE RESUMABLE SOURCE OF TRUTH.** If a session is lost/corrupted, re-run
> the original prompt (below), then read this file top-to-bottom and continue from the
> **first task that is not `✅ DONE`**. Every `✅ DONE` task is committed to git — do not redo it.

---

## How to resume (read this first)

1. **Original prompt** (re-runnable verbatim):
   > `/Users/a35254/code/25/vaani/docs/plans/poc-universal-coaching-app-plan.md`
   > implement this plan make sure you keep track of progress in proper way so that even if
   > this session is corrupted, you can continue with exact same prompt to implement exact
   > same plan without redoing what's already done in last lost/broken session.

2. **Branch:** `feat/poc-coaching-app` (off `feat/vaani-db-foundation`). Run `git checkout feat/poc-coaching-app`.
3. **Check what's done:** `git log --oneline` + the Milestone Status table below. Each `✅ DONE`
   row names the commit(s) that completed it. Trust the table, but verify with `git log`.
4. **Continue:** start at the first `⬜ TODO` / `🔄 IN PROGRESS` task. Re-read its checklist.
5. **After finishing any task:** update its row here, commit code + this file together, then move on.

---

## Hard constraints (from the user — never violate)

- **DO NOT touch the real DB** `public_speaking_intelligence` (container `vaani_mongo`, port 27017).
- **DO NOT disturb the user's running CLI scripts / their `.venv` and `.venv311`.**
- POC uses an **isolated** Mongo: container `vaani_poc_mongo`, **port 27018**, DB
  `public_speaking_intelligence_mock`, separate docker volume `vaani_poc_mongo_data`.
- POC Python uses a **separate `.venv-poc`** (never `.venv` / `.venv311`).
- **Audio is never stored inside Mongo documents** — object storage only (local FS adapter by
  default at `.poc-storage/`, MinIO/S3 adapter pluggable via config).
- Target platforms: **Android + Web must work**; iOS is best-effort for the POC.

---

## Locked decisions (the "why", so future sessions don't relitigate)

| Decision | Choice | Why |
|---|---|---|
| Backend framework | **FastAPI** (Python 3.11) | Plan §5.2 specifies FastAPI; repo's whole quality system is Python; single-language API+worker = fastest POC. |
| AI/ML providers | **Interfaces + deterministic mock impls** | No cloud creds in env; must run + be testable today. Real STT/TTS/LLM swap in via `PROVIDER_*` env. |
| Object storage | **`ObjectStore` interface; LocalFS default**, MinIO/S3 pluggable | Avoids extra infra today; honors "no audio in Mongo"; production-swappable. |
| Async work | **In-process async + WebSocket progress** for POC; `JobRunner` abstraction | Real queue (Redis/Celery) pluggable later; keeps POC runnable with one process. |
| DB isolation | Separate container on **27018**, DB `public_speaking_intelligence_mock` | User hard constraint: never dirty the real DB. |
| Mode A "transcription" | Mock STT derives a realistic timestamped transcript from the known script, injecting a few deterministic "delivery errors" to coach on | Makes A/B coaching demonstrable end-to-end without real audio models. |
| Git | Branch `feat/poc-coaching-app`, frequent commits, push + PR | User chose "Commit + push + PR". Identity: `github.com-personal` / `sagarpahwa`. |

---

## Architecture (target for POC)

```
Expo app (web + Android)            services/api  (FastAPI)
  expo-router screens         ─────▶  POST /sessions, /utterances, /retry
  expo-audio (record/play)            GET  /sessions/{id}, /scripts
  expo-speech (read-aloud)            WS   /sessions/{id}/events  (progress)
  api client + feature flags          coaching pipeline orchestrator
                                         │
            ┌────────────────────────────┼─────────────────────────────┐
            ▼                            ▼                              ▼
   providers (mock)              MongoDB (mock DB :27018)        ObjectStore (LocalFS)
   STT · Align · Features ·      10 new collections              raw + ideal audio clips
   Score · Feedback · TTS
```

---

## Milestone Status

Status legend: `⬜ TODO` · `🔄 IN PROGRESS` · `✅ DONE` · `⏸ DEFERRED`

| # | Milestone | Status | Commit(s) | Verify with |
|---|-----------|--------|-----------|-------------|
| P0 | Isolated infra + branch + this tracker | ✅ DONE | `chore(poc): isolated infra + progress tracker` | `docker ps` shows vaani_poc_mongo:27018; `make poc-db-up` |
| P1 | FastAPI backend scaffold + CI + `.venv-poc` | ✅ DONE | `feat(poc-api): FastAPI backend scaffold + CI wiring` | `make poc-api-run` → GET /health 200; `make poc-api-test` |
| P2 | Data model: 10 collections + mock DB seed | ✅ DONE | `feat(poc-db): 10 collection schemas + mock DB init/seed` | `make poc-db-setup` → collections+seed present in mock DB |
| P3 | Domain: providers + Goal Signature + scoring + pipeline | 🔄 IN PROGRESS | — | `make poc-api-test` (unit) green |
| P4 | API endpoints + contract/integration tests | ⬜ TODO | — | `make poc-api-test-all` green |
| P5 | Expo app scaffold + CI + API client | ⬜ TODO | — | `make poc-app-web` serves; `make poc-app-test` |
| P6 | Screens: Mode A & B full coaching flows | ⬜ TODO | — | web E2E: record→feedback→A/B→retry |
| P7 | Reliability artifacts (SLO, rollback, telemetry, golden) | ⬜ TODO | — | docs present; golden regression test in CI |
| P8 | E2E verify (web) + Android compat + push + PR | ⬜ TODO | — | both modes pass on web; PR open |

---

## Detailed task checklists

### P0 — Isolated infra + branch + tracker  ✅
- [x] Create branch `feat/poc-coaching-app`
- [x] Write this progress tracker
- [x] Add pointer to this tracker at top of the plan file + update PLANS.md
- [x] `docker-compose.poc.yml` (vaani_poc_mongo:27018, own volume, no auth for POC simplicity) + optional MinIO (profile `storage`)
- [x] `.env.poc.example` (POC_MONGO_URI, POC_MONGO_DB, OBJECT_STORE, PROVIDER_* = mock)
- [x] `.gitignore`: `.venv-poc/` (via `.venv*/`), `.poc-storage/`, `.env.poc`, app build dirs
- [x] `Makefile`: `poc-db-up/down`, `poc-db-setup`, `poc-api-*`, `poc-app-*` targets
- [x] Bring up POC Mongo; confirmed `vaani_mongo`/real DB untouched (27018 vs 27017, both healthy)
- [x] Commit

### P1 — FastAPI backend scaffold  ✅
- [x] `services/api/` package: `app.py` (factory), `config.py` (pydantic-settings), `main.py` (uvicorn entry)
- [x] `GET /health` + `GET /` endpoints
- [x] `services/api/requirements.txt` (fastapi, uvicorn, pydantic-settings, pymongo, httpx, python-multipart, pytest, pytest-asyncio, pytest-cov, mongomock, ruff, black)
- [x] `.venv-poc` created; deps installed; app boots (`uvicorn`), `/health` returns 200
- [x] `services/api/tests/test_health.py` — 2 tests green (97.73% coverage, gate ≥70%)
- [x] New Layer Protocol: `.github/workflows/reusable-python-api.yml` + `reusable-node-app.yml` (placeholder) wired into `ci.yml`; Makefile `poc-*` targets; updated CLAUDE.md (architecture map + CI table + POC section); `.coveragerc` isolates backend coverage
- [x] Commit

### P2 — Data model + mock DB  ✅
- [x] **`services/api/db/schemas/` JSON** (NOT shared `schemas/`, for isolation) for all 10: users, learner_profiles, guided_scripts, practice_sessions, session_utterances, coaching_feedback, audio_corrections, progress_snapshots, model_eval_runs, release_health_events (each `$jsonSchema`, created_at/updated_at/schema_version; version fields on sessions+feedback)
- [x] `services/api/db/init_mock_db.py` — create collections + validators + 19 indexes in mock DB (idempotent); `assert_mock_target` guard refuses non-`_mock` DB / port 27017
- [x] `services/api/db/seed_data/{guided_scripts,users,learner_profiles}.json` (4 scripts across goal profiles + demo user/profile)
- [x] `services/api/db/seed_mock.py` — `update_one` upsert into mock DB (mongomock-portable)
- [x] Tests (25 total, 96.97% cov): schema JSON valid; init idempotent; seed upsert idempotent; isolation guard
- [x] Verified live: `make poc-db-setup` created 10 collections + validators on :27018; real DB (27017) confirmed untouched (still only its 12 collections, no `*_mock` DB)
- [x] Commit

### P3 — Domain logic  ⬜
- [ ] `services/api/domain/versions.py` — rubric/scoring/feature/prompt version constants
- [ ] `services/api/domain/goal_signature.py` — Goal Signature model + capability weighting
- [ ] `services/api/providers/base.py` — STTProvider, FeatureExtractor, Aligner, Scorer, FeedbackGenerator, TTSProvider, ObjectStore interfaces
- [ ] `services/api/providers/mock/*.py` — deterministic mock impls + LocalFS ObjectStore
- [ ] `services/api/domain/pipeline.py` — orchestrator (transcribe→align→features→score→feedback→A/B TTS) + retry delta rescoring
- [ ] Unit tests for every pure function (happy + empty + 1 error path)
- [ ] Commit

### P4 — API endpoints + tests  ⬜
- [ ] `services/api/models.py` — Pydantic req/resp (with version fields in outputs)
- [ ] Routes: `GET /scripts`, `POST /sessions`, `POST /sessions/{id}/utterances` (+process), `GET /sessions/{id}`, `POST /sessions/{id}/retry`, `GET /audio/{key}`, `WS /sessions/{id}/events`
- [ ] Wire pipeline + persistence (mock DB) + ObjectStore
- [ ] Contract tests (TestClient) + integration test (full pipeline) marked appropriately
- [ ] Coverage gate green
- [ ] Commit

### P5 — Expo app scaffold  ⬜
- [ ] `app/` Expo + Expo Router project (TS), runs on web
- [ ] API client (`app/src/api/client.ts`) + config (base URL from env) + feature-flag shell
- [ ] First component/logic test (jest-expo) green
- [ ] New Layer Protocol: `.github/workflows/reusable-node-app.yml` + wire into `ci.yml`; Makefile targets; **update CLAUDE.md**
- [ ] Commit

### P6 — Screens (Mode A & B)  ⬜
- [ ] Home / mode select
- [ ] Goal Signature form (objective, occasion, audience, style, language, duration)
- [ ] Mode A: script list → script display → record (expo-audio)
- [ ] Mode B: script + occasion + purpose intake → record
- [ ] Processing screen (WS progress)
- [ ] Feedback report: written feedback + read-aloud (expo-speech) + A/B correction cards (expo-audio play user vs ideal)
- [ ] Retry flow: re-record flagged line → rescore → delta display
- [ ] Component/logic tests + web smoke
- [ ] Commit(s)

### P7 — Reliability artifacts  ⬜
- [ ] `docs/reliability/slos.md` (SLO set + error budget policy)
- [ ] `docs/reliability/rollback-runbook.md` + progressive rollout + incident/on-call + privacy/retention
- [ ] Extend `quality-baseline.json` (or `quality-baseline.poc.json`) with latency/failure-rate/golden-score floors
- [ ] `services/api/telemetry.py` — telemetry event emitters (plan §11.1)
- [ ] `services/api/tests/golden/` dataset + model regression test; wire into CI
- [ ] Commit

### P8 — E2E verify + ship  ⬜
- [ ] Start mock Mongo + API + Expo web; walk Mode A E2E in browser (screenshots)
- [ ] Walk Mode B E2E in browser
- [ ] Android compatibility check (bundles for Android; cross-platform APIs only)
- [ ] Final tracker update; push branch; open PR (base `feat/vaani-db-foundation`)

---

## Run commands (filled in as targets are created)

```bash
# POC database (isolated, port 27018)
make poc-db-up           # start vaani_poc_mongo
make poc-db-setup        # init collections + indexes + seed (mock DB)
make poc-db-down

# Backend (FastAPI, .venv-poc)
make poc-api-install
make poc-api-run         # uvicorn on :8090
make poc-api-test

# Frontend (Expo)
make poc-app-install
make poc-app-web         # expo web
make poc-app-test
```

## Notes / open issues / decisions log
- 2026-05-31: Tracker created. Backend=FastAPI (see decisions table). Android emulator not
  available in this dev env per host capabilities, so Android verified by bundling + cross-platform
  API discipline; user to confirm on device. Web is fully verified here.
- 2026-05-31 (P2): **POC schemas live in `services/api/db/schemas/`, NOT the shared `schemas/`.**
  Why: the shared dir is wired into the data-foundation Node scripts (`db_init.js` COLLECTIONS) and
  the `json-validate`/`test_schemas_json.py` gates that run against the **real** DB. Keeping POC
  schemas separate guarantees the real DB can never accidentally get POC collections. The
  `assert_mock_target` guard in `init_mock_db.py` is the runtime backstop.
- 2026-05-31 (P2): seeder uses per-doc `update_one` (not `bulk_write`) — pymongo 4.17 passes a
  `sort` kwarg that this mongomock version rejects in bulk ops. `update_one` is portable across
  mock + real Mongo and fine for tiny seed sets.
