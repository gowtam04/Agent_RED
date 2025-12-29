"""Integration tests for the game loop."""

from unittest.mock import MagicMock, Mock, patch
import pytest

from src.agent.types import AgentResult, Objective
from src.recovery import RecoveryAction, diagnose_failure


class TestGameLoopInitialization:
    """Tests for GameLoop initialization."""

    @patch("src.main.EmulatorInterface")
    @patch("src.main.StateReader")
    @patch("src.main.StateConverter")
    @patch("src.main.AgentRegistry")
    def test_initial_objective_become_champion(
        self,
        mock_registry,
        mock_converter,
        mock_reader,
        mock_emulator,
        mock_config,
    ):
        """Test that initial objective is set correctly for become_champion."""
        from src.main import GameLoop

        mock_config.initial_objective = "become_champion"
        mock_config.initial_objective_target = "Elite Four"

        game = GameLoop(mock_config)

        assert game.agent_state.current_objective is not None
        assert game.agent_state.current_objective.type == "become_champion"
        assert game.agent_state.current_objective.target == "Elite Four"

    @patch("src.main.EmulatorInterface")
    @patch("src.main.StateReader")
    @patch("src.main.StateConverter")
    @patch("src.main.AgentRegistry")
    def test_initial_objective_defeat_gym(
        self,
        mock_registry,
        mock_converter,
        mock_reader,
        mock_emulator,
        mock_config,
    ):
        """Test that initial objective is set correctly for defeat_gym."""
        from src.main import GameLoop

        mock_config.initial_objective = "defeat_gym"
        mock_config.initial_objective_target = "Brock"

        game = GameLoop(mock_config)

        assert game.agent_state.current_objective is not None
        assert game.agent_state.current_objective.type == "defeat_gym"
        assert game.agent_state.current_objective.target == "Brock"

    @patch("src.main.EmulatorInterface")
    @patch("src.main.StateReader")
    @patch("src.main.StateConverter")
    @patch("src.main.AgentRegistry")
    def test_initial_objective_catch_pokemon(
        self,
        mock_registry,
        mock_converter,
        mock_reader,
        mock_emulator,
        mock_config,
    ):
        """Test that initial objective is set correctly for catch_pokemon."""
        from src.main import GameLoop

        mock_config.initial_objective = "catch_pokemon"
        mock_config.initial_objective_target = "PIKACHU"

        game = GameLoop(mock_config)

        assert game.agent_state.current_objective is not None
        assert game.agent_state.current_objective.type == "catch_pokemon"
        assert game.agent_state.current_objective.target == "PIKACHU"


class TestModeDetection:
    """Tests for game mode detection and routing."""

    def test_overworld_routes_to_navigation(self, sample_agent_state):
        """Test that overworld mode routes to navigation agent."""
        from src.agent import AgentRegistry

        registry = AgentRegistry()
        sample_agent_state.mode = "OVERWORLD"

        agent_type = registry.route_by_mode("OVERWORLD")
        assert agent_type == "NAVIGATION"

    def test_battle_routes_to_battle(self, sample_agent_state):
        """Test that battle mode routes to battle agent."""
        from src.agent import AgentRegistry

        registry = AgentRegistry()

        agent_type = registry.route_by_mode("BATTLE")
        assert agent_type == "BATTLE"

    def test_menu_routes_to_menu(self, sample_agent_state):
        """Test that menu mode routes to menu agent."""
        from src.agent import AgentRegistry

        registry = AgentRegistry()

        agent_type = registry.route_by_mode("MENU")
        assert agent_type == "MENU"

    def test_dialogue_routes_to_menu(self, sample_agent_state):
        """Test that dialogue mode routes to menu agent."""
        from src.agent import AgentRegistry

        registry = AgentRegistry()

        agent_type = registry.route_by_mode("DIALOGUE")
        assert agent_type == "MENU"


