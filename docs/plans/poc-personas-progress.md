# POC Personas ("20 Legends Speaking Coach") — Implementation Progress Tracker

> **This file is the committed, resumable source of truth for Iteration 1.**
> It is authoritative across sessions — not in-session memory, not the TaskList.

---

## ▶ HOW TO RESUME (agent: read this block FIRST, every run)

You were told: *"implement this plan"* (pointing at this file or at
[`poc-personas-plan.md`](poc-personas-plan.md)). Do exactly this:

1. **Read the plan:** [`docs/plans/poc-personas-plan.md`](poc-personas-plan.md) — the full
   approved design (Parts A–D, verification, acceptance). This tracker is its checklist.
2. **Read this whole file** — find the **first sub-task whose status is not `DONE`** in the
   tables below. That is where you resume.
3. **Re-verify the last `DONE` row actually landed** before continuing (run its *Verify*
   command / confirm the file exists). A session can die between writing code and committing,
   so the last row marked `DONE` might not be on disk. If it didn't land, redo **only** that
   one step. **Never redo work already `DONE` and verified.**
4. Work **one atomic sub-task at a time**: do it → run its *Verify* → set status `DONE` +
   record the commit SHA → **`git commit` the code and this tracker together** (branch
   `feat/poc-coaching-app`, conventional commit) → next row. Never batch multiple sub-tasks
   into one commit. A crash then costs at most one in-flight step.
5. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but **this committed
   file is authoritative** — reconcile against it, not against memory.

**Status legend:** `TODO` (not started) · `DOING` (in flight, not committed) · `DONE` (committed; SHA recorded).

---

## Key constraints (do not violate — full detail in the plan & CLAUDE.md)

- **Acoustic-first, never transcript-as-judge.** The persona path scores the *real waveform*
  (pace = syllables/sec, pauses = silence segmentation, expressiveness = pitch/energy,
  coverage = detected-vs-expected syllables). Whisper STT stays **OFF** in the persona path.
  This honors the user's hard rule: judge my speech, not a cleaned-up transcript.
- **Additive, zero regression.** Mode A/B keep their existing transcript-based path **untouched**.
  The existing Mode A/B golden fixtures must stay byte-for-byte identical (no churn).
- **Mock is the CI default.** `PROVIDER_ACOUSTIC=mock` (deterministic, offline) is default;
  `librosa` is the opt-in real impl for the demo machine only. Registry raises on unknown name.
- **Hard DB isolation.** Mock DB only: container `vaani_poc_mongo`, port **27018**, database
  `public_speaking_intelligence_mock` (name must end `_mock`). Never touch the real DB / 27017.
- **POC schemas are isolated.** New schema goes in `services/api/db/schemas/` — NOT shared `schemas/`.
- **Audio never in Mongo.** Use the `ObjectStore` abstraction (LocalFS at `.poc-storage/` by default).
- **Versioning/golden gate.** Every scored output carries `*_version` fields; a version bump
  requires regenerating the persona golden fixtures or CI fails.
- **Python env:** `.venv-poc` only (via `make poc-api-install`). Never `.venv` / `.venv311`.
- **Keep green:** `make poc-api-lint && make poc-api-test` (coverage ≥70%) and `make poc-app-test`.
- **Git identity:** branch `feat/poc-coaching-app`; conventional commits; never `git add -A`,
  never force-push / `reset --hard` without explicit ask (see global CLAUDE.md dual-identity rules).

---

## P0 — Resumability scaffold

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | In-repo copy of full plan → [`poc-personas-plan.md`](poc-personas-plan.md) | DONE | `3baf934` | `test -f docs/plans/poc-personas-plan.md` |
| P0.2 | This resumable tracker → `poc-personas-progress.md` | DONE | `3baf934` | `test -f docs/plans/poc-personas-progress.md` |
| P0.3 | Link this milestone from [`poc-implementation-progress.md`](poc-implementation-progress.md) | DONE | `3baf934` | grep finds "poc-personas-progress" in that file |

---

## P1 — Persona content + data plumbing (Part A + Part B.1, B.8)

