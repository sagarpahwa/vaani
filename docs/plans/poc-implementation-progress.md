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
| P3 | Domain: providers + Goal Signature + scoring + pipeline | ✅ DONE | `feat(poc-domain): coaching pipeline + providers + Goal Signature` | `make poc-api-test` green (68 tests, 97.7% cov) |
| P4 | API endpoints + contract/integration tests | ✅ DONE | `feat(poc-api): coaching endpoints + contract/integration tests` (09ebbe0) | `make poc-api-test-all` green (99 tests, 97% cov) |
| P5 | Expo app scaffold + CI + API client | ✅ DONE | `feat(poc-app): Expo universal app scaffold + typed API client + CI` (56bed0d) | `make poc-app-test` green (22 tests + tsc + lint); web bundle exports |
| P6 | Screens: Mode A & B full coaching flows | 🔄 IN PROGRESS | — | web E2E: record→feedback→A/B→retry |
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

### P3 — Domain logic  ✅
- [x] `services/api/domain/text.py` — tokenize/normalize/`stable_seed` (md5, cross-run determinism)/`split_script_text` (Mode B line+sentence splitting)
- [x] `services/api/domain/versions.py` — rubric/scoring/feature/prompt version constants + `version_stamp()`
- [x] `services/api/domain/types.py` — dataclasses (Word, Transcript, AlignOp, UtteranceAnalysis, DeliveryFeatures, ScoreResult, Improvement, FeedbackResult, CorrectionDraft, PipelineResult.to_dict)
- [x] `services/api/domain/goal_signature.py` — `GoalSignature` (frozen) + `capability_weights` (6 canonical capabilities, keyword boosts normalized to mean 1.0)
- [x] `services/api/providers/base.py` — STTProvider, Aligner, FeatureExtractor, Scorer, FeedbackGenerator, TTSProvider, ObjectStore ABCs + FILLER_WORDS
- [x] `services/api/providers/object_store.py` — LocalFSObjectStore (path-traversal-safe) + InMemoryObjectStore
- [x] `services/api/providers/analysis.py` — SequenceAligner (Levenshtein DP), DeliveryFeatureExtractor, RubricScorer (transparent per-capability curves, goal-weighted overall)
- [x] `services/api/providers/mock_ai.py` — MockSTT (deterministic transcript w/ injected fillers/omissions/pauses), MockTTS (valid mono PCM WAV), MockFeedbackGenerator (templated improvements/strengths/A-B drafts)
- [x] `services/api/providers/registry.py` — `ProviderBundle` + `build_providers` (mock-only; ValueError on non-mock, NotImplementedError on minio)
- [x] `services/api/domain/pipeline.py` — `CoachingPipeline` (analyze→features→score→feedback→A/B TTS), `retry`, `compute_delta`
- [x] Unit tests (43 new; happy + empty + ≥1 error path each): test_text, test_goal_signature, test_analysis, test_mock_ai, test_object_store, test_registry, test_pipeline
- [x] `make poc-api-lint` clean, `make poc-api-test` green (68 tests, 97.7% cov)
- [x] Commit

### P4 — API endpoints + tests  ✅
- [x] `services/api/models.py` — Pydantic req/resp (with version fields in outputs)
- [x] Routes: `GET /scripts` (+`/scripts/{id}`), `POST /sessions`, `POST /sessions/{id}/utterances` (+process), `GET /sessions/{id}`, `POST /sessions/{id}/retry`, `GET /audio/{key}`, `WS /sessions/{id}/events`
- [x] Wire pipeline + persistence via thin `coaching_service.py` + lazy `app.state` DI (`deps.py`); `repository.py` helpers
- [x] Contract tests (TestClient, incl. WS) + integration test (`@pytest.mark.integration`, self-skips if :27018 down, cleans up its own docs)
- [x] Coverage gate green (97.17% unit / 97% with integration; gate ≥70%)
- [x] Commit (09ebbe0)

### P5 — Expo app scaffold  ✅
- [x] `app/` Expo SDK 56 + Expo Router project (TS, `src/` layout), bundles + exports on web (5 static routes)
- [x] API client (`app/src/api/client.ts`, typed, `ApiError` carries status+detail) + wire types (`api/types.ts`) + audio/WS URL helpers
- [x] Config (`src/config.ts`, platform-aware base URL: Android emulator → 10.0.2.2:8090) + feature-flag shell (`src/featureFlags.ts`, EXPO_PUBLIC_FLAG_*)
- [x] Router shell (`_layout.tsx`) + home (`index.tsx`) + Mode A/B route stubs; theme tokens
- [x] 22 jest-expo logic tests green; `tsc --noEmit` clean (jest globals imported from `@jest/globals`); eslint flat config clean
- [x] New Layer Protocol: `reusable-node-app.yml` now runs install+lint+typecheck+test; `make poc-app-test` mirrors CI; CLAUDE.md documents app/ structure
- [x] Pruned unused tabbed-starter assets + stale template README
- [x] Commit (56bed0d)

### P6 — Screens (Mode A & B)  🔄

Broken into committable sub-milestones (each keeps `make poc-app-test` green). P6 flips to ✅
only when **all** of P6a–P6e are done.

