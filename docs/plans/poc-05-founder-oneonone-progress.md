# POC 05 — Founder / CEO One-on-One Rehearsal — Implementation Progress Tracker

> **This file is the committed, resumable source of truth for POC 05.**
> It is authoritative across sessions — not in-session memory, not the TaskList.

---

## HOW TO RESUME (agent: read this block FIRST, every run)

You were told: *"implement this plan"* (pointing at this file or at
[`poc-05-founder-oneonone-plan.md`](poc-05-founder-oneonone-plan.md)). Do exactly this:

1. **Read the plan:** [`docs/plans/poc-05-founder-oneonone-plan.md`](poc-05-founder-oneonone-plan.md)
   — the full approved design (Parts A–D, acceptance criteria). This tracker is its checklist.
2. **Read this whole file** — find the **first sub-task whose status is not `DONE`** in the
   tables below. That is where you resume.
3. **Re-verify the last `DONE` row actually landed** before continuing (run its *Verify* command /
   confirm the file exists). A session can die between writing code and committing, so the last row
   marked `DONE` might not be on disk. If it didn't land, redo **only** that one step.
   **Never redo work already `DONE` and verified.**
4. Work **one atomic sub-task at a time**: do it → run its *Verify* → set status `DONE` +
   record the commit SHA → **`git commit` the code and this tracker together** (branch
   `feat/poc-05-founder-oneonone`, conventional commit) → next row. Never batch multiple
   sub-tasks into one commit.
5. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but **this committed
   file is authoritative** — reconcile against it, not against memory.

**Status legend:** `TODO` (not started) · `DOING` (in flight, not committed) · `DONE` (committed; SHA recorded) · `DEFERRED` (committed decision to skip; blocker recorded).

---

## Key constraints (do not violate — full detail in the plan & CLAUDE.md)

- **Base branch:** `feat/poc-04-difficult-conv`. Branch: `feat/poc-05-founder-oneonone`.
- **Zero new infrastructure.** Entire conversation engine (routes, domain, DB schemas, frontend
  screens) from POC 04 is reused unchanged. New artifacts: one scenario JSON entry, one intake
  screen, one home card.
- **Deterministic mock.** 5 fixed questions, word-count + specificity branching, no LLM.
- **Hard DB isolation.** Mock DB only: container `vaani_poc_mongo`, port **27018**, database
  `public_speaking_intelligence_mock`. Never touch the real DB / 27017.
- **Python env:** `.venv-poc` only (via `make poc-api-install`). Never `.venv` / `.venv311`.
- **Keep green:** `make poc-api-lint && make poc-api-test` (coverage ≥70%) and `make poc-app-test`.
- **Git identity:** branch `feat/poc-05-founder-oneonone`; conventional commits; never `git add -A`,
  never force-push / `reset --hard` without explicit ask.

---

## P0 — Docs & resumability scaffold

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | In-repo copy of full plan → [`poc-05-founder-oneonone-plan.md`](poc-05-founder-oneonone-plan.md) | TODO | | `test -f docs/plans/poc-05-founder-oneonone-plan.md` |
| P0.2 | This resumable tracker → `poc-05-founder-oneonone-progress.md` | TODO | | `test -f docs/plans/poc-05-founder-oneonone-progress.md` |
| P0.3 | Link this milestone from [`poc-implementation-progress.md`](poc-implementation-progress.md) | TODO | | `grep "poc-05" docs/plans/poc-implementation-progress.md` |

---

## P1 — Backend: scenario seed data + scoring markers

*Checkpoint:* `GET /conversations/scenarios` returns the `founder_ceo_oneonone` scenario with 5
fixed questions and a 6-dimension rubric.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | Add `founder_ceo_oneonone` entry to `services/api/db/seed_data/conversation_scenarios.json` — `scenario_id`, `title`, `brief`, `persona_role`, `user_role`, `opening_message`, `fixed_questions` (5), `branching_rules` (concise_threshold=60, long_threshold=120, vague_markers, follow_up_messages), `rubric` (6 dimensions × weight), `rubric_markers` (positive + negative keyword lists per dimension) | TODO | | `python3 -c "import json; d=json.load(open('services/api/db/seed_data/conversation_scenarios.json')); s=[x for x in d if x['scenario_id']=='founder_ceo_oneonone']; assert len(s)==1 and len(s[0]['fixed_questions'])==5"` |
| P1.2 | Verify `score_conversation()` in `domain/conversation.py` already reads `rubric_markers` per-scenario — no domain changes needed; if missing, add the marker-lookup (minimal, additive) | TODO | | `grep rubric_markers services/api/domain/conversation.py` |
| P1.3 | Verify seeder in `seed_mock.py` already upserts all entries in `conversation_scenarios.json` — no seeder change needed; if missing, add upsert | TODO | | `grep conversation_scenarios services/api/db/seed_mock.py` |
| P1.4 | Backend unit tests — scenario loads and scores correctly (6 test cases: all-6-dimensions present, branching vague trigger, branching long trigger, branching concise advance, 3 rephrasings in review, 404 on unknown scenario) | TODO | | `pytest services/api/tests/ -k founder` |

