"""Main entry point for the Pokemon Red AI Agent.

This module implements the Orchestrator-based game loop that coordinates
multiple specialized agents (Navigation, Battle, Menu) to play Pokemon Red.
"""

from __future__ import annotations

import signal
import sys
import time

import structlog

from .agent import AgentRegistry, AgentResult, Objective
from .agent import GameState as AgentGameState
from .config import Config, get_config
from .emulator import Button, EmulatorInterface, StateReader
from .emulator.state_converter import StateConverter
from .logging_config import setup_logging
from .recovery import RecoveryManager, diagnose_failure, execute_recovery

logger = structlog.get_logger()


class GameLoop:
    """
    Main game loop using multi-agent architecture.

    Coordinates the Orchestrator agent which routes to specialized agents
    (Navigation, Battle, Menu) based on the current game mode.
    """

    def __init__(self, settings: Config):
        """
        Initialize the game loop.

        Args:
            settings: Application configuration.
        """
        self.settings = settings

        # Initialize emulator
        self.emulator = EmulatorInterface(
            rom_path=settings.get_rom_path(),
            headless=settings.headless,
            speed=settings.emulation_speed,
        )

        # State reading and conversion
        self.state_reader = StateReader(self.emulator)
        self.state_converter = StateConverter()

        # Agent system
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.registry = AgentRegistry(client=client)
        self.agent_state = AgentGameState()

        # Recovery
        self.recovery = RecoveryManager(
            max_retries=settings.max_retries,
            retry_delay=settings.retry_delay_seconds,
        )

        # Checkpointing
        self.last_checkpoint = time.time()
        self._last_save_state: bytes | None = None

        # Control
        self._running = False
        self._start_time: float | None = None

        # Set initial objective
        self._set_initial_objective()

    def _set_initial_objective(self) -> None:
        """Set the initial high-level objective from config."""
        objective_map = {
            "become_champion": Objective(
                type="become_champion",
                target=self.settings.initial_objective_target,
                priority=1,
            ),
            "defeat_gym": Objective(
                type="defeat_gym",
                target=self.settings.initial_objective_target,
                priority=5,
            ),
            "catch_pokemon": Objective(
                type="catch_pokemon",
                target=self.settings.initial_objective_target,
                priority=3,
            ),
        }

        obj = objective_map.get(
            self.settings.initial_objective,
            objective_map["become_champion"],
        )
        self.agent_state.push_objective(obj)
        logger.info(
            "Initial objective set",
            type=obj.type,
            target=obj.target,
        )

    def run(self) -> None:
        """Main game loop."""
        self._running = True
        self._start_time = time.time()

        # Create initial checkpoint
        self._last_save_state = self.emulator.save_state()
        logger.info("Initial checkpoint created")

        logger.info(
            "Starting game loop",
            checkpoint_interval=self.settings.checkpoint_interval_seconds,
        )

        try:
            while self._running and self.emulator.is_running:
                self._tick()

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error("Error in game loop", error=str(e), exc_info=True)
            self._handle_failure(str(e))
        finally:
            self._cleanup()

    def _tick(self) -> None:
        """Single iteration of the game loop."""
        # 1. Read current game state from emulator
        raw_state = self.state_reader.get_game_state()

        # 2. Convert to agent state (updates agent_state in-place)
        self.state_converter.convert(raw_state, self.agent_state)

        # 3. Log current state
        pos = self.agent_state.position
        obj = self.agent_state.current_objective
        logger.debug(
            "Game state",
            mode=self.agent_state.mode,
            position=f"{pos.map_id} ({pos.x}, {pos.y})",
            party_count=len(self.agent_state.party),
            objective=obj.type if obj else None,
        )

        # 4. Get Orchestrator decision
        orchestrator = self.registry.get_agent("ORCHESTRATOR")
        result = orchestrator.act(self.agent_state)

        if not result.success:
            logger.warning(f"Orchestrator failed: {result.error}")
            self._handle_failure(result.error or "Orchestrator failure")
            return

        # 5. If Orchestrator routes to another agent, execute that agent
        if result.handoff_to:
            self._execute_handoff(result)

        # 6. Process new objectives from orchestrator
        for obj in result.new_objectives:
            self.agent_state.push_objective(obj)
            logger.info(f"New objective: {obj.type} -> {obj.target}")

        # 7. Record success for recovery tracking
        self.recovery.record_success()

        # 8. Checkpoint periodically
        self._maybe_checkpoint()

        # 9. Small delay to prevent hammering
        time.sleep(0.1)

    def _execute_handoff(self, orchestrator_result: AgentResult) -> None:
        """Execute a handoff to a specialist agent.

        Args:
            orchestrator_result: Result from orchestrator with handoff info.
        """
        agent_type = orchestrator_result.handoff_to
        if not agent_type:
            return

        logger.info(f"Handing off to {agent_type} agent")

        agent = self.registry.get_agent(agent_type)

        # Check for Opus escalation (for boss battles)
        if orchestrator_result.result_data.get("escalate_to_opus"):
            if self.settings.use_opus_for_bosses:
                agent.model = "opus"
                logger.info(f"Escalated {agent_type} agent to Opus model")

        # Execute the agent
        agent_result = agent.act(self.agent_state)

        if not agent_result.success:
            logger.warning(f"{agent_type} agent failed: {agent_result.error}")
            self._handle_failure(agent_result.error or f"{agent_type} failure")
            return

        # Execute the result (translate to emulator actions)
        self._execute_result(agent_result)

        # Process new objectives from agent
        for obj in agent_result.new_objectives:
            self.agent_state.push_objective(obj)
            logger.info(f"New objective from {agent_type}: {obj.type} -> {obj.target}")

    def _execute_result(self, result: AgentResult) -> None:
        """Execute an agent result by translating to emulator actions.

        Args:
            result: Result from an agent containing action info.
        """
        action = result.action_taken
        data = result.result_data

        logger.info("Executing action", action=action, data=data)

        if action == "press_button":
            button_name = data.get("button", "A")
            try:
                button = Button[button_name]
                self.emulator.press_button(button)
            except KeyError:
                logger.warning("Invalid button", button=button_name)

        elif action == "move" or action == "execute_movement":
            direction = data.get("direction", "DOWN")
            tiles = data.get("tiles", 1)
            self.emulator.move(direction, tiles)

        elif action == "wait":
            seconds = data.get("seconds", 1.0)
            self.emulator.run_for_seconds(seconds)

        elif action in ("detect_game_mode", "route_to_agent", "get_current_objective"):
            # Orchestrator internal actions - no emulator action needed
            pass

        else:
            # For unrecognized actions, advance frames to let game progress
            logger.debug(f"Unhandled action type: {action}")
            self.emulator.tick(30)

        # Always advance frames after action to let it take effect
        self.emulator.tick(30)

    def _handle_failure(self, error: str) -> None:
        """Handle agent failure with recovery.

        Args:
            error: Error message describing the failure.
        """
        self.recovery.record_failure(error)

        if self.recovery.should_abort():
            logger.error("Too many failures, aborting")
            self._running = False
            return

        # Diagnose and execute recovery
        action = diagnose_failure(self.agent_state, error)
        success = execute_recovery(action, self)

        if not success:
            logger.warning("Recovery failed")

    def _maybe_checkpoint(self) -> None:
        """Create checkpoint if enough time has passed."""
        now = time.time()
        if now - self.last_checkpoint > self.settings.checkpoint_interval_seconds:
            logger.info("Creating checkpoint...")
            self._last_save_state = self.emulator.save_state()
            self.last_checkpoint = now

    def _cleanup(self) -> None:
        """Clean up resources."""
        if self._start_time:
            duration = time.time() - self._start_time
            logger.info(
                "Game loop ended",
                duration_seconds=int(duration),
                total_frames=self.emulator.frame_count,
            )

    def stop(self) -> None:
        """Stop the game loop gracefully."""
        self._running = False


def main() -> None:
    """Entry point."""
    # Load configuration
    config = get_config()

    # Setup logging
    setup_logging(
        log_level=config.log_level,
        log_to_file=config.log_to_file,
        log_dir=config.log_dir,
    )

    logger.info(
        "Pokemon Red AI Agent starting",
        model=config.agent_model,
        rom_path=config.rom_path,
        headless=config.headless,
        speed=config.emulation_speed,
        initial_objective=config.initial_objective,
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

    # Create game loop
    logger.info("Initializing game loop")
    game = GameLoop(config)

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum: int, frame: object) -> None:
        logger.info("Received signal, shutting down", signal=signum)
        game.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the game loop
    try:
        game.run()
    finally:
        game.emulator.close()
        logger.info("Emulator closed")


if __name__ == "__main__":
    main()
