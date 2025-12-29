"""Shared fixtures for integration tests."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock
import pytest

from src.emulator.state_reader import (
    BattleState,
    GameMode,
    GameState,
    InventoryItem,
    Pokemon,
    Position,
    RawMove,
    RawStats,
)
from src.agent.state import GameState as AgentGameState
from src.agent.types import Objective


@pytest.fixture
def mock_emulator():
    """Create a mock emulator interface."""
    mock = MagicMock()
    mock.read_memory.return_value = 0
    mock.read_memory_word.return_value = 0
    mock.read_memory_range.return_value = bytes([0, 0, 0])
    mock.frame_count = 1000
    mock.is_running = True
    mock.save_state.return_value = b"mock_save_state"
    return mock


@pytest.fixture
def sample_position():
    """Create a sample emulator Position."""
    return Position(map_id=0, x=5, y=5, facing="DOWN")


@pytest.fixture
def sample_pokemon():
    """Create a sample emulator Pokemon with moves and stats."""
    return Pokemon(
        species_id=25,
        species_name="PIKACHU",
        level=15,
        current_hp=35,
        max_hp=40,
        status=None,
        moves=[
            RawMove(move_id=84, pp_current=20, pp_ups=0),  # Thunder Shock
            RawMove(move_id=45, pp_current=25, pp_ups=0),  # Growl
            RawMove(move_id=39, pp_current=30, pp_ups=0),  # Tail Whip
            RawMove(move_id=98, pp_current=15, pp_ups=0),  # Quick Attack
        ],
        stats=RawStats(attack=45, defense=35, speed=90, special=50),
    )


@pytest.fixture
def sample_raw_state(sample_position, sample_pokemon):
    """Create a sample emulator GameState."""
    return GameState(
        mode=GameMode.OVERWORLD,
        position=sample_position,
        party=[sample_pokemon],
        party_count=1,
        badges=["BOULDER"],
        badge_count=1,
        money=3000,
        frame_count=1000,
        battle=None,
        inventory=[
            InventoryItem(item_id=4, item_name="POKE_BALL", count=10),
            InventoryItem(item_id=20, item_name="POTION", count=5),
        ],
    )


@pytest.fixture
def sample_battle_state():
    """Create a sample emulator BattleState."""
    return BattleState(
        battle_type="WILD",
        enemy_species_id=19,
        enemy_species_name="RATTATA",
        enemy_level=5,
        enemy_hp_percent=100.0,
    )


@pytest.fixture
def sample_agent_state():
    """Create a sample agent GameState with a party."""
    from src.agent.types import Pokemon, Stats

    state = AgentGameState()
    state.push_objective(Objective(
        type="become_champion",
        target="Elite Four",
        priority=1,
    ))
    # Add a party with at least one alive Pokemon so fainted_count != len(party)
    state.party = [
        Pokemon(
            species="PIKACHU",
            level=20,
            current_hp=50,
            max_hp=50,
            types=["ELECTRIC"],
            moves=[],
            stats=Stats(hp=50, attack=40, defense=30, speed=90, special=50),
        )
    ]
    return state


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    mock = Mock()
    mock.rom_path = "test.gb"
    mock.headless = True
    mock.emulation_speed = 0
    mock.initial_objective = "become_champion"
    mock.initial_objective_target = "Elite Four"
    mock.use_opus_for_bosses = True
    mock.checkpoint_interval_seconds = 300
    mock.max_retries = 3
    mock.retry_delay_seconds = 1.0
    mock.get_rom_path.return_value = MagicMock(exists=lambda: True)
    return mock