class TestOpusEscalation:
    """Tests for Opus model escalation."""

    def test_should_escalate_for_gym_leader(self):
        """Test that gym leader battles trigger Opus escalation."""
        from src.agent import AgentRegistry
        from src.agent.state import GameState
        from src.agent.types import BattleState, Pokemon, Stats, Move

        registry = AgentRegistry()
        state = GameState()

        # Create a gym leader battle
        state.battle = BattleState(
            battle_type="GYM_LEADER",
            can_flee=False,
            can_catch=False,
            turn_number=1,
            our_pokemon=Pokemon(
                species="PIKACHU",
                level=20,
                current_hp=50,
                max_hp=50,
                types=["ELECTRIC"],
                moves=[],
                stats=Stats(50, 40, 30, 90, 50),
            ),
            enemy_pokemon=Pokemon(
                species="ONIX",
                level=14,
                current_hp=30,
                max_hp=30,
                types=["ROCK", "GROUND"],
                moves=[],
                stats=Stats(30, 40, 100, 40, 30),
            ),
        )

        assert registry.should_escalate_to_opus(state) is True

    def test_should_escalate_for_elite_four(self):
        """Test that Elite Four battles trigger Opus escalation."""
        from src.agent import AgentRegistry
        from src.agent.state import GameState
        from src.agent.types import BattleState, Pokemon, Stats

        registry = AgentRegistry()
        state = GameState()

        state.battle = BattleState(
            battle_type="ELITE_FOUR",
            can_flee=False,
            can_catch=False,
            turn_number=1,
            our_pokemon=Pokemon("PIKACHU", 50, 100, 100, ["ELECTRIC"], [], Stats(100, 80, 60, 120, 80)),
            enemy_pokemon=Pokemon("DEWGONG", 54, 100, 100, ["WATER", "ICE"], [], Stats(100, 70, 80, 70, 95)),
        )

        assert registry.should_escalate_to_opus(state) is True

    def test_should_not_escalate_for_wild(self):
        """Test that wild battles don't trigger Opus escalation."""
        from src.agent import AgentRegistry
        from src.agent.state import GameState
        from src.agent.types import BattleState, Pokemon, Stats

        registry = AgentRegistry()
        state = GameState()

        state.battle = BattleState(
            battle_type="WILD",
            can_flee=True,
            can_catch=True,
            turn_number=1,
            our_pokemon=Pokemon("PIKACHU", 20, 50, 50, ["ELECTRIC"], [], Stats(50, 40, 30, 90, 50)),
            enemy_pokemon=Pokemon("RATTATA", 5, 15, 15, ["NORMAL"], [], Stats(15, 20, 15, 30, 10)),
        )

        assert registry.should_escalate_to_opus(state) is False


class TestRecovery:
    """Tests for error recovery."""

    def test_diagnose_stuck_navigation(self, sample_agent_state):
        """Test that stuck navigation is diagnosed correctly."""
        action = diagnose_failure(sample_agent_state, "stuck in navigation, no path found")

        assert action.type in ("fly_to_pc", "navigate_to_pc")

    def test_diagnose_party_wiped(self, sample_agent_state):
        """Test that party wipe is diagnosed correctly."""
        action = diagnose_failure(sample_agent_state, "all Pokemon fainted")

        assert action.type == "wait_for_respawn"

    def test_diagnose_underleveled(self, sample_agent_state):
        """Test that underleveled is diagnosed correctly."""
        action = diagnose_failure(sample_agent_state, "underleveled for this fight")

        assert action.type == "grind"
        assert action.objective is not None
        assert action.objective.type == "grind"

    def test_diagnose_api_error(self, sample_agent_state):
        """Test that API errors trigger wait and retry."""
        action = diagnose_failure(sample_agent_state, "API timeout error")

        assert action.type == "wait_and_retry"

    def test_diagnose_unknown_falls_back_to_checkpoint(self, sample_agent_state):
        """Test that unknown errors fall back to checkpoint reload."""
        action = diagnose_failure(sample_agent_state, "some unknown error")

        assert action.type == "reload_checkpoint"


class TestCheckpointing:
    """Tests for checkpoint creation."""

    @patch("src.main.EmulatorInterface")
    @patch("src.main.StateReader")
    @patch("src.main.StateConverter")
    @patch("src.main.AgentRegistry")
    def test_checkpoint_created_on_init(
        self,
        mock_registry,
        mock_converter,
        mock_reader,
        mock_emulator_class,
        mock_config,
    ):
        """Test that initial checkpoint is created."""
        from src.main import GameLoop

        mock_emulator = MagicMock()
        mock_emulator.save_state.return_value = b"initial_state"
        mock_emulator_class.return_value = mock_emulator

        game = GameLoop(mock_config)
        game._last_save_state = game.emulator.save_state()

        assert game._last_save_state == b"initial_state"

    @patch("src.main.EmulatorInterface")
    @patch("src.main.StateReader")
    @patch("src.main.StateConverter")
    @patch("src.main.AgentRegistry")
    @patch("time.time")
    def test_checkpoint_created_after_interval(
        self,
        mock_time,
        mock_registry,
        mock_converter,
        mock_reader,
        mock_emulator_class,
        mock_config,
    ):
        """Test that checkpoint is created after interval."""
        from src.main import GameLoop

        mock_emulator = MagicMock()
        mock_emulator.save_state.return_value = b"new_state"
        mock_emulator_class.return_value = mock_emulator

        mock_config.checkpoint_interval_seconds = 300

        game = GameLoop(mock_config)
        game.last_checkpoint = 0

        # Simulate time passing
        mock_time.return_value = 400  # 400 seconds > 300 interval

        game._maybe_checkpoint()

        # Should have saved state
        assert mock_emulator.save_state.called
