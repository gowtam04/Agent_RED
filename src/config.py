"""Configuration management for the Pokemon Red AI Agent."""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API Configuration
    anthropic_api_key: str = Field(description="Anthropic API key for Claude")

    # ROM Configuration
    rom_path: str = Field(
        default="roms/pokemon_red.gb",
        description="Path to the Pokemon Red ROM file",
    )

    # Emulator Settings
    emulation_speed: int = Field(
        default=1,
        ge=0,
        description="Emulation speed (0=unlimited, 1=normal, 2+=faster)",
    )
    headless: bool = Field(
        default=False,
        description="Run without display window",
    )

    # Agent Settings
    agent_model: str = Field(
        default="claude-sonnet-4-5-20250929",
        description="Claude model to use for decision making",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )

    def get_rom_path(self) -> Path:
        """Get the absolute path to the ROM file."""
        rom_path = Path(self.rom_path)
        if rom_path.is_absolute():
            return rom_path
        # Relative to project root
        return Path(__file__).parent.parent / rom_path

    def validate_rom_exists(self) -> bool:
        """Check if the ROM file exists."""
        return self.get_rom_path().exists()


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config() -> Config:
    """Reload configuration from environment."""
    global _config
    _config = Config()
    return _config
