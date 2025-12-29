"""Pydantic models for the web API."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class PokemonStatus(BaseModel):
    """Status of a Pokemon in the party."""

    species: str
    level: int
    hp: int
    max_hp: int
    status: Optional[str] = None


class PositionData(BaseModel):
    """Player position data."""

    map_id: str
    map_name: str
    x: int
    y: int
    facing: str


class BattleData(BaseModel):
    """Current battle information."""

    battle_type: str
    enemy_species: str
    enemy_level: int
    enemy_hp_percent: float = 100.0


class GameData(BaseModel):
    """Current game state data."""

    mode: Literal["OVERWORLD", "BATTLE", "MENU", "DIALOGUE"]
    position: PositionData
    party: list[PokemonStatus]
    in_battle: bool
    battle: Optional[BattleData] = None
    money: int
    badges: list[str]


class ObjectiveData(BaseModel):
    """An objective in the objective stack."""

    type: str
    target: str
    priority: int


class EngineData(BaseModel):
    """Engine/runtime state data."""

    running: bool
    paused: bool
    current_agent: str
    objective_stack: list[ObjectiveData]
    total_frames: int
    api_calls: int
    uptime_seconds: float


class StateUpdate(BaseModel):
    """Full state update payload sent via WebSocket."""

    type: Literal["STATE_UPDATE"] = "STATE_UPDATE"
    game: GameData
    engine: EngineData
    screen: str  # Base64 PNG


class ThoughtData(BaseModel):
    """Agent thought/reasoning data."""

    timestamp: str
    agent_type: str
    reasoning: str
    action: str
    result_data: dict[str, Any] = Field(default_factory=dict)


class GameEventData(BaseModel):
    """Game event data."""

    timestamp: str
    event_type: str
    description: str
    data: dict[str, Any] = Field(default_factory=dict)


class ControlCommand(BaseModel):
    """Control command from the dashboard."""

    type: Literal["SET_SPEED", "PAUSE", "RESUME", "SAVE_STATE", "LOAD_STATE"]
    payload: Optional[dict[str, Any]] = None


class GameStatus(BaseModel):
    """Quick status check response."""

    running: bool
    paused: bool
    current_mode: str
    current_agent: str
    total_frames: int
    api_calls: int
    uptime_seconds: float


class WebSocketMessage(BaseModel):
    """Generic WebSocket message wrapper."""

    type: str
    data: Optional[Any] = None
