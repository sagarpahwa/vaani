# POC 19 — Human vs AI Twin — Implementation Plan

> **This file is the committed, resumable source of truth for POC 19.**
> It is authoritative across sessions — not in-session memory, not the TaskList.

---

## HOW TO RESUME (agent: read this block FIRST, every run)

You were told: *"implement this plan"* (pointing at this file or at the progress tracker).
Do exactly this:

1. **Read the companion progress tracker** `poc-19-human-vs-ai-progress.md` — find the
   **first sub-task whose status is not `DONE`** in the tables there. That is where you resume.
2. **Re-verify the last `DONE` row actually landed** before continuing (run its *Verify* command /
   confirm the file exists). A session can die between writing code and committing.
3. Work **one atomic sub-task at a time**: do it → run its *Verify* → set status `DONE` + record
   the commit SHA → **`git commit` the code and the progress tracker together** → next row.
4. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but the **committed
   progress tracker is authoritative**.

**Status legend:** `TODO` · `DOING` · `DONE` (SHA recorded) · `DEFERRED` (blocker recorded)

---

## KEY CONSTRAINTS (never violate — full rules in CLAUDE.md)

- **Base branch:** `feat/poc-18-pause-gym` → new branch `feat/poc-19-human-vs-ai`
- **No LLM required.** The deterministic transformation path (filler removal, sentence shortening,
  passive→active, opener/closer improvement) must work fully offline. LLM enhancement is an
  opt-in path gated by `PROVIDER_LLM` env var — its absence never breaks the flow.
- **Additive, zero regression.** Mode A/B + persona golden fixtures stay byte-identical. The
  new `human_vs_ai` route and `domain/ideal_version.py` are entirely separate from the pipeline.
- **Hard DB isolation.** Mock DB only: port **27018**. Never touch port 27017.
- **No new collection needed** — this feature is stateless (transform and return; no persistence
  required for the POC). If caching ideal versions is desired later, a collection can be added.
- **Python env:** `.venv-poc` only. **Keep green:** `make poc-api-lint && make poc-api-test`
  (coverage ≥70%) and `make poc-app-test`.
- **Git identity:** personal SSH host `github.com-personal` / username `sagarpahwa`.
- **Anti-ElevenLabs positioning.** This demo's message is: "AI shows your ideal self and helps
  you become it." The ideal version should feel meaningfully cleaner — not slightly tweaked.
  The transformation rules must produce a noticeable improvement on typical user input.

---

## Purpose

User pastes (or records + auto-transcribes) a short speech. The app shows side-by-side: the user's
original version with an analysis (filler count, long sentences, passive voice instances) vs a
deterministically improved "ideal version". A gap analysis explains what changed. The user can
also press "Listen" to hear the ideal version read aloud via expo-speech. A "Retry" panel lets
the user re-deliver one specific improved paragraph.

**Why deterministic transformation is enough:** the goal is to demonstrate the coaching concept
("here is your current self vs your ideal self"), not to produce publication-quality prose.
Deterministic rules produce a clearly cleaner version reliably without cloud credentials. LLM
enhancement plugs in later via `PROVIDER_LLM`.

---

## Architecture notes

### Transformation rules in `domain/ideal_version.py`

Applied in order; each rule is a pure function taking and returning a string:

1. **Strip fillers** — tokenize, remove words in `FILLER_WORDS` (from `providers/base.py`),
   rejoin. Preserves sentence structure.
2. **Shorten long sentences** — find sentences > 25 words (split on `.?!`); if a natural comma
   or "and/but/because/which" exists past word 15, split there; else truncate to first clause.
3. **Add strategic pause markers** — after sentences containing high-confidence claim markers
   ("the key is", "the result", "in other words", "most importantly", "the truth is",
   "what this means", "the bottom line"), append ` [pause]`. Max 3 added per text.
4. **Passive→active conversion** — apply a small set of regex replacements for common patterns:
   `"was (built|created|done|made|developed|launched|released|designed|written|published)
   by ([A-Z][a-z]+)"` → `"\2 \1 it"` (simplified; flag and log conversion count). Aims for
   obvious cases only — no NLP dependency.
5. **Improve opener** — if the first sentence is > 20 words, shorten it to the first
   subject+verb+object clause (split at first comma or "and/but/because"). Never removes the
   first sentence entirely.
6. **Improve closer** — if the last sentence does not end with a conviction marker
   (does not contain "is", "will", "must", "matters", "key", "future" or similar), append
   " And that is what matters."

**`GapAnalysis` dataclass:**
- `fillers_removed: int` — count of filler words stripped
- `sentences_shortened: int` — count of sentences split or shortened
- `pause_markers_added: int` — count of `[pause]` markers inserted
- `passive_converted: int` — count of passive patterns rewritten
- `opener_improved: bool`
- `closer_improved: bool`
- `summary: str` — one human-readable sentence, e.g.:
  "Removed 3 fillers, shortened 2 long sentences, added 1 pause marker."

