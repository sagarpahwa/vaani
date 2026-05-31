# Vaani POC Plan: Universal Coaching App + Live Reliability System

**Date:** May 31, 2026  
**Status:** Proposed for review  
**Owner:** Product + Engineering + Reliability  
**Scope:** React Native + Expo universal app (Android, iOS, web) with production-safe coaching platform

> **▶ IMPLEMENTATION IN PROGRESS — RESUME HERE:** Live, git-committed build progress is tracked in
> [`poc-implementation-progress.md`](./poc-implementation-progress.md). To continue an interrupted
> build, read that file first and start from the first task that is not `✅ DONE`. Do not redo
> completed (committed) work.

## 1) Executive Intent

Build a real speaking coach, not a demo, and launch it with guardrails strong enough that once features go live they do not silently degrade.

This plan therefore has two equal tracks:

1. **Product Delivery Track**: Guided and user-script coaching workflows.
2. **Reliability Track**: Quality gates, staged rollout, observability, rollback, and operational policy that prevents regressions from reaching users.

## 2) Non-Negotiable Outcomes

The POC succeeds only if all are true:

1. User completes end-to-end coaching on phone.
2. Feedback is goal-aware and actionable.
3. Full response can be read aloud.
4. Each critical correction has A/B audio:
   - how user said it
   - how it should sound
5. Retry loop shows measurable improvement.
6. Production reliability controls are active before broad rollout.

## 3) Product Scope

## 3.1 Mode A (POC Priority): System-Guided

1. User selects speaking goal profile.
2. App shows script.
3. User reads aloud.
4. System analyzes and coaches.
5. User hears full feedback and line-level A/B corrections.
6. User retries flagged lines.
7. System scores delta.

## 3.2 Mode B (POC Secondary): User-Provided Script

User provides:

- script
- occasion
- purpose

System runs the same coaching loop with context-aware evaluation.

## 4) Personalization Model

Each session has a **Goal Signature**:

- objective
- occasion
- audience context
- desired style
- language and duration

Goal Signature weights capability scoring so recommendations are directionally correct for that user outcome, not generic.

## 5) System Architecture (Single Codebase + Service Safety)

## 5.1 Frontend

- Expo + React Native + Expo Router.
- One codebase for Android, iOS, web.
- Audio capture/playback via `expo-audio`.
- Full feedback read-aloud via `expo-speech`.
- Feature flags and remote config in app shell.

## 5.2 Backend

- FastAPI orchestration APIs.
- Async workers for analysis and TTS generation.
- WebSocket progress events.
- MongoDB as source of truth.
- Object storage for audio artifacts.

## 5.3 AI/ML Layer

- Timestamped transcription.
- Script alignment.
- Delivery feature extraction.
- Goal-aware scoring.
- Feedback and correction generation.
- Ideal-voice synthesis for corrected segments.

## 6) Data Model Extensions

Add:

1. `users`
2. `learner_profiles`
3. `guided_scripts`
4. `practice_sessions`
5. `session_utterances`
6. `coaching_feedback`
7. `audio_corrections`
8. `progress_snapshots`
9. `model_eval_runs`
10. `release_health_events`

Version fields required in outputs:

- `rubric_version`
- `scoring_model_version`
- `feature_extractor_version`
- `prompt_version`

## 7) The Live Stability System (How We Prevent Breakage)

This is the core upgrade from a development-only plan.

### 7.1 Immutable Principles

1. **Convention over configuration**: new modules automatically enter quality checks.
2. **Ratcheting quality bar**: coverage and reliability floors only move up.
3. **Test-first completeness**: no feature considered done without tests.
4. **Progressive delivery**: no direct global rollout.
5. **Instant rollback readiness**: every release has a verified rollback path.
6. **Observability by default**: unobserved code is considered unsafe code.

### 7.2 Compatibility Contract

Any release must preserve:

1. API compatibility for mobile/web clients.
2. Schema compatibility for existing sessions.
3. Backward readability for existing scoring artifacts.
4. Runtime compatibility for OTA updates and native build versions.

## 8) Quality Engineering Strategy

## 8.1 Test Pyramid

1. Static checks: lint, format, type checks.
2. Unit tests: scoring logic, validators, feature extractors, prompt templates.
3. Contract tests: API request/response and schema compatibility.
4. Integration tests: full session pipeline with storage + DB.
5. E2E tests: user flow from script render to retry delta.
6. Model regression tests: golden dataset scoring drift checks.
7. Performance tests: latency and concurrency baselines.

## 8.2 Non-Regression Gates

Every merge to protected branch must pass:

1. Unit and integration tests.
2. E2E smoke for Guided mode.
3. Schema validation checks.
4. Coverage floor check.
5. Model quality gate against golden dataset.
6. Security and secret scan.

If any gate fails, release is blocked.

## 8.3 Ratchet Policy

Maintain `quality-baseline.json` with:

- minimum line coverage
- module-level coverage floors
- max p95 latency
- max coaching failure rate
- minimum golden-set score

CI fails if metrics regress below baseline. Baseline updates are allowed only upward except emergency exemptions with documented approval.

## 9) Release and Deployment Safety

## 9.1 Environment Ladder

1. local
2. CI ephemeral
3. staging internal
4. beta cohort
5. production canary
6. production full

## 9.2 Progressive Rollout Policy

Use staged rollout percentages for app updates and OTA updates:

1. 1% canary
2. 5% rollout
3. 20% rollout
4. 50% rollout
5. 100% rollout

Promotion to next stage requires SLO health and no Sev1/Sev2 incident in hold window.

## 9.3 Release Gates

A release cannot move forward unless:

