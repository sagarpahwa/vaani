# ADR 0002 — Profession Buckets: REAL vs MAPPED, sourced from Wikidata coverage

- **Status:** Accepted
- **Date:** 2026-05-31
- **Deciders:** Vaani founder
- **Relates to:** [ADR 0001](0001-intelligent-archetype-router.md) (this ADR supplies the
  archetypes + data-sufficiency the router consumes)

## Context

`candidate_speakers` was skewed: ~11k rows but only **4 professions** populated
(activist, academic, business_leader, politician), because `ingest_wikidata.py` iterates
occupations sequentially and stops at a single global `--max-records` — early occupations
eat the whole budget. Target is **1,000–10,000 real exemplars per profession**, no
fabrication.

We probed Wikidata coverage to learn what is actually achievable (see Appendix C for
method/endpoint/query).

## Findings

- Master table = **10,673 occupations**, counting distinct `wdt:P31 wd:Q5` humans with an
  English Wikipedia article, grouped by `wdt:P106`.
- **349 occupations have ≥1,000** such people (440 ≥700, 546 ≥500). Building 100 real
  buckets is easy.
- Coverage is **asymmetric**: deep historical/political/cultural/academic roles are dense
  (politician 305k, writer 130k, actor 112k, lawyer 52k); **modern corporate/soft roles
  are near-empty** (product manager 15, technology evangelist 27, negotiator 7, most of
  Marketing = 0).
- **A `0` is not "nobody in this role can speak."** Notable speakers in modern/narrow roles
  are catalogued under their *bigger* identity (an "HR leader" who speaks well is filed as
  businessperson / psychologist / activist). The **learner identity** and the **data
  anchor** are two different things.

## Decision

1. **Decouple identity from anchor.** Every bucket is tagged:
   - **REAL** — ≥1,000 catalogued exemplars; harvest directly from its Wikidata occupation.
   - **MAPPED** — thin/empty modern identity; kept as a first-class row, but exemplars are
     sourced from a **parent REAL archetype** (+ a curated/non-Wikidata list later). Never
     dropped, never fabricated.
2. **100 buckets** across 10 families (Appendix B): **72 REAL + 28 MAPPED**. The founder's
   origin roles (founder, CEO, product, sales/marketing, negotiator, storyteller,
   psychologist, teacher, tech-evangelist, philosopher, …) are all present — thin ones as
   MAPPED with a real parent.
3. **Bounds:** harvest **1,000–10,000 per REAL bucket**; cap giant pools (politician,
   writer, actor, journalist, military…) at 10k so they don't starve others; floor 1,000
   (relax to 700 only where a role is strategically required and just short).
4. **Ingest rework** (`ingest_wikidata.py`): switch fetch backend to **QLever**
   (`https://qlever.dev/api/wikidata`); **round-robin per-profession quotas** instead of a
   global budget; write a fine-grained **`profession`** field (not just
   `profession_category`); add **`--count-only`** and resumable checkpoints; keep co-located
   tests + ≥70% coverage so CI stays green.
5. **P1 harvest target = the founder's 20** (Appendix A) — the solo-founder→YC
   communication set. If the product can't make the founder a great speaker, it can't help
   anyone. All 20 are gatherable now (MAPPED rows harvest their REAL parent).

## Consequences

- ~**72 REAL** buckets × 1k–10k, de-duped across shared pools → realistically
  **~300k–400k** real candidate rows — past the original 200k goal, zero fabrication.
- **28 MAPPED** identities stay first-class and get a real learning source via their parent;
  they are also exactly the rows the ADR-0001 router will *compose blends* for.
- Non-Wikidata sourcing (Crunchbase/curated speaker lists) becomes a **separate later
  track** for the modern-corporate long tail — not a blocker for P1.
- `profession_taxonomy` grows from 22 → 100 rows (REAL/MAPPED + parent fields); a
  data-sufficiency metric per profession feeds the router.

## Alternatives considered

- **Broaden occupation mapping** (map execs onto "negotiator"/"product manager" labels to
  fake counts). **Rejected** — fabrication; pollutes training data.
- **Drop empty/thin roles.** Rejected — they are the learner identities the product must
  serve; MAPPED preserves them honestly.
- **One flat global budget (status quo).** Rejected — root cause of the skew.

---

## Appendix A — P1 harvest: the founder's 20

Skill the founder gains ← archetype harvested (parent for MAPPED) · count · type.

```
 1 Founder conviction & origin story    Entrepreneur/Founder        11,052  REAL
 2 Executive presence & command         Business leader             36,988  REAL
 3 Investor/VC pitch                     Investor → 1 + Biz-exec      4,675  MAPPED
 4 Product vision & roadmap clarity      Product leader → 1 + Engineer 21,369 MAPPED
 5 Selling & objection handling          Sales → Lawyer + Spokesperson 51,590 MAPPED
 6 Customer empathy & CX voice           CX → Psychologist + Spokesperson 6,397 MAPPED
 7 Audience building / influencer reach   Digital creator (YouTuber)   1,946  REAL
 8 Negotiation & win-win framing         Negotiator → Diplomat + Activist 24,682 MAPPED
 9 Emotional intelligence, read a room    Psychologist                 6,397  REAL
10 People leadership & motivating a team  People manager               1,946  REAL
11 Narrative & storytelling for pitches   Storyteller → Author + Voice actor 129,552 MAPPED
12 Keynote / motivational oratory         Motiv. speaker → Activist + Author 6,222 MAPPED
13 Charisma, timing, disarm a room        Comedian                     5,981  REAL
14 Debate sharpness & tough Q&A           Debater → Politician + Lawyer 305,037 REAL
15 Media-ready: interviews & podcasts     Interviewer (Journalist)    59,017  REAL
16 Thought leadership & strong POV        Columnist / Author          10,487  REAL
17 Visionary / futurist framing           Tech evangelist → 1 + Comp-sci 6,662 MAPPED
18 Explain complex ideas simply           Educator (Univ. professor)  68,573  REAL
19 Reason aloud from first principles     Philosopher                 13,598  REAL
20 Coaching & feedback register           Coach / Corporate trainer    4,044  REAL
```
12 REAL + 8 MAPPED · 1k–10k each, de-duped → ~20k–70k rows.

