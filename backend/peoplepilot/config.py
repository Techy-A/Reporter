"""Runtime configuration, read from environment variables (or a .env file).

Security-relevant rule: the admin portal and the employee portal use DIFFERENT
signing keys, so a token minted for one can never be accepted by the other.
"""
from __future__ import annotations

import ipaddress
import os
from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=os.environ.get("PP_ENV_FILE", ".env"), env_prefix="PP_", extra="ignore")

    env: str = "dev"  # dev | test | prod
    database_url: str = "sqlite:///./peoplepilot.db"

    # --- secrets (must be set in prod; see .env.example) ---
    admin_jwt_key: str = Field(min_length=32)
    portal_jwt_key: str = Field(min_length=32)
    data_key: str = Field(description="Fernet key used to encrypt phone numbers and channel tokens")
    hmac_key: str = Field(min_length=32, description="Key for phone-number lookup hashes")
    setup_token: str = Field(min_length=16, description="One-time token required for first-run setup")

    # --- origins (each portal only trusts its own origin) ---
    admin_origin: str = "https://admin.localhost:8001"
    portal_origin: str = "https://me.localhost:8002"

    # --- network ---
    admin_allowed_cidrs: str = "127.0.0.0/8,::1/128,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"

    # --- sessions ---
    admin_session_minutes: int = 60
    portal_session_minutes: int = 120

    # --- retention ---
    message_retention_days: int = 30
    audit_retention_days: int = 365

    # --- optional LLM (bring your own key, or local Ollama). Buttons work without it. ---
    llm_base_url: str | None = None  # e.g. http://localhost:11434/v1 or https://api.groq.com/openai/v1
    llm_api_key: str | None = None
    llm_model: str | None = None

    # --- email for employee portal one-time codes ---
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "PeoplePilot <no-reply@localhost>"

    # Dev only: route all candidate messages to an in-app simulator instead of WhatsApp/Telegram.
    # Ignored when PP_ENV=prod.
    simulator: bool = False

    @property
    def simulator_on(self) -> bool:
        return self.simulator and self.env != "prod"

    @field_validator("admin_allowed_cidrs")
    @classmethod
    def _valid_cidrs(cls, v: str) -> str:
        for part in v.split(","):
            ipaddress.ip_network(part.strip(), strict=False)
        return v

    @model_validator(mode="after")
    def _keys_differ(self) -> "Settings":
        if self.admin_jwt_key == self.portal_jwt_key:
            raise ValueError("PP_ADMIN_JWT_KEY and PP_PORTAL_JWT_KEY must be different")
        return self

    @property
    def admin_networks(self) -> list[ipaddress._BaseNetwork]:
        return [ipaddress.ip_network(p.strip(), strict=False) for p in self.admin_allowed_cidrs.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
