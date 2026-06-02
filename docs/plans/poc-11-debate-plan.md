# POC 11 — Debate Under Pressure — Implementation Plan

> **This file is the committed, resumable source of truth for POC 11.**
> It is authoritative across sessions — not in-session memory, not the TaskList.

---

## HOW TO RESUME (agent: read this block FIRST, every run)

1. **Read this whole file** — find the **first sub-task whose status is not `DONE`** in the
   tables below. That is where you resume.
2. **Re-verify the last `DONE` row actually landed** before continuing (run its *Verify*
   command / confirm the file exists). A session can die between writing code and committing,
   so the last row marked `DONE` might not be on disk. If it didn't land, redo **only** that
   one step. **Never redo work already `DONE` and verified.**
3. Work **one atomic sub-task at a time**: do it → run its *Verify* → set status `DONE` +
   record the commit SHA → **`git commit` the code and this tracker together** (branch
   `feat/poc-11-debate`, conventional commit) → next row. Never batch multiple sub-tasks
   into one commit.
4. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but **this committed
   file is authoritative**.

**Base branch:** `feat/poc-10-investor-pitch`
**Working branch:** `feat/poc-11-debate`

**Status legend:** `TODO` · `DOING` · `DONE` (SHA recorded) · `DEFERRED` (blocker recorded)

---

## KEY CONSTRAINTS

- **Hard DB isolation:** POC only — container `vaani_poc_mongo`, port **27018**, DB
  `public_speaking_intelligence_mock`. Never touch the real DB / port 27017.
- **Python env:** `.venv-poc` only. Never `.venv` / `.venv311`.
- **New dedicated endpoints, not a session.** `GET /debate-topics` and
  `POST /debate-topics/{id}/analyze` are standalone analyze-on-demand routes.
  The existing `POST /sessions` coaching pipeline is not involved.
- **No LLM required.** All argument-quality dimensions are keyword/phrase-pattern based.
  The "stronger version" is a deterministic template, not generated text.
- **Additive, zero regression.** Existing Mode A/B/persona pipelines, golden fixtures, and
  the feedback_coach and pitch_drill routes are completely untouched.
- **Keep green:** `make poc-api-lint && make poc-api-test` (coverage ≥70%) and
  `make poc-app-test` after every sub-task commit.
- **POC schemas isolated:** any new schema in `services/api/db/schemas/` only.
- **Input is text + optional audio.** The user types a response or records voice (transcribed
  by MockSTT). Audio path is a convenience affordance, not the primary UX for this POC.
- **Git identity:** conventional commits; never `git add -A`.

---

## What to build

