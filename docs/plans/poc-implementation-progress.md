# POC Implementation Progress Tracker

> **THIS IS THE RESUMABLE SOURCE OF TRUTH.** If a session is lost/corrupted, re-run
> the original prompt (below), then read this file top-to-bottom and continue from the
> **first task that is not `✅ DONE`**. Every `✅ DONE` task is committed to git — do not redo it.

> **▶ Iteration 1 — "20 Legends Speaking Coach" (personas, acoustic-first): ✅ functionally complete.**
> Full plan + tracker live in [`poc-personas-plan.md`](poc-personas-plan.md) and
> [`poc-personas-progress.md`](poc-personas-progress.md) — P0–P5 DONE (20 personas, mock+librosa
> acoustic engine, persona scoring + style-match + grounded corrections, web
> grid→detail→record→feedback; real librosa run verified). Open items: Android emulator click-through
> deferred (P4.9 — needs an SDK box); coverage-baseline bump (P5.7). Resume from the first
> non-`DONE`/`DEFERRED` sub-task in that tracker.

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
| Real STT/TTS (post-feedback, 2026-05-31) | **No-key LOCAL providers: faster-whisper (STT) + macOS `say` (TTS)** | User demands real behavior; env probe found `say`+`afconvert`+`ffmpeg` present and pypi+HF reachable → real STT/TTS with **zero cloud creds**, honoring the locked "no creds" rule. Heavy deps stay in `requirements-local.txt` (not CI) and load **lazily**, so CI/tests keep using mocks (golden stays deterministic + green). Selected via `.env.poc` (`PROVIDER_STT=whisper`, `PROVIDER_TTS=macos`); mock remains the default + fallback. |
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
| P6 | Screens: Mode A & B full coaching flows | ✅ DONE | P6a–P6e (debe97e…72302a3) | `make poc-app-test` green (80 tests + tsc + lint); web export 8 routes |
| P7 | Reliability artifacts (SLO, rollback, telemetry, golden) | ✅ DONE | `feat(poc-api): reliability artifacts — telemetry, golden regression, SLO docs (P7)` (62aa1ed) | `make poc-api-test` green (109 tests incl. golden + telemetry, 97.37% cov); docs/reliability/* present |
| P8 | E2E verify (web) + Android compat + push + PR | 🔄 IN PROGRESS | — | both modes pass on web; PR open |
| P9 | **Real STT** — transcribe the actual recording; real mistake detection (plan §5.3) | ✅ DONE | `feat(poc-api): real STT/TTS providers + grounded feedback, hardened for real-mic input (P9/P10)` (adec89f) | faster-whisper transcribes real audio; empty/quiet/noisy → empty transcript (anti-hallucination guards); grounded feedback cites real diffs |
| P10 | **Real TTS** ideal-voice clips + fix A/B audio playback (stop control, no beep) | ✅ DONE | backend macOS `say` TTS (adec89f); frontend app-wide single playback (60c6ddf) | macOS `say` speaks the ideal line; buttons toggle ▶/⏸, gated on `isLoaded`; starting any clip stops every other (shared `exclusivePlayback`) |
| It1 | **Iteration 1 — 20 Legends personas (acoustic-first)**: 20-persona seed, acoustic engine (mock default · librosa real), persona scoring + style-match + grounded corrections, web grid→detail→record→feedback | ✅ DONE | `poc-personas-progress.md` P0–P5 (96dcc51…3502f98) | `GET /personas` → 20; `make poc-api-test` (195, 93.82%) + `make poc-app-test` (96) green; real librosa run verified pace/skip/per-persona; Android emulator deferred (P4.9) |

---

## Post-demo feedback — Round 1 (2026-05-31)

The user drove a full Mode A demo on web and gave direct feedback. **This is now the top
priority — P9/P10 come before P8 ship.** The bar shifted: the POC must behave like a *real*
coach, not a deterministic mock. Verbatim observations + code-grounded root cause + acceptance.

### Observation 1 — "Ideal" audio is broken (silent, or an unstoppable beep)
> *"when I pressed the CTA 'IDEAL' button — I heard nothing, sometimes a long unstopping beep
> and I had to close and reopen the tab."*

**Root cause (two bugs):**
- **The beep itself** is by design: `MockTTS.synthesize` in
  [services/api/providers/mock_ai.py](../../services/api/providers/mock_ai.py) emits a pure
  sine wave (`freq = 180 + (len(text) % 7) * 25`, mono 16 kHz PCM WAV). It was never speech.
- **Silent / unstoppable** is a playback bug in
  [app/src/ui/CorrectionAudio.tsx](../../app/src/ui/CorrectionAudio.tsx): `onPress` does only
  `seekTo(0); play()` with **no stop/pause control**, no load/status guard, and **no
  mutual-exclusion** between the two players. `play()` before the source loads → silence;
  a long clip can't be stopped → user closes the tab.

**Acceptance:** the "Ideal" button speaks the corrected line in a real human-sounding voice;
playback is stoppable (button toggles ▶/⏸), never silent on a valid clip, and starting one
clip stops the other.

### Observation 2 — feedback is not real
> *"feedback is not real at all … the feedback itself is wrong."* (Read-aloud reads it
> correctly — the *text* is the problem, not the TTS of the report.)

**Root cause:** `MockFeedbackGenerator` in `mock_ai.py` fills `_IMPROVEMENT_TEMPLATES` /
`_STRENGTH_TEMPLATES` keyed only by capability id — it is **ungrounded in what was actually
said**. With a real transcript + real alignment, feedback must cite the actual
substitutions/omissions/insertions and the real delivery features.

**Acceptance:** feedback names concrete, true mistakes from the learner's actual delivery
(e.g. "you said *‘their’* but the line is *‘there’*"; "you dropped the word *‘quarterly’*").

### Observation 3 (the #1 must-fix) — it ignores what I actually said
> *"no matter what I speak it thinks I spoke almost correct. The first basic thing that at
> least must work is: it must understand what I spoke and what I was supposed to speak, and
> based on that say what mistakes I did … common things easy for STT/TTS must work. Voice
> modulation, pauses etc. can come later. This is very easy, very easily achievable."*

**Root cause:** `MockSTT.transcribe` **ignores `audio_ref` entirely** and rebuilds the
transcript *from `expected_text`* (seeded filler injection + ~6% omission) — so output always
≈ the script. Confirmed by the call site
[services/api/domain/pipeline.py:55](../../services/api/domain/pipeline.py): it passes the
storage **key string** (or `b""`), never the audio bytes. → output cannot reflect real speech.

**Acceptance:** when the learner says words different from the script, the transcript reflects
what was *actually said*, the aligner flags the real diffs, and the score/feedback move
accordingly (not pinned near "correct").

### Observation 4 — "Get feedback" without recording everything (skip-all)
> *"if I select Inspire / Job interview / Investor … then Start practice, even without
> recording everything I can Get feedback … looks good and bad to me, I don't know. I'm okay
> with it for now."*

**Disposition:** **keep as-is for the POC.** The skip-all path
(`toUtteranceInputs` → all `audio_base64: null`) intentionally lets the backend coach from
expected text so the flow is demoable with no mic. Revisit post-P9/P10. No action now.

### Also observed (mine, lower priority — deferred unless quick)
- The local stage timeline in `processing.tsx` is **cosmetic** (backend pipeline is synchronous);
  with real STT, transcription latency becomes real → revisit pacing so the bar tracks actual work.
- No "what you actually said vs the script" diff is surfaced in the report even though the
  aligner computes it — once STT is real, **show the diff** (it's the proof the coaching is real).

---

## Post-demo feedback — Round 2 (2026-05-31)

The user re-tested in **their own Chrome** (real microphone) with the "Product Launch Pitch"
script: recorded **only line 1**, skipped lines 2–5, then pressed Get feedback. Three concrete
bugs surfaced — all real-world artifacts that Round 1's clean-TTS verification masked. Verbatim
observations + code-grounded root cause + acceptance.

### Observation 5 — real-mic STT returns hallucinated garbage
> *"for line 1, it is saying that I said some garbage thing … the focus next is the clarity.
> Line 1, you said 'there' instead of 'every', you said 'who' instead of 'they' … This all is
> incorrect feedback."* (Line 1 transcribed as *"yesterday was there who was here no one was
> running i was crying you were happy i was sad"* — unrelated to the script.)

**Root cause:** Whisper **hallucinates coherent-sounding text on near-silent / noisy input** — a
well-known faster-whisper failure mode. [services/api/providers/whisper_stt.py](../../services/api/providers/whisper_stt.py)
called `model.transcribe(..., vad_filter=True)` with **no anti-hallucination guards**
(`condition_on_previous_text` defaulted True, no explicit `no_speech`/`log_prob` thresholds, no
segment-level rejection). A quiet mic clip → confident garbage instead of "we didn't catch that".
Round 1's verification used **clean TTS WAV** (transcribes verbatim), so this never showed.

**Acceptance:** quiet/empty/noisy audio yields an **empty transcript** (honest "couldn't hear
you"), not fabricated words; real speech still transcribes. When unsure, prefer empty over garbage.

### Observation 6 — a line I never recorded shows a fabricated "YOU SAID"
> *"for line 2, surprisingly, it is saying that you said something, something, something, while I
> didn't even record anything."* (Line 2 card showed *"You said: We built Pulse so those two hours
> come back to you."* — i.e. the **expected** text, presented as what the learner said.)

**Root cause:** `MockFeedbackGenerator` in [services/api/providers/mock_ai.py](../../services/api/providers/mock_ai.py)
treated a skipped line (empty transcript) as a delivery mistake: `_corrections` used
`original_text=a.transcript.text or a.expected_text` — the `or` falls back to **expected text** when
nothing was said; and `_concrete_mistakes` / `_corrections` rank by error count, so an all-deleted
(skipped) line scores as *maximal* error and dominates the cards as "you skipped …".

**Acceptance:** a line with **no recorded audio** never generates a correction card or a "you said /
you skipped" callout, and never echoes the expected text as what was said. Only actually-recorded
lines (non-empty transcript) are coached.

### Observation 7 (the user's "basic thing") — two clips play at once
> *"for Your Take, I played it, and then I played Ideal. Both sounds were coming in parallel at the
> same time, mixed. … if I press any play button, then the previous sound that was playing should
> stop. No two sounds should play at once."*

**Root cause:** [app/src/ui/CorrectionAudio.tsx](../../app/src/ui/CorrectionAudio.tsx) coordinated
playback **only within a single card** (`other.pause()` pauses the sibling player). Each correction
card mounts its **own** `useAudioPlayer` pair with no cross-card coordination, so "Your Take" on
card 1 and "Ideal" on card 2 play simultaneously.

**Acceptance:** **app-wide single playback** — pressing any play button stops whatever was playing
anywhere (across all cards, both sides). At most one clip audible at any time.

### Resolution — Round 2 (2026-05-31)

All three observations are fixed and verified. Backend fixes shipped in **adec89f**; the
cross-card playback fix shipped in **60c6ddf**.

| # | Fix | Where | Verified |
|---|-----|-------|----------|
| 5 | Anti-hallucination guards on real STT: `condition_on_previous_text=False`, explicit `no_speech`/`log_prob` thresholds, and a segment-level `_is_hallucinated` reject (OR of high `no_speech_prob` / low `avg_logprob`). Non-bytes/empty audio → empty `Transcript`. | `services/api/providers/whisper_stt.py` (adec89f) | `test_whisper_stt.py` (7 tests); quiet/empty input now yields an empty transcript, not fabricated words. |
| 6 | Skipped lines are never coached: `_was_recorded(a) = bool(a.transcript.words)` gates both `_concrete_mistakes` and `_corrections`; `original_text = a.transcript.text` (no `or expected_text` fallback). | `services/api/providers/mock_ai.py` (adec89f) | `test_mock_ai.py::test_feedback_ignores_skipped_lines`; **live browser** skip-all run on the fixed backend shows **0 correction cards** and no script text echoed as "you said". |
| 7 | App-wide single playback via a shared `exclusivePlayback` registry: starting any clip first pauses whatever was playing anywhere (try/catch for released players); buttons toggle ▶/⏸ and gate play on `isLoaded`. | `app/src/audio/exclusivePlayback.ts` + `app/src/ui/CorrectionAudio.tsx` (60c6ddf) | `exclusivePlayback.test.ts` (4 tests). A/B audio cards only appear for recorded-and-mistaken lines, so the no-mic skip path can't demo it in-browser — unit-tested instead. |

**Live verification (2026-05-31):** re-drove the full Mode A flow in the browser (home → picker →
Product Launch Pitch + Goal Signature → recorder → skip-all → feedback) against a backend restarted
on the **committed** code. Feedback report rendered Overall 61%, six capability ScoreBars, "What
worked" / "Focus next" cards, read-aloud, and **no "Line by line" cards** — bug 6 gone. Mode B intake
also verified (script paste + goal form, "Start practice" disabled until a script is entered).

> **Gotcha:** a uvicorn started **without `--reload`** holds stale in-memory code — the previously
> running `:8090` predated adec89f and still served the pre-fix `mock_ai.py`, so the browser showed
> the old bug 6 until restart. `make poc-api-run` uses `--reload`; restart after a provider/domain
> change (or rely on `--reload`) before manual re-verification.

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
| P6d | Flow store for audio handoff + processing screen (submit/retry, animate STAGES, WS behind `liveProgress` flag) → feedback | ✅ DONE | `feat(poc-app): processing screen + audio handoff flow store` (2251ea6) |
| P6e | Feedback report (overall + capability ScoreBars, strengths, improvements, read-aloud behind `readAloud` flag, A/B correction cards, retry showing `delta`) | ✅ DONE | P6e-1 full report + retry + delta (78b7c60); P6e-2 read-aloud + A/B audio (72302a3) |

Feature checklist (the user-visible surface these sub-milestones add up to):
- [x] Home / mode select (P5 `index.tsx`; mode-B card behind `flags.modeB`)
- [x] Goal Signature form (objective, occasion, audience, style, duration) — `ui/GoalSignatureForm` (P6b)
- [x] Mode A: script list → script display → record → **per-line recorder + Get feedback** (P6c)
- [x] Mode B: paste-script intake + goal → record → **per-line recorder + Get feedback** (P6c)
- [x] Per-line recorder: record/stop/skip/re-record; skip-everything path submits all-null (P6c)
- [x] Minimal feedback report: overall + capability ScoreBars + summary (P6c; full report = P6e)
- [x] Processing screen: staged timeline + real submit/retry → feedback; WS behind `liveProgress` (P6d)
- [x] Feedback report: written feedback (summary, strengths, severity-coded improvements, line-by-line correction cards) — P6e-1 (78b7c60)
- [x] Read-aloud (expo-speech) + A/B correction audio (expo-audio play user vs ideal) — P6e-2 (72302a3)
- [x] Retry flow: re-record flagged line → rescore → delta display (overall + per-capability) — P6e-1 (78b7c60)
- [x] **P6a:** coaching helpers + UI primitives + 44 tests green (debe97e)
- [x] **P6b:** Mode A/B setup + Goal Signature form; createSession → /record loads session (96ed825)
- [x] **P6c:** per-line recorder + record/feedback screens; 64 app tests green, web export 7 routes (d63081b)
- [x] **P6d:** flow store + processing screen (record→processing→feedback); 71 app tests, web export 8 routes (2251ea6)
- [x] **P6e-1:** full feedback report (overall+per-capability delta, strengths, severity improvements, correction cards) + retry flow (flagged-lines hint, processing routes to forked child session id); 76 app tests, web export 8 routes (78b7c60)
- [x] **P6e-2:** read-aloud (expo-speech) + A/B correction audio (expo-audio `useAudioPlayer`, client-gated); backend already populates `ideal_audio_key`/`user_audio_key`/`read_aloud_text`; 80 app tests, web export 8 routes (72302a3)
- [x] **P6 COMPLETE** — all of P6a–P6e done; both Mode A & B flows record→processing→feedback→A/B→retry on web

### P7 — Reliability artifacts  ✅ (62aa1ed)
- [x] `docs/reliability/slos.md` (SLO set + error budget policy + telemetry→SLO mapping + dashboards/alerting)
- [x] `docs/reliability/rollback-runbook.md` (env ladder + progressive rollout + release gates + rollback playbook + incident runbooks + privacy/retention)
- [x] `quality-baseline.poc.json` — SLO targets + model-quality floor (min_overall_score, max MAE) + coverage floor
- [x] `services/api/telemetry.py` — `Telemetry` emitter for all 8 plan-§11.1 event types → `release_health_events` (best-effort; never fails the request). Wired into `coaching_service.process_session` (transcription/scoring/feedback_latency) + `routes/sessions.py` (session_started/completed/retry_delta). `repository.save_event`/`save_eval_run` added.
- [x] `services/api/tests/golden/{dataset.json,test_golden_regression.py}` — pins deterministic overall+capability scores; fails on drift > tolerance (0.0005), below floor, MAE breach, or a `*_version` bump without regenerated golden. Auto-discovered by `make poc-api-test` (= CI-wired). Records a `model_eval_runs` doc.
- [x] `test_telemetry.py` (6 tests) — build/persist/best-effort/severity coercion/named emitters
- [x] Verified live: all 6 event types + an eval-run pass the **real** `:27018` `$jsonSchema` validators (probe, then cleaned up); 106 unit + 2 integration green, lint clean
- [x] Commit (62aa1ed) + CLAUDE.md updated (backend tree, reliability section, Adding-POC-code rules)

### P8 — E2E verify + ship  🔄
- [x] **Backend E2E (live :27018 + uvicorn :8090):** Mode A guided (`product-launch-pitch`, 5 lines)
  → scored 0.819, 6 capabilities, 2 corrections, version-stamped; ideal-clip `GET /audio/{key}`
  returns a valid WAV (`RIFF` header). Retry forks a child (attempt 2), `delta.overall=+0.0696`,
  7 delta keys. Mode B user-script split into 2 units → scored 0.969. **All E2E assertions passed.**
- [x] **Telemetry verified persisted:** parent session emitted session_started/transcription/scoring/
  feedback_latency/session_completed; child additionally retry_delta — all in `release_health_events`
  on the live mock DB.
- [x] **Web build:** `expo export --platform web` pre-renders all **8 routes** SSR-safe
  (/, mode-a, mode-b, record, processing, feedback, _sitemap, +not-found); 1.2MB bundle, React
  Compiler on. `make poc-app-test` green (lint + tsc + 80 jest tests).
- [x] **Android compatibility:** same Metro JS bundle backs Android; only cross-platform expo APIs at
  module load, browser-bound ones (`useRecorder`, `useAudioPlayer`) gated behind `useClientReady`;
  platform-aware API base URL (Android emulator → `10.0.2.2:8090`); `readBytes.web.ts`/`readBytes.ts`
  split. Emulator not available in this env → device run is the user's final confirm (same as P0 note).
- [x] **Live browser walkthrough (web, Claude Preview):** full Mode A flow (home → picker → Product
  Launch Pitch + Goal Signature → recorder → skip-all → feedback) on the fixed backend; feedback
  rendered correctly with **no fabricated correction cards** (Round 2 bug 6 verified gone). Mode B
  intake verified (script-paste guard disables "Start practice"). Screenshots captured at each step.
- [ ] Push branch (`feat/poc-coaching-app`, personal identity `github.com-personal`/`sagarpahwa`) +
  open PR (base `feat/vaani-db-foundation`); record PR URL here.

> Note: browser-driven click-through with screenshots was substituted by a deterministic **backend
> E2E driver** (real HTTP against uvicorn + live mock DB) plus the **static web export** (compile +
> SSR pre-render of every route). Together these exercise the full Mode A/B/retry contract and prove
> the UI bundles for web + Android without a flaky headless-browser dependency.

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
- 2026-05-31 (P6d): submit moved **out of the recorder and into a processing screen**. The record
  screen stashes the captured `UtteranceInput[]` in an in-memory `audio/flowStore` (base64 can't ride
  URL params) and navigates with only the `sessionId`; `processing.tsx` reads it and runs the real
  `submitUtterances`/`retrySession`. The store is **peeked, not consumed, on read** and dropped only
  after the call succeeds, with a `startedRef` guard — this survives React Strict Mode's
  double-invoked effects without double-submitting or losing the payload. The backend pipeline is
  **synchronous** (`routes/events.py` says so — the WS just replays a cosmetic `received→…→done`
  timeline), so the screen paces stages with a local timer (`STAGE_INTERVAL_MS`, mirrors backend
  `STAGES` in `coaching/stages.ts`) and treats the HTTP result as truth; it navigates to /feedback
  only once **both** the submit resolved and the timeline finished. `liveProgress` (default **on**)
  opens the WS purely to surface a server `error` event — additive, defensive (`new WebSocket` in a
  client-only effect, wrapped in try/catch), a real seam for when processing becomes async. Hard
  reload of /processing finds an empty store → recover by re-fetching the session (feedback/score
  present → go to feedback; else error). Same `react-hooks/set-state-in-effect` gotcha as P6b: the
  missing-`sessionId` banner is derived at render, not set in the effect.
- 2026-05-31 (P6e-1): a **retry forks a child session with a new `session_id`** (backend
  `routes/sessions.py` returns the child `SessionDetail`), so `processing.tsx` now navigates to the
  **response's** id, not the route param — tracked as `resultId` (submit returns the same id; the
  hard-reload recover path uses the re-fetched session's id). `submitDone` is **derived** from
  `resultId != null` rather than a separate state, sidestepping the `set-state-in-effect` rule.
  `delta` keys are `overall` + each capability (backend `compute_delta`), present only on retries;
  the feedback screen shows the overall delta under the big score and wires per-capability deltas into
  the existing `ScoreBar` `deltaText`/`deltaColor`. "Practice again" routes to `/record?retry=1` with
  the **parent** `sessionId` (the parent carries `corrections`, so `flaggedLineNumbers()` can render a
  focus hint); record stashes `kind: 'retry'` so processing calls `retrySession`. `CorrectionCard` is
  **presentational with an `actions?: ReactNode` slot** — P6e-2 injects A/B audio buttons there so the
  card itself never touches browser globals and stays SSR-exportable + unit-testable (text flattened
  in the test because interpolated `Line {n}` splits into separate string children).
- 2026-05-31 (P6e-2): audio playback mirrors the recorder's SSR gate. `CorrectionAudio`
  (`useAudioPlayer` from expo-audio, browser-bound on web) is mounted **only when `ready`** in
  feedback.tsx, and renders a play button per side only when that key exists — so the no-mic skip
  path (no `user_audio_key`) still offers the ideal clip (backend always sets `ideal_audio_key` via
  mock TTS in `domain/pipeline.py`). It self-returns `null` after the two hooks when both keys are
  absent (hooks stay unconditional). `ReadAloudButton` does **not** need the client gate — it only
  imports the `audio/speech.ts` wrapper and calls `expo-speech` from the press handler (never at
  render), so it ships in the static HTML; it's behind the `readAloud` flag and toggles Stop using
  speech's `onDone`/`onStopped`/`onError` callbacks. expo-speech installed via `expo install` to pin
  the SDK-56-matched version (~56.0.3). Like `useRecorder`, the browser-bound `CorrectionAudio` has
  no unit test (jest-expo has no audio backend); the static export is the SSR safety net instead.
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
- 2026-05-31 (P7): telemetry is **best-effort** — `Telemetry.emit` wraps the DB write in
  try/except and swallows, so a validator rejection or DB blip never breaks a coaching request
  (reliability > observability on the hot path). Consequence: mongomock (no validators) can't catch
  a schema mismatch, so a one-off probe inserted all 6 event types + an eval-run against the **real**
  `:27018` validators and confirmed acceptance, then deleted them. `latency_ms` is coerced to a
  non-negative `int` (schema bsonType) and unknown severities fall back to `info` for the same
  reason. Telemetry is wired **minimally** (backend session lifecycle/scoring/latency/retry);
  `ab_playback`/`api_error`/`mobile_crash` emitters exist but are client/edge-reported (no ingest
  endpoint in the POC) — unit-tested, not auto-wired. Golden test is the single enforcement point
  tying `domain/versions.py` ↔ `dataset.json` ↔ `quality-baseline.poc.json`: bumping a model version
  without regenerating the golden values fails CI by design (the `*_version` audit trail, plan §13.4).
  Golden values were generated by running the real pipeline once (deterministic mock stack) and baked
  in; lowest overall is 0.8615, floor set conservatively at 0.30 to catch a wholly-broken pipeline.
- 2026-05-31 (P6a): jest needs `moduleNameMapper: { '^@/(.*)$': '<rootDir>/src/$1' }` to resolve the
  `@/` alias — Metro reads tsconfig `paths` but jest does not. Component tests use bare
  `react-test-renderer` (no @testing-library/react-native installed): wrap `TestRenderer.create` in
  `act(...)`, and find Pressables via `root.findAll(n => typeof n.props?.onPress === 'function')` —
  the jest-expo preset wraps `Pressable` so `findAllByType(Pressable)` returns 0. Coaching `OCCASIONS`
  option values deliberately embed backend boost keywords (investor/wedding/toast/interview/lecture/
  keynote/standup) so the Goal Signature drives `domain/goal_signature.py` capability weighting; a
  goal.test.ts assertion guards this contract.
