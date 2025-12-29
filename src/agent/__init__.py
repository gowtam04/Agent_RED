"""Agent module for Pokemon Red AI."""

from .base import BaseAgent
from .objective import (
    ObjectiveStack,
    create_catch_objective,
    create_gym_objective,
    create_heal_objective,
)
from .registry import AgentRegistry
from .simple_agent import SimpleAgent
from .state import GameState
from .types import (
    AgentResult,
    AgentType,
    BattleState,
    BattleType,
    Direction,
    GameMode,
    MenuType,
    ModelType,
    Move,
    MoveCategory,
    Objective,
    Pokemon,
    Position,
    Stats,
    Status,
    TileType,
)

__all__ = [
    # Types
    "GameMode",
    "BattleType",
    "Direction",
    "MoveCategory",
    "Status",
    "TileType",
    "MenuType",
    "AgentType",
    "ModelType",
    # Dataclasses
    "Position",
    "Stats",
    "Move",
    "Pokemon",
    "BattleState",
    "Objective",
    "AgentResult",
    # State
    "GameState",
    # Agents
    "BaseAgent",
    "SimpleAgent",
    # Registry
    "AgentRegistry",
    # Objective management
    "ObjectiveStack",
    "create_heal_objective",
    "create_gym_objective",
    "create_catch_objective",
]
