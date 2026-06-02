# ADR 0001 — Capability-Mediated Archetype Router (no hardcoded role map)

- **Status:** Accepted
- **Date:** 2026-05-31
- **Deciders:** Vaani founder
- **Context tags:** candidate ingestion, coaching, personalization

## Context

The product coaches anyone to become a better public speaker by letting them learn
from real exemplar speakers we have catalogued (`candidate_speakers`, harvested per
profession from Wikidata). We can only gather *sufficient training data* for archetypes
that are densely catalogued — politician, author, entrepreneur, lawyer, professor, etc.
(the **REAL** buckets, ≥1,000 exemplars each).

But learners describe themselves with modern, narrow, or invented titles —
"HR leader", "go-to-market strategist", "wellness coach", "campaign strategist",
"community manager", "growth marketer". A count of `0` for such a title does **not**
mean no such person can speak well. It means **great speakers in that role file
themselves under a bigger identity** (businessperson, psychologist, activist…). The
identity label and the data anchor are two different things.

We need to serve any incoming role, in real time, by deciding **which catalogued
archetype(s) that learner should learn from** — and when no single archetype fits,
**what combination** does.

## Decision

**We will NOT maintain a hardcoded `role → archetype` table.** It does not scale
(O(roles × archetypes) hand-maintenance), breaks on every new title, cannot express
blends, has no notion of whether we actually hold enough data to train against a target,
and never improves.

Instead we build a **capability-mediated semantic router**. The insight: a learner's
**role** and a catalogued **archetype** are both projected into one shared space — the
existing **25-entry `capability_taxonomy`** (vocal_command, story_arc_control,
evidence_based_persuasion, debate_sharpness, vision_framing, emotional_resonance,
teaching_simplicity, …). Roles are unbounded; capabilities are a fixed, small basis.

Three components:

1. **Archetype capability signature** — every archetype (the ~100 buckets) carries a
   weighted vector over the 25 capabilities, plus a **data-sufficiency score**
   (count of trainable exemplars we hold). Signatures are *data-derived*: aggregated
   from the capability scores of its exemplar speakers' analysed speeches. Cold-start
   is bootstrapped from coarse capability tags on `profession_taxonomy`, then refined as
   real scored speeches arrive.

2. **Role resolver** — at request time, a free-text title is resolved into a **target
   capability profile** (which capabilities a great *<role>* communicator needs) via
   embedding similarity against archetype descriptors + LLM decomposition. Unbounded
   input, zero config per new title.

3. **Selector / composer** — picks or composes archetypes whose signatures best cover
   the target profile, **subject to the data-sufficiency gate** (never route to an
   archetype we cannot actually train against):
   - one archetype clears the coverage threshold → **direct route**;
   - otherwise → **greedy set-cover blend** of ≤3 archetypes, each contributing the
     capabilities it is strongest *and* data-richest in, returned as weighted mix
     (e.g. *growth marketer* → persuasion[Marketer/Spokesperson] + audience[Influencer]
     + evidence[Data scientist]).

A **feedback loop** records which routes produced measured learner improvement and
refines signature weights and thresholds over time.

### Runtime algorithm (sketch)

```
route(title):
  target, conf   = resolve_role(title)              # → capability vector
  pool           = [a for a in archetypes if a.data_sufficiency >= FLOOR]
  scored         = [(a, cosine(a.signature, target)) for a in pool]
  best, s        = argmax(scored)
  if s >= TAU_DIRECT:        return [(best, 1.0)]    # direct map
  blend          = greedy_set_cover(target, pool, k_max=3, coverage>=THETA)
  return weighted(blend)                             # intelligent combination
  # cache(title → route); emit telemetry; collect outcome → refine
```

## Consequences

**Positive**
- Scales to any title with no per-role configuration; new archetypes plug in by
  publishing a signature + sufficiency score.
- Honest by construction: the sufficiency gate forbids routing to data we don't have.
- Expresses *blends*, matching the founder's "what combination serves them" requirement.
- Improves with use via the feedback loop.
- Reuses existing assets: `capability_taxonomy` (basis), `profession_taxonomy`
  (bootstrap tags), `candidate_speakers` (sufficiency + signatures), the POC scoring
  stack (capability scores), and telemetry (`release_health_events`).

**Costs / new work**
- A capability-signature pipeline (score exemplar speeches → aggregate per archetype).
- An embedding index over archetype descriptors (label, description, aliases, exemplars).
- A per-profession data-sufficiency metric on `candidate_speakers`.
- Threshold tuning (`TAU_DIRECT`, `THETA`, `FLOOR`, `k_max`).

**Phasing**
- **P1 (now):** harvest data for the first 20 founder-critical archetypes; compute
  data-sufficiency per profession. *(This ADR's immediate dependency.)*
- **P2:** bootstrap coarse archetype signatures from `profession_taxonomy` capability tags.
- **P3:** embedding role-resolver + direct routing.
- **P4:** set-cover blend/compose for unmatched roles.
- **P5:** feedback loop + signature refinement from scored speeches.

## Alternatives considered

- **Hardcoded `role → archetype` map.** Rejected: unscalable, brittle, no blends, no
  data-awareness, no learning. (This ADR exists to reject it explicitly.)
- **LLM free-form "who should I learn from" per request, no capability basis.** Rejected
  as the *primary* mechanism: non-deterministic, unauditable, can hallucinate archetypes
  we have no data for, no sufficiency guarantee. (LLM is used *inside* the resolver to
  decompose a title into the fixed capability basis, where its output is bounded.)
- **Pure embedding nearest-archetype, no capability layer.** Rejected: collapses to the
  single closest label, cannot compose blends, and ignores data-sufficiency.

## Open questions

- Capability-signature source of truth: scored exemplar speeches vs. hand tags vs.
  LLM-rated descriptions — likely a blend that shifts toward scored data over time.
- How the learner self-describes: free-text title vs. guided picker vs. both.
- Blend cap (`k_max=3`) and minimum per-archetype data floor (`FLOOR`) — tune in P3/P4.
