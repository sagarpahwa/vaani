# POC 14 — High-Speed Fluency Q&A Coach — Implementation Plan & Progress Tracker

> **This file is the committed, resumable source of truth for POC 14.**
> It is authoritative across sessions — not in-session memory, not the TaskList.

---

## ▶ HOW TO RESUME (agent: read this block FIRST, every run)

You were told: *"implement this plan"* (pointing at this file). Do exactly this:

1. **Read this whole file** — find the **first sub-task whose status is not `DONE`** in the
   tables below. That is where you resume.
2. **Re-verify the last `DONE` row actually landed** before continuing (run its *Verify*
   command). A session can die between writing code and committing, so the last row marked
   `DONE` might not be on disk. If it didn't land, redo **only** that one step. **Never redo
   work already `DONE` and verified.**
3. Work **one atomic sub-task at a time**: do it → run its *Verify* → set status `DONE` +
   record the commit SHA → **`git commit` the code and this tracker together** (branch
   `feat/poc-14-highspeed-qa`, conventional commit) → next row. Never batch multiple sub-tasks
   into one commit.
4. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but **this committed
   file is authoritative** — reconcile against it, not against memory.

**Status legend:** `TODO` (not started) · `DOING` (in flight, not committed) · `DONE` (committed; SHA recorded) · `DEFERRED` (committed decision to skip; blocker recorded).

---

## Key constraints (do not violate — full detail in CLAUDE.md)

- **Base branch:** `feat/poc-13-teacher-explain`. New branch: `feat/poc-14-highspeed-qa` (branch off base, never commit to base).
- **No LLM.** All scoring is deterministic — WPM, filler count, word count from transcript analysis (re-uses existing `DeliveryFeatureExtractor` from `providers/analysis.py` and `domain/text.py`).
- **Reuses existing infrastructure.** CountdownTimer component from POC 08 (`app/src/ui/CountdownTimer.tsx`). Record screen infrastructure. The existing `DeliveryFeatures` dataclass carries WPM/filler_count/filler_per_min already computed by `DeliveryFeatureExtractor` — no new domain logic needed for the metrics.
- **Additive, zero regression.** Existing Mode A/B/persona/storytelling/explainer paths and their golden fixtures stay byte-for-byte identical. `make poc-api-test` must pass with the same golden values after every commit.
- **Python env:** `.venv-poc` only. Never `.venv` / `.venv311`.
- **DB isolation.** Mock DB only: container `vaani_poc_mongo`, port **27018**, database `public_speaking_intelligence_mock`. Never touch port 27017.
- **Keep green:** `make poc-api-lint && make poc-api-test` (coverage ≥70%) and `make poc-app-test` after every commit.
- **Git identity:** conventional commits; never `git add -A`; never force-push without explicit request.

---

## P0 — Docs & resumability scaffold

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | This plan/tracker file → `docs/plans/poc-14-highspeed-qa-plan.md` | TODO | | `test -f docs/plans/poc-14-highspeed-qa-plan.md` |
| P0.2 | Link this milestone in `docs/plans/poc-implementation-progress.md` (add POC 14 row to Milestone Status table) | TODO | | `grep "poc-14" docs/plans/poc-implementation-progress.md` |

---

## P1 — Backend data: highspeed questions + speed/clarity rubric

*Checkpoint:* 5 rapid-fire questions loadable from seed data; speed/clarity scoring logic tested.

**The 5 rapid-fire questions (timer_seconds: 20 each):**
1. `"Name three things that make a great manager."`
2. `"What is the one word that describes your communication style?"`
3. `"Tell me your biggest professional achievement in under 20 seconds."`
4. `"What would your team say is your superpower?"`
5. `"If you had to give one piece of advice to a new graduate, what would it be?"`