**`IdealVersionResult` dataclass:**
- `original_text: str`
- `ideal_text: str`
- `gap_analysis: GapAnalysis`
- `retry_paragraph: str` — the single paragraph that changed the most (by word-count delta);
  the user is encouraged to re-deliver this one paragraph

### Route

`services/api/routes/human_vs_ai.py`:
- `POST /human-vs-ai/transform` body: `{text: str, goal_context?: str}` → `IdealVersionResult`
  serialized to JSON
- No DB access needed. Pure domain call.

---

## P0 — Docs / resumability scaffold

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | In-repo copy of this plan → `docs/plans/poc-19-human-vs-ai-plan.md` | TODO | | `test -f docs/plans/poc-19-human-vs-ai-plan.md` |
| P0.2 | Resumable progress tracker → `docs/plans/poc-19-human-vs-ai-progress.md` | TODO | | `test -f docs/plans/poc-19-human-vs-ai-progress.md` |
| P0.3 | Link milestone from `docs/plans/poc-implementation-progress.md` | TODO | | `grep poc-19-human-vs-ai docs/plans/poc-implementation-progress.md` |

---

## P1 — Backend domain: ideal version transformation

*Checkpoint:* `generate_ideal_version` applies all 6 rules correctly; 10+ unit test cases pass.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | `services/api/domain/ideal_version.py` — `GapAnalysis` dataclass + `IdealVersionResult` dataclass; import `FILLER_WORDS` from `providers/base` (no circular import — domain does NOT import from providers; pass filler_words as a parameter with a default) | TODO | | `python3 -c "from services.api.domain.ideal_version import GapAnalysis, IdealVersionResult; print('ok')"` |
| P1.2 | Rule 1 — `_strip_fillers(text, filler_words) → tuple[str, int]` (returns cleaned text + count removed). Case-insensitive. Preserves sentence capitalization. | TODO | | Unit test: "um I think like this is great" → "I think this is great", count=2 |
| P1.3 | Rule 2 — `_shorten_long_sentences(text) → tuple[str, int]` (returns text with shortened sentences + count shortened). Split on `.?!`; for sentences > 25 words: find first comma/conjunction past word 15 and split. | TODO | | Unit test: 30-word sentence with comma at word 18 → split into two shorter sentences |
| P1.4 | Rule 3 — `_add_pause_markers(text, max_markers=3) → tuple[str, int]` (returns text with `[pause]` appended after claim-marker sentences + count added). | TODO | | Unit test: sentence containing "the key is" → " [pause]" appended |
| P1.5 | Rule 4 — `_convert_passive(text) → tuple[str, int]` (returns text with passive patterns converted + count). Apply regex replacements for common was/were + past participle + "by" patterns. Gracefully handles zero matches. | TODO | | Unit test: "The app was built by our team" → "our team built it", count=1 |
| P1.6 | Rule 5 — `_improve_opener(text) → tuple[str, bool]` (returns text with shortened first sentence if > 20 words + bool changed). | TODO | | Unit test: 25-word first sentence with "and" at word 12 → first sentence shortened |
| P1.7 | Rule 6 — `_improve_closer(text) → tuple[str, bool]` (returns text with conviction appended if last sentence lacks conviction markers + bool changed). | TODO | | Unit test: neutral last sentence → "And that is what matters." appended |
| P1.8 | `generate_ideal_version(text, filler_words=None) → IdealVersionResult` — chains all 6 rules, builds `GapAnalysis`, selects `retry_paragraph` (paragraph with largest word-count delta from before→after), returns `IdealVersionResult` | TODO | | Unit test: realistic short speech paragraph → ideal_text noticeably shorter + gap_analysis counts correct |
| P1.9 | Unit tests `services/api/tests/test_ideal_version.py` — ≥10 cases: (a) empty text → unchanged, (b) text with only fillers → all stripped, (c) no fillers → original unchanged by rule 1, (d) single long sentence → shortened, (e) short sentences → unchanged by rule 2, (f) sentence with claim marker → pause marker added, (g) max 3 pause markers respected, (h) passive pattern converted, (i) no passive pattern → unchanged, (j) first sentence > 20 words → opener improved, (k) last sentence conviction marker already present → closer unchanged, (l) gap_analysis.summary is non-empty string | TODO | | `pytest services/api/tests/test_ideal_version.py -v` → ≥12 passed |

---

## P2 — Backend API: human vs AI route

*Checkpoint:* `POST /human-vs-ai/transform` returns `IdealVersionResult` with correct gap analysis.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | `services/api/routes/human_vs_ai.py` — `TransformRequest` + `TransformResponse` (serializes `IdealVersionResult` fields); `POST /human-vs-ai/transform`; validate text is non-empty (400 if empty) | TODO | | `curl -X POST localhost:8090/human-vs-ai/transform -H 'Content-Type: application/json' -d '{"text":"um I think this is like a test"}' → 200` |
| P2.2 | Register `human_vs_ai.router` in `services/api/app.py` | TODO | | `curl localhost:8090/docs` shows `/human-vs-ai/transform` |
| P2.3 | API tests `services/api/tests/test_api_human_vs_ai.py` — (a) valid speech → `ideal_text` differs from input + gap_analysis non-zero, (b) empty text → 400, (c) text with no fillers → `fillers_removed == 0`, (d) text with fillers → `fillers_removed > 0`, (e) `retry_paragraph` is non-empty string | TODO | | `pytest services/api/tests/test_api_human_vs_ai.py -v` → ≥5 passed |

