# POC 07 — Sales Objection Handling Simulator — Implementation Plan

> **This file is the committed, resumable source of truth for POC 07.**
> It is authoritative across sessions — not in-session memory, not the TaskList.

---

## HOW TO RESUME (agent: read this block FIRST, every run)

You were told: *"implement this plan"* (pointing at this file or at
[`poc-07-sales-objection-progress.md`](poc-07-sales-objection-progress.md)).
Do exactly this:

1. **Read this whole file** — understand the full design before touching code.
2. **Read the progress tracker:** [`docs/plans/poc-07-sales-objection-progress.md`](poc-07-sales-objection-progress.md)
   — find the **first sub-task whose status is not `DONE`**. That is where you resume.
3. **Re-verify the last `DONE` row actually landed** before continuing (run its *Verify* command).
   A session can die between writing code and committing — if the last `DONE` row isn't on disk,
   redo **only** that one step. **Never redo work already `DONE` and verified.**
4. Work **one atomic sub-task at a time**: do it → run its *Verify* → set status `DONE` +
   record commit SHA → **`git commit` the code and the progress tracker together** (branch
   `feat/poc-07-sales-objection`, conventional commit) → next row.
5. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but **this committed
   file is authoritative** — reconcile against it, not against memory.

**Status legend:** `TODO` · `DOING` · `DONE` (SHA recorded) · `DEFERRED` (blocker recorded).

---

## KEY CONSTRAINTS

- **Base branch:** `feat/poc-06-listening-gym`. Branch: `feat/poc-07-sales-objection`.
- **Zero new infrastructure.** This POC reuses the entire conversation engine from POC 04.
  `domain/conversation.py`, `providers/mock_conversation.py`, `routes/conversations.py`,
  `db/schemas/conversation_sessions.json`, `db/schemas/conversation_turns.json`,
  `app/src/app/conversation.tsx`, `app/src/app/conversation-review.tsx` — all untouched.
- **Pure data + home card.** The only new artifacts are:
  (a) the `sales_pricing_objection` entry in `conversation_scenarios.json`,
  (b) a new home card linking to the existing `conversation-setup.tsx` screen with
      `scenario_id="sales_pricing_objection"` pre-selected.
  No new screens, no new routes, no new domain files.
- **3 buyer turns.** The conversation is fixed at 3 buyer persona messages. After the user's
  third response, the conversation ends and the review is available.
- **Branching: buyer warmth.** If the user's first response acknowledges the objection, the
  second buyer message softens ("Tell me more about that."). If the user defends price, the
  buyer stays cold ("I am still not convinced.").
- **Deterministic mock.** All buyer turns and branching are rule-based. No LLM.
- **Hard DB isolation.** Mock DB only: container `vaani_poc_mongo`, port **27018**, database
  `public_speaking_intelligence_mock`. Never touch the real DB / 27017.
- **Python env:** `.venv-poc` only. Never `.venv` / `.venv311`.
- **Keep green:** `make poc-api-lint && make poc-api-test` (coverage ≥70%) and `make poc-app-test`.
- **Git identity:** branch `feat/poc-07-sales-objection`; conventional commits; never `git add -A`.

---

## Part A — Product design

### Scenario overview

The user is a salesperson responding to a buyer who raises a pricing objection. The session runs
for exactly 3 buyer turns (the buyer opens, pushes back after turn 1, and closes after turn 2).
The user responds 3 times (one response per buyer turn). After turn 3, the review screen shows
5 sales-capability scores and 3 better phrasings.

### Conversation structure (fixed)

```
Buyer turn 1 (opening):
  "This is too expensive and I do not see why we need it now."

  [User responds — turn 1]

Buyer turn 2 (pushback — branching):
  IF user turn 1 contains acknowledge marker:
    → "I hear you. Tell me more about what you mean."
  ELSE:
    → "I hear you but we already have tools that do something similar."

  [User responds — turn 2]

Buyer turn 3 (closing — fixed, end of roleplay):
  "Okay, I will think about it."

  [User responds — turn 3]

  → Session ends → review available
```

### Acknowledge markers (for branching on turn 1)