These are stored in `services/api/db/seed_data/highspeed_questions.json`:
```
[
  { "question_id": "great-manager",    "text": "...", "timer_seconds": 20, "category": "leadership" },
  { "question_id": "comm-style-word",  "text": "...", "timer_seconds": 20, "category": "self-awareness" },
  { "question_id": "biggest-achievement","text": "...", "timer_seconds": 20, "category": "achievement" },
  { "question_id": "team-superpower",  "text": "...", "timer_seconds": 20, "category": "self-awareness" },
  { "question_id": "new-grad-advice",  "text": "...", "timer_seconds": 20, "category": "wisdom" }
]
```

**Speed/clarity rubric — `services/api/domain/highspeed.py` — `score_rapid_answer(text: str, timer_seconds: int = 20) -> dict`:**

The function reuses existing analysis primitives (`domain/text.py` for tokenization; a local WPM estimate for the typed-text path; filler detection from `providers/analysis.py` FILLER_WORDS constant).

- `word_count` — `len(text.split())`
- `estimated_wpm` — `word_count / (timer_seconds / 60.0)` (assumes the user used the full timer; capped at a maximum of 300 for sanity)
- `speed_score` — WPM ≥ 140 → 1.0; WPM ≤ 60 → 0.0; linearly interpolated between. (For audio path: real WPM from transcript timing.)
- `filler_words_found` — list of filler words detected (using `FILLER_WORDS` from `providers/base.py`: "um", "uh", "like", "you know", "sort of", "kind of", "basically", "literally", etc.)
- `filler_count` — `len(filler_words_found)`
- `filler_per_min` — `filler_count / (timer_seconds / 60.0)`
- `clarity_score` — filler_per_min ≤ 1 → 1.0; filler_per_min ≥ 8 → 0.0; linearly interpolated.
- `completeness_score` — word_count ≥ 25 → 1.0; word_count ≤ 8 → 0.0; linearly interpolated between 8 and 25.
- `recovery_score` — for the typed-text path: always 0.8 (neutral; no pause data available). For the audio path (future): `1.0 - min(1.0, long_pause_count * 0.2)` where long_pause = silence > 1.5s.
- `classification` — derived from speed_score + clarity_score:
  - speed_score ≥ 0.6 AND clarity_score ≥ 0.6 → `"Fast + Clear"` (ideal)
  - speed_score ≥ 0.6 AND clarity_score < 0.6  → `"Fast but Chaotic"`
  - speed_score < 0.6 AND clarity_score ≥ 0.6  → `"Clear but Slow"`
  - speed_score < 0.6 AND clarity_score < 0.6  → `"Needs Work"`
- `overall_score` — weighted: speed 0.30, clarity 0.30, completeness 0.30, recovery 0.10.

**Goal Signature integration:** add `"highspeed"` as a valid `occasion` value in `goal_signature.py`'s `OCCASIONS` list (or wherever occasions are validated), with capability weights that emphasize `fluency` and `pace`.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | `services/api/db/seed_data/highspeed_questions.json` — 5 rapid-fire questions with fields above | TODO | | `python3 -c "import json; d=json.load(open('services/api/db/seed_data/highspeed_questions.json')); assert len(d)==5"` |
| P1.2 | `services/api/domain/highspeed.py` — `score_rapid_answer(text, timer_seconds) -> dict` with all dimensions above; imports FILLER_WORDS from `providers/base.py` (no new dep) | TODO | | `python3 -c "from services.api.domain.highspeed import score_rapid_answer; r=score_rapid_answer('Three things: vision clarity empathy',20); assert 'classification' in r"` |
| P1.3 | Add `"highspeed"` to valid occasions in `goal_signature.py` (wherever occasions are enumerated/validated); add highspeed-specific capability_weights emphasizing fluency + pace | TODO | | `grep -i highspeed services/api/domain/goal_signature.py` |
| P1.4 | `services/api/tests/test_highspeed.py` — tests: fast+clear text → classification "Fast + Clear"; too-slow text → "Clear but Slow"; filler-heavy → "Fast but Chaotic"; both slow+fillers → "Needs Work"; completeness_score 0 for 1-word answer; overall_score in [0,1]; filler_words_found list populated; goal_signature highspeed occasion returns correct weights | TODO | | `pytest services/api/tests/test_highspeed.py -v` → tests passed |
| P1.5 | `make poc-api-lint && make poc-api-test` green after P1 | TODO | | `make poc-api-lint && make poc-api-test` → 0 errors, coverage ≥70% |

