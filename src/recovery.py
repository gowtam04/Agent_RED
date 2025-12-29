"""Error recovery system for the Pokemon Red AI Agent."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.agent.types import Objective

if TYPE_CHECKING:
    from src.agent.state import GameState

logger = logging.getLogger(__name__)


@dataclass
class RecoveryAction:
    """An action to recover from a failure."""

    type: str  # reload_checkpoint, fly_to_pc, grind, wait, navigate_to_pc
    description: str
    objective: Objective | None = None


def diagnose_failure(state: GameState, error: str) -> RecoveryAction:
    """Diagnose a failure and recommend recovery action.

    Analyzes the current game state and error message to determine
    the best recovery strategy.

    Args:
        state: Current game state.
        error: Error message describing the failure.

    Returns:
        RecoveryAction with recommended recovery steps.
    """
    error_lower = error.lower()

    # Navigation stuck - try to fly or walk to Pokemon Center
    if "stuck" in error_lower or "no path" in error_lower or "blocked" in error_lower:
        # If we have Fly and can use it, fly to last Pokemon Center
        if "FLY" in state.hms_usable and state.last_pokemon_center:
            return RecoveryAction(
                type="fly_to_pc",
                description=f"Use Fly to return to {state.last_pokemon_center}",
                objective=Objective(
                    type="fly",
                    target=state.last_pokemon_center,
                    priority=10,
                ),
            )
        # Otherwise try to walk to nearest Pokemon Center
        return RecoveryAction(
            type="navigate_to_pc",
            description="Navigate to nearest Pokemon Center",
            objective=Objective(
                type="navigate",
                target="pokemon_center",
                priority=10,
            ),
        )

    # Party wiped - wait for respawn at Pokemon Center
    if "fainted" in error_lower or "whiteout" in error_lower or state.fainted_count == len(state.party):
        return RecoveryAction(
            type="wait_for_respawn",
            description="Wait for respawn at Pokemon Center",
        )

    # Underleveled - need to grind
    if "underleveled" in error_lower or "too strong" in error_lower:
        return RecoveryAction(
            type="grind",
            description="Grind for experience",
            objective=Objective(
                type="grind",
                target="level_up",
                priority=8,
            ),
        )

    # No money - grind trainers
    if "no money" in error_lower or "broke" in error_lower:
        return RecoveryAction(
            type="grind_money",
            description="Battle trainers for money",
            objective=Objective(
                type="grind",
                target="money",
                priority=7,
            ),
        )

    # Out of Poke Balls
    if "no poke ball" in error_lower or "out of balls" in error_lower:
        return RecoveryAction(
            type="buy_pokeballs",
            description="Go to mart and buy Poke Balls",
            objective=Objective(
                type="shop",
                target="POKE_BALL",
                priority=6,
            ),
        )

    # Need healing
    if "low hp" in error_lower or state.needs_healing:
        return RecoveryAction(
            type="heal",
            description="Heal at Pokemon Center",
            objective=Objective(
                type="heal",
                target="pokemon_center",
                priority=9,
            ),
        )

    # API error or unknown - reload checkpoint
    if "api" in error_lower or "timeout" in error_lower or "rate limit" in error_lower:
        return RecoveryAction(
            type="wait_and_retry",
            description="Wait and retry after API error",
        )

    # Default: reload last checkpoint
    return RecoveryAction(
        type="reload_checkpoint",
        description="Reload last checkpoint",
    )


def execute_recovery(action: RecoveryAction, game_loop: Any) -> bool:
    """Execute a recovery action.

    Args:
        action: The recovery action to execute.
        game_loop: Reference to the main game loop.

    Returns:
        True if recovery was successful, False otherwise.
    """
    logger.info(f"Executing recovery: {action.description}")

    if action.type == "reload_checkpoint":
        if hasattr(game_loop, "_last_save_state") and game_loop._last_save_state:
            logger.info("Loading last checkpoint...")
            game_loop.emulator.load_state(game_loop._last_save_state)
            return True
        logger.warning("No checkpoint available for reload")
        return False

    if action.type == "wait_for_respawn":
        # Game automatically respawns at Pokemon Center after whiteout
        # Just wait for the animation to complete
        import time

        logger.info("Waiting for respawn animation...")
        time.sleep(3)
        # Advance some frames to let the game process
        game_loop.emulator.tick(180)  # ~3 seconds at 60fps
        return True

    if action.type == "wait_and_retry":
        import time

        logger.info("Waiting before retry...")
        time.sleep(game_loop.settings.retry_delay_seconds)
        return True

    # For objective-based recoveries, push the objective and continue
    if action.objective:
        logger.info(f"Pushing recovery objective: {action.objective.type} -> {action.objective.target}")
        game_loop.agent_state.push_objective(action.objective)
        return True

    logger.warning(f"Unknown recovery action type: {action.type}")
    return False


class RecoveryManager:
    """Manages error recovery with retry logic."""

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """Initialize the recovery manager.

        Args:
            max_retries: Maximum number of retries before giving up.
            retry_delay: Delay in seconds between retries.
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._failure_count = 0
        self._last_error: str | None = None

    def record_failure(self, error: str) -> None:
        """Record a failure.

        Args:
            error: Error message describing the failure.
        """
        self._failure_count += 1
        self._last_error = error
        logger.warning(f"Failure #{self._failure_count}: {error}")

    def record_success(self) -> None:
        """Record a successful action, resetting failure count."""
        if self._failure_count > 0:
            logger.info(f"Recovery successful after {self._failure_count} failures")
        self._failure_count = 0
        self._last_error = None

    def should_recover(self) -> bool:
        """Check if we should attempt recovery.

        Returns:
            True if we should try to recover, False if we've exceeded max retries.
        """
        return self._failure_count <= self.max_retries

    def should_abort(self) -> bool:
        """Check if we should abort due to too many failures.

        Returns:
            True if we've exceeded max retries.
        """
        return self._failure_count > self.max_retries

    def get_failure_count(self) -> int:
        """Get the current failure count."""
        return self._failure_count

    def get_last_error(self) -> str | None:
        """Get the last error message."""
        return self._last_error

    def reset(self) -> None:
        """Reset the failure count and last error."""
        self._failure_count = 0
        self._last_error = None