*Checkpoint:* `GET /personas` returns 20; each speech readable in `/docs`.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | Research the 20 (confirm top reference video + distill speaking qualities) → notes feed P1.2 | DONE | `96dcc51` | profiles drafted for all 20 (Jobs…Kelly) — embodied in personas.json |
| P1.2 | Author `services/api/db/seed_data/personas.json` — 20 records (persona_id, name, role, archetype, reference, goal_line, signature_qualities, speech.lines, rubric) | DONE | `96dcc51` | `python3 -c "import json;d=json.load(open('services/api/db/seed_data/personas.json'));assert len(d)==20"` |
| P1.3 | Schema `services/api/db/schemas/personas.json` (`$jsonSchema`, required fields) | DONE | `531ed44` | file parses; has `$jsonSchema`; `required` lists persona_id/name/speech/rubric |
| P1.4 | Register `personas` in `COLLECTION_SPECS` (`services/api/db/init_mock_db.py`) + indexes | DONE | `531ed44` | `grep personas services/api/db/init_mock_db.py` |
| P1.5 | Seed personas in `services/api/db/seed_mock.py` (upsert by `persona_id`) | DONE | `531ed44` | init+seed on mongomock → 20 personas, idempotent re-seed inserts 0 |
| P1.6 | Schema test case in `services/api/tests/test_schemas_poc.py` | DONE | `531ed44` | `pytest services/api/tests/test_schemas_poc.py` → 10 passed |
| P1.7 | Repo accessors `list_personas` / `get_persona` in `services/api/repository.py` | DONE | `3f6dfae` | test_repository green |
| P1.8 | Pydantic `PersonaSummary` / `PersonaDetail` in `services/api/models.py` | DONE | `3f6dfae` | route returns typed payloads (test_api_personas) |
| P1.9 | `services/api/routes/personas.py` (`GET /personas`, `GET /personas/{id}`) + register in app | DONE | `3f6dfae` | `GET /personas` → 20; `GET /personas/steve-jobs` → 200 |
| P1.10 | Route tests in `services/api/tests/` (list + detail + 404) | DONE | `3f6dfae` | `pytest test_api_personas.py` → 5 passed |
| P1.11 | Add `personas` row to CLAUDE.md POC Data Model table | DONE | `3f6dfae` | `grep personas CLAUDE.md` |

---

## P2 — Acoustic engine (Part B.2–B.3)

*Checkpoint:* a sample clip yields real pace/pause/pitch numbers; mock yields deterministic ones.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | `services/api/providers/audio_decode.py` — bytes (webm/opus \| m4a) → mono 16 kHz float32 PCM via PyAV | DONE | `62cdb57` | unit test decodes a tiny fixture to non-empty PCM |
| P2.2 | `AcousticFeatures` dataclass in `services/api/domain/types.py` (rate, pauses, pitch, energy, syllables, coverage) | DONE | `ffcb02e` | import works; fields per plan B.3 |
| P2.3 | `AcousticAnalyzer` ABC in `services/api/providers/base.py` — refined to `analyze(audio_ref, *, expected_text, seed)` to mirror `STTProvider` (real impl decodes internally; mock ignores content), so the pipeline never branches on provider type | DONE | `ffcb02e` | import works |
| P2.4 | Mock acoustic impl (deterministic from expected_text + seed; empty recording → skipped-line zeros) in `services/api/providers/acoustic.py`; syllable estimator added to `domain/text.py` | DONE | `dc0fbaf` | same input → identical features (unit test) |
| P2.5 | Real librosa impl (speech_rate_sps via syllable-nuclei peaks, pauses via short-window RMS silence runs, pitch via pyin) — kept in its **own** `services/api/providers/acoustic_librosa.py` (top-level `import librosa`; omitted from `.coveragerc` like `audio_decode.py`, since CI lacks the dep) so the mock `acoustic.py` stays fully CI-covered | DONE | `af980c7` | `pytest test_acoustic_librosa.py` on synthetic tone-burst / silence-gap signals (5 passed where librosa installed); key test: faster read → higher measured pace |
| P2.6 | Wire `provider_acoustic` in `registry.py` (added `acoustic` to `ProviderBundle` + `_build_acoustic`: mock default, lazy-import librosa real, raise on unknown) + `config.py` (`provider_acoustic="mock"`) | DONE | `be55ce9` | `grep provider_acoustic services/api/config.py services/api/providers/registry.py` |
| P2.7 | Unit tests: syllable-nuclei rate + pause detection (in `test_acoustic_librosa.py`, P2.5) · mock determinism (in `test_acoustic.py`, P2.4) · registry build/raise (added to `test_registry.py` here, coupled to P2.6 wiring) | DONE | `be55ce9` | `make poc-api-test` green (148 passed, 93.26%) |
| P2.8 | Add `librosa` (+ scipy/soundfile; numpy/PyAV transitive) to `services/api/requirements-local.txt` (NOT CI requirements) | DONE | `c6c9b50` | `grep librosa services/api/requirements-local.txt` |