---

## P2 — Frontend: intake screen + home card

*Checkpoint:* User can tap the home card, fill the form, and land on the conversation screen.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | `app/src/api/client.ts` — confirm `createConversation(payload)` method exists from POC 04; if not, add it (calls `POST /conversations`, returns `{ conversationId: string }`) | TODO | | `grep createConversation app/src/api/client.ts` |
| P2.2 | `app/src/api/types.ts` — confirm `ConversationScenario`, `ConversationTurn`, `ConversationReview` types exist from POC 04; add any missing fields (`custom_context` on request payload) | TODO | | `grep ConversationScenario app/src/api/types.ts` |
| P2.3 | `app/src/app/founder-setup.tsx` — intake form screen (4 fields: `meeting_agenda`, `user_role`, `desired_outcome`, `company_context`); Submit disabled until 3 required fields filled; on submit calls `createConversation`; navigates to `/conversation?conversationId={id}`; loading state + error banner | TODO | | `test -f app/src/app/founder-setup.tsx` |
| P2.4 | Register `/founder-setup` route in `app/src/app/_layout.tsx` — `Stack.Screen title="Founder / CEO One-on-One"` | TODO | | `grep founder-setup app/src/app/_layout.tsx` |
| P2.5 | Add home card in `app/src/app/index.tsx` — title "Founder / CEO One-on-One", badge "STRATEGY", subtitle about 5 hard questions, CTA → `/founder-setup` | TODO | | `grep founder-setup app/src/app/index.tsx` |
| P2.6 | Co-located tests: `app/src/app/founder-setup.test.tsx` — renders form; Submit disabled until required fields filled; calls `createConversation` with correct payload; navigates on success; shows banner on error (5+ jest cases) | TODO | | `make poc-app-test` |

---

## P3 — E2E verify

*Checkpoint:* Full click-through from home → intake → 5 questions → review with 6 capability scores.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | Start backend (`make poc-api-run`) and web app (`make poc-app-web`); navigate home → "Founder / CEO One-on-One" card → intake form | TODO | | Browser shows founder-setup screen with 4 fields |
| P3.2 | Fill form (sample agenda, PM role, desired outcome) → Submit → conversation screen opens with founder opening "You have ten minutes. What do you need?" | TODO | | Conversation screen shows founder opening message |
| P3.3 | Complete 5 turns (type responses) — verify founder follows fixed question order and applies at least one branching follow-up on a vague answer | TODO | | Conversation shows 5 founder questions + any branch follow-ups |
| P3.4 | After turn 5, navigate to review — verify all 6 capability score cards (strategic_clarity, business_impact, conciseness, handling_challenge, executive_presence, strong_ask) and 3 better phrasings | TODO | | Review screen shows 6 dimensions + 3 phrasings |

---

## P4 — Tests polish & CI green

*Checkpoint:* Both test suites green with no coverage regression.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P4.1 | `make poc-api-lint` clean (ruff + black) | TODO | | `make poc-api-lint` exits 0 |
| P4.2 | `make poc-api-test` green — all new scenario + scoring tests pass; coverage ≥70% | TODO | | `make poc-api-test` exits 0 |
| P4.3 | `make poc-app-test` green — lint + typecheck + jest (including `founder-setup.test.tsx`) | TODO | | `make poc-app-test` exits 0 |
| P4.4 | Update `docs/plans/poc-implementation-progress.md` — add POC 05 row to Milestone Status table | TODO | | `grep "POC 05" docs/plans/poc-implementation-progress.md` |

---

## Decisions & open notes (carry across sessions)

- **No new routes or DB schemas.** The only DB artifact is a new entry in the
  `conversation_scenarios` seed document. The conversation engine handles it automatically.
- **Branching heuristics are intentionally simple.** Word-count (60 / 120 thresholds) and a
  digit-or-uppercase check are enough for a demonstrable POC. Real NLP scoring is Iteration 2.
- **`custom_context` is stored but not used for branching.** The intake data enriches the session
  record and can be surfaced in the review, but the deterministic mock ignores it for routing.
- **`conversation-review.tsx` and `conversation.tsx` are not touched.** Any data-shape changes
  required must be backward-compatible additions to `ConversationReview` (new optional fields only).
