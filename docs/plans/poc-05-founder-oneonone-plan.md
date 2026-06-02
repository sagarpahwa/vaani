# POC 05 — Founder / CEO One-on-One Rehearsal — Implementation Plan

> **This file is the committed, resumable source of truth for POC 05.**
> It is authoritative across sessions — not in-session memory, not the TaskList.

---

## HOW TO RESUME (agent: read this block FIRST, every run)

You were told: *"implement this plan"* (pointing at this file or at
[`poc-05-founder-oneonone-progress.md`](poc-05-founder-oneonone-progress.md)).
Do exactly this:

1. **Read this whole file** — understand the full design before touching code.
2. **Read the progress tracker:** [`docs/plans/poc-05-founder-oneonone-progress.md`](poc-05-founder-oneonone-progress.md)
   — find the **first sub-task whose status is not `DONE`**. That is where you resume.
3. **Re-verify the last `DONE` row actually landed** before continuing (run its *Verify* command).
   A session can die between writing code and committing — if the last `DONE` row isn't on disk,
   redo **only** that one step. **Never redo work already `DONE` and verified.**
4. Work **one atomic sub-task at a time**: do it → run its *Verify* → set status `DONE` +
   record commit SHA → **`git commit` the code and the progress tracker together** (branch
   `feat/poc-05-founder-oneonone`, conventional commit) → next row.
5. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but **this committed
   file is authoritative** — reconcile against it, not against memory.

**Status legend:** `TODO` · `DOING` · `DONE` (SHA recorded) · `DEFERRED` (blocker recorded).

---

## KEY CONSTRAINTS

- **Base branch:** `feat/poc-04-difficult-conv`. Branch off it as `feat/poc-05-founder-oneonone`.
- **Zero new infrastructure.** This POC reuses the conversation engine from POC 04 entirely:
  `domain/conversation.py`, `providers/mock_conversation.py`, `routes/conversations.py`,
  `db/schemas/conversation_sessions.json`, `db/schemas/conversation_turns.json`,
  `app/src/app/conversation.tsx`, `app/src/app/conversation-review.tsx` — all untouched.
- **Pure data + one new screen.** The only new artifacts are:
  (a) the `founder_ceo_oneonone` entry in `conversation_scenarios.json`,
  (b) the `founder-setup.tsx` intake form screen,
  (c) a home card linking to it.
- **Deterministic mock.** The founder asks exactly 5 fixed questions; branching is rule-based
  (word-count + specificity markers), no LLM. Default `PROVIDER_CONVERSATION=mock`.
- **Hard DB isolation.** Mock DB only: container `vaani_poc_mongo`, port **27018**, database
  `public_speaking_intelligence_mock`. Never touch the real DB / 27017.
- **Python env:** `.venv-poc` only. Never `.venv` / `.venv311`.
- **Keep green:** `make poc-api-lint && make poc-api-test` (coverage ≥70%) and `make poc-app-test`.
- **Git identity:** branch `feat/poc-05-founder-oneonone`; conventional commits; never `git add -A`.

---

## Part A — Product design

### Scenario overview

The user (playing a product manager or engineer) presents a meeting agenda to a sharp, impatient
founder. The session runs for exactly 5 founder questions. After the final response the user gets
a scored review with 6 capability dimensions and 3 better phrasings.

### Intake form (`founder-setup.tsx`)

Four fields collected before the conversation starts:

| Field | Label | Type | Required |
|---|---|---|---|
| `meeting_agenda` | What is on your agenda? | multi-line text | yes |
| `user_role` | Your role (e.g. PM, Engineer) | single-line text | yes |
| `desired_outcome` | What do you want to leave with? | single-line text | yes |
| `company_context` | Company / product context (optional) | multi-line text | no |

On submit: `POST /conversations` with `scenario_id="founder_ceo_oneonone"` and
`custom_context` assembled from the form fields. Navigate to the existing `conversation.tsx`
screen, passing `conversationId`.

### Founder persona (deterministic mock)

**Opening message (always):** "You have ten minutes. What do you need?"

**Five fixed questions (in order):**

1. "Why does this matter now?"
2. "What is the business impact?"
3. "What will break if we do nothing?"
4. "What is the simplest version?"
5. "What tradeoff are you making?"

**Branching rules applied after each user answer (before next question):**

| Condition | Detected by | Founder response |
|---|---|---|
| Concise answer (<60 words) | word count | Next question immediately |
| Vague (no numbers and no specific nouns) | absence of digit + absence of specificity markers | "Can you be more specific?" (then next question) |
| Rambling (>120 words) | word count | "Can you say that in one sentence?" (then next question) |
| After question 5 | turn count == 5 | "Okay, I have heard enough. Let me think about it." → END |

Specificity markers: any digit (`\d`), "$", "%", a proper noun starting with a capital letter
(simple heuristic: ≥1 word starting with uppercase that is not the first word of the sentence).

### Rubric (6 dimensions, weights sum to 100)

| Capability | Weight | What is scored |
|---|---|---|
| `strategic_clarity` | 25 | User states the why and context without prompting |
| `business_impact` | 20 | Concrete business numbers, revenue, cost, time cited |
| `conciseness` | 15 | Answers stay under 80 words on average |
| `handling_challenge` | 20 | User does not back down on vague push-back but sharpens the answer |
| `executive_presence` | 10 | Confident language, no filler hedges (maybe/I think/sort of) |
| `strong_ask` | 10 | Closes with a clear ask or next step |