## Appendix B — the 100 buckets (count = Wikidata anchor; → = MAPPED parent)

```
A Founders & Business        1 Entrepreneur/Founder 11,052 R · 2 Business leader 36,988 R ·
  3 CEO 1,565 R · 4 Business executive 4,675 R · 5 Banker 5,730 R · 6 Investor/VC 382 →1,4 ·
  7 Product manager 15 →1,45 · 8 Strategy consultant 53 →4 · 9 People manager 1,946 R ·
  10 Sales/GTM 22 →2,11
B Marketing & Comms          11 Marketer 244 →14,51 · 12 Brand strategist 0 →11,4 ·
  13 PR professional 99 →14 · 14 Spokesperson 228 →21,51 · 15 Comms director 64 →14 ·
  16 Creative director 135 →73 · 17 Copywriter/Speechwriter 114 →61 · 18 Growth/Content mktr 0 →58 ·
  19 Campaign strategist 0 →28 · 20 Brand ambassador/Evangelist 66 →1,14
C Public Leadership          21 Politician 305,037 R · 22 Diplomat 24,682 R · 23 Civil servant 9,179 R ·
  24 Activist 6,222 R · 25 Human rights defender 3,252 R · 26 Union leader 5,961 R ·
  27 Environmentalist 1,910 R · 28 Political scientist 5,855 R · 29 Social reformer 387 →24 ·
  30 Peace negotiator/Mediator 951 →22,24
D Education & Thought        31 Teacher 16,562 R · 32 University professor 68,573 R · 33 Academic 10,212 R ·
  34 Lecturer 1,070 R · 35 Education reformer 4,863 R · 36 Historian 29,513 R · 37 Economist 14,248 R ·
  38 Philosopher 13,598 R · 39 Sociologist 5,454 R · 40 Anthropologist 5,991 R
E Science & Technology       41 Researcher 13,760 R · 42 Physicist 11,908 R · 43 Mathematician 13,999 R ·
  44 Computer scientist 6,662 R · 45 Engineer 21,369 R · 46 Inventor 4,939 R · 47 Biologist 8,903 R ·
  48 Chemist 8,324 R · 49 AI/Data scientist 423 →44 · 50 Futurist/Tech evangelist 82 →1,44
F Media & Broadcasting       51 Journalist 59,017 R · 52 Editor 8,575 R · 53 Columnist 4,846 R ·
  54 TV presenter 10,269 R · 55 Radio host 5,498 R · 56 Sports commentator 1,813 R ·
  57 Podcast host 1,346 R · 58 YouTuber 1,946 R · 59 Influencer 533 →58 · 60 Publisher 5,375 R
G Writers & Storytellers     61 Author/Writer 129,552 R · 62 Novelist 20,803 R · 63 Poet 38,548 R ·
  64 Playwright 11,007 R · 65 Screenwriter 37,035 R · 66 Children's author 6,518 R ·
  67 Translator 16,664 R · 68 Storyteller/Narrator 331 →61,74 · 69 Essayist 10,487 R · 70 Literary critic 5,808 R
H Performing Arts            71 Film actor 46,784 R · 72 Stage actor 19,509 R · 73 Television actor 39,892 R ·
  74 Voice actor 7,804 R · 75 Comedian 5,981 R · 76 Stand-up/MC 734 →75 · 77 Film director 37,710 R ·
  78 Singer 55,284 R · 79 Musician 43,243 R · 80 Motivational speaker 545 →24,61
I Healthcare & Wellness      81 Physician 21,475 R · 82 Surgeon 4,433 R · 83 Psychiatrist 2,424 R ·
  84 Psychologist 6,397 R · 85 Public health 925 →81 · 86 Therapist/Counselor 640 →84 ·
  87 Coach/Trainer 4,044 R · 88 Nutritionist 330 →81 · 89 Fitness/Yoga 143 →87 · 90 Mental health advocate 20 →84,24
J Law, Faith & Specialized   91 Lawyer 51,590 R · 92 Judge/Jurist 23,553 R · 93 Legal scholar 1,131 R ·
  94 Human/Civil rights lawyer 39 →91,24 · 95 Faith leader (priest) 22,392 R · 96 Theologian 9,708 R ·
  97 Monk 1,859 R · 98 Philanthropist 2,558 R · 99 Military leader 55,196 R · 100 Architect 16,086 R
```
R = REAL (≥1,000, harvest directly). `→ n` = MAPPED, harvest parent bucket(s) n. Counts cap
at 10,000 on harvest.

## Appendix C — reproduce the counts

Endpoint: **`https://qlever.dev/api/wikidata`** (POST form `query=`, header
`Accept: application/sparql-results+json`). The master occupation→count table:

```sparql
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX schema: <http://schema.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?occ ?occLabel (COUNT(DISTINCT ?item) AS ?c) WHERE {
  ?item wdt:P31 wd:Q5 ; wdt:P106 ?occ .
  ?a schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> .
  ?occ rdfs:label ?occLabel . FILTER(LANG(?occLabel) = "en")
} GROUP BY ?occ ?occLabel ORDER BY DESC(?c)
```

A multi-occupation bucket's count is a `DISTINCT` union over its QIDs (people in several
occupations counted once).
