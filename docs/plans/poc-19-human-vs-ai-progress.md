# POC 19 — Human vs AI Twin — Implementation Progress Tracker

> **This file is the committed, resumable source of truth for POC 19.**
> It is authoritative across sessions — not in-session memory, not the TaskList.

---

## HOW TO RESUME (agent: read this block FIRST, every run)

You were told: *"implement this plan"* (pointing at this file or at
[`poc-19-human-vs-ai-plan.md`](poc-19-human-vs-ai-plan.md)). Do exactly this:

1. **Read the plan:** [`docs/plans/poc-19-human-vs-ai-plan.md`](poc-19-human-vs-ai-plan.md) — the
   full approved design. This tracker is its checklist.
2. **Read this whole file** — find the **first sub-task whose status is not `DONE`** in the
   tables below. That is where you resume.
3. **Re-verify the last `DONE` row actually landed** before continuing (run its *Verify*
   command / confirm the file exists). A session can die between writing code and committing,
   so the last row marked `DONE` might not be on disk. If it didn't land, redo **only** that
   one step. **Never redo work already `DONE` and verified.**
4. Work **one atomic sub-task at a time**: do it → run its *Verify* → set status `DONE` +
   record the commit SHA → **`git commit` the code and this tracker together** (branch
   `feat/poc-19-human-vs-ai`, conventional commit) → next row. Never batch multiple sub-tasks
   into one commit.
5. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but **this committed
   file is authoritative** — reconcile against it, not against memory.

**Status legend:** `TODO` (not started) · `DOING` (in flight, not committed) · `DONE` (committed; SHA recorded) · `DEFERRED` (committed decision to skip; blocker recorded).

---

## Key constraints (do not violate — full detail in the plan & CLAUDE.md)

- **Base branch:** `feat/poc-18-pause-gym` → new branch `feat/poc-19-human-vs-ai`
- **No LLM required.** Deterministic transformation path works fully offline. LLM is opt-in via
  `PROVIDER_LLM` — its absence never breaks the flow.
- **Additive, zero regression.** Mode A/B + persona golden fixtures stay byte-identical.
- **No new DB collection.** The `/human-vs-ai/transform` endpoint is stateless.
- **Python env:** `.venv-poc` only. **Keep green:** `make poc-api-lint && make poc-api-test`
  (coverage ≥70%) and `make poc-app-test`.
- **Git identity:** personal SSH host `github.com-personal` / username `sagarpahwa`.

---

## P0 — Docs / resumability scaffold

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | In-repo copy of this plan → `docs/plans/poc-19-human-vs-ai-plan.md` | TODO | | `test -f docs/plans/poc-19-human-vs-ai-plan.md` |
| P0.2 | This resumable tracker → `poc-19-human-vs-ai-progress.md` | TODO | | `test -f docs/plans/poc-19-human-vs-ai-progress.md` |
| P0.3 | Link milestone from `docs/plans/poc-implementation-progress.md` | TODO | | `grep poc-19-human-vs-ai docs/plans/poc-implementation-progress.md` |

---

## P1 — Backend domain: ideal version transformation

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | `services/api/domain/ideal_version.py` — `GapAnalysis` dataclass + `IdealVersionResult` dataclass | TODO | | `python3 -c "from services.api.domain.ideal_version import GapAnalysis, IdealVersionResult; print('ok')"` |
| P1.2 | Rule 1 — `_strip_fillers(text, filler_words) → tuple[str, int]` | TODO | | Unit test: "um I think like this is great" → "I think this is great", count=2 |
| P1.3 | Rule 2 — `_shorten_long_sentences(text) → tuple[str, int]` | TODO | | Unit test: 30-word sentence with comma at word 18 → split into two shorter sentences |
| P1.4 | Rule 3 — `_add_pause_markers(text, max_markers=3) → tuple[str, int]` | TODO | | Unit test: sentence with "the key is" → " [pause]" appended |
| P1.5 | Rule 4 — `_convert_passive(text) → tuple[str, int]` | TODO | | Unit test: "The app was built by our team" → "our team built it", count=1 |
| P1.6 | Rule 5 — `_improve_opener(text) → tuple[str, bool]` | TODO | | Unit test: 25-word first sentence with "and" at word 12 → shortened |
| P1.7 | Rule 6 — `_improve_closer(text) → tuple[str, bool]` | TODO | | Unit test: neutral last sentence → "And that is what matters." appended |
| P1.8 | `generate_ideal_version(text, filler_words=None) → IdealVersionResult` — chains all 6 rules, builds `GapAnalysis`, selects `retry_paragraph` | TODO | | Unit test: realistic paragraph → ideal_text noticeably shorter + gap_analysis counts correct |
| P1.9 | Unit tests `test_ideal_version.py` — ≥12 cases (empty, only fillers, no fillers, long sentence, short sentences, claim marker, max 3 markers, passive, no passive, opener >20w, closer with conviction marker, gap_analysis.summary non-empty) | TODO | | `pytest services/api/tests/test_ideal_version.py -v` → ≥12 passed |

