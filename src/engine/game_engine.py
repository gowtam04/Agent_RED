"""Async game engine that wraps GameLoop for web dashboard."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine, Optional

import structlog

from ..agent import AgentRegistry, AgentResult, Objective
from ..agent import GameState as AgentGameState
from ..api.broadcaster import AgentThought, GameEvent, get_broadcaster
from ..config import Config
from ..emulator import EmulatorInterface, StateReader
from ..emulator.state_converter import StateConverter
from ..recovery import RecoveryManager, diagnose_failure

logger = structlog.get_logger()


@dataclass
class EngineState:
    """Runtime state of the game engine."""

    running: bool = False
    paused: bool = False
    current_agent: str = "none"
    total_frames: int = 0
    api_calls: int = 0
    start_time: Optional[datetime] = None

    @property
    def uptime_seconds(self) -> float:
        """Get the uptime in seconds."""
        if self.start_time is None:
            return 0.0
        return (datetime.now() - self.start_time).total_seconds()


@dataclass
class EngineCallbacks:
    """Callbacks for engine events."""

    on_state_update: list[Callable[[dict[str, Any]], Coroutine[Any, Any, None]]] = field(
        default_factory=list
    )


class GameEngine:
    """Async wrapper around game components for web dashboard integration.

    This class manages the game loop asynchronously, allowing for:
    - Non-blocking state updates at configurable FPS
    - Event broadcasting to WebSocket clients
    - Pause/resume/speed control from the dashboard
    """

    def __init__(self, config: Config):
        """Initialize the game engine.

        Args:
            config: Application configuration.
        """
        self.config = config
        self.state = EngineState()
        self.callbacks = EngineCallbacks()
        self.broadcaster = get_broadcaster()

        # Thread pool for blocking emulator operations
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="game_engine")

        # Game components (initialized on start)
        self._emulator: Optional[EmulatorInterface] = None
        self._state_reader: Optional[StateReader] = None
        self._state_converter: Optional[StateConverter] = None
        self._registry: Optional[AgentRegistry] = None
        self._agent_state: Optional[AgentGameState] = None
        self._recovery: Optional[RecoveryManager] = None

        # Main loop task
        self._task: Optional[asyncio.Task[None]] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Previous state for event detection
        self._prev_map: Optional[str] = None
        self._prev_battle: bool = False

    async def start(self) -> None:
        """Start the game engine."""
        if self.state.running:
            logger.warning("Engine already running")
            return

        logger.info("Starting game engine")

        # Initialize components in executor (blocking I/O)
        loop = asyncio.get_running_loop()
        self._loop = loop
        self.broadcaster.set_event_loop(loop)

        await loop.run_in_executor(self._executor, self._initialize_components)

        self.state.running = True
        self.state.start_time = datetime.now()

        # Start main loop
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Game engine started")

    def _initialize_components(self) -> None:
        """Initialize game components (runs in executor)."""
        import anthropic

        # Initialize emulator (headless for dashboard - we stream the screen)
        self._emulator = EmulatorInterface(
            rom_path=self.config.get_rom_path(),
            headless=True,  # Always headless for dashboard
            speed=self.config.emulation_speed,
        )

        # State reading and conversion
        self._state_reader = StateReader(self._emulator)
        self._state_converter = StateConverter()

        # Agent system
        client = anthropic.Anthropic(api_key=self.config.anthropic_api_key)
        self._registry = AgentRegistry(client=client)
        self._agent_state = AgentGameState()

        # Recovery
        self._recovery = RecoveryManager(
            max_retries=self.config.max_retries,
            retry_delay=self.config.retry_delay_seconds,
        )

        # Set initial objective
        self._set_initial_objective()

        logger.info("Game components initialized")

    def _set_initial_objective(self) -> None:
        """Set the initial high-level objective from config."""
        objective_map = {
            "become_champion": Objective(
                type="become_champion",
                target=self.config.initial_objective_target,
                priority=1,
            ),
            "defeat_gym": Objective(
                type="defeat_gym",
                target=self.config.initial_objective_target,
                priority=5,
            ),
            "catch_pokemon": Objective(
                type="catch_pokemon",
                target=self.config.initial_objective_target,
                priority=3,
            ),
        }

        obj = objective_map.get(
            self.config.initial_objective,
            objective_map["become_champion"],
        )
        if self._agent_state:
            self._agent_state.push_objective(obj)

    async def _run_loop(self) -> None:
        """Main async game loop."""
        target_interval = 1.0 / self.config.state_broadcast_fps

        while self.state.running:
            loop_start = asyncio.get_event_loop().time()

            if self.state.paused:
                await asyncio.sleep(0.1)
                continue

            try:
                # Run tick in executor (blocking)
                if self._loop:
                    await self._loop.run_in_executor(self._executor, self._tick_sync)

                # Broadcast state update
                await self._broadcast_state()

            except Exception as e:
                logger.error("Error in game loop", error=str(e), exc_info=True)
                await asyncio.sleep(1.0)  # Prevent tight loop on repeated errors

            # Frame pacing
            elapsed = asyncio.get_event_loop().time() - loop_start
            sleep_time = max(0, target_interval - elapsed)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

    def _tick_sync(self) -> None:
        """Synchronous tick (runs in executor)."""
        if not all([self._emulator, self._state_reader, self._state_converter,
                    self._registry, self._agent_state, self._recovery]):
            return

        # Store previous state for event detection
        prev_map = self._agent_state.position.map_id if self._agent_state else None
        prev_battle = self._agent_state.battle is not None if self._agent_state else False

        # 1. Read current game state from emulator
        raw_state = self._state_reader.get_game_state()

        # 2. Convert to agent state
        self._state_converter.convert(raw_state, self._agent_state)

        # 3. Update frame counter
        self.state.total_frames = self._emulator.frame_count

        # 4. Get Orchestrator decision
        orchestrator = self._registry.get_agent("ORCHESTRATOR")
        self.state.current_agent = "ORCHESTRATOR"
        result = orchestrator.act(self._agent_state)
        self.state.api_calls += 1

        # 5. Broadcast agent thought
        self._emit_thought("ORCHESTRATOR", result)

        if not result.success:
            logger.warning(f"Orchestrator failed: {result.error}")
            self._handle_failure(result.error or "Orchestrator failure")
            return

        # 6. If Orchestrator routes to another agent, execute that agent
        if result.handoff_to:
            self._execute_handoff(result)

        # 7. Process new objectives
        for obj in result.new_objectives:
            self._agent_state.push_objective(obj)

        # 8. Record success
        self._recovery.record_success()

        # 9. Detect and emit game events
        self._detect_events(prev_map, prev_battle)

    def _execute_handoff(self, orchestrator_result: AgentResult) -> None:
        """Execute a handoff to a specialist agent."""
        agent_type = orchestrator_result.handoff_to
        if not agent_type or not self._registry or not self._agent_state:
            return

        self.state.current_agent = agent_type

        agent = self._registry.get_agent(agent_type)

        # Check for Opus escalation
        if orchestrator_result.result_data.get("escalate_to_opus"):
            if self.config.use_opus_for_bosses:
                agent.model = "opus"

        # Execute the agent
        agent_result = agent.act(self._agent_state)
        self.state.api_calls += 1

        # Broadcast agent thought
        self._emit_thought(agent_type, agent_result)

        if not agent_result.success:
            logger.warning(f"{agent_type} agent failed: {agent_result.error}")
            self._handle_failure(agent_result.error or f"{agent_type} failure")
            return

        # Execute the result
        self._execute_result(agent_result)

        # Process new objectives
        for obj in agent_result.new_objectives:
            self._agent_state.push_objective(obj)

    def _execute_result(self, result: AgentResult) -> None:
        """Execute an agent result by translating to emulator actions."""
        if not self._emulator:
            return

        from ..emulator import Button

        action = result.action_taken
        data = result.result_data

        if action == "press_button":
            button_name = data.get("button", "A")
            try:
                button = Button[button_name]
                self._emulator.press_button(button)
            except KeyError:
                logger.warning("Invalid button", button=button_name)

        elif action in ("move", "execute_movement"):
            direction = data.get("direction", "DOWN")
            tiles = data.get("tiles", 1)
            self._emulator.move(direction, tiles)

        elif action == "wait":
            seconds = data.get("seconds", 1.0)
            self._emulator.run_for_seconds(seconds)

        elif action in ("detect_game_mode", "route_to_agent", "get_current_objective"):
            # Orchestrator internal actions
            pass

        else:
            # Advance frames for unhandled actions
            self._emulator.tick(30)

        # Always advance frames after action
        self._emulator.tick(30)

    def _handle_failure(self, error: str) -> None:
        """Handle agent failure."""
        if not self._recovery or not self._agent_state:
            return

        self._recovery.record_failure(error)

        if self._recovery.should_abort():
            logger.error("Too many failures, stopping engine")
            self.state.running = False
            return

        # Diagnose failure
        action = diagnose_failure(self._agent_state, error)
        logger.info(f"Recovery action: {action.type}")

    def _emit_thought(self, agent_type: str, result: AgentResult) -> None:
        """Emit an agent thought to the broadcaster."""
        if result.reasoning:
            thought = AgentThought(
                timestamp=datetime.now(),
                agent_type=agent_type,
                reasoning=result.reasoning,
                action=result.action_taken,
                result_data=result.result_data,
            )
            self.broadcaster.add_thought(thought)

    def _detect_events(self, prev_map: Optional[str], prev_battle: bool) -> None:
        """Detect game events by comparing state changes."""
        if not self._agent_state:
            return

        state = self._agent_state
        now = datetime.now()

        # Map change
        if prev_map and state.position.map_id != prev_map:
            self.broadcaster.add_event(
                GameEvent(
                    timestamp=now,
                    event_type="map_change",
                    description=f"Entered {state.position.map_id}",
                    data={"from": prev_map, "to": state.position.map_id},
                )
            )

        # Battle start
        if state.battle is not None and not prev_battle:
            enemy = state.battle.enemy_pokemon
            self.broadcaster.add_event(
                GameEvent(
                    timestamp=now,
                    event_type="battle_start",
                    description=f"Battle started vs {enemy.species} Lv{enemy.level}",
                    data={
                        "battle_type": state.battle.battle_type,
                        "enemy_species": enemy.species,
                        "enemy_level": enemy.level,
                    },
                )
            )

        # Battle end
        if state.battle is None and prev_battle:
            self.broadcaster.add_event(
                GameEvent(
                    timestamp=now,
                    event_type="battle_end",
                    description="Battle ended",
                    data={},
                )
            )

    async def _broadcast_state(self) -> None:
        """Broadcast current state to all listeners."""
        if not self._emulator or not self._agent_state:
            return

        state_data = self._build_state_payload()

        for callback in self.callbacks.on_state_update:
            try:
                await callback(state_data)
            except Exception as e:
                logger.warning("Failed to broadcast state", error=str(e))

    def _build_state_payload(self) -> dict[str, Any]:
        """Build the state update payload."""
        if not self._emulator or not self._agent_state:
            return {}

        state = self._agent_state

        return {
            "type": "STATE_UPDATE",
            "game": {
                "mode": state.mode,
                "position": {
                    "map_id": state.position.map_id,
                    "map_name": state.position.map_id,  # Could map to friendly name
                    "x": state.position.x,
                    "y": state.position.y,
                    "facing": state.position.facing,
                },
                "party": [
                    {
                        "species": p.species,
                        "level": p.level,
                        "hp": p.current_hp,
                        "max_hp": p.max_hp,
                        "status": p.status,
                    }
                    for p in state.party
                ],
                "in_battle": state.battle is not None,
                "battle": {
                    "battle_type": state.battle.battle_type,
                    "enemy_species": state.battle.enemy_pokemon.species,
                    "enemy_level": state.battle.enemy_pokemon.level,
                    "enemy_hp_percent": (
                        state.battle.enemy_pokemon.current_hp
                        / state.battle.enemy_pokemon.max_hp
                        * 100
                    ),
                }
                if state.battle
                else None,
                "money": state.money,
                "badges": list(state.badges),
            },
            "engine": {
                "running": self.state.running,
                "paused": self.state.paused,
                "current_agent": self.state.current_agent,
                "objective_stack": [
                    {"type": o.type, "target": o.target, "priority": o.priority}
                    for o in state.objective_stack
                ],
                "total_frames": self.state.total_frames,
                "api_calls": self.state.api_calls,
                "uptime_seconds": self.state.uptime_seconds,
            },
            "screen": self._emulator.get_screen_base64(scale=3),
        }

    def on_state_update(
        self, callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
    ) -> None:
        """Register callback for state updates.

        Args:
            callback: Async function(state_data) to call on updates.
        """
        self.callbacks.on_state_update.append(callback)

    def pause(self) -> None:
        """Pause the game."""
        self.state.paused = True
        logger.info("Game paused")

    def resume(self) -> None:
        """Resume the game."""
        self.state.paused = False
        logger.info("Game resumed")

    def set_speed(self, speed: int) -> None:
        """Set the emulation speed.

        Args:
            speed: 0=unlimited, 1=normal, 2+=faster
        """
        if self._emulator:
            self._emulator._pyboy.set_emulation_speed(speed)
            logger.info("Emulation speed set", speed=speed)

    async def stop(self) -> None:
        """Stop the game engine."""
        logger.info("Stopping game engine")
        self.state.running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # Cleanup in executor
        if self._loop:
            await self._loop.run_in_executor(self._executor, self._cleanup)

        self._executor.shutdown(wait=True)
        logger.info("Game engine stopped")

    def _cleanup(self) -> None:
        """Clean up resources (runs in executor)."""
        if self._emulator:
            self._emulator.close()
            self._emulator = None

    def get_status(self) -> dict[str, Any]:
        """Get current engine status."""
        return {
            "running": self.state.running,
            "paused": self.state.paused,
            "current_mode": self._agent_state.mode if self._agent_state else "UNKNOWN",
            "current_agent": self.state.current_agent,
            "total_frames": self.state.total_frames,
            "api_calls": self.state.api_calls,
            "uptime_seconds": self.state.uptime_seconds,
        }
