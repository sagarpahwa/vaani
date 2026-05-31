"""Provider interfaces and mock implementations for the coaching pipeline.

The domain layer reaches all AI (STT, alignment, scoring, feedback, TTS) and all
storage only through the abstract base classes in `base.py`. The POC ships
deterministic mock implementations; real cloud providers swap in via the
`PROVIDER_*` / `OBJECT_STORE` env vars without touching domain code.
"""