---

## P2 — Frontend: `highspeed-qa.tsx` screen

*Checkpoint:* browser shows intro + 5 questions one at a time with 20s timer; text entry path → feedback screen showing speed/clarity classification.

**This POC reuses:**
- `app/src/ui/CountdownTimer.tsx` (from POC 08) — the 20-second per-question timer.
- The existing record screen infrastructure and API client for the typed-text path.
- The existing `DeliveryFeatures` display pattern from `feedback.tsx` for score bars.

**New API wiring needed:**
- `GET /highspeed-questions` — returns list of 5 questions.
- `POST /highspeed-questions/{id}/analyze` — submits text for scoring, returns `RapidAnswerResponse`.

Add to `app/src/api/types.ts`:
- `HighspeedQuestion` — `question_id`, `text`, `timer_seconds`, `category`
- `RapidAnswerResponse` — `question_id`, `word_count`, `estimated_wpm`, `speed_score`, `clarity_score`, `completeness_score`, `recovery_score`, `classification`, `filler_words_found`, `overall_score`

Add to `app/src/api/client.ts`:
- `listHighspeedQuestions()`, `analyzeRapidAnswer(questionId, text)`

**Screen layout — `app/src/app/highspeed-qa.tsx` (single route, view-state driven):**

**View 1: Intro**
- Header: "High-Speed Q&A".
- Big headline: "5 Questions. 20 Seconds Each."
- Subtitle: "Think fast, speak clearly. Rapid-fire answers train your fluency under pressure."
- CTA: "Start Challenge" → moves to View 2, question 1.

**View 2: Question (per question, index 0–4)**
- Question counter: "Question {n} of 5".
- Question text in a large card.
- `CountdownTimer` component (20 seconds, counting down). When it reaches 0, auto-advance.
- Large multiline `TextInput` below the timer ("Type your answer…").
- "Next" button (or "Finish" on question 5): saves answer text, advances.
- (Future audio: record button alongside text input — additive enhancement.)

**View 3: Results (shown after all 5 questions answered)**
- Header: "Your Results".
- For each of the 5 questions: question text + classification badge (color-coded: green "Fast + Clear", yellow "Fast but Chaotic" / "Clear but Slow", red "Needs Work") + speed/clarity/completeness bars.
- Overall summary card: "You were [most common classification]" with aggregate WPM average and filler count total.
- "Try again" button → resets to View 1.

**Route integration:**
- Register `highspeed-qa` in `app/src/app/_layout.tsx`.
- Add home card: "High-Speed Q&A" with subtitle "5 questions, 20 seconds each".