---

## P2 — Backend API: human vs AI route

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | `services/api/routes/human_vs_ai.py` — `TransformRequest` + `TransformResponse`; `POST /human-vs-ai/transform`; 400 on empty text | TODO | | `curl -X POST localhost:8090/human-vs-ai/transform -d '{"text":"um test"}' → 200` |
| P2.2 | Register `human_vs_ai.router` in `services/api/app.py` | TODO | | `curl localhost:8090/docs` shows `/human-vs-ai/transform` |
| P2.3 | API tests `test_api_human_vs_ai.py` — ≥5 cases (valid → different ideal_text, empty → 400, no fillers → count=0, with fillers → count>0, retry_paragraph non-empty) | TODO | | `pytest services/api/tests/test_api_human_vs_ai.py -v` → ≥5 passed |

---

## P3 — Frontend: human vs AI screen

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | `app/src/api/types.ts` — `TransformRequest`, `GapAnalysis`, `IdealVersionResult` | TODO | | `make poc-app-test` → typecheck clean |
| P3.2 | `app/src/api/client.ts` — `transformSpeech(req)` | TODO | | `make poc-app-test` → new client test passes |
| P3.3 | `app/src/app/human-vs-ai.tsx` — text input, "Transform" button, loading state, error banner, shows `ComparisonView` | TODO | | `make poc-app-test` green |
| P3.4 | `app/src/ui/ComparisonView.tsx` — YOUR VERSION panel + IDEAL VERSION panel (with `ReadAloudButton`) + GAP ANALYSIS section + RETRY PARAGRAPH section | TODO | | `ComparisonView.test.tsx` ≥4 cases pass |
| P3.5 | Register `/human-vs-ai` route in `_layout.tsx` ("Human vs AI Twin") | TODO | | `make poc-app-test` green |
| P3.6 | Home `index.tsx` — add "Human vs AI Twin" card with "See your ideal self" | TODO | | Card visible on home; `make poc-app-test` green |

---

## P4 — E2E verify

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P4.1 | Paste filler-heavy 30-word sentence → ideal_text noticeably cleaner; gap analysis chips show correct counts | TODO | | `ComparisonView` renders meaningful diff |
| P4.2 | Press "Listen" → ideal version spoken aloud via expo-speech | TODO | | Speech plays without error |
| P4.3 | Paste empty text → 400 error banner; no crash | TODO | | Error banner renders gracefully |
| P4.4 | Mode A/B + persona flows still work (regression check) | TODO | | Mode A session scores correctly |
| P4.5 | `make poc-api-test` green; `make poc-app-test` green | TODO | | Both test suites pass |

---

## Decisions & open notes

- `retry_paragraph`: split into paragraphs, zip original vs ideal, return paragraph with largest
  word-count delta. Single-paragraph input → return full `ideal_text`.
- `ReadAloudButton` component already exists from P6e-2; check path before creating a new one.
- Passive conversion is intentionally limited — errs on the side of no-op when uncertain.
- LLM opt-in: `PROVIDER_LLM` gate; deterministic result always computed first as fallback.