A user response is considered acknowledging if it contains any of:
`"i understand"`, `"that makes sense"`, `"i hear you"`, `"i appreciate"`, `"fair point"`,
`"valid concern"`, `"good point"`.

### Rubric (5 dimensions, weights sum to 100)

| Capability | Key | Weight | What is scored |
|---|---|---|---|
| Acknowledge concern | `acknowledge_concern` | 20 | User validates the buyer's worry before pitching |
| Diagnostic question | `diagnostic_question` | 20 | User asks a question to understand the buyer's real blocker |
| Reframe value | `reframe_value` | 20 | User shifts the conversation from price to value/ROI |
| Cost of inaction | `cost_of_inaction` | 20 | User surfaces the risk of doing nothing |
| Next step | `next_step` | 20 | User proposes a concrete next step to keep momentum |

### Rubric markers (scored across all 3 user turns combined)

| Dimension | Positive markers | Negative markers |
|---|---|---|
| `acknowledge_concern` | "i understand", "that makes sense", "i hear you", "valid concern", "fair point" | — |
| `diagnostic_question` | "?" + "what", "?" + "why", "?" + "how", "tell me more", "help me understand", "what is your biggest concern" | — |
| `reframe_value` | "roi", "return", "value", "benefit", "cost of not", "save", "revenue", "payback" | "cheaper", "discount", "lower the price" |
| `cost_of_inaction` | "cost of not", "risk of waiting", "what happens if", "stay the same", "without this", "delay will" | — |
| `next_step` | "next step", "schedule", "follow up", "set up a call", "send you", "demo", "pilot", "free trial" | — |

Scoring: each dimension is 0.0–1.0 based on presence of ≥1 positive marker (1.0) and absence of
negative markers (any negative marker caps dimension at 0.5). Overall = equal-weight average.

### Better phrasings

`GET /conversations/{id}/review` returns `suggested_rephrasings` (list of 3). These are generated
by `build_conversation_review()` in `domain/conversation.py` from the lowest-scoring dimensions —
no change needed to that function.

---

## Part B — Backend changes

### B.1 — Scenario seed data

File: `services/api/db/seed_data/conversation_scenarios.json`

Add one entry with `scenario_id: "sales_pricing_objection"`. Required fields:

```
scenario_id:       "sales_pricing_objection"
title:             "Pricing Objection"
brief:             "A buyer says your product is too expensive and not urgent. Handle the objection."
persona_role:      "skeptical buyer"
user_role:         "salesperson"
opening_message:   "This is too expensive and I do not see why we need it now."
fixed_questions:   [] (not used — buyer turns are defined in persona_turns instead)
persona_turns:     [
  { "turn": 1, "message": "This is too expensive and I do not see why we need it now." },
  { "turn": 2,
    "variants": {
      "warm":  "I hear you. Tell me more about what you mean.",
      "cold":  "I hear you but we already have tools that do something similar."
    }
  },
  { "turn": 3, "message": "Okay, I will think about it." }
]
branching_rules:   {
  "turn_1_acknowledge_markers": ["i understand", "that makes sense", "i hear you",
                                  "i appreciate", "fair point", "valid concern", "good point"],
  "warm_variant": "warm",
  "cold_variant": "cold"
}
max_turns:         3
rubric:            { acknowledge_concern: 20, diagnostic_question: 20, reframe_value: 20,
                     cost_of_inaction: 20, next_step: 20 }
rubric_markers:    { ... positive and negative lists per dimension ... }
```

Note: the `persona_turns` / `variants` structure extends the existing `ConversationScenario`
type. Verify that `domain/conversation.py` already handles a `persona_turns` field (added in
POC 04 for the difficult-conversation scenario) — if not, add it as an optional field.

### B.2 — Verify / extend conversation engine (minimal, additive)

Check that `providers/mock_conversation.py` already supports the `persona_turns` + `variants`
branching pattern from POC 04. If the difficult-conversation scenario already uses this same
structure, no code change is needed. If `sales_pricing_objection` introduces a new structural
variant, make the minimum additive change.