**Backend route (added alongside frontend):**
- `services/api/routes/highspeed.py` — `GET /highspeed-questions`, `POST /highspeed-questions/{id}/analyze`
- Add `HighspeedQuestion`, `RapidAnswerRequest`, `RapidAnswerResponse` to `services/api/models.py`
- Register router in `services/api/app.py`
- Tests: `services/api/tests/test_api_highspeed.py` — list (5 items), analyze valid text, invalid id → 404

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | `services/api/routes/highspeed.py` — `GET /highspeed-questions`, `POST /highspeed-questions/{id}/analyze`; register in `app.py`; add Pydantic models to `models.py` | TODO | | `curl -s http://localhost:8090/highspeed-questions \| python3 -c "import sys,json;assert len(json.load(sys.stdin))==5"` |
| P2.2 | `services/api/tests/test_api_highspeed.py` — 4+ tests: list (5 items), analyze text → classification present, invalid id → 404, empty text → valid low-score response | TODO | | `pytest services/api/tests/test_api_highspeed.py -v` → 4+ passed |
| P2.3 | `make poc-api-lint && make poc-api-test` green after P2.1–P2.2 | TODO | | `make poc-api-lint && make poc-api-test` → 0 errors, coverage ≥70% |
| P2.4 | Add `HighspeedQuestion`, `RapidAnswerResponse` to `app/src/api/types.ts` | TODO | | `grep RapidAnswerResponse app/src/api/types.ts` |
| P2.5 | Add `listHighspeedQuestions()`, `analyzeRapidAnswer(questionId, text)` to `app/src/api/client.ts` + tests | TODO | | `make poc-app-test` green; client test covers both methods |
| P2.6 | `app/src/app/highspeed-qa.tsx` — Intro → per-question view with CountdownTimer + text input → Results with classification badges + score bars; wired to API | TODO | | screen file exists; no TS errors in `tsc --noEmit` |
| P2.7 | Register `/highspeed-qa` route in `app/src/app/_layout.tsx` (title "High-Speed Q&A") | TODO | | `grep "highspeed-qa" app/src/app/_layout.tsx` |
| P2.8 | Add "High-Speed Q&A" home card to `app/src/app/index.tsx` | TODO | | `grep "highspeed-qa" app/src/app/index.tsx` |
| P2.9 | Co-located test `app/src/app/highspeed-qa.test.ts` — classification badge color mapping from mock response; "Start Challenge" renders intro text; results summary renders | TODO | | `make poc-app-test` green (new test cases counted) |
| P2.10 | `make poc-app-test` green after all P2 | TODO | | `make poc-app-test` → lint + typecheck + jest all pass |

---

## P3 — End-to-end verify

*Checkpoint:* 5 rapid-fire questions answered (typed), results show speed/clarity classification for each.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | Backend E2E: `POST /highspeed-questions/great-manager/analyze` with a fast, filler-free answer → classification "Fast + Clear"; with a slow answer → "Clear but Slow" | TODO | | `curl -s -X POST http://localhost:8090/highspeed-questions/great-manager/analyze -H 'Content-Type: application/json' -d '{"text":"Vision clarity and empathy matter most in a great manager"}' \| python3 -c "import sys,json;d=json.load(sys.stdin);assert d['classification'] in ['Fast + Clear','Clear but Slow','Fast but Chaotic','Needs Work']"` |
| P3.2 | Full `make poc-api-test` + `make poc-app-test` green | TODO | | `make poc-api-test && make poc-app-test` |
| P3.3 | Update `docs/plans/poc-implementation-progress.md` to mark POC 14 `DONE` | TODO | | `grep "POC 14\|poc-14" docs/plans/poc-implementation-progress.md` |

---

## Decisions & notes

- **Text-first scoring.** The `estimated_wpm` is computed assuming the user took the full `timer_seconds` to produce the answer. This is an approximation — a typed answer produced in 5 seconds of a 20-second timer would artificially lower the WPM estimate. For the POC demo, this is acceptable. The audio path would use real transcript timing and yields accurate WPM.
- **CountdownTimer reuse.** `app/src/ui/CountdownTimer.tsx` was introduced in POC 08. If it does not exist on the base branch at the time of implementation, create a minimal version: a `useEffect` + `setInterval` countdown hook, rendering the seconds remaining as a large number.
- **No new MongoDB collection.** Questions served from a static JSON file at startup. No upsert/schema required.
- **`recovery_score` is hardcoded 0.8 for the typed path.** Real pause-detection requires audio. The value is neutral (not 0, not 1) so it has a meaningful presence in `overall_score` without penalizing text-only answers.
- **Goal Signature `"highspeed"` occasion.** Adding this occasion ensures users who pick "highspeed" get capability weights that emphasize `fluency` (pace, filler reduction) over `content`. This does not change existing Mode A/B scoring or goldens — `goal_signature.py` only changes the weights returned for the new occasion key.
- **Classification quad.** The four cells (Fast+Clear, Fast+Chaotic, Clear+Slow, Needs Work) map directly to the rhetorical tradeoff space: speed without clarity is chaotic; clarity without speed is hesitant; both present is the goal. This makes the feedback memorable and actionable.
- **Existing golden fixtures stay byte-identical.** `highspeed.py` is a new module; `goal_signature.py` change only adds a new key, not modifies existing weights.
