"""POC domain layer: Goal Signature, coaching types, scoring rubric, pipeline.

Pure, deterministic logic with no cloud dependencies. AI is reached only through
the `providers/` interfaces so real STT/TTS/LLM can swap in via `PROVIDER_*` env.
"""
