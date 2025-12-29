"""Dashboard entry point for the Pokemon Red AI Agent.

This module starts the FastAPI server that serves the web dashboard
and manages the game engine.

Usage:
    poetry run pokemon-dashboard

Or:
    poetry run python -m src.dashboard

Or with uvicorn directly (for development):
    poetry run uvicorn src.api.main:app --reload
"""

from __future__ import annotations

import sys

import structlog
import uvicorn

from .config import get_config
from .logging_config import setup_logging

logger = structlog.get_logger()


def main() -> None:
    """Entry point for the dashboard server."""
    # Load configuration
    config = get_config()

    # Setup logging
    setup_logging(
        log_level=config.log_level,
        log_to_file=config.log_to_file,
        log_dir=config.log_dir,
    )

    # Validate ROM exists
    rom_path = config.get_rom_path()
    if not rom_path.exists():
        logger.error(
            "ROM file not found",
            path=str(rom_path),
            hint="Place your Pokemon Red ROM at the specified path",
        )
        sys.exit(1)

    logger.info(
        "Starting Pokemon Red AI Agent Dashboard",
        port=config.dashboard_port,
        rom_path=str(rom_path),
        broadcast_fps=config.state_broadcast_fps,
    )

    # Run the FastAPI server
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=config.dashboard_port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
