"""Backend configuration (POC).

Reads from .env.poc when present; otherwise falls back to isolated-mock defaults.
Defaults intentionally point at the POC mock DB (port 27018), never the real DB.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.poc", env_file_encoding="utf-8", extra="ignore"
    )

    # Isolated mock MongoDB — NEVER public_speaking_intelligence on 27017.
    poc_mongo_uri: str = "mongodb://localhost:27018"
    poc_mongo_db: str = "public_speaking_intelligence_mock"

    # API
    poc_api_host: str = "0.0.0.0"
    poc_api_port: int = 8090
    poc_cors_origins: str = "*"

    # Object storage (audio is never stored in Mongo).
    object_store: str = "localfs"  # localfs | minio
    poc_storage_dir: str = "./.poc-storage"
    poc_minio_endpoint: str = "http://localhost:9000"
    poc_minio_user: str = "vaani_poc"
    poc_minio_pass: str = "vaani_poc_secret"
    poc_minio_bucket: str = "vaani-poc-audio"

    # AI providers (mock = deterministic, no cloud creds).
    #   provider_stt: "mock" | "whisper" (local faster-whisper, no key)
    #   provider_tts: "mock" | "macos"   (macOS `say`, no key)
    #   provider_llm: "mock"             (only deterministic feedback in the POC)
    #   provider_acoustic: "mock" | "librosa" (real waveform analysis, no key) — the
    #     persona path scores delivery from raw audio, never a transcript.
    provider_stt: str = "mock"
    provider_tts: str = "mock"
    provider_llm: str = "mock"
    provider_acoustic: str = "mock"

    # Real-provider knobs (used only when the matching provider_* is non-mock).
    poc_whisper_model: str = "base.en"  # tiny.en | base.en | small.en | …
    poc_whisper_device: str = "cpu"
    poc_whisper_compute: str = "int8"
    poc_tts_voice: str = ""  # "" → system default voice
    poc_tts_rate: int = 0  # 0 → system default words-per-minute

    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        raw = (self.poc_cors_origins or "*").strip()
        if raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