---

## P3 — Persona scoring + feedback (Part B.4–B.9)

*Checkpoint:* `POST /sessions` (persona) → score + style_match + grounded corrections from real audio.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | Carry `AcousticFeatures` on `UtteranceAnalysis`; add `AcousticProfile` aggregate + `style_match` on `ScoreResult`/`PipelineResult` (`types.py`); `PipelineResult.to_dict()` adds persona keys **only when set** so Mode A/B + golden stay byte-identical | DONE | `a500760` | `pytest test_types.py` (6 passed); Mode A/B golden unchanged |
| P3.2 | Pipeline persona branch: `analyze_utterances_acoustic` (decode → `AcousticAnalyzer` per line, **no STT/align**) + `aggregate_acoustic` (→ `AcousticProfile`) in new `domain/persona.py`. Pace measured over spoken lines; a skip drags coverage. Mode A/B branch untouched | DONE | `211746f` | `pytest test_persona_pipeline.py` (5 passed): spy STT never called; skip lowers coverage not pace |
| P3.3 | Persona scorer (`PersonaRubric` + `score_persona` in `domain/persona.py`): pace from `speech_rate_sps` vs persona band; fluency from pauses; engagement from pitch/energy; clarity/confidence from coverage/steadiness; apply persona `capability_weights`; `style_match` left `None` (P3.4) | DONE | `b95516e` | `pytest test_persona_scorer.py` (10 passed): same fast read = full marks vs Huang band, docked vs Buffett band |
| P3.4 | `compute_style_match` (0–1) from band/pause/expressiveness distance — *two-directional*: overshooting the persona docks it | DONE | `54c9c04` | `pytest test_persona_style_match.py` (6 passed): matched → high, far → low, overexpressive lowers match for monotone persona |
| P3.5 | Persona-flavored, acoustic-grounded per-line corrections via `build_persona_feedback` using `rubric.feedback_notes`; classifies each line's dominant real event (skip/stall/too-fast/too-slow/monotone), caps to top-3 by severity, A/B `corrected_text` = the line | DONE | `af0ba82` | `pytest test_persona_feedback.py` (8 passed): too-fast cites "6.0 syll/s", stall cites "2.4s", skip cites "0 of 5" |
| P3.6 | Session create + lifecycle: `mode="persona"` + `persona_id` on `CreateSessionRequest`; `_create_persona_session` loads the speech as `expected_units` + stashes the rubric; `process_session` branches to `run_persona` (acoustic, no STT) and persists `style_match`+`acoustic`; `assemble_detail` surfaces persona fields; retry carries persona context | DONE | `pending` | `POST /sessions {persona_id}` → 201, session carries rubric; full flow → `style_match`+`acoustic`, persona version stamp; retry preserves persona + delta (test_api_sessions: 5 new passed) |
| P3.7 | Persona version constants + `persona_version_stamp()` in `domain/versions.py` (distinct from Mode A/B so goldens stay independent) | DONE | `25f9888` | `pytest test_versions.py` (3 passed): same 4 keys, all values differ from Mode A/B |
| P3.8 | **New** persona golden fixtures under `services/api/tests/golden/` (Mode A/B golden untouched) | TODO | | `make poc-api-test` golden green; Mode A/B golden unchanged in `git diff` |
| P3.9 | End-to-end backend test: persona session fast vs slow read → pace/style_match differ | TODO | | `make poc-api-test` green |

