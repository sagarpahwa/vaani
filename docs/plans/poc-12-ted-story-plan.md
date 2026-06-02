# POC 12 — TED Storytelling Arc Coach — Implementation Plan & Progress Tracker

> **This file is the committed, resumable source of truth for POC 12.**
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
   `feat/poc-12-ted-story`, conventional commit) → next row. Never batch multiple sub-tasks
   into one commit.
4. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but **this committed
   file is authoritative** — reconcile against it, not against memory.

**Status legend:** `TODO` (not started) · `DOING` (in flight, not committed) · `DONE` (committed; SHA recorded) · `DEFERRED` (committed decision to skip; blocker recorded).

---

## Key constraints (do not violate — full detail in CLAUDE.md)

- **Base branch:** `feat/poc-11-debate`. New branch: `feat/poc-12-ted-story` (branch off base, never commit to base).
- **No LLM.** All scoring is deterministic marker/heuristic logic in Python. No cloud credentials required.
- **Additive, zero regression.** Existing Mode A/B/persona paths and their golden fixtures stay byte-for-byte identical. `make poc-api-test` must pass with the same golden values after every commit.
- **Python env:** `.venv-poc` only (via `make poc-api-install`). Never `.venv` / `.venv311`.
- **DB isolation.** Mock DB only: container `vaani_poc_mongo`, port **27018**, database `public_speaking_intelligence_mock`. Never touch port 27017 or the real DB.
- **POC schemas isolated.** New schema → `services/api/db/schemas/` (NOT shared `schemas/`).
- **Audio never in Mongo.** ObjectStore abstraction only.
- **Keep green:** `make poc-api-lint && make poc-api-test` (coverage ≥70%) and `make poc-app-test` after every commit.
- **Git identity:** conventional commits; never `git add -A`; never force-push without explicit request.

---

## P0 — Docs & resumability scaffold

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | This plan/tracker file → `docs/plans/poc-12-ted-story-plan.md` | TODO | | `test -f docs/plans/poc-12-ted-story-plan.md` |
| P0.2 | Link this milestone in `docs/plans/poc-implementation-progress.md` (add POC 12 row to Milestone Status table) | TODO | | `grep "poc-12" docs/plans/poc-implementation-progress.md` |

---

## P1 — Backend domain: storytelling arc scorer

*Checkpoint:* `from services.api.domain.storytelling import score_story` works; 8+ unit tests green.

The scorer is **pure Python** — no DB, no audio, no LLM. It receives the full story text and returns a dict with arc component flags, sub-scores, and improvement suggestions. All markers are word/phrase lists applied via case-insensitive substring/regex matching.

**Arc components and markers:**
- `hook_score` — question openers (`"?"`-terminated first sentence), surprising-fact openers (`"did you know"`, `"here's the thing"`, `"what if i told you"`), narrative openers (`"there was a time"`, `"i remember when"`, `"it all started"`, `"years ago"`)
- `scene_score` — location/time anchors: `"it was"`, `"in 20\d\d"`, `"at the time"`, `"back in"`, `"the place"`, `"i was standing"`, `"i was sitting"`, `"i found myself"`
- `conflict_score` — tension words: `"but then"`, `"suddenly"`, `"the problem was"`, `"i struggled"`, `"i failed"`, `"everything changed"`, `"hit a wall"`, `"realised i was wrong"`
- `insight_score` — reflection words: `"i realized"`, `"i learnt"`, `"that taught me"`, `"what i learned"`, `"it hit me"`, `"i understood"`, `"it dawned on me"`
- `lesson_score` — universal takeaway: `"and that is why"`, `"the point is"`, `"what this means for you"`, `"the lesson"`, `"take away"`, `"the truth is"`, `"what i want you to know"`
- `specificity_score` — (proper_noun_count × 0.4 + number_count × 0.6) / max(word_count / 50, 1); capped at 1.0. Proper nouns: title-cased words not at sentence start. Numbers: digit sequences.
- `pacing_score` — sentence-length coefficient of variation (CV = stdev/mean); CV > 0.4 = good pacing (varied), CV < 0.15 = monotone pacing; linearly interpolated between.
- `ending_quality` — bool: last two sentences contain any insight or lesson marker.
- `stronger_opening` — if `hook_score == 0`: template suggestion based on first sentence topic; else `None`.
- `stronger_closing` — if `ending_quality == False`: template suggestion; else `None`.
- `arc_components_found` — list of which of the 5 components are present.
- `overall_score` — weighted mean: hook 0.25, scene 0.15, conflict 0.20, insight 0.20, lesson 0.10, specificity 0.05, pacing 0.05.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | `services/api/domain/storytelling.py` — `score_story(text: str) -> dict` implementing all arc/specificity/pacing markers above, `stronger_opening`, `stronger_closing`, `arc_components_found`, `overall_score` | TODO | | `python3 -c "from services.api.domain.storytelling import score_story; r=score_story('There was a time I failed. But then I realized the lesson.'); assert 'overall_score' in r"` |
| P1.2 | `services/api/tests/test_storytelling.py` — 8+ unit test cases: hook present/absent; scene detected; conflict detected; insight detected; lesson detected; high vs low specificity; pacing varied vs monotone; ending_quality True/False; stronger_opening/closing suggestions | TODO | | `pytest services/api/tests/test_storytelling.py -v` → 8+ passed |
| P1.3 | `make poc-api-lint && make poc-api-test` green after P1.1–P1.2 | TODO | | `make poc-api-lint && make poc-api-test` → 0 errors, coverage ≥70% |