Document the result in the progress tracker (either "no code change needed" or the one-line
change made).

### B.3 — Tests

Add test cases for the sales scenario (in the existing conversation test file from POC 04 or a
new `test_conversation_sales.py`):

- Scenario loads from seed with `scenario_id="sales_pricing_objection"`.
- `score_conversation()` on a 3-turn sales session returns all 5 dimensions.
- Branching: user turn 1 with acknowledge marker → buyer turn 2 is the warm variant.
- Branching: user turn 1 with no acknowledge marker → buyer turn 2 is the cold variant.
- `reframe_value`: "roi" in user text → score 1.0; "cheaper" → score capped at 0.5.
- `next_step`: "let's schedule a call" → score 1.0; no next step → 0.0.
- Review returns exactly 3 `suggested_rephrasings`.

---

## Part C — Frontend changes

### C.1 — Home screen card

Add a card in `app/src/app/index.tsx`:

```
Title: "Handle a Buyer Objection"
Badge: "SALES"
Subtitle: "A skeptical buyer says it's too expensive. Respond, get pushed back, close."
CTA: → /conversation-setup?scenario_id=sales_pricing_objection
```

This links directly to the existing `conversation-setup.tsx` screen from POC 04 with the
scenario pre-selected. No new screen.

### C.2 — Verify `conversation-setup.tsx` accepts a `scenario_id` param

Confirm that `app/src/app/conversation-setup.tsx` (from POC 04) reads an optional `scenario_id`
route param and pre-selects that scenario in the picker. If it does not, add the optional param
handling (small additive change, no structural change to the screen).

### C.3 — Tests

- `index.test.tsx` (or existing home screen test) — verify the "Handle a Buyer Objection" card
  renders and links to `/conversation-setup?scenario_id=sales_pricing_objection`.
- If `conversation-setup.tsx` was modified, add 1 test verifying it pre-selects the scenario
  from the route param.

---

## Part D — Acceptance criteria

1. The "Handle a Buyer Objection" card is visible on the home screen.
2. Tapping it navigates to `conversation-setup.tsx` with the sales scenario pre-selected.
3. Starting the session shows the buyer opening: "This is too expensive and I do not see why we
   need it now."
4. After user turn 1 with an acknowledge marker, the buyer's second message is the warm variant.
5. After user turn 1 with no acknowledge marker, the buyer's second message is the cold variant.
6. After 3 user turns, the review screen shows scores for all 5 capability dimensions:
   `acknowledge_concern`, `diagnostic_question`, `reframe_value`, `cost_of_inaction`, `next_step`.
7. The review shows 3 better phrasings.
8. `conversation.tsx` and `conversation-review.tsx` are used unchanged from POC 04.
9. `make poc-api-test` green (≥70% coverage, all new scenario + scoring tests pass).
10. `make poc-app-test` green (lint + typecheck + jest, including updated home card test).

---

## Decisions & notes

- **Buyer warmth branching is a coaching signal.** Buyers become more open when acknowledged. This
  teaches the user that acknowledging a concern first is not a weakness — it's a technique. The
  branching makes this viscerally demonstrable.
- **3 turns is the right length.** Enough to demonstrate the full arc (acknowledge → diagnose →
  reframe → cost → close) without over-engineering a longer flow.
- **Equal weights (20% each).** Unlike the founder scenario, all 5 sales dimensions are equally
  important for a balanced objection-handling framework.
- **`reframe_value` penalizes price-defense language.** Saying "cheaper" or "discount" gets the
  score capped at 0.5, teaching that defending price is less effective than shifting to value.
- **No new frontend screen.** The home card goes directly to `conversation-setup.tsx`, which
  already handles scenario selection. POC 07 is purely a data + linking exercise on the frontend.
- **`persona_turns` / `variants` structure.** If this is already used by the difficult-conversation
  scenario (POC 04), the sales scenario inherits it at zero cost. If it is new, the engine change
  is minimal (read the variant key from branching rules, select from `variants` dict).
- **`max_turns: 3`** caps the conversation. The mock engine from POC 04 must respect this field —
  verify or add a one-line guard.
