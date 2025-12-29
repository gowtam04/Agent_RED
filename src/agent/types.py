"""Shared types for the Pokemon Red AI Agent system."""

from dataclasses import dataclass, field
from typing import Any, Literal

# Game Mode Detection
GameMode = Literal["OVERWORLD", "BATTLE", "MENU", "DIALOGUE"]

# Battle Types
BattleType = Literal["WILD", "TRAINER", "GYM_LEADER", "ELITE_FOUR", "CHAMPION", "RIVAL"]

# Directions
Direction = Literal["UP", "DOWN", "LEFT", "RIGHT"]

# Move Categories (Gen 1: determined by type)
MoveCategory = Literal["PHYSICAL", "SPECIAL", "STATUS"]

# Status Conditions
Status = Literal["POISON", "BURN", "SLEEP", "FREEZE", "PARALYSIS"]

# Tile Types
TileType = Literal["PATH", "GRASS", "WATER", "LEDGE", "DOOR", "CUT_TREE", "BOULDER", "WALL"]

# Menu Types
MenuType = Literal["START_MENU", "BAG", "PARTY", "PC", "SHOP", "DIALOGUE", "YES_NO", "MOVE_LEARN"]

# Agent Types
AgentType = Literal["ORCHESTRATOR", "NAVIGATION", "BATTLE", "MENU"]

# Model Selection
ModelType = Literal["haiku", "sonnet", "opus"]


@dataclass
class Position:
    """Player or entity position."""

    map_id: str
    x: int
    y: int
    facing: Direction = "DOWN"


@dataclass
class Stats:
    """Pokemon stats (Gen 1 style)."""

    hp: int
    attack: int
    defense: int
    speed: int
    special: int


@dataclass
class Move:
    """A Pokemon's move in battle."""

    name: str
    type: str
    category: MoveCategory
    power: int
    accuracy: int
    pp_current: int
    pp_max: int
    effect: str | None = None


@dataclass
class Pokemon:
    """A Pokemon in the party or encountered."""

    species: str
    level: int
    current_hp: int
    max_hp: int
    types: list[str]
    moves: list[Move]
    stats: Stats
    status: Status | None = None


@dataclass
class BattleState:
    """Current battle state."""

    battle_type: BattleType
    can_flee: bool
    can_catch: bool
    turn_number: int
    our_pokemon: Pokemon
    enemy_pokemon: Pokemon
    our_stat_stages: dict[str, int] = field(default_factory=dict)
    enemy_stat_stages: dict[str, int] = field(default_factory=dict)
    enemy_trainer: str | None = None
    enemy_remaining: int = 1


@dataclass
class Objective:
    """An objective in the objective stack."""

    type: str  # navigate, defeat_gym, catch_pokemon, heal, grind, etc.
    target: str
    priority: int = 1
    requirements: list[str] = field(default_factory=list)
    completed: bool = False


@dataclass
class AgentResult:
    """Result returned by an agent after taking action."""

    success: bool
    action_taken: str
    result_data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    handoff_to: AgentType | None = None
    new_objectives: list[Objective] = field(default_factory=list)
