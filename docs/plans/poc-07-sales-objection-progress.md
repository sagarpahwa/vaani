# POC 07 — Sales Objection Handling Simulator — Implementation Progress Tracker

> **This file is the committed, resumable source of truth for POC 07.**
> It is authoritative across sessions — not in-session memory, not the TaskList.

---

## HOW TO RESUME (agent: read this block FIRST, every run)

You were told: *"implement this plan"* (pointing at this file or at
[`poc-07-sales-objection-plan.md`](poc-07-sales-objection-plan.md)). Do exactly this:

1. **Read the plan:** [`docs/plans/poc-07-sales-objection-plan.md`](poc-07-sales-objection-plan.md)
   — the full approved design (Parts A–D, acceptance criteria). This tracker is its checklist.
2. **Read this whole file** — find the **first sub-task whose status is not `DONE`** in the
   tables below. That is where you resume.
3. **Re-verify the last `DONE` row actually landed** before continuing (run its *Verify* command /
   confirm the file exists). A session can die between writing code and committing, so the last row
   marked `DONE` might not be on disk. If it didn't land, redo **only** that one step.
   **Never redo work already `DONE` and verified.**
4. Work **one atomic sub-task at a time**: do it → run its *Verify* → set status `DONE` +
   record the commit SHA → **`git commit` the code and this tracker together** (branch
   `feat/poc-07-sales-objection`, conventional commit) → next row. Never batch multiple
   sub-tasks into one commit.
5. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but **this committed
   file is authoritative** — reconcile against it, not against memory.

**Status legend:** `TODO` (not started) · `DOING` (in flight, not committed) · `DONE` (committed; SHA recorded) · `DEFERRED` (committed decision to skip; blocker recorded).

---

## Key constraints (do not violate — full detail in the plan & CLAUDE.md)

