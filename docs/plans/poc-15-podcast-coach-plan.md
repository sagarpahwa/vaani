# POC 15 — Podcast Conversation Coach — Implementation Plan & Progress Tracker

> **This file is the committed, resumable source of truth for POC 15.**
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
   `feat/poc-15-podcast-coach`, conventional commit) → next row. Never batch multiple sub-tasks
   into one commit.
4. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but **this committed
   file is authoritative** — reconcile against it, not against memory.

**Status legend:** `TODO` (not started) · `DOING` (in flight, not committed) · `DONE` (committed; SHA recorded) · `DEFERRED` (committed decision to skip; blocker recorded).

---

## Key constraints (do not violate — full detail in CLAUDE.md)

- **Base branch:** `feat/poc-14-highspeed-qa`. New branch: `feat/poc-15-podcast-coach` (branch off base, never commit to base).
- **CRITICAL PREREQUISITE: POC 04 conversation engine must be in place on the base branch.** This POC reuses the multi-turn conversation infrastructure introduced in POC 04: `conversation_sessions` schema, `conversation.tsx` screen, `conversation-review.tsx` screen, and the conversation scenario engine. Do not re-implement any of that — only add a new scenario and wire the home card. If the POC 04 conversation engine is not present on the base branch, surface this as a blocker before writing any code.
- **No LLM for host scoring.** Host behavior is scored with deterministic keyword/phrase heuristics — the same pattern used in POC 09–11 (feedback_coach.py, pitch.py, debate.py). Guest responses are fixed scripts branched on question quality detection.
- **No new infrastructure.** No new collections, no new provider ABCs, no new Makefile targets. This POC adds only: one scenario data record in `conversation_scenarios.json`, one host-scoring module, and a home card.
- **Additive, zero regression.** Existing conversation scenarios and all existing Mode A/B/persona/storytelling/explainer/highspeed paths stay untouched. `make poc-api-test` must pass with the same golden values after every commit.
- **Python env:** `.venv-poc` only. Never `.venv` / `.venv311`.
- **DB isolation.** Mock DB only: container `vaani_poc_mongo`, port **27018**, database `public_speaking_intelligence_mock`. Never touch port 27017.
- **Keep green:** `make poc-api-lint && make poc-api-test` (coverage ≥70%) and `make poc-app-test` after every commit.
- **Git identity:** conventional commits; never `git add -A`; never force-push without explicit request.

---

## Pre-flight: verify POC 04 conversation engine exists

Before starting P0, confirm the following artefacts are present on the base branch. If any are missing, surface as a blocker and stop.

| Artefact | Check command |
|---|---|
| `app/src/app/conversation.tsx` | `test -f app/src/app/conversation.tsx` |
| `app/src/app/conversation-review.tsx` | `test -f app/src/app/conversation-review.tsx` |
| `services/api/db/seed_data/conversation_scenarios.json` | `test -f services/api/db/seed_data/conversation_scenarios.json` |
| Conversation scenario engine in backend (route or service) | `grep -r "conversation_scenarios" services/api/routes/ \|\| grep -r "conversation" services/api/routes/` |

---

## P0 — Docs & resumability scaffold

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | This plan/tracker file → `docs/plans/poc-15-podcast-coach-plan.md` | TODO | | `test -f docs/plans/poc-15-podcast-coach-plan.md` |
| P0.2 | Link this milestone in `docs/plans/poc-implementation-progress.md` (add POC 15 row to Milestone Status table) | TODO | | `grep "poc-15" docs/plans/poc-implementation-progress.md` |

---

## P1 — Backend data: podcast scenario + host scoring

*Checkpoint:* `conversation_scenarios.json` has the `podcast_host_guest` scenario; `score_host_turn(text, prior_guest_text) -> dict` tested; guest branching logic tested.

### 1a — Scenario data

Add one new entry to `services/api/db/seed_data/conversation_scenarios.json` (do not replace existing entries — append):