The app presents a provocative opposing statement (e.g. "Remote work has made teams less
productive"). The user records or types a rebuttal. The app scores the argument on five
dimensions and applies two penalty flags:

**Positive dimensions:**
1. **Steelmanning** — did the user acknowledge the opponent's strongest point before
   countering? ("you have a point", "I understand why", "fair concern", "valid")
2. **Principle** — did the user state a core principle or value underlying their position?
   ("because", "in principle", "fundamentally", "at its core")
3. **Evidence** — did the user cite data, research, or concrete examples?
   (numbers, "research shows", "data suggests", "studies", "according to", "evidence")
4. **Tradeoffs** — did the user acknowledge the other side's costs or limitations?
   ("however", "tradeoff", "at the cost", "the downside", "caveat", "but")
5. **Conclusion** — did the user close with a clear synthesis?
   ("in conclusion", "therefore", "which means", "ultimately", "my point is")

**Penalty flags (subtract from overall score when triggered):**
- **Personal attack** — attacks the person, not the idea
  ("you're wrong", "absurd", "ridiculous", "that's stupid", "you clearly")
- **Defensive language** — signals emotional reactivity rather than reasoned response
  ("how dare", "that's unfair", "you have no right", "that offends")

The result shows: 5 dimension scores (present/absent), penalty flags, overall argument score,
and a "stronger version" rewrite.

### Architecture

- `services/api/domain/debate.py` — pure domain module: marker lists for 5 dimensions +
  2 penalty flags, `DebateScores` dataclass, `score_debate_response(text, topic_id)`.
- `services/api/db/seed_data/debate_topics.json` — 5 provocative topic statements.
- `services/api/routes/debate.py` — `GET /debate-topics` + `POST /debate-topics/{id}/analyze`.
- `app/src/app/debate.tsx` — screen showing the provocative statement, response input
  (text + optional mic), submit, result cards.

---

## P0 — Docs + branch scaffold

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | This plan file → `docs/plans/poc-11-debate-plan.md` | TODO | | `test -f docs/plans/poc-11-debate-plan.md` |
| P0.2 | Progress tracker → `docs/plans/poc-11-debate-progress.md` (all TODO) | TODO | | `test -f docs/plans/poc-11-debate-progress.md` |
| P0.3 | Link milestone from `docs/plans/poc-implementation-progress.md` | TODO | | `grep poc-11 docs/plans/poc-implementation-progress.md` |

---

## P1 — Backend domain: argument quality scorer + penalty flags

*Checkpoint:* `score_debate_response(text, topic_id)` returns correct dimension booleans,
penalty flags, and an overall score; 10+ unit tests pass.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | Create `services/api/domain/debate.py` — define `DebateScores` dataclass (fields: `steelman_present`, `principle_present`, `evidence_present`, `tradeoff_present`, `conclusion_present`, `personal_attack_flag`, `defensive_flag`, `dimension_count: int`, `penalty_count: int`, `overall_score: float`, `stronger_version: str`) | TODO | | `python3 -c "from services.api.domain.debate import DebateScores"` |
| P1.2 | Implement dimension marker lists in `debate.py`: `STEELMAN_MARKERS` (`"you have a point"`, `"i understand why"`, `"fair concern"`, `"valid point"`, `"i see where"`, `"to be fair"`), `PRINCIPLE_MARKERS` (`"because"`, `"in principle"`, `"fundamentally"`, `"at its core"`, `"the reason is"`), `EVIDENCE_MARKERS` (numeric pattern `\d+%|\d+x|[\$£€]\d+` plus `"research shows"`, `"data suggests"`, `"studies"`, `"according to"`, `"evidence"`, `"statistic"`), `TRADEOFF_MARKERS` (`"however"`, `"tradeoff"`, `"at the cost"`, `"the downside"`, `"caveat"`, `"but"`, `"yet"`, `"though"`), `CONCLUSION_MARKERS` (`"in conclusion"`, `"therefore"`, `"which means"`, `"ultimately"`, `"my point is"`, `"so"` at sentence start) | TODO | | `grep STEELMAN_MARKERS services/api/domain/debate.py` |
| P1.3 | Implement penalty marker lists in `debate.py`: `PERSONAL_ATTACK_MARKERS` (`"you're wrong"`, `"you are wrong"`, `"absurd"`, `"ridiculous"`, `"that's stupid"`, `"you clearly"`, `"obviously you"`, `"ignorant"`), `DEFENSIVE_MARKERS` (`"how dare"`, `"that's unfair"`, `"you have no right"`, `"that offends"`, `"how could you"`, `"i can't believe you`) | TODO | | `grep PERSONAL_ATTACK_MARKERS services/api/domain/debate.py` |
| P1.4 | Implement `score_debate_response(text: str, topic_id: str) -> DebateScores` — lowercase text; detect each of 5 dimensions and 2 penalties; `dimension_count = sum of present dims`; `penalty_count = sum of triggered penalties`; `overall_score = max(0.0, round((dimension_count / 5 - penalty_count * 0.2) * 100, 1))`; `stronger_version` = template assembled from topic_id lookup + dimension-targeted coaching prompts for absent dimensions | TODO | | `python3 -c "from services.api.domain.debate import score_debate_response; r=score_debate_response('you have a point but research shows 30% improvement therefore', 't1'); print(r.dimension_count)"` |
| P1.5 | Unit tests `services/api/tests/test_debate.py` — 10+ cases: (a) all 5 dims present, no penalties → `dimension_count==5`, `overall_score==100`; (b) steelman present; (c) evidence numeric pattern detected; (d) personal attack → `personal_attack_flag==True`, score reduced; (e) defensive language → `defensive_flag==True`, score reduced; (f) both penalties → score floor 0.0; (g) empty text → 0 dims, 0 penalties; (h) `stronger_version` is non-empty string; (i) conclusion marker at sentence start detected; (j) tradeoff marker detected | TODO | | `pytest services/api/tests/test_debate.py` → ≥10 passed |
| P1.6 | `make poc-api-lint && make poc-api-test` green | TODO | | `make poc-api-lint && make poc-api-test` |

---

## P2 — Backend API: debate topics seed + routes

*Checkpoint:* `GET /debate-topics` returns 5 topics;
`POST /debate-topics/remote-work/analyze` with a steelmanned response returns
`steelman_present==true` and a non-zero `overall_score`.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | Create `services/api/db/seed_data/debate_topics.json` — 5 topics: (a) `remote-work` ("Remote work has made teams less productive."), (b) `ai-developers` ("AI will make most developers obsolete within 5 years."), (c) `startup-profitability` ("Startups should not focus on profitability in their first 3 years."), (d) `social-media-harm` ("Social media does more harm than good to society."), (e) `degree-value` ("A university degree is no longer worth the cost."); each has `topic_id`, `statement`, `context` (2-sentence background), `opposing_argument` (the steelmannable version of the claim) | TODO | | `python3 -c "import json; d=json.load(open('services/api/db/seed_data/debate_topics.json')); assert len(d)==5"` |
| P2.2 | Create `services/api/routes/debate.py` — `GET /debate-topics` returns list of `DebateTopicSummary` (topic_id, statement, context); `POST /debate-topics/{topic_id}/analyze` accepts `DebateAnalyzeRequest(response_text: Optional[str], audio_base64: Optional[str])`; resolves text (direct or via MockSTT); calls `score_debate_response`; returns `DebateScores` dict; 404 on unknown `topic_id`; 422 if both fields absent | TODO | | `grep "debate-topics" services/api/routes/debate.py` |
| P2.3 | Register `debate` router in `services/api/app.py` with prefix `/debate-topics` | TODO | | `grep debate services/api/app.py` |
| P2.4 | API tests `services/api/tests/test_api_debate.py` — (a) `GET /debate-topics` → 200, list length 5; (b) POST with steelman + evidence + conclusion → 3 dims present; (c) POST with personal attack phrase → `personal_attack_flag==True`; (d) POST empty text → `dimension_count==0`; (e) POST unknown topic_id → 404; (f) POST neither field → 422; (g) `overall_score` field present in response and ≥ 0 | TODO | | `pytest services/api/tests/test_api_debate.py` → ≥7 passed |
| P2.5 | `make poc-api-lint && make poc-api-test` green (coverage ≥70%) | TODO | | `make poc-api-lint && make poc-api-test` |

---

## P3 — Frontend: debate screen + route + home card

*Checkpoint:* Home → "Debate Under Pressure" → provocative statement shown → user responds
→ submit → 5 dimension scores + penalty flags + stronger version displayed.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | Add `DebateTopicSummary`, `DebateScores`, `DebateAnalyzeRequest`, `listDebateTopics`, `analyzeDebate` to `app/src/api/types.ts` and `app/src/api/client.ts` | TODO | | `make poc-app-test` green (typecheck) |
| P3.2 | Create `app/src/app/debate.tsx` — on mount: `listDebateTopics()` → pick a random topic (rotate for demo); show `statement` text in a prominent card; show `context` in smaller text; text response input (`TextInput multiline`) + optional mic button using `useRecorder` (audio_base64 path); "Submit Response" button (disabled when empty); loading state while analyzing | TODO | | `make poc-app-test` green (typecheck + lint) |
| P3.3 | Results section in `debate.tsx`: 5 dimension `Card` components (label + ✓/✗); two penalty `Card` components in a distinct colour (theme `error` token) showing whether each penalty was triggered; overall argument score as a numeric display; "Stronger Version" collapsible card showing `stronger_version` text | TODO | | `make poc-app-test` green |
| P3.4 | Register `/debate` route in `app/src/app/_layout.tsx` with title "Debate Under Pressure" | TODO | | `grep debate app/src/app/_layout.tsx` |
| P3.5 | Add "Debate Under Pressure" card to `app/src/app/index.tsx` home — badge "5 DIMENSIONS · STEELMANNING", links to `/debate` | TODO | | `make poc-app-test` green |
| P3.6 | `make poc-app-test` fully green (lint + typecheck + all jest) | TODO | | `make poc-app-test` |

---

## P4 — E2E verify

*Checkpoint:* end-to-end flow works; both test suites green.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P4.1 | Backend smoke: `GET /debate-topics` → 200, 5 topics; `POST /debate-topics/remote-work/analyze` with a steelmanning, evidence-backed response → `steelman_present==true`, `evidence_present==true`, `overall_score > 0` | TODO | | curl or `pytest -k debate -m integration` |
| P4.2 | Backend smoke: response with personal attack → `personal_attack_flag==true`, score penalised vs clean version | TODO | | curl or pytest |
| P4.3 | `make poc-api-test` fully green (no regressions) | TODO | | `make poc-api-test` |
| P4.4 | `make poc-app-test` fully green | TODO | | `make poc-app-test` |
| P4.5 | Manual / Claude Preview: Home → "Debate Under Pressure" → provocative statement shown → type a weak response → submit → multiple ✗ dims + score shown → try again with steelman + evidence → more ✓ and higher score | TODO | | visual confirmation |

---

## Decisions & notes

- **No `practice_sessions` involvement.** The debate drill is stateless. No retry, no
  per-line breakdown. If debate history / progress is needed post-POC, add a
  `debate_results` collection then.
- **Steelmanning is the key differentiator.** Most coaching apps score argument structure
  (claim → evidence → conclusion). The steelmanning dimension is rarer and educationally
  more valuable — it teaches the user to acknowledge the strongest version of the opposing
  view before countering, which is the hallmark of high-quality discourse.
- **Penalty score reduction: 0.2 per penalty.** A single personal attack knocks 20 points
  off regardless of how many positive dimensions were hit. This reflects the disproportionate
  harm a single attack does to the credibility of an argument. The floor is 0.0.
- **"But" as a tradeoff marker.** The word "but" alone is a weak signal, but it is
  extremely common as a tradeoff introducer. It is included in `TRADEOFF_MARKERS` but
  only contributes if no stronger tradeoff marker is detected first. (Implementation note:
  the simple presence-based scan counts it; a follow-on post-POC improvement would require
  stronger signals before crediting "but".)
- **5 debate topics.** The seed covers tech (AI/developers), work (remote work), business
  (startup profitability), society (social media), and education (degree value). Topics can
  be rotated or added without backend changes.
- **Stronger version is a template.** For each absent dimension, the route appends a
  coaching sentence: e.g. "To strengthen this, acknowledge the opposing view first"
  (steelman missing), "Cite a specific study or statistic" (evidence missing). Post-POC:
  generate a coherent rewrite using an LLM prompt with the detected fragments as context.
- **Topic rotation in frontend.** The debate screen picks a random topic from the list on
  each mount. The user can't select a topic in the POC. Topic selection is post-POC.
- **Audio path uses MockSTT in POC.** When `audio_base64` is provided, the route calls
  `MockSTT.transcribe`. Real Whisper (`PROVIDER_STT=whisper`) works end-to-end but is
  out of scope for automated tests.
