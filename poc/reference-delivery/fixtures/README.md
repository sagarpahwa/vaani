# Test Fixtures

Place the following file here to enable the regression test:

## `bad_user_audio.webm`

A browser-recorded WebM/Opus file of someone **poorly attempting** the TinyTrail script —
rushing through it, skipping most lines, mumbling, etc.

This file is NOT committed to git (see `.gitignore`). Copy it from your local recordings.

### Expected regression result

When run through `npm run test:speech-lab`:

| Field | Expected |
|---|---|
| `summary.overallScore` | ≤ 5 |
| `summary.validity` | `catastrophic_script_mismatch` |
| `validityInfo.maxOverall` | ≤ 5 |
| `feedback.top5Fixes[0]` | Mentions "complete the script" |

### Running the test

```bash
# Terminal 1: start the server
npm run dev

# Terminal 2: run the regression test
npm run test:speech-lab
```
