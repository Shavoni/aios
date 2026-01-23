"""Router configuration."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class RouterSettings(BaseSettings):
    """Router settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Anthropic API
    anthropic_api_key: str = ""

    # OpenAI API
    openai_api_key: str = ""

    # Provider selection: "openai" or "anthropic"
    llm_provider: str = "openai"

    # Model defaults
    default_model: str = "claude-sonnet-4-20250514"
    default_openai_model: str = "gpt-4o"
    max_tokens: int = 1024
    temperature: float = 0.7

    @property
    def has_anthropic_key(self) -> bool:
        """Check if Anthropic API key is configured."""
        return bool(self.anthropic_api_key and self.anthropic_api_key.startswith("sk-ant-"))

    @property
    def has_openai_key(self) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(self.openai_api_key and self.openai_api_key.startswith("sk-"))

    @property
    def has_api_key(self) -> bool:
        """Check if any API key is configured for the selected provider."""
        if self.llm_provider == "openai":
            return self.has_openai_key
        return self.has_anthropic_key
