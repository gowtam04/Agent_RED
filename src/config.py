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

    # Initial Objective Settings
    initial_objective: str = Field(
        default="become_champion",
        description="Initial game objective (become_champion, defeat_gym, catch_pokemon)",
    )
    initial_objective_target: str = Field(
        default="Elite Four",
        description="Target for the initial objective (e.g., gym leader name, Pokemon name)",
    )

    # Agent Behavior Settings
    use_opus_for_bosses: bool = Field(
        default=True,
        description="Use Opus model for gym leaders, Elite Four, and Champion battles",
    )
    checkpoint_interval_seconds: int = Field(
        default=300,
        ge=60,
        description="Seconds between automatic checkpoints (save states)",
    )

    # Recovery Settings
    max_retries: int = Field(
        default=3,
        ge=1,
        description="Maximum retries for agent failures before recovery",
    )
    retry_delay_seconds: float = Field(
        default=1.0,
        ge=0.1,
        description="Delay between retry attempts",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    log_to_file: bool = Field(
        default=True,
        description="Write logs to file in addition to console",
    )
    log_dir: str = Field(
        default="logs",
        description="Directory for log files",
    )

    # Dashboard Settings
    dashboard_port: int = Field(
        default=8000,
        ge=1024,
        le=65535,
        description="Port for the dashboard API server",
    )
    state_broadcast_fps: int = Field(
        default=15,
        ge=5,
        le=60,
        description="Target FPS for state broadcasts to dashboard (5-60)",
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

    def get_log_dir(self) -> Path:
        """Get the absolute path to the log directory."""
        log_path = Path(self.log_dir)
        if log_path.is_absolute():
            return log_path
        # Relative to project root
        return Path(__file__).parent.parent / log_path


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
