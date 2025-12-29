"""Integration tests for StateConverter."""

import pytest

from src.emulator.state_converter import StateConverter
from src.emulator.state_reader import GameMode, GameState, Pokemon, Position, RawMove, RawStats
from src.agent.state import GameState as AgentGameState


class TestStateConverter:
    """Tests for the StateConverter class."""

    def test_convert_position_map_id(self, sample_raw_state, sample_agent_state):
        """Test that map ID is converted from int to string name."""
        converter = StateConverter()

        # Map ID 0 should be PALLET_TOWN
        sample_raw_state.position.map_id = 0
        converter.convert(sample_raw_state, sample_agent_state)

        assert sample_agent_state.position.map_id == "PALLET_TOWN"

    def test_convert_position_coordinates(self, sample_raw_state, sample_agent_state):
        """Test that position coordinates are preserved."""
        converter = StateConverter()

        sample_raw_state.position.x = 10
        sample_raw_state.position.y = 15
        sample_raw_state.position.facing = "UP"

        converter.convert(sample_raw_state, sample_agent_state)

        assert sample_agent_state.position.x == 10
        assert sample_agent_state.position.y == 15
        assert sample_agent_state.position.facing == "UP"

    def test_convert_mode(self, sample_raw_state, sample_agent_state):
        """Test that game mode is converted correctly."""
        converter = StateConverter()

        sample_raw_state.mode = GameMode.BATTLE
        converter.convert(sample_raw_state, sample_agent_state)
        assert sample_agent_state.mode == "BATTLE"

        sample_raw_state.mode = GameMode.MENU
        converter.convert(sample_raw_state, sample_agent_state)
        assert sample_agent_state.mode == "MENU"

        sample_raw_state.mode = GameMode.DIALOGUE
        converter.convert(sample_raw_state, sample_agent_state)
        assert sample_agent_state.mode == "DIALOGUE"

        sample_raw_state.mode = GameMode.OVERWORLD
        converter.convert(sample_raw_state, sample_agent_state)
        assert sample_agent_state.mode == "OVERWORLD"

    def test_convert_party_basic(self, sample_raw_state, sample_agent_state):
        """Test that party Pokemon are converted."""
        converter = StateConverter()
        converter.convert(sample_raw_state, sample_agent_state)

        assert len(sample_agent_state.party) == 1
        pokemon = sample_agent_state.party[0]
        assert pokemon.species == "PIKACHU"
        assert pokemon.level == 15
        assert pokemon.current_hp == 35
        assert pokemon.max_hp == 40

    def test_convert_party_types(self, sample_raw_state, sample_agent_state):
        """Test that Pokemon types are looked up from knowledge base."""
        converter = StateConverter()
        converter.convert(sample_raw_state, sample_agent_state)

        pokemon = sample_agent_state.party[0]
        # Pikachu should have ELECTRIC type
        assert "ELECTRIC" in pokemon.types

    def test_convert_party_stats(self, sample_raw_state, sample_agent_state):
        """Test that Pokemon stats are converted from memory."""
        converter = StateConverter()
        converter.convert(sample_raw_state, sample_agent_state)

        pokemon = sample_agent_state.party[0]
        assert pokemon.stats.attack == 45
        assert pokemon.stats.defense == 35
        assert pokemon.stats.speed == 90
        assert pokemon.stats.special == 50

    def test_convert_badges(self, sample_raw_state, sample_agent_state):
        """Test that badges are synced."""
        converter = StateConverter()

        sample_raw_state.badges = ["BOULDER", "CASCADE"]
        converter.convert(sample_raw_state, sample_agent_state)

        assert sample_agent_state.badges == ["BOULDER", "CASCADE"]

    def test_convert_money(self, sample_raw_state, sample_agent_state):
        """Test that money is synced."""
        converter = StateConverter()

        sample_raw_state.money = 5000
        converter.convert(sample_raw_state, sample_agent_state)

        assert sample_agent_state.money == 5000

    def test_convert_inventory_items(self, sample_raw_state, sample_agent_state):
        """Test that inventory is converted."""
        converter = StateConverter()
        converter.convert(sample_raw_state, sample_agent_state)

        assert "POKE_BALL" in sample_agent_state.items
        assert sample_agent_state.items["POKE_BALL"] == 10
        assert "POTION" in sample_agent_state.items
        assert sample_agent_state.items["POTION"] == 5

    def test_preserves_objectives(self, sample_raw_state, sample_agent_state):
        """Test that agent-only state (objectives) is preserved."""
        converter = StateConverter()

        # Agent state already has an objective from fixture
        original_objective = sample_agent_state.current_objective

        converter.convert(sample_raw_state, sample_agent_state)

        # Objective should still be there
        assert sample_agent_state.current_objective == original_objective

    def test_convert_move_id_to_move(self):
        """Test move ID to Move object conversion."""
        converter = StateConverter()

        # Thunder Shock has ID 84
        move = converter.convert_move_id_to_move(84, pp_current=20)

        assert move is not None
        assert move.name == "THUNDERSHOCK"
        assert move.type == "ELECTRIC"
        assert move.pp_current == 20

    def test_convert_move_id_zero_returns_none(self):
        """Test that move ID 0 returns None."""
        converter = StateConverter()

        move = converter.convert_move_id_to_move(0, pp_current=0)

        assert move is None

    def test_unknown_map_id_fallback(self, sample_raw_state, sample_agent_state):
        """Test that unknown map IDs get a fallback name."""
        converter = StateConverter()

        sample_raw_state.position.map_id = 999  # Invalid ID
        converter.convert(sample_raw_state, sample_agent_state)

        # Should get a fallback name like MAP_3E7
        assert sample_agent_state.position.map_id.startswith("MAP_")