```json
{
  "scenario_id": "podcast_host_guest",
  "title": "Podcast Host",
  "subtitle": "Interview Priya, a startup founder. Ask great follow-up questions.",
  "guest_persona": {
    "name": "Priya",
    "role": "Startup founder, Series A, mental health tech"
  },
  "opening_guest_line": "I've spent the last three years building something I wish had existed when I was struggling with burnout. We help founders track emotional patterns before they become crises.",
  "turn_count": 5,
  "guest_response_scripts": [
    {
      "trigger": "specific_followup",
      "trigger_markers": ["what made you", "why did you", "how did you", "what was the moment", "tell me more about", "what does that mean", "how does it work", "what kind of"],
      "response": "The turning point was when I saw three founders in my network burn out in the same month. I thought: this is a pattern. So I started logging my own emotional state daily — and I realised the data was there, the tooling wasn't. That's when I decided to build Prism."
    },
    {
      "trigger": "self_reference",
      "trigger_markers": ["i had", "i think", "in my experience", "i once", "when i was", "i also", "i remember"],
      "response": "That's an interesting perspective. For us, the unique challenge was that founders don't talk about this — so the first product was almost about permission. Giving founders permission to say: I'm struggling."
    },
    {
      "trigger": "generic",
      "trigger_markers": ["tell me more", "interesting", "go on", "really", "wow", "that's great", "amazing"],
      "response": "Yes — and what surprised me most was the retention. People came back daily, not because we asked them to, but because seeing your own patterns is genuinely fascinating. It's like a mirror you never had before."
    },
    {
      "trigger": "summary_attempt",
      "trigger_markers": ["so what you're saying", "if i understand", "to summarize", "so essentially", "so you're saying", "in other words"],
      "response": "Exactly. And the meta-lesson is: founders are often the last to notice their own decline because they're too close to the problem. External visibility changes that."
    },
    {
      "trigger": "transition",
      "trigger_markers": ["building on that", "related to what you said", "you mentioned", "going back to", "earlier you said", "picking up on"],
      "response": "Right — and that connects to the fundraising story. Investors initially didn't get it. They kept asking 'is this a wellness app?' I had to reframe it as an operational risk tool. That changed everything."
    }
  ],
  "default_guest_response": "That's a good question. I think the core insight is that emotional data is just as important as financial data — and founders deserve both.",
  "host_rubric": {
    "curiosity":           { "weight": 0.20, "markers": ["why", "how did you", "what made", "what was", "what led", "what happened", "when did", "where did"] },
    "followup_quality":    { "weight": 0.25, "description": "question references guest's prior words (specificity markers)" },
    "not_self_referencing":{ "weight": 0.20, "penalty_markers": ["i think", "i had", "in my experience", "i once", "when i was", "i also"] },
    "transition":          { "weight": 0.15, "markers": ["building on that", "related to what you said", "you mentioned", "going back to", "earlier you said", "picking up on"] },
    "summary_skill":       { "weight": 0.20, "markers": ["so what you're saying", "if i understand", "to summarize", "so essentially", "so you're saying", "in other words"] }
  }
}
```

### 1b — Host scoring module

`services/api/domain/podcast_host.py` — `score_host_turn(host_text: str, prior_guest_text: str) -> dict`:

Scoring per dimension (all case-insensitive substring matching):

- `curiosity_score` — count of curiosity markers from `host_rubric.curiosity.markers`; min(1.0, count / 2).
- `followup_quality_score` — extract significant words from `prior_guest_text` (words > 4 chars, not stopwords); count how many appear in `host_text`; min(1.0, overlap_count / 3). "Specific follow-up" = at least 2 shared significant words.
- `self_reference_penalty` — count of `not_self_referencing.penalty_markers` in `host_text`; penalty = min(1.0, count * 0.4). `not_self_referencing_score = max(0.0, 1.0 - penalty)`.
- `transition_score` — any of `transition.markers` in `host_text` → 1.0; else 0.0.
- `summary_score` — any of `summary_skill.markers` in `host_text` → 1.0; else 0.0.
- `overall_score` — weighted sum per `host_rubric` weights.
- `dominant_trigger` — which guest response script would fire for this host turn (check trigger_markers in order: `specific_followup` → `self_reference` → `summary_attempt` → `transition` → `generic`; first match wins; `"default"` if none).
- `better_followup_example` — if `followup_quality_score < 0.4`: a canned suggestion referencing a key phrase from `prior_guest_text` (e.g. "Try asking about a specific detail from what Priya said, e.g. 'You mentioned emotional patterns — what does that data actually look like?'"); else `None`.

