"""Main entry point for the Pokemon Red AI Agent."""

import signal
import sys
import time
from pathlib import Path

import structlog

from .agent import SimpleAgent
from .config import get_config
from .emulator import Button, EmulatorInterface, StateReader
from .logging_config import setup_logging

logger = structlog.get_logger()


class GameLoop:
    """
    Main game loop that coordinates the emulator and AI agent.

    Responsible for:
    - Running the game loop
    - Reading game state
    - Getting agent decisions
    - Executing actions
    - Handling interrupts
    """

    def __init__(
        self,
        emulator: EmulatorInterface,
        agent: SimpleAgent,
        checkpoint_interval: int = 300,  # 5 minutes
    ):
        """
        Initialize the game loop.

        Args:
            emulator: The emulator interface
            agent: The AI agent
            checkpoint_interval: Seconds between auto-saves
        """
        self._emulator = emulator
        self._agent = agent
        self._state_reader = StateReader(emulator)
        self._checkpoint_interval = checkpoint_interval

        self._running = False
        self._last_checkpoint_time = time.time()
        self._last_checkpoint: bytes | None = None
        self._start_time: float | None = None

    def run(self) -> None:
        """Run the main game loop."""
        self._running = True
        self._start_time = time.time()

        # Create initial checkpoint
        self._last_checkpoint = self._emulator.save_state()
        logger.info("Initial checkpoint created")

        logger.info("Starting game loop", checkpoint_interval=self._checkpoint_interval)

        try:
            while self._running and self._emulator.is_running:
                self._loop_iteration()

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error("Error in game loop", error=str(e), exc_info=True)
            self._handle_error(e)
        finally:
            self._cleanup()

    def _loop_iteration(self) -> None:
        """Single iteration of the game loop."""
        # 1. Read current game state
        game_state = self._state_reader.get_game_state()

        # 2. Log current state (abbreviated)
        logger.debug(
            "Game state",
            mode=game_state.mode.name,
            position=str(game_state.position),
            party_count=game_state.party_count,
        )

        # 3. Get agent decision
        action = self._agent.get_action(game_state)

        # 4. Execute the action
        self._execute_action(action)

        # 5. Run emulator for a short time to let action take effect
        self._emulator.tick(30)  # ~0.5 seconds at 60fps

        # 6. Periodic checkpoint
        now = time.time()
        if now - self._last_checkpoint_time > self._checkpoint_interval:
            self._create_checkpoint()
            self._last_checkpoint_time = now

    def _execute_action(self, action: dict) -> None:
        """Execute an action from the agent."""
        action_type = action.get("type")
        reason = action.get("reason", "")

        logger.info("Executing action", type=action_type, reason=reason)

        if action_type == "press_button":
            button_name = action.get("button", "A")
            try:
                button = Button[button_name]
                self._emulator.press_button(button)
            except KeyError:
                logger.warning("Invalid button", button=button_name)

        elif action_type == "move_direction":
            direction = action.get("direction", "DOWN")
            tiles = action.get("tiles", 1)
            self._emulator.move(direction, tiles)

        elif action_type == "wait":
            seconds = action.get("seconds", 1.0)
            self._emulator.run_for_seconds(seconds)

        else:
            logger.warning("Unknown action type", type=action_type)

    def _create_checkpoint(self) -> None:
        """Create a checkpoint save state."""
        self._last_checkpoint = self._emulator.save_state()
        logger.info(
            "Checkpoint created",
            frame=self._emulator.frame_count,
            actions=self._agent.action_count,
        )

    def _handle_error(self, error: Exception) -> None:
        """Handle errors by attempting recovery."""
        logger.error("Attempting recovery from error", error=str(error))

        if self._last_checkpoint:
            try:
                self._emulator.load_state(self._last_checkpoint)
                logger.info("Recovered from checkpoint")
                # Reset agent conversation to avoid confusion
                self._agent.reset_conversation()
            except Exception as e:
                logger.error("Failed to recover from checkpoint", error=str(e))
                self._running = False
        else:
            self._running = False

    def _cleanup(self) -> None:
        """Clean up resources."""
        if self._start_time:
            duration = time.time() - self._start_time
            logger.info(
                "Game loop ended",
                duration_seconds=int(duration),
                total_frames=self._emulator.frame_count,
                total_actions=self._agent.action_count,
            )

    def stop(self) -> None:
        """Stop the game loop."""
        self._running = False


def main() -> None:
    """Main entry point."""
    # Load configuration
    config = get_config()

    # Setup logging
    setup_logging(config.log_level)

    logger.info(
        "Pokemon Red AI Agent starting",
        model=config.agent_model,
        rom_path=config.rom_path,
        headless=config.headless,
        speed=config.emulation_speed,
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

    # Initialize emulator
    logger.info("Initializing emulator", rom_path=str(rom_path))
    emulator = EmulatorInterface(
        rom_path=rom_path,
        headless=config.headless,
        speed=config.emulation_speed,
    )

    # Initialize agent
    logger.info("Initializing AI agent", model=config.agent_model)
    agent = SimpleAgent(
        api_key=config.anthropic_api_key,
        model=config.agent_model,
    )

    # Create game loop
    game_loop = GameLoop(emulator, agent)

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received signal, shutting down", signal=signum)
        game_loop.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the game loop
    try:
        game_loop.run()
    finally:
        emulator.close()
        logger.info("Emulator closed")


if __name__ == "__main__":
    main()
