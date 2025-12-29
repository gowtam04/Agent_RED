"""Logging configuration for the Pokemon Red AI Agent."""

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import structlog

# Agent-specific logger names
AGENT_LOGGERS = {
    "orchestrator": "pokemon.agent.orchestrator",
    "navigation": "pokemon.agent.navigation",
    "battle": "pokemon.agent.battle",
    "menu": "pokemon.agent.menu",
    "game_loop": "pokemon.game_loop",
    "emulator": "pokemon.emulator",
    "recovery": "pokemon.recovery",
}


def add_game_context(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add game context fields to log events.

    This processor adds structured fields for game state when available.
    """
    # These fields can be bound to the logger when context is available
    # e.g., log = log.bind(mode="BATTLE", position="VIRIDIAN_CITY")
    return event_dict


def setup_logging(
    log_level: str = "INFO",
    log_to_file: bool = True,
    log_dir: str = "logs",
) -> None:
    """
    Configure structured logging with optional file output.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Whether to write logs to file
        log_dir: Directory for log files
    """
    # Convert string level to logging constant
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Create log directory if needed
    log_path = Path(log_dir)
    if log_to_file:
        log_path.mkdir(parents=True, exist_ok=True)

    # Shared processors for both console and file
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        add_game_context,
    ]

    # Configure structlog
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Console formatter (colored)
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(colors=True),
        foreign_pre_chain=shared_processors,
    )

    # File formatter (JSON for structured queries)
    file_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(level)
    root_logger.addHandler(console_handler)

    # File handler with rotation
    if log_to_file:
        # Main log file with rotation (10MB max, keep 5 backups)
        log_file = log_path / f"pokemon_agent_{datetime.now():%Y%m%d}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(level)
        root_logger.addHandler(file_handler)

        # Separate error log (errors and above only)
        error_log_file = log_path / "errors.log"
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8",
        )
        error_handler.setFormatter(file_formatter)
        error_handler.setLevel(logging.ERROR)
        root_logger.addHandler(error_handler)

    # Set levels for noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)


def get_agent_logger(agent_type: str) -> Any:
    """Get a logger for a specific agent type.

    Args:
        agent_type: One of 'orchestrator', 'navigation', 'battle', 'menu'

    Returns:
        A bound structlog logger for the agent.
    """
    logger_name = AGENT_LOGGERS.get(agent_type.lower(), f"pokemon.agent.{agent_type}")
    return structlog.get_logger(logger_name).bind(agent=agent_type)


def get_game_loop_logger() -> Any:
    """Get a logger for the game loop."""
    return structlog.get_logger(AGENT_LOGGERS["game_loop"]).bind(component="game_loop")


def get_emulator_logger() -> Any:
    """Get a logger for the emulator interface."""
    return structlog.get_logger(AGENT_LOGGERS["emulator"]).bind(component="emulator")


def get_recovery_logger() -> Any:
    """Get a logger for the recovery system."""
    return structlog.get_logger(AGENT_LOGGERS["recovery"]).bind(component="recovery")