`score_conversation_review(host_turns: list[dict]) -> dict` — aggregates 5 host turns:
- Per-dimension average across all turns.
- `overall_score` — weighted average of per-turn `overall_score`.
- `strengths` — dimensions where average ≥ 0.65.
- `improvements` — dimensions where average < 0.40.
- `better_followup_examples` — collected non-null suggestions from per-turn scoring (up to 3).

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | Add `podcast_host_guest` scenario to `services/api/db/seed_data/conversation_scenarios.json` (append, do not replace existing entries) | TODO | | `python3 -c "import json; d=json.load(open('services/api/db/seed_data/conversation_scenarios.json')); ids=[s['scenario_id'] for s in d]; assert 'podcast_host_guest' in ids"` |
| P1.2 | `services/api/domain/podcast_host.py` — `score_host_turn(host_text, prior_guest_text) -> dict` and `score_conversation_review(host_turns) -> dict` | TODO | | `python3 -c "from services.api.domain.podcast_host import score_host_turn; r=score_host_turn('Why did you decide to build this?','I spent three years building'); assert 'overall_score' in r"` |
| P1.3 | `services/api/tests/test_podcast_host.py` — tests: curiosity markers detected; specific follow-up (references prior words) scores higher than generic; self-reference → penalty applied; transition marker → full score; summary attempt → full score; `dominant_trigger` routes to correct script key; `better_followup_example` returned when follow-up is generic; `score_conversation_review` aggregates 5 turns correctly | TODO | | `pytest services/api/tests/test_podcast_host.py -v` → tests passed |
| P1.4 | Wire `podcast_host_guest` scenario into the existing conversation engine backend: confirm the conversation route returns the scenario in `GET /conversation-scenarios` (or equivalent list endpoint); confirm the guest response branching logic is triggered by `dominant_trigger` from `score_host_turn`; confirm the review endpoint calls `score_conversation_review` | TODO | | `grep podcast_host_guest services/api/routes/*.py services/api/*.py` (present in at least one file) |
| P1.5 | `make poc-api-lint && make poc-api-test` green after P1 | TODO | | `make poc-api-lint && make poc-api-test` → 0 errors, coverage ≥70% |

---

## P2 — Frontend: home card + conversation wiring

*Checkpoint:* home screen shows "Podcast Conversation Coach" card; tapping it navigates to the existing conversation setup screen with `scenario_id=podcast_host_guest` pre-selected or auto-loaded.

**No new screen required.** The existing `conversation.tsx` and `conversation-review.tsx` screens from POC 04 handle the multi-turn chat UI and the final review. This POC only adds:
1. A home card on `index.tsx`.
2. Optionally: a `scenario_id` route param or deep-link that pre-selects the podcast scenario on the conversation setup screen.

**Home card spec:**
```
Title:    "Podcast Conversation Coach"
Subtitle: "Interview a startup founder. Ask great follow-up questions."
Badge:    "CONVERSATION"
Action:   navigate to /conversation?scenario_id=podcast_host_guest
           (or /conversation-setup with the scenario pre-selected, depending on POC 04 nav model)
```

**Review screen additions (if the review screen does not already show per-host-dimension scores):**
Check `conversation-review.tsx`. If it already renders per-dimension scores from the conversation engine's review payload, no change is needed. If it only shows a generic score, add 5 dimension score bars: Curiosity, Follow-Up Quality, Not Self-Referencing, Transition, Summary Skill — using the existing `ScoreBar` component.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | Inspect `conversation.tsx` and `conversation-review.tsx` to confirm nav model (how scenario_id is passed) and what the review screen already renders | TODO | | Read both files; no code change in this step |
| P2.2 | Add "Podcast Conversation Coach" home card to `app/src/app/index.tsx` → navigates to `/conversation` (or `/conversation-setup`) with `scenario_id=podcast_host_guest` | TODO | | `grep "podcast_host_guest\|podcast" app/src/app/index.tsx` |
| P2.3 | If `conversation-review.tsx` does not render per-host-dimension scores: add 5 `ScoreBar` components (Curiosity, Follow-Up Quality, Not Self-Referencing, Transition, Summary Skill) from the review payload | TODO | | `grep "curiosity\|followup_quality\|summary_skill" app/src/app/conversation-review.tsx` (if review renders them) OR note DEFERRED if already handled |
| P2.4 | Co-located test or addition to existing conversation test: assert the home card renders the podcast scenario title; assert navigation params carry the correct `scenario_id` | TODO | | `make poc-app-test` green (new assertion counted) |
| P2.5 | `make poc-app-test` green after all P2 | TODO | | `make poc-app-test` → lint + typecheck + jest all pass |

