"""
Configuration module for Max to Telegram bridge.
Loads settings from environment variables.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # GREEN-API settings
    max_instance_id: str = os.getenv("MAX_INSTANCE_ID", "")
    max_api_token: str = os.getenv("MAX_API_TOKEN", "")

    # Telegram settings
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_channel_id: str = os.getenv("TELEGRAM_CHANNEL_ID", "")

    # Max chat filtering
    max_chat_id: Optional[str] = os.getenv("MAX_CHAT_ID")

    # Telegram webhook settings (for Telegram → Max direction)
    telegram_webhook_url: Optional[str] = os.getenv("TELEGRAM_WEBHOOK_URL")
    telegram_webhook_secret: Optional[str] = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    telegram_chat_id: Optional[str] = os.getenv("TELEGRAM_CHAT_ID")  # Filter Telegram messages from this chat
    max_target_chat_id: str = os.getenv("MAX_TARGET_CHAT_ID", "")  # Where to send Telegram messages in Max

    # Direction control flags
    enable_max_to_telegram: bool = os.getenv("ENABLE_MAX_TO_TELEGRAM", "true").lower() == "true"
    enable_telegram_to_max: bool = os.getenv("ENABLE_TELEGRAM_TO_MAX", "true").lower() == "true"

    # Server settings
    webhook_port: int = int(os.getenv("WEBHOOK_PORT", "8000"))
    webhook_host: str = os.getenv("WEBHOOK_HOST", "0.0.0.0")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Optional: Webhook secret for security (for GREEN-API → Telegram direction)
    webhook_secret: Optional[str] = os.getenv("WEBHOOK_SECRET")

    class Config:
        env_file = ".env"
        case_sensitive = False

    def validate_settings(self) -> bool:
        """Validate that all required settings are present."""
        # Check that both directions are not enabled simultaneously
        if self.enable_max_to_telegram and self.enable_telegram_to_max:
            raise ValueError(
                "Нельзя включить оба направления одновременно. "
                "Это приведёт к бесконечному дублированию сообщений. "
                "Выберите одно направление: "
                "ENABLE_MAX_TO_TELEGRAM=true или ENABLE_TELEGRAM_TO_MAX=true"
            )

        # Check that at least one direction is enabled
        if not self.enable_max_to_telegram and not self.enable_telegram_to_max:
            raise ValueError(
                "Необходимо включить хотя бы одно направление синхронизации: "
                "ENABLE_MAX_TO_TELEGRAM=true или ENABLE_TELEGRAM_TO_MAX=true"
            )

        # Basic required settings
        required = [
            self.max_instance_id,
            self.max_api_token,
            self.telegram_bot_token,
        ]

        # Max → Telegram direction requires channel ID
        if self.enable_max_to_telegram:
            required.append(self.telegram_channel_id)

        # Telegram → Max direction requires target chat ID
        if self.enable_telegram_to_max:
            required.append(self.max_target_chat_id)

        return all(required)


# Global settings instance
settings = Settings()