Scoring: keyword-based (same approach as POC 04 conversation scoring in `domain/conversation.py`).
Each dimension has a list of positive markers and negative markers counted across all user turns.

### Better phrasings

The review surface (`conversation-review.tsx` reused as-is) shows 3 better phrasings drawn from
the `review.suggested_rephrasings` field returned by `GET /conversations/{id}/review`. These are
generated by `build_conversation_review()` in `domain/conversation.py` — no changes needed there.

---

## Part B — Backend changes

### B.1 — Scenario seed data

File: `services/api/db/seed_data/conversation_scenarios.json`

Add one entry with `scenario_id: "founder_ceo_oneonone"`. Required fields (matching the
`ConversationScenario` type from POC 04):

```
scenario_id, title, brief, persona_role, user_role,
opening_message, fixed_questions (list of 5),
branching_rules (object: concise_threshold, vague_markers, long_threshold, follow_up_messages),
rubric (object: dimension → weight)
```

The seeder in `services/api/db/seed_mock.py` already upserts all scenarios — no seeder change.

### B.2 — Scoring markers

Add founder-specific positive and negative marker lists inside the scenario JSON under
`rubric_markers`. The `score_conversation()` function in `domain/conversation.py` already reads
these per-scenario markers — no domain code change.

### B.3 — Tests

Add test cases in `services/api/tests/test_conversation_scenarios.py` (or equivalent test file
from POC 04):

- Scenario loads from seed and validates required fields.
- `score_conversation()` on a sample founder session returns all 6 dimensions.
- Branching rule: >120-word answer triggers "Can you say that in one sentence?".
- Branching rule: answer with no specificity markers triggers "Can you be more specific?".
- Branching rule: <60-word concise answer advances without a follow-up.
- Review contains exactly 3 `suggested_rephrasings`.

---

## Part C — Frontend changes

### C.1 — `founder-setup.tsx`

New screen at `app/src/app/founder-setup.tsx`. Responsibilities:

1. Render intake form (4 fields per Part A).
2. Validate: `meeting_agenda`, `user_role`, `desired_outcome` must be non-empty; disable Submit
   until all three are filled.
3. On Submit: call `POST /conversations` (via `api/client.ts` `createConversation`) with
   `scenario_id="founder_ceo_oneonone"` and `custom_context` object.
4. On success: navigate to `/conversation?conversationId={id}` (existing screen from POC 04).
5. Show a loading state while the request is in-flight; show an error banner on failure.

Reuse existing UI primitives: `Screen`, `Button`, `Field`, `Banner` from `app/src/ui/`.

### C.2 — Route registration

Register `/founder-setup` in `app/src/app/_layout.tsx` with `Stack.Screen title="Founder / CEO One-on-One"`.

### C.3 — Home screen card

Add a card in `app/src/app/index.tsx` below the personas card and above Guided Practice:

```
Title: "Founder / CEO One-on-One"
Badge: "STRATEGY"
Subtitle: "Present your agenda to a sharp, impatient founder. 5 hard questions."
CTA: → /founder-setup
```

### C.4 — API client method

Add `createConversation(payload)` to `app/src/api/client.ts` if not already present from POC 04.
The method calls `POST /conversations` and returns `{ conversationId: string }`.

Confirm `ConversationScenario`, `ConversationTurn`, `ConversationReview` types exist in
`app/src/api/types.ts` (added by POC 04); add any missing fields.

### C.5 — Tests

Co-locate tests next to the new module:

- `founder-setup.test.tsx` — renders form, Submit disabled until required fields filled, calls
  `createConversation` with correct payload on submit, navigates on success, shows banner on error.
- If `createConversation` is new in `client.ts` — add a test in the existing client test file.

---

## Part D — Acceptance criteria (verify before marking DONE)

1. User can open the Founder / CEO One-on-One card from the home screen.
2. The intake form collects agenda, role, outcome, and optional context. Submit is disabled until
   the three required fields are filled.
3. On submit, the app navigates to the conversation screen and the founder opens with
   "You have ten minutes. What do you need?"
4. The founder asks exactly 5 hard business questions in the fixed order, with branching follow-ups
   applied where applicable.
5. After turn 5, the review screen shows scores for all 6 capability dimensions.
6. The review shows exactly 3 better phrasings.
7. The `conversation.tsx` and `conversation-review.tsx` screens are used exactly as built in
   POC 04 — no modifications.
8. `make poc-api-test` green (≥70% coverage, all new scenario + scoring tests pass).
9. `make poc-app-test` green (lint + typecheck + jest, including `founder-setup.test.tsx`).

---

## Decisions & notes

- **Reuse over build.** The entire conversation engine (state machine, routes, DB schemas, frontend
  screens) ships from POC 04. POC 05 is deliberately a pure content + thin-UI extension.
- **No LLM.** The founder persona is fully deterministic. Branching on word-count and a lightweight
  specificity heuristic (digits + uppercase tokens) gives enough differentiation without any model
  dependency.
- **`custom_context` field.** The intake form data is passed as `custom_context` in the POST body.
  The mock conversation engine surfaces it in the session but does not use it for branching — it is
  stored for future real-AI use.
- **Rubric weights are intentionally unequal.** `strategic_clarity` (25%) and `handling_challenge`
  (20%) are the core skills being trained; conciseness and strong_ask are secondary hygiene.
- **`conversation-review.tsx` is not changed.** It already renders capability scores and
  rephrasings from `ConversationReview` — no screen-level adaptation needed.
