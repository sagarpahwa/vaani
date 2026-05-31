# Vaani POC — Reliability SLOs & Error Budget Policy

> Source of truth for the POC's reliability targets. Implements plan §10–§11 of
> [`poc-universal-coaching-app-plan.md`](../plans/poc-universal-coaching-app-plan.md).
> The machine-readable copy of these numbers lives in
> [`quality-baseline.poc.json`](../../quality-baseline.poc.json) (`slo_targets`) so CI/ops
> can read them without parsing prose. **If you change a target, change both.**

---

## 1) Initial SLO set (plan §10.1)

Measured over a rolling **28-day** window unless noted.

| # | SLO | Target | Telemetry it's computed from |
|---|-----|--------|------------------------------|
| 1 | Session completion availability | ≥ 99.5% | `session_started` vs `session_completed` |
| 2 | Coaching generation success | ≥ 99.0% | `scoring` (`success=true` / total) |
| 3 | Median feedback latency | ≤ 12s | `feedback_latency.latency_ms` p50 |
| 4 | P95 feedback latency | ≤ 20s | `feedback_latency.latency_ms` p95 |
| 5 | A/B audio playback success | ≥ 99.5% | `ab_playback` (`success=true` / total) |
| 6 | Crash-free sessions | ≥ 99.0% | `mobile_crash` count vs sessions |

All six map directly to event types emitted by
[`services/api/telemetry.py`](../../services/api/telemetry.py) and persisted to the
`release_health_events` collection (schema:
[`release_health_events.json`](../../services/api/db/schemas/release_health_events.json)).

### How each event is produced today (POC)

- **Backend, automatic:** `session_started`, `session_completed`, `scoring`,
  `transcription`, `feedback_latency`, `retry_delta` are emitted from the
  `/sessions` routes + `coaching_service.process_session`. Emission is *best-effort*:
  a telemetry write never fails a coaching request.
- **Client / edge, reported:** `ab_playback`, `api_error`, `mobile_crash` have emitters
  ready in `telemetry.py`; the app reports them through a (future) ingest endpoint.
  Until that endpoint exists they are available for server-side and test use.

Latency is recorded as a **non-negative integer of milliseconds** (`latency_ms`).
The synchronous mock pipeline runs in well under a second; the ≤12s/≤20s targets are
the budgets for when real STT/TTS/LLM providers are swapped in via `PROVIDER_*`.

---

## 2) Model-quality SLO (golden regression)

Beyond runtime SLOs, scoring **behavior** is itself gated. The deterministic mock
pipeline must reproduce the pinned golden scores:

- Fixture: [`services/api/tests/golden/dataset.json`](../../services/api/tests/golden/dataset.json)
  (exact overall + per-capability scores for representative sessions).
- Gate: [`test_golden_regression.py`](../../services/api/tests/golden/test_golden_regression.py)
  fails CI if any score drifts beyond `tolerance` (0.0005), if overall drops below
  `model_quality.min_overall_score`, or if mean absolute error exceeds
  `model_quality.max_mean_absolute_error`.
- Audit: every scored output carries `rubric_version`, `scoring_model_version`,
  `feature_extractor_version`, `prompt_version` (see `domain/versions.py`). The golden
  test asserts the dataset's pinned versions match the code — a model bump that forgets
  to regenerate the golden set fails the build (plan §13.4 audit trail).

This is the "model quality drift" dashboard input (plan §11.2.3) in test form: ops
records each real golden run as a `model_eval_runs` document
([schema](../../services/api/db/schemas/model_eval_runs.json)).

---

## 3) Error budget policy (plan §10.2)

The error budget is `1 − SLO target`. When burn exceeds threshold for any SLO:

1. **Freeze new feature releases** — no new user-facing flags flip on.
2. **Allow only reliability or security fixes** to ship.
3. **Run an incident review** and write a corrective plan (link the postmortem).
4. **Resume feature work** only after the health-restoration window is met
   (SLOs green for a full hold window, no open Sev1/Sev2).

The freeze is enforced procedurally via the release gates in
[`rollback-runbook.md`](./rollback-runbook.md#release-gates): gate 4 ("error budget not
exhausted") blocks promotion.

---

## 4) Dashboards (plan §11.2)

Four dashboards, all sourced from `release_health_events` + `model_eval_runs`:

1. **User outcomes** — sessions completed, scores, retry uplift (`retry_delta`).
2. **Reliability / SLO** — the six SLOs above with burn-rate overlays.
3. **Model-quality drift** — golden MAE over time, version transitions.
4. **Rollout adoption & failure profile** — events sliced by build/rollout stage.

## 5) Alerting (plan §11.3) — page only on actionable conditions

1. SLO burn-rate alerts (fast + slow burn).
2. Session-failure spikes (`scoring success=false` rate).
3. Crash spikes (`mobile_crash` rate).
4. Persistent high latency (`feedback_latency` p95 over target beyond the window).

Each alert maps to a runbook section in
[`rollback-runbook.md`](./rollback-runbook.md#incident-management).