| Sub | Scope | Status | Commit |
|---|---|---|---|
| P6a | Pure coaching helpers (capabilities, format, goal) + UI primitives (Screen, Button, Card, ScoreBar, OptionGroup, Field, Banner) + tests | ✅ DONE | `feat(poc-app): coaching format/goal helpers + UI primitives` (debe97e) |
| P6b | Mode A script-list + Goal Signature form; Mode B intake (paste script + occasion/purpose); wire `createSession` → navigate to record | ✅ DONE | `feat(poc-app): Mode A & B setup screens + Goal Signature form` (96ed825) |
| P6c | Cross-platform recorder (expo-audio: web MediaRecorder + native file→base64; no-mic fallback → `audio_base64=null`) + per-line record screen | ✅ DONE | `feat(poc-app): per-line recorder + record/feedback screens` (d63081b) |
| P6d | Flow store for audio handoff + processing screen (submit/retry, animate STAGES, WS behind `liveProgress` flag) → feedback | ⬜ TODO | — |
| P6e | Feedback report (overall + capability ScoreBars, strengths, improvements, read-aloud behind `readAloud` flag, A/B correction cards, retry showing `delta`) | ⬜ TODO | — |

Feature checklist (the user-visible surface these sub-milestones add up to):
- [x] Home / mode select (P5 `index.tsx`; mode-B card behind `flags.modeB`)
- [x] Goal Signature form (objective, occasion, audience, style, duration) — `ui/GoalSignatureForm` (P6b)
- [x] Mode A: script list → script display → record → **per-line recorder + Get feedback** (P6c)
- [x] Mode B: paste-script intake + goal → record → **per-line recorder + Get feedback** (P6c)
- [x] Per-line recorder: record/stop/skip/re-record; skip-everything path submits all-null (P6c)
- [x] Minimal feedback report: overall + capability ScoreBars + summary (P6c; full report = P6e)
- [ ] Processing screen (WS progress) — P6d
- [ ] Feedback report: written feedback + read-aloud (expo-speech) + A/B correction cards (expo-audio play user vs ideal) — P6e
- [ ] Retry flow: re-record flagged line → rescore → delta display — P6e
- [x] **P6a:** coaching helpers + UI primitives + 44 tests green (debe97e)
- [x] **P6b:** Mode A/B setup + Goal Signature form; createSession → /record loads session (96ed825)
- [x] **P6c:** per-line recorder + record/feedback screens; 64 app tests green, web export 7 routes (d63081b)

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
- 2026-05-31 (P5): test files import jest globals from `@jest/globals` (not the ambient `@types/jest`
  globals). Why: under `tsc --noEmit` the ambient globals weren't resolving (TS2304/TS2593), and the
  explicit import is robust and runs fine through babel-jest. `jest.fn()` from `@jest/globals` needs
  an explicit signature (`jest.fn<(...args: unknown[]) => Promise<unknown>>()`) or `mockResolvedValue`
  infers `never`. Verified clean-room: typecheck passes with `.expo/`+`expo-env.d.ts` deleted, so CI
  (`npm ci` with no generated Expo types) is safe. `Link href` typing falls back to string without
  generated typed-routes — acceptable for POC.
- 2026-05-31 (P5): CI `reusable-node-app.yml` adds `actions/setup-node@v4` (node 20) + runs
  `npm ci → lint → typecheck → test`; keeps the `if [ -f app/package.json ]` guard so it stays green
  on branches without the app. `make poc-app-test` runs the same lint+typecheck+jest locally.
- 2026-05-31 (P6b): session handoff between a setup screen and `/record` is a **`sessionId` route
  param + `getSession` re-fetch** — stateless and survives a web reload; no global store needed. The
  P6d flow store is only for *audio* (blobs can't ride in URL params). `router.push({ pathname:
  '/record', params: { sessionId } })` object form typechecks under the typedRoutes experiment even
  with no generated route types. expo's eslint `react-hooks/set-state-in-effect` forbids synchronous
  `setState` in an effect body — derive that state during render instead (record.tsx computes the
  missing-session banner at render, not in the effect). `createSession` does **not** require the user
  to pre-exist (backend just stores `user_id`), so `DEMO_USER_ID = 'demo-user'` is sufficient.
- 2026-05-31 (P6c): the recorder is a child component (`ui/Recorder`) mounted **only when
  `useClientReady()` is true** — `useRecorder` calls expo-audio hooks (browser-only on web), so
  mounting it during static export (Node SSR) crashes. `record.tsx` renders a read-only line list
  until hydration, then swaps in `<Recorder>`; the web export still emits all 7 routes. Cross-platform
  split stays minimal: expo-audio drives capture on both targets, only URI→bytes differs
  (`readBytes.web.ts` fetch vs `readBytes.ts` File API), and pure `bytesToBase64` unifies encoding.
  `useRecorder.start()` returns a boolean so a line flips to `recording` only once capture truly began
  (denied/unavailable mic → stays idle + shows a skip-anyway banner). The **skip-everything path**
  (`toUtteranceInputs` → all `audio_base64: null`) lets the backend coach from expected text, so the
  full record→feedback flow is demoable on web with no microphone. Line display state is derived by
  the pure `lineState(index, activeLine, recordings)` in `audio/recordings.ts` (unit-tested), keeping
  `LineRecorder` presentational.
- 2026-05-31 (P6a): jest needs `moduleNameMapper: { '^@/(.*)$': '<rootDir>/src/$1' }` to resolve the
  `@/` alias — Metro reads tsconfig `paths` but jest does not. Component tests use bare
  `react-test-renderer` (no @testing-library/react-native installed): wrap `TestRenderer.create` in
  `act(...)`, and find Pressables via `root.findAll(n => typeof n.props?.onPress === 'function')` —
  the jest-expo preset wraps `Pressable` so `findAllByType(Pressable)` returns 0. Coaching `OCCASIONS`
  option values deliberately embed backend boost keywords (investor/wedding/toast/interview/lecture/
  keynote/standup) so the Goal Signature drives `domain/goal_signature.py` capability weighting; a
  goal.test.ts assertion guards this contract.