---

## P2 — Backend API: storytelling routes + seed data

*Checkpoint:* `GET /storytelling-prompts` returns 5 prompts; `POST /storytelling-prompts/{id}/analyze` returns arc scores.

**Seed data — `services/api/db/seed_data/storytelling_prompts.json` (5 prompts):**
```
[
  { "prompt_id": "failure-lesson", "title": "A time you failed and what you learned",
    "description": "...", "timer_seconds": 60 },
  { "prompt_id": "world-view-change", "title": "A moment that changed how you see the world",
    "description": "...", "timer_seconds": 60 },
  { "prompt_id": "person-shaped-you", "title": "A person who shaped who you are",
    "description": "...", "timer_seconds": 60 },
  { "prompt_id": "challenge-stronger", "title": "A challenge that made you stronger",
    "description": "...", "timer_seconds": 60 },
  { "prompt_id": "decided-to-change", "title": "The moment you decided to change direction",
    "description": "...", "timer_seconds": 60 }
]
```

The `analyze` endpoint accepts `{ "text": "..." }` (typed story text) or `{ "audio_key": "..." }` (if the client uploaded audio and received a transcribed text from a prior STT call — use the existing `ObjectStore` + `MockSTT` path to get text). For the POC, the plain text path is the primary; audio path is additive.

Pydantic models:
- `StoryPrompt` — `prompt_id`, `title`, `description`, `timer_seconds`
- `StoryAnalysisRequest` — `text: str` (required), `prompt_id: str | None`
- `StoryAnalysisResponse` — `prompt_id`, `hook_score`, `scene_score`, `conflict_score`, `insight_score`, `lesson_score`, `specificity_score`, `pacing_score`, `ending_quality`, `arc_components_found`, `overall_score`, `stronger_opening`, `stronger_closing`

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | `services/api/db/seed_data/storytelling_prompts.json` — 5 prompts with fields above | TODO | | `python3 -c "import json; d=json.load(open('services/api/db/seed_data/storytelling_prompts.json')); assert len(d)==5"` |
| P2.2 | `services/api/routes/storytelling.py` — `GET /storytelling-prompts` (returns list of `StoryPrompt`), `POST /storytelling-prompts/{id}/analyze` (validates prompt_id exists, calls `score_story`, returns `StoryAnalysisResponse`) | TODO | | `curl -s http://localhost:8090/storytelling-prompts \| python3 -c "import sys,json;d=json.load(sys.stdin);assert len(d)==5"` |
| P2.3 | Register storytelling router in `services/api/app.py` | TODO | | `grep storytelling services/api/app.py` |
| P2.4 | Add `StoryPrompt`, `StoryAnalysisRequest`, `StoryAnalysisResponse` to `services/api/models.py` | TODO | | `python3 -c "from services.api.models import StoryAnalysisResponse"` |
| P2.5 | `services/api/tests/test_api_storytelling.py` — 4+ API tests: list prompts (5 items), analyze valid text (arc fields present, overall_score in [0,1]), analyze with invalid prompt_id (404), analyze empty text (valid response, zero scores) | TODO | | `pytest services/api/tests/test_api_storytelling.py -v` → 4+ passed |
| P2.6 | `make poc-api-lint && make poc-api-test` green after P2 | TODO | | `make poc-api-lint && make poc-api-test` → 0 errors, coverage ≥70% |

---

## P3 — Frontend: `ted-story.tsx` screen

*Checkpoint:* browser shows a story prompt, allows text entry (or 60s timer notation), submits, shows 5 arc component results + scores + suggestions.