---

## P4 — Frontend (Part C)

*Checkpoint:* full click-through in the browser (grid → detail → record → feedback).

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P4.1 | `app/src/api/types.ts` — `PersonaSummary`, `PersonaDetail`; extend `SessionDetail` (style_match + acoustic metrics) | TODO | | `make poc-app-test` typecheck green |
| P4.2 | `app/src/api/client.ts` — `listPersonas()`, `getPersona(id)`; extend `createSession` with `persona_id` | TODO | | co-located client test green |
| P4.3 | `app/src/app/personas.tsx` — 20 monogram tiles grid → detail (goal_line, lines, signature_qualities, reference, Start) | TODO | | renders in browser; tiles show initials |
| P4.4 | Register `/personas` route in `app/src/app/_layout.tsx` | TODO | | route navigable |
| P4.5 | `app/src/app/index.tsx` — primary "Practice with a great speaker" headline card → `/personas` | TODO | | home shows the card |
| P4.6 | `app/src/app/feedback.tsx` — persona name, style-match score beside Overall, acoustic readout (pace vs band, pause count) | TODO | | feedback screen shows style_match |
| P4.7 | Co-located frontend test(s) for persona screen/client | TODO | | `make poc-app-test` green |
| P4.8 | Verify web click-through with preview tools (grid → detail → record → processing → feedback) | TODO | | screenshot of feedback with style_match |
| P4.9 | Confirm Android path (`make poc-app-android`; config already → `10.0.2.2:8090`) | TODO | | emulator click-through reaches feedback |

---

## P5 — End-to-end, tests, docs (Part D + Verification)

*Checkpoint:* real-voice run on web (and Android); full suites green; docs updated.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P5.1 | Real-voice run: `PROVIDER_ACOUSTIC=librosa PROVIDER_TTS=macos` — fast vs slow, monotone vs expressive, skip-a-line, retry delta | TODO | | each acceptance bullet in plan "Verification" passes |
| P5.2 | Cross-persona check: same fast read suits Huang but is flagged for Buffett (per-persona bands) | TODO | | manual demo confirms |
| P5.3 | `make poc-api-test` fully green (incl. new persona golden) | TODO | | command exits 0 |
| P5.4 | `make poc-app-test` fully green (lint + typecheck + jest) | TODO | | command exits 0 |
| P5.5 | Update CLAUDE.md: `AcousticAnalyzer` + `PROVIDER_ACOUSTIC`, persona version constants + golden, `librosa` note | TODO | | `grep -i acoustic CLAUDE.md` |
| P5.6 | Add this milestone to [`poc-implementation-progress.md`](poc-implementation-progress.md) (mark P0.3 done here) | TODO | | milestone present |
| P5.7 | Final: raise coverage baseline if it improved; confirm CI-relevant suites green | TODO | | `make poc-api-test && make poc-app-test` |

---

## Decisions & open notes (carry across sessions)

- **Speeches are original-in-style** (~130–150 words ≈ 60s), zero copyright. `reference.video_url`
  seeds from the user-provided YouTube links; qualities come from documented analyses + reasoning,
  **not** video transcription.
- **Tiles are monograms** (initials + name + role chip), zero image licensing — identical on web/Android.
- **Distinct target bands make the demo land:** Buffett slow/steady (~2.4–3.0 sps), Huang fast/high
  (~4.2–5.0), Jobs measured/dramatic, Khan even, Voss calm/low/deliberate, Brené warm/variable.
- **Reconciliation flag (raised to user):** GPT's POC3 listed "transcript accuracy" as a scored
  dimension. We deliberately dropped transcript-as-judge of *delivery* to honor the stronger
  "judge my speech, not the transcript" instruction. Pronunciation (forced alignment) is **Iteration 2**.