1. Change is behind feature flag (unless emergency hotfix).
2. Rollback command tested in staging.
3. SLO dashboard is green.
4. Error budget is not exhausted.
5. On-call owner assigned.

## 9.4 Rollback Policy

For every deploy:

1. Keep previous stable build/update ready.
2. Maintain one-command rollback playbook.
3. Auto-trigger rollback when hard thresholds breach:
   - crash spike
   - session failure spike
   - latency breach sustained beyond window

## 10) Reliability SLOs and Error Budget Policy

## 10.1 Initial SLO Set

1. Session completion availability: `99.5%` per 28 days.
2. Coaching generation success: `99.0%` per 28 days.
3. Median feedback latency: `<= 12s`.
4. P95 feedback latency: `<= 20s`.
5. A/B audio playback success: `99.5%`.
6. Crash-free sessions: `>= 99.0%`.

## 10.2 Error Budget Policy

If budget burn exceeds threshold:

1. Freeze new feature releases.
2. Allow only reliability or security fixes.
3. Run incident review and corrective plan.
4. Resume feature work only after health restoration window is met.

## 11) Observability and Monitoring

## 11.1 Telemetry Events

Emit events for:

1. session start and completion
2. transcription success/failure
3. scoring success/failure
4. feedback generation latency
5. A/B clip playback success/failure
6. retry attempt and delta score
7. API errors by endpoint and class
8. mobile app crashes and ANRs

## 11.2 Dashboards

Create dashboards for:

1. user outcome metrics
2. reliability/SLO metrics
3. model quality drift
4. rollout adoption and failure profile

## 11.3 Alerting

Page only on actionable conditions:

1. SLO burn rate alerts
2. session failure spikes
3. crash spikes
4. persistent high latency

## 12) Incident Management and Operational Readiness

1. On-call rotation for app + backend.
2. Severity definitions (Sev1 to Sev4).
3. Runbooks for top failure classes:
   - STT outage
   - TTS outage
   - DB connectivity
   - object storage failure
   - bad model/prompt rollout
4. Postmortem within 48 hours for Sev1/Sev2.
5. Corrective actions tracked to closure.

## 13) Data Integrity, Privacy, and Compliance Guardrails

1. PII minimization in transcripts and logs.
2. Sensitive data redaction before logging.
3. Explicit retention policy for audio and transcripts.
4. Audit trail for model version and feedback output.
5. Access control by role for session data.

## 14) Milestone Plan (Product + Reliability Integrated)

## Milestone 0 (Week 1): Reliability Contract + Scope Lock

- Finalize rubric and Goal Signature.
- Define SLOs and error budget.
- Define CI gate matrix and quality baseline file.
- Freeze POC scope and acceptance tests.

Exit gate:

- Product, engineering, and reliability signoff.

## Milestone 1 (Week 1-2): Universal App Scaffold + Guardrails

- Expo project scaffold.
- Recording + script UI skeleton.
- Feature flag framework.
- CI baseline with unit tests and lint gates.

Exit gate:

- App runs cross-platform and CI is enforcing mandatory checks.

## Milestone 2 (Week 3-4): Guided Mode E2E + Contract Tests

- Session creation and recording upload.
- Transcribe, align, and score flow.
- Written feedback rendering.
- API contract tests and schema compatibility tests.

Exit gate:

- Guided flow complete in staging with green contracts.

## Milestone 3 (Week 5-6): A/B Audio + Rollback Automation

- User vs ideal clip generation.
- Correction card playback controls.
- Full report read-aloud.
- Rollback scripts and runbook validation.

Exit gate:

- A/B correction flow works and rollback drill passes.

## Milestone 4 (Week 6-7): Retry Loop + Golden Regression Suite

- Retry capture and immediate rescoring.
- Delta feedback display.
- Golden dataset evaluations in CI.

Exit gate:

- Retry improvements measurable and model regression gate active.

## Milestone 5 (Week 8): User-Provided Script Mode v1

- Script + occasion + purpose intake.
- Context-aware scoring and coaching.

Exit gate:

- Second workflow production-candidate with same reliability gates.

## Milestone 6 (Week 9-10): Pilot Release with Progressive Delivery

- Staging soak test.
- 1% to 100% controlled rollout process.
- Production observability and alerting go-live.

Exit gate:

- Pilot live with stable SLO performance and rollback readiness.

## 15) Release Readiness Checklist (Must Pass Before Go-Live)

1. All CI gates green.
2. E2E Guided mode pass on Android and web.
3. A/B playback success above threshold in staging.
4. SLO dashboards live and verified.
5. On-call schedule published.
6. Runbooks reviewed and tested.
7. Rollback rehearsal completed and timed.
8. Security checks complete.
9. Data retention and privacy controls verified.

## 16) No-Ship Criteria

Do not release if any condition holds:

1. Crash-free sessions below target in staging.
2. Golden dataset quality regression.
3. Rollback path unverified.
4. Unknown Sev1/Sev2 incident open.
5. Error budget exhausted.

## 17) Post-Launch Reliability Cadence

1. Daily health review during rollout window.
2. Weekly reliability review:
   - SLO trend
   - top incidents
   - flaky tests
   - model drift
3. Monthly quality ratchet update:
   - raise floors where current performance is stable
   - remove weak/unhelpful alerts
4. Quarterly game-day drills for incident simulation.

## 18) Immediate Next Actions

1. Approve this integrated product + reliability plan.
2. Create implementation backlog with two swimlanes:
   - feature delivery
   - reliability platform
3. Start Milestone 0 artifacts:
   - `quality-baseline.json`
   - CI gate definitions
   - SLO document
   - rollback runbook