**Screen layout:**
1. Header: "TED Storytelling Arc" + back arrow.
2. Prompt card: title + description in a highlighted box. Timer badge "60 seconds".
3. Input area: large multiline `TextInput` ("Type or paste your story here…") — primary path for the POC. Below it: small note "or record a 60-second story" (future).
4. Submit button: "Analyse My Story" (disabled if text < 20 chars).
5. Results section (shown after submit):
   - 5 arc component chips: HOOK ✓/✗, SCENE ✓/✗, CONFLICT ✓/✗, INSIGHT ✓/✗, LESSON ✓/✗ — green fill if found, grey if missing.
   - Sub-score rows: Specificity, Pacing (each with a thin bar).
   - Ending Quality: "Strong ending ✓" or "Ending could be stronger".
   - Overall score badge (large number, e.g. "72%").
   - Suggestions section (only if `stronger_opening` or `stronger_closing` non-null): "Try a stronger opening: …" and/or "Try a stronger closing: …".

**Route integration:**
- Register `ted-story` in `app/src/app/_layout.tsx`.
- Add a home card on `index.tsx`: "TED Story Arc" with a brief subtitle "Tell a 1-minute story, get arc feedback".

**API wiring:**
- Add `listStoryPrompts()` and `analyzeStory(promptId, text)` to `app/src/api/client.ts`.
- Add `StoryPrompt`, `StoryAnalysisResponse` to `app/src/api/types.ts`.

**Component test strategy:**
- `ted-story.test.tsx` (or `ted-story.test.ts` for logic helpers): test that submit is disabled on short text, enabled on sufficient text; test that arc chips render correctly from a mock API response.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | Add `StoryPrompt`, `StoryAnalysisResponse` to `app/src/api/types.ts` | TODO | | `grep StoryAnalysisResponse app/src/api/types.ts` |
| P3.2 | Add `listStoryPrompts()`, `analyzeStory(promptId, text)` to `app/src/api/client.ts` + tests in `client.test.ts` | TODO | | `make poc-app-test` green; client test covers both new methods |
| P3.3 | `app/src/app/ted-story.tsx` — prompt display, text input, submit, results section with arc chips/scores/suggestions | TODO | | `grep "ted-story" app/src/app/_layout.tsx` (route registered); screen file exists |
| P3.4 | Register `/ted-story` route in `app/src/app/_layout.tsx` (Stack.Screen title "TED Story Arc") | TODO | | `grep "ted-story" app/src/app/_layout.tsx` |
| P3.5 | Add "TED Story Arc" home card to `app/src/app/index.tsx` → navigates to `/ted-story` | TODO | | `grep "ted-story" app/src/app/index.tsx` |
| P3.6 | Co-located test `app/src/app/ted-story.test.ts` (or `.tsx`) — submit disabled on short text, arc chip rendering from mock response | TODO | | `make poc-app-test` green (new test cases counted) |
| P3.7 | `make poc-app-test` green after all P3 | TODO | | `make poc-app-test` → lint + typecheck + jest all pass |

---

## P4 — End-to-end verify

*Checkpoint:* story text submitted via browser (or direct API call) → arc component scores returned → frontend renders results correctly.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P4.1 | Backend E2E: `POST /storytelling-prompts/failure-lesson/analyze` with a sample story text containing hook/conflict/insight → response has `hook_score > 0`, `conflict_score > 0`, `insight_score > 0`, `overall_score` in (0,1] | TODO | | `curl -s -X POST http://localhost:8090/storytelling-prompts/failure-lesson/analyze -H 'Content-Type: application/json' -d '{"text":"There was a time I failed badly. But then I realized what mattered."}' \| python3 -c "import sys,json;d=json.load(sys.stdin);assert d['overall_score']>0"` |
| P4.2 | Full `make poc-api-test` + `make poc-app-test` green | TODO | | `make poc-api-test && make poc-app-test` |
| P4.3 | Update `docs/plans/poc-implementation-progress.md` to mark POC 12 `DONE` | TODO | | `grep "POC 12\|poc-12" docs/plans/poc-implementation-progress.md` |

---

## Decisions & notes

- **Text-first, audio-additive.** The POC primary path is typed text. Audio → STT → analysis is wired but not the demo path, keeping the POC verifiable without a microphone.
- **No new MongoDB collection.** Storytelling prompts are served from a static JSON file loaded at startup (no upsert, no schema needed). This avoids a DB schema PR blocker while keeping the POC lightweight. If prompts need user-specific history, add a `storytelling_sessions` collection in a future iteration.
- **Arc markers are keyword/phrase heuristics.** No NLP library required — `str.lower()` + substring matching covers 95% of natural-language stories for this POC fidelity level.
- **Specificity uses title-casing heuristic** (not NER). Sufficient for demo; a real NER pass is an Iteration 2 upgrade.
- **Pacing uses sentence-length CV.** Sentence splitting is on `[.!?]` boundaries. Edge cases (abbreviations, ellipsis) are acceptable for the POC.
- **Existing Mode A/B/persona goldens must stay byte-identical.** `storytelling.py` is a new module with no imports from `domain/pipeline.py` or `domain/persona.py`, so there is zero risk of golden drift.