---

## P3 — End-to-end verify

*Checkpoint:* 5 host turns submitted → guest responds with branching script → review shows 5 host-dimension scores + better follow-up examples.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | Backend E2E: simulate 5 host turns via the conversation API (or a direct `score_conversation_review` call with 5 crafted turns — one curious, one self-referencing, one generic, one summary, one transition); confirm review has `curiosity`, `followup_quality`, `not_self_referencing`, `transition`, `summary_skill` scores; confirm `better_followup_examples` non-empty when follow-ups were generic | TODO | | `python3 -c "from services.api.domain.podcast_host import score_conversation_review; r=score_conversation_review([{'host_text':'Why did you build this?','prior_guest_text':'I built it after burnout'},{'host_text':'I also built something once','prior_guest_text':'The data surprised me'},{'host_text':'You mentioned patterns','prior_guest_text':'patterns are key'},{'host_text':'So you are saying it is a mirror','prior_guest_text':'like a mirror'},{'host_text':'Building on your point about permission','prior_guest_text':'permission was the product'}]); assert r['overall_score']>0"` |
| P3.2 | Full `make poc-api-test` + `make poc-app-test` green | TODO | | `make poc-api-test && make poc-app-test` |
| P3.3 | Update `docs/plans/poc-implementation-progress.md` to mark POC 15 `DONE` | TODO | | `grep "POC 15\|poc-15" docs/plans/poc-implementation-progress.md` |

---

## Decisions & notes

- **No new infrastructure** — this is the hardest constraint for this POC and the clearest path to shipping it quickly. The conversation engine, multi-turn routing, review screen, and session persistence are all from POC 04. This POC adds only scenario data + a domain scoring module + a home card.
- **Guest branching is keyword-triggered, not LLM.** The `dominant_trigger` value from `score_host_turn` tells the conversation engine which of the 5 guest response scripts to use. If the engine's turn-dispatch already supports a `trigger → script` map, wire `dominant_trigger` directly. If the POC 04 engine uses a different dispatch model, add a thin adapter in `podcast_host.py` (a `pick_guest_response(scenario, trigger) -> str` function) that maps `dominant_trigger` to the right script text. Do not change the conversation engine's core dispatch.
- **Order of trigger matching matters.** `specific_followup` is checked first (highest quality behavior), then `self_reference` (penalty path), then `summary_attempt`, then `transition`, then `generic`. This means a question that is both specific and contains a self-reference token still gets the high-quality response (the model rewards the better behavior).
- **`followup_quality_score` stopwords.** Use a minimal stopword list: `{"the","a","an","is","was","are","were","i","you","we","they","he","she","it","of","in","to","and","or","but","for","on","at","by","with","from","that","this","have","has","had","do","did","not","be","been","will","would","could","should"}`. The overlap check after stopword removal is more meaningful than raw word overlap.
- **Review screen dim scores.** `curiosity`, `followup_quality`, `not_self_referencing`, `transition`, `summary_skill` in the review payload use the same key names as in the host rubric JSON above, so the frontend can render them with a generic loop without hardcoding labels — each key maps to a display label (`followup_quality` → "Follow-Up Quality", `not_self_referencing` → "Not About You", etc.).
- **P2.3 is conditional.** If POC 04's review screen already renders dimension scores, P2.3 is a no-op (mark DONE immediately with the verification confirming the grep matches). If it only renders a single overall score, the 5 ScoreBars must be added.
- **`better_followup_example` canned templates.** Each template references a real phrase from `prior_guest_text` to make the suggestion feel grounded. Example: if prior guest text contains "emotional patterns", the suggestion could be: `"Try: 'You mentioned emotional patterns — what does that data actually look like for a founder?'"`. The template picks the first noun phrase (4+ char word) from `prior_guest_text` as the anchor. This is deterministic and requires no NLP.
- **Existing golden fixtures stay byte-identical.** `podcast_host.py` is a new module; the new scenario entry in `conversation_scenarios.json` is append-only.