- **Base branch:** `feat/poc-06-listening-gym`. Branch: `feat/poc-07-sales-objection`.
- **Zero new infrastructure.** Entire conversation engine from POC 04 is reused unchanged.
  New artifacts: one scenario JSON entry, one home card (and possibly a one-line param addition
  to `conversation-setup.tsx` if it doesn't already accept a `scenario_id` route param).
- **3 buyer turns.** Buyer opens, pushes back (warm or cold), closes. 3 user responses total.
- **Branching on turn 1.** Acknowledge marker in user's first response → warm pushback; otherwise cold.
- **Deterministic.** All buyer messages are fixed strings selected by rule. No LLM.
- **Hard DB isolation.** Mock DB only: container `vaani_poc_mongo`, port **27018**, database
  `public_speaking_intelligence_mock`. Never touch the real DB / 27017.
- **Python env:** `.venv-poc` only (via `make poc-api-install`). Never `.venv` / `.venv311`.
- **Keep green:** `make poc-api-lint && make poc-api-test` (coverage ≥70%) and `make poc-app-test`.
- **Git identity:** branch `feat/poc-07-sales-objection`; conventional commits; never `git add -A`,
  never force-push / `reset --hard` without explicit ask.

---

## P0 — Docs & resumability scaffold

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | In-repo copy of full plan → [`poc-07-sales-objection-plan.md`](poc-07-sales-objection-plan.md) | TODO | | `test -f docs/plans/poc-07-sales-objection-plan.md` |
| P0.2 | This resumable tracker → `poc-07-sales-objection-progress.md` | TODO | | `test -f docs/plans/poc-07-sales-objection-progress.md` |
| P0.3 | Link this milestone from [`poc-implementation-progress.md`](poc-implementation-progress.md) | TODO | | `grep "poc-07" docs/plans/poc-implementation-progress.md` |

---

## P1 — Backend: scenario seed data + engine verification

*Checkpoint:* `GET /conversations/scenarios` returns `sales_pricing_objection` with 3 buyer turns
and a 5-dimension rubric. `score_conversation()` returns all 5 sales dimensions.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | Inspect `domain/conversation.py` and `providers/mock_conversation.py` from POC 04 — verify they support `persona_turns` + `variants` branching + `max_turns`; document finding in the progress tracker (either "no code change" or the exact minimal addition made) | TODO | | `grep persona_turns services/api/domain/conversation.py` |
| P1.2 | Add `sales_pricing_objection` entry to `services/api/db/seed_data/conversation_scenarios.json` — full schema per plan Part B.1: `scenario_id`, `title`, `brief`, `persona_role`, `user_role`, `opening_message`, `persona_turns` (3 buyer messages with warm/cold variants for turn 2), `branching_rules` (acknowledge_markers list, warm/cold variant keys), `max_turns: 3`, `rubric` (5 dimensions × 20%), `rubric_markers` (positive + negative per dimension) | TODO | | `python3 -c "import json; d=json.load(open('services/api/db/seed_data/conversation_scenarios.json')); s=[x for x in d if x['scenario_id']=='sales_pricing_objection']; assert len(s)==1 and s[0]['max_turns']==3"` |
| P1.3 | If P1.1 found a missing engine feature (e.g. `persona_turns` not supported, `max_turns` not enforced): make the minimum additive change to `domain/conversation.py` or `providers/mock_conversation.py` — no structural refactor, additive only | TODO | | `make poc-api-test` still green after any engine change |
| P1.4 | Backend unit tests (7 cases): scenario loads with 5 dimensions; `score_conversation()` returns all 5 keys; branching warm (acknowledge marker → warm variant); branching cold (no acknowledge → cold variant); `reframe_value` penalizes "cheaper" (capped at 0.5); `next_step` scores "let's schedule a call" as 1.0; review returns 3 `suggested_rephrasings` | TODO | | `pytest services/api/tests/ -k sales` → 7 passed |

---

## P2 — Frontend: home card + conversation-setup param

*Checkpoint:* Tapping home card navigates to conversation-setup with sales scenario pre-selected.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | Inspect `app/src/app/conversation-setup.tsx` — verify it reads an optional `scenario_id` route param and pre-selects that scenario in the picker | TODO | | `grep scenario_id app/src/app/conversation-setup.tsx` |
| P2.2 | If `conversation-setup.tsx` does not accept `scenario_id` param: add optional route param reading + pre-selection logic (small additive change, ≤10 lines) | TODO | | Navigating to `/conversation-setup?scenario_id=sales_pricing_objection` pre-selects "Pricing Objection" |
| P2.3 | Add home card in `app/src/app/index.tsx` — title "Handle a Buyer Objection", badge "SALES", subtitle about pricing objection + 3 turns, CTA → `/conversation-setup?scenario_id=sales_pricing_objection` | TODO | | `grep sales_pricing_objection app/src/app/index.tsx` |
| P2.4 | Test updates: add 1 test in home screen test file verifying "Handle a Buyer Objection" card renders and links correctly; if conversation-setup was modified, add 1 test verifying scenario_id param pre-selects the scenario | TODO | | `make poc-app-test` |

---

## P3 — E2E verify

*Checkpoint:* Full click-through from home → conversation → 3 buyer turns → review with 5 sales dimension scores.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | Start backend (`make poc-api-run`) and web app (`make poc-app-web`); navigate home → "Handle a Buyer Objection" → conversation-setup with sales scenario pre-selected | TODO | | Browser shows conversation-setup with "Pricing Objection" scenario |
| P3.2 | Start session → conversation screen opens with buyer opening "This is too expensive and I do not see why we need it now." | TODO | | Buyer opening message displayed |
| P3.3 | Respond with an acknowledge marker (e.g. "I understand your concern…") → verify buyer turn 2 is the warm variant "I hear you. Tell me more about what you mean." | TODO | | Warm variant appears for turn 2 |
| P3.4 | Complete remaining turns → review screen shows all 5 capability scores (acknowledge_concern, diagnostic_question, reframe_value, cost_of_inaction, next_step) and 3 better phrasings | TODO | | Review screen shows 5 dimensions + 3 phrasings |
| P3.5 | Run a second session WITHOUT an acknowledge marker in turn 1 → verify buyer turn 2 is the cold variant "I hear you but we already have tools that do something similar." | TODO | | Cold variant appears when no acknowledge marker |

---

## P4 — Tests polish & CI green

*Checkpoint:* Both test suites green with no coverage regression.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P4.1 | `make poc-api-lint` clean (ruff + black) | TODO | | `make poc-api-lint` exits 0 |
| P4.2 | `make poc-api-test` green — all new scenario + scoring tests pass; coverage ≥70% | TODO | | `make poc-api-test` exits 0 |
| P4.3 | `make poc-app-test` green — lint + typecheck + jest (including home card test + any conversation-setup update test) | TODO | | `make poc-app-test` exits 0 |
| P4.4 | Update `docs/plans/poc-implementation-progress.md` — add POC 07 row to Milestone Status table | TODO | | `grep "POC 07" docs/plans/poc-implementation-progress.md` |

---

## Decisions & open notes (carry across sessions)

- **P1.1 is a discovery step.** The POC 04 conversation engine may already fully support
  `persona_turns` + `variants` + `max_turns`. If so, P1.3 is a no-op (record "no change needed"
  and move on). If not, the fix is intentionally small and additive.
- **Buyer warmth branching is the core coaching mechanism.** A single acknowledge marker in the
  first user turn unlocks a softer buyer — this teaches acknowledging first as a concrete technique
  rather than abstract advice.
- **`reframe_value` negative markers.** "Cheaper" and "discount" cap the score at 0.5 rather than
  zeroing it out. This is intentional: price-defense is bad but not catastrophic. The 0.5 cap
  signals "this weakens your position" without making the overall score collapse.
- **`next_step` is a closing skill.** Many salespeople fail to propose a concrete next step even
  after a good conversation. The 20% weight makes it high-stakes and clearly rewarded.
- **No new frontend screen.** The entire frontend contribution is one home card and (if needed)
  one param on an existing screen. This is the lightest-weight POC in the series.
- **`conversation.tsx` and `conversation-review.tsx` are unchanged.** Any review of this PR should
  confirm that neither file has a diff. The review rendering (5 dimensions, 3 phrasings) is driven
  entirely by the scenario data, not by screen logic.
- **Equal weights (20% each).** Unlike the listening gym where dimensions have different weights,
  all 5 sales dimensions are equally critical in a balanced objection-handling framework. Changing
  weights is a seed-data-only change.
