# Vaani POC — Release, Rollback & Operations Runbook

> Operational playbook for shipping the coaching app safely. Implements plan
> §9, §12, §13 of
> [`poc-universal-coaching-app-plan.md`](../plans/poc-universal-coaching-app-plan.md).
> Reliability targets referenced here live in [`slos.md`](./slos.md).

---

## Environment ladder (plan §9.1)

`local → CI ephemeral → staging internal → beta cohort → production canary → production full`

Each rung must be green before promotion. CI ephemeral = the GitHub Actions run
(`make poc-api-test`, `make poc-app-test`); staging = the isolated POC stack
(`docker-compose.poc.yml` + `make poc-api-run` + Expo web/Android build).

---

## Progressive rollout policy (plan §9.2)

Every app update and OTA update advances through fixed stages:

`1% canary → 5% → 20% → 50% → 100%`

- **Promotion rule:** advance only when SLOs are green ([`slos.md`](./slos.md)) and there
  is **no Sev1/Sev2** incident in the hold window.
- **Hold window:** minimum 24h per stage during the pilot (plan §16/§17 daily review).
- **Mechanism:** user-facing capabilities ship dark behind feature flags
  ([`app/src/featureFlags.ts`](../../app/src/featureFlags.ts) — `modeB`, `liveProgress`,
  `readAloud`, read from `EXPO_PUBLIC_FLAG_*`). Flip a flag on for the cohort; the build
  itself is already deployed. This is the seam where a real remote-config provider
  (LaunchDarkly/GrowthBook) replaces static env flags.

---

## Release gates (plan §9.3) — all five must hold to advance a stage

1. **Behind a feature flag** (unless an emergency hotfix).
2. **Rollback command tested in staging** (drill below passed for this build).
3. **SLO dashboard green** (the six SLOs in [`slos.md`](./slos.md)).
4. **Error budget not exhausted** (enforces the §10.2 freeze — see `slos.md` §3).
5. **On-call owner assigned** for app + backend.

A release that fails any gate stops. No exceptions outside the documented emergency
hotfix path.

---

## Rollback policy (plan §9.4)

For every deploy:

1. **Keep the previous stable build/update ready** — never delete the last-known-good
   artifact (native build + OTA bundle) until the new one clears 100% + a full window.
2. **One-command rollback playbook** (below).
3. **Auto-trigger rollback** when a hard threshold breaches:
   - crash spike (`mobile_crash` rate over guard),
   - session-failure spike (`scoring success=false` rate over guard),
   - sustained latency breach (`feedback_latency` p95 over target beyond the window).

### One-command rollback playbook

| Surface | Roll back by | Notes |
|---|---|---|
| **Feature/behavior** (fastest) | Flip the offending `EXPO_PUBLIC_FLAG_*` off for the cohort | No redeploy; instant. First lever for anything flag-gated. |
| **OTA bundle** | Re-point the channel to the previous EAS Update | Minutes; no app-store review. |
| **Native app build** | Halt rollout + promote the prior store build | Slowest; only when native code is implicated. |
| **Backend (`services/api`)** | Redeploy the previous image tag; providers stay mock-default if `PROVIDER_*` unset | Version stamps (`*_version`) make it auditable which build scored a session. |

**Drill (must pass in staging before each release — gate 2):** flip a flag off and
confirm the cohort reverts; re-point OTA to the previous bundle and confirm version; for
the backend, redeploy the prior tag and confirm `/health` + a smoke session. Record the
drill in the release checklist.

---

## Incident management (plan §12)

- **On-call rotation** covers app + backend.
- **Severity:** Sev1 (broad outage / data risk) · Sev2 (major degradation, SLO burning) ·
  Sev3 (minor, workaround exists) · Sev4 (cosmetic / low impact).
- **Postmortem within 48h** for Sev1/Sev2; corrective actions tracked to closure.

### Runbooks for top failure classes

| Failure class | First signal | Immediate action | Mitigation |
|---|---|---|---|
| **STT outage** | `transcription success=false` spike | Roll back if a provider change is implicated | Fall back to mock STT / expected-text scoring; queue audio for re-process |
| **TTS outage** | A/B ideal-clip synthesis errors | Disable A/B (flag) | Serve cached ideal clips; text-only corrections still work |
| **DB connectivity** | `scoring`/session writes failing; `api_error` 5xx | Page on-call; check the POC Mongo (`:27018`, never `:27017`) | Restore connection; sessions are idempotent (`session_id` upsert) so retries are safe |
| **Object storage failure** | audio `put`/`get` errors | Fail soft: coaching proceeds, audio unavailable | LocalFS→S3/MinIO is swappable via `OBJECT_STORE`; audio never in Mongo |
| **Bad model/prompt rollout** | golden MAE jump / score drift / `retry_delta` anomalies | Roll back `scoring_model_version`/`prompt_version` | Golden suite (`tests/golden/`) should have caught it pre-ship; add the missed case |

---

## Data integrity, privacy & retention (plan §13)

1. **PII minimization** in transcripts and logs — store only what coaching needs; no
   names/contact info in `release_health_events.payload`. Telemetry payloads carry IDs,
   scores, latencies, and error classes — **never transcript text or raw audio**.
2. **Redaction before logging** — scrub sensitive content from any log line; telemetry
   already excludes transcript bodies by construction.
3. **Retention policy** — audio clips and transcripts have an explicit TTL (audio in the
   object store, transcripts in `session_utterances`); telemetry events are retained for
   the SLO window (28 days) plus an ops margin, then expired. Audio is **never** stored in
   Mongo documents — object store only (hard constraint).
4. **Audit trail** — every scored/feedback document carries the four `*_version` fields
   (`domain/versions.py`); `model_eval_runs` records which model version produced which
   golden result. Together these answer "which model scored this session?".
5. **Role-based access** to session data — coaching data is scoped per `user_id`;
   admin/ops read access is separate from the learner's own access.

---

## Release readiness checklist (plan §15) — must pass before go-live

- [ ] CI green: `make poc-api-test` (+ golden suite) and `make poc-app-test`.
- [ ] Both modes walked E2E (web), Android build verified (plan §14 / P8).
- [ ] SLO dashboards live and verified ([`slos.md`](./slos.md)).
- [ ] Rollback drill passed for this build (all four surfaces above).
- [ ] Feature flags default-safe; cohort flags set for the target stage.
- [ ] On-call assigned; error budget not exhausted.
- [ ] Data retention + privacy controls verified.