---

## P3 — Frontend: human vs AI screen

*Checkpoint:* `/human-vs-ai` renders side-by-side comparison; read-aloud button works.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | `app/src/api/types.ts` — add `TransformRequest`, `GapAnalysis`, `IdealVersionResult` wire types | TODO | | `make poc-app-test` → typecheck clean |
| P3.2 | `app/src/api/client.ts` — `transformSpeech(req: TransformRequest) → Promise<IdealVersionResult>` | TODO | | `make poc-app-test` → new client test passes |
| P3.3 | `app/src/app/human-vs-ai.tsx` — (a) multiline text input for user speech paste, (b) "Transform" button → `transformSpeech` → show `ComparisonView`, (c) loading state while API call in flight, (d) error banner on failure | TODO | | `make poc-app-test` green |
| P3.4 | `app/src/ui/ComparisonView.tsx` — stacked or side-by-side layout (stacked on mobile viewport): YOUR VERSION panel (original text + analysis chips: "{n} fillers", "{n} long sentences") vs IDEAL VERSION panel (ideal_text + `ReadAloudButton` using existing `expo-speech` wrapper from `audio/speech.ts`) + GAP ANALYSIS section (summary sentence + chip row for each non-zero gap dimension) + RETRY PARAGRAPH section (retry_paragraph in a highlighted `Card` with a copy prompt "Try saying this paragraph again") | TODO | | `ComparisonView.test.tsx` ≥4 cases pass (fillers removed, no change, retry paragraph shown, read-aloud button present when ideal_text non-empty) |
| P3.5 | Register `/human-vs-ai` route in `app/src/app/_layout.tsx` (`Stack.Screen` title "Human vs AI Twin") | TODO | | `make poc-app-test` green |
| P3.6 | Home `index.tsx` — add "Human vs AI Twin" card with description "See your ideal self" → `/human-vs-ai` | TODO | | Card visible on home; `make poc-app-test` green |

---

## P4 — E2E verify

*Checkpoint:* paste speech → see meaningful ideal version → read-aloud works.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P4.1 | Start API + app; navigate to `/human-vs-ai`; paste: "Um so basically what we built is like a product that was created by our team and it was basically designed to help people you know manage their time and I think it really like does that well you know" → submit | TODO | | `ComparisonView` renders with `ideal_text` noticeably shorter and cleaner |
| P4.2 | Verify gap_analysis chips show correct counts (fillers removed, sentences shortened, passive converted) | TODO | | Chip "Removed X fillers" matches visible diff |
| P4.3 | Press "Listen" → expo-speech reads the ideal version aloud (on web this uses the browser's speechSynthesis) | TODO | | Ideal version is spoken aloud (or gracefully silent if not on a web browser with speech support) |
| P4.4 | Paste empty text → submit → 400 error banner shown; no crash | TODO | | Error banner renders |
| P4.5 | Confirm Mode A/B + persona flows still work (regression check) | TODO | | Mode A session scores correctly |
| P4.6 | `make poc-api-test` green (coverage ≥70%); `make poc-app-test` green | TODO | | Both test suites pass |

---

## Acceptance criteria

- User pastes a speech; app returns improved ideal version with gap analysis
- Gap analysis shows: fillers removed, sentences shortened, pause markers added, passive converted
- "Listen" button speaks the ideal version via expo-speech
- "Retry" panel highlights one specific paragraph for the user to re-practice
- All transformation rules applied deterministically, no LLM required
- `make poc-api-test` + `make poc-app-test` green

---

## Decisions & notes

- The `retry_paragraph` selection heuristic: split both `original_text` and `ideal_text` into
  paragraphs (split on double newline or every 3 sentences as a fallback), zip them, compute
  word-count delta for each pair, return the `ideal_text` paragraph with the largest delta. If
  only one paragraph, return the full `ideal_text`.
- The `ReadAloudButton` component already exists from P6e-2 of the main coaching app
  (`app/src/ui/ReadAloudButton.tsx` or similar). `ComparisonView` imports and reuses it directly.
  Check the existing component path before creating a new one.
- Passive voice conversion is intentionally limited to obvious patterns to avoid false positives.
  A conversion that changes meaning is worse than no conversion. The rule errs on the side of
  doing nothing when uncertain.
- LLM opt-in: if `PROVIDER_LLM` is set in `.env.poc` to a supported provider (e.g. `anthropic`),
  the `generate_ideal_version` function can be extended to post-process the deterministic result
  through an LLM prompt ("Make this speech more natural while preserving all key claims"). The
  deterministic result is always computed first as a fallback.
