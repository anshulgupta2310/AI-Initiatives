"""Configuration, loaded from .env once at import."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]

Effort = Literal["low", "medium", "high", "xhigh", "max"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    voyage_api_key: str = Field(default="", alias="VOYAGE_API_KEY")

    model: str = Field(default="claude-opus-5", alias="AI_MODEL")
    effort: Effort = Field(default="high", alias="AI_EFFORT")

    # Safety rail: aicore refuses to call the API once a process exceeds this.
    spend_limit_usd: float = Field(default=2.00, alias="AI_SPEND_LIMIT_USD")

    @property
    def data_dir(self) -> Path:
        d = REPO_ROOT / "data"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def require_anthropic_key(self) -> None:
        """Fail loudly and usefully, rather than deep inside an HTTP 401."""
        if not self.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set.\n"
                f"  1. cp {REPO_ROOT / '.env.example'} {REPO_ROOT / '.env'}\n"
                "  2. Paste a key from https://console.anthropic.com/settings/keys"
            )


settings = Settings()
