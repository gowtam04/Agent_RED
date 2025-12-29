"""Tests for OrchestratorAgent."""

import pytest

from src.agent import (
    BattleState,
    GameState,
    Move,
    Objective,
    OrchestratorAgent,
    Pokemon,
    Position,
    Stats,
)


@pytest.fixture
def orchestrator_agent() -> OrchestratorAgent:
    """Create an OrchestratorAgent instance."""
    return OrchestratorAgent(client=None)


@pytest.fixture
def sample_pokemon() -> Pokemon:
    """Create a sample Pokemon for testing."""
    return Pokemon(
        species="PIKACHU",
        level=25,
        current_hp=60,
        max_hp=60,
        types=["ELECTRIC"],
        moves=[
            Move(
                name="THUNDERBOLT",
                type="ELECTRIC",
                category="SPECIAL",
                power=95,
                accuracy=100,
                pp_current=15,
                pp_max=15,
            ),
        ],
        stats=Stats(hp=60, attack=55, defense=40, speed=90, special=50),
    )


def test_orchestrator_agent_initialization(
    orchestrator_agent: OrchestratorAgent,
) -> None:
    """Test OrchestratorAgent initialization."""
    assert orchestrator_agent.AGENT_TYPE == "ORCHESTRATOR"
    assert orchestrator_agent.DEFAULT_MODEL == "sonnet"
    assert "Orchestrator agent" in orchestrator_agent.SYSTEM_PROMPT


def test_register_tools(orchestrator_agent: OrchestratorAgent) -> None:
    """Test that tools are properly registered."""
    tools = orchestrator_agent._register_tools()
    assert len(tools) == 7
    tool_names = [t["name"] for t in tools]
    assert "detect_game_mode" in tool_names
    assert "get_current_objective" in tool_names
    assert "route_to_agent" in tool_names
    assert "manage_objective_stack" in tool_names


def test_detect_game_mode_from_state(orchestrator_agent: OrchestratorAgent) -> None:
    """Test detecting game mode from cached state."""
    state = GameState()
    state.mode = "OVERWORLD"

    result = orchestrator_agent._detect_game_mode({}, state)

    assert result.success is True
    assert result.result_data["mode"] == "OVERWORLD"
    assert result.result_data["source"] == "cached_state"


def test_detect_game_mode_battle(
    orchestrator_agent: OrchestratorAgent,
    sample_pokemon: Pokemon,
) -> None:
    """Test detecting battle mode with submode."""
    state = GameState()
    state.mode = "BATTLE"
    state.battle = BattleState(
        battle_type="WILD",
        can_flee=True,
        can_catch=True,
        turn_number=1,
        our_pokemon=sample_pokemon,
        enemy_pokemon=sample_pokemon,
    )

    result = orchestrator_agent._detect_game_mode({}, state)

    assert result.success is True
    assert result.result_data["mode"] == "BATTLE"
    assert result.result_data["submode"] == "WILD"


def test_get_current_objective_empty_stack(
    orchestrator_agent: OrchestratorAgent,
) -> None:
    """Test getting current objective when stack is empty."""
    state = GameState()
    state.objective_stack = []

    result = orchestrator_agent._get_current_objective({}, state)

    assert result.success is True
    assert result.result_data["needs_objective"] is True


def test_get_current_objective_with_objective(
    orchestrator_agent: OrchestratorAgent,
) -> None:
    """Test getting current objective from stack."""
    state = GameState()
    state.push_objective(
        Objective(
            type="defeat_gym",
            target="Brock",
            priority=5,
        )
    )

    result = orchestrator_agent._get_current_objective({}, state)

    assert result.success is True
    assert result.result_data["objective"]["type"] == "defeat_gym"
    assert result.result_data["objective"]["target"] == "Brock"


def test_get_next_milestone(orchestrator_agent: OrchestratorAgent) -> None:
    """Test getting next milestone."""
    state = GameState()
    state.badges = []
    state.story_flags = []

    result = orchestrator_agent._get_next_milestone(
        {"badges": [], "story_flags": []},
        state,
    )

    assert result.success is True
    # Should suggest first gym or first story objective


def test_check_requirements_gym_battle(
    orchestrator_agent: OrchestratorAgent,
) -> None:
    """Test checking requirements for gym battle."""
    state = GameState()
    state.party = []

    result = orchestrator_agent._check_requirements(
        {
            "objective_type": "defeat_gym",
            "objective_target": "BROCK",
            "current_state": {
                "badges": [],
                "party_types": ["ELECTRIC", "NORMAL"],
            },
        },
        state,
    )

    assert result.success is True
    # Should suggest getting Water or Grass type
    if result.result_data["suggestions"]:
        suggestion_reasons = [s.get("reason", "") for s in result.result_data["suggestions"]]
        assert any("type" in r.lower() for r in suggestion_reasons)


def test_check_requirements_catch_pokemon_no_balls(
    orchestrator_agent: OrchestratorAgent,
) -> None:
    """Test catching requirements without Poke Balls."""
    state = GameState()
    state.items = {}

    result = orchestrator_agent._check_requirements(
        {
            "objective_type": "catch_pokemon",
            "objective_target": "PIKACHU",
            "current_state": {},
        },
        state,
    )

    assert result.success is True
    assert result.result_data["requirements_met"] is False
    assert any(m["type"] == "item" for m in result.result_data["missing"])


def test_route_to_agent_overworld(orchestrator_agent: OrchestratorAgent) -> None:
    """Test routing to Navigation in overworld."""
    state = GameState()
    state.mode = "OVERWORLD"

    result = orchestrator_agent._route_to_agent(
        {"game_mode": "OVERWORLD", "current_objective": None},
        state,
    )

    assert result.success is True
    assert result.result_data["agent"] == "NAVIGATION"


def test_route_to_agent_battle(orchestrator_agent: OrchestratorAgent) -> None:
    """Test routing to Battle in battle mode."""
    state = GameState()
    state.mode = "BATTLE"

    result = orchestrator_agent._route_to_agent(
        {"game_mode": "BATTLE", "current_objective": None},
        state,
    )

    assert result.success is True
    assert result.result_data["agent"] == "BATTLE"


def test_route_to_agent_menu(orchestrator_agent: OrchestratorAgent) -> None:
    """Test routing to Menu in menu mode."""
    state = GameState()
    state.mode = "MENU"

    result = orchestrator_agent._route_to_agent(
        {"game_mode": "MENU", "current_objective": None},
        state,
    )

    assert result.success is True
    assert result.result_data["agent"] == "MENU"


def test_route_to_agent_dialogue(orchestrator_agent: OrchestratorAgent) -> None:
    """Test routing dialogue to Menu agent."""
    state = GameState()
    state.mode = "DIALOGUE"

    result = orchestrator_agent._route_to_agent(
        {"game_mode": "DIALOGUE", "current_objective": None},
        state,
    )

    assert result.success is True
    assert result.result_data["agent"] == "MENU"


def test_route_to_agent_needs_healing(
    orchestrator_agent: OrchestratorAgent,
    sample_pokemon: Pokemon,
) -> None:
    """Test routing to Menu for healing."""
    state = GameState()
    state.mode = "OVERWORLD"
    # Low HP Pokemon
    low_hp_pokemon = Pokemon(
        species="PIKACHU",
        level=25,
        current_hp=10,
        max_hp=60,
        types=["ELECTRIC"],
        moves=[],
        stats=Stats(hp=60, attack=55, defense=40, speed=90, special=50),
    )
    state.party = [low_hp_pokemon]

    result = orchestrator_agent._route_to_agent(
        {
            "game_mode": "OVERWORLD",
            "current_objective": None,
            "game_state_summary": {
                "party_avg_hp_percent": 16.7,
                "fainted_count": 0,
            },
        },
        state,
    )

    assert result.success is True
    assert result.result_data["agent"] == "MENU"
    assert result.result_data["reason"] == "party_needs_healing"
    # Should have pushed heal objective
    assert result.new_objectives is not None


def test_route_to_agent_boss_battle(
    orchestrator_agent: OrchestratorAgent,
    sample_pokemon: Pokemon,
) -> None:
    """Test routing with Opus escalation for gym leader."""
    state = GameState()
    state.mode = "BATTLE"
    state.battle = BattleState(
        battle_type="GYM_LEADER",
        can_flee=False,
        can_catch=False,
        turn_number=1,
        our_pokemon=sample_pokemon,
        enemy_pokemon=sample_pokemon,
        enemy_trainer="Brock",
    )

    result = orchestrator_agent._route_to_agent(
        {"game_mode": "BATTLE", "current_objective": None},
        state,
    )

    assert result.success is True
    assert result.result_data["agent"] == "BATTLE"
    assert result.result_data["escalate_to_opus"] is True


def test_update_game_state(orchestrator_agent: OrchestratorAgent) -> None:
    """Test updating game state."""
    state = GameState()
    state.money = 1000

    result = orchestrator_agent._update_game_state(
        {
            "updates": {
                "money": 2000,
                "current_mode": "MENU",
            },
            "source": "agent_report",
        },
        state,
    )

    assert result.success is True
    assert state.money == 2000
    assert state.mode == "MENU"
    assert "money" in result.result_data["updated_fields"]
    assert "mode" in result.result_data["updated_fields"]


def test_update_game_state_position(orchestrator_agent: OrchestratorAgent) -> None:
    """Test updating position in game state."""
    state = GameState()
    state.position = Position(map_id="PALLET_TOWN", x=0, y=0)

    result = orchestrator_agent._update_game_state(
        {
            "updates": {
                "current_map": "VIRIDIAN_CITY",
                "player_position": {"x": 10, "y": 15},
            },
            "source": "memory_read",
        },
        state,
    )

    assert result.success is True
    assert state.position.map_id == "VIRIDIAN_CITY"
    assert state.position.x == 10
    assert state.position.y == 15


def test_manage_objective_stack_push(orchestrator_agent: OrchestratorAgent) -> None:
    """Test pushing objective to stack."""
    state = GameState()
    state.objective_stack = []

    result = orchestrator_agent._manage_objective_stack(
        {
            "operation": "push",
            "objective": {
                "type": "defeat_gym",
                "target": "Brock",
                "priority": 5,
            },
        },
        state,
    )

    assert result.success is True
    assert result.result_data["operation"] == "push"
    assert len(state.objective_stack) == 1


def test_manage_objective_stack_pop(orchestrator_agent: OrchestratorAgent) -> None:
    """Test popping objective from stack."""
    state = GameState()
    state.push_objective(
        Objective(type="heal", target="POKEMON_CENTER")
    )

    result = orchestrator_agent._manage_objective_stack(
        {"operation": "pop"},
        state,
    )

    assert result.success is True
    assert result.result_data["operation"] == "pop"
    assert result.result_data["popped"]["type"] == "heal"
    assert len(state.objective_stack) == 0


def test_manage_objective_stack_pop_empty(
    orchestrator_agent: OrchestratorAgent,
) -> None:
    """Test popping from empty stack."""
    state = GameState()
    state.objective_stack = []

    result = orchestrator_agent._manage_objective_stack(
        {"operation": "pop"},
        state,
    )

    assert result.success is False
    assert "empty" in result.error.lower()


def test_manage_objective_stack_peek(orchestrator_agent: OrchestratorAgent) -> None:
    """Test peeking at top of stack."""
    state = GameState()
    state.push_objective(
        Objective(type="navigate", target="VIRIDIAN_CITY")
    )

    result = orchestrator_agent._manage_objective_stack(
        {"operation": "peek"},
        state,
    )

    assert result.success is True
    assert result.result_data["current"]["type"] == "navigate"
    assert len(state.objective_stack) == 1  # Not removed


def test_manage_objective_stack_peek_empty(
    orchestrator_agent: OrchestratorAgent,
) -> None:
    """Test peeking at empty stack."""
    state = GameState()
    state.objective_stack = []

    result = orchestrator_agent._manage_objective_stack(
        {"operation": "peek"},
        state,
    )

    assert result.success is True
    assert result.result_data["current"] is None


def test_manage_objective_stack_clear_completed(
    orchestrator_agent: OrchestratorAgent,
) -> None:
    """Test clearing completed objectives."""
    state = GameState()
    state.push_objective(Objective(type="heal", target="PC", completed=True))
    state.push_objective(Objective(type="navigate", target="CITY", completed=False))
    state.push_objective(Objective(type="catch", target="PIKACHU", completed=True))

    result = orchestrator_agent._manage_objective_stack(
        {"operation": "clear_completed"},
        state,
    )

    assert result.success is True
    assert result.result_data["removed_count"] == 2
    assert len(state.objective_stack) == 1


def test_manage_objective_stack_push_missing_data(
    orchestrator_agent: OrchestratorAgent,
) -> None:
    """Test pushing without objective data."""
    state = GameState()

    result = orchestrator_agent._manage_objective_stack(
        {"operation": "push"},
        state,
    )

    assert result.success is False
    assert "requires objective" in result.error.lower()


def test_execute_tool_unknown(orchestrator_agent: OrchestratorAgent) -> None:
    """Test executing unknown tool."""
    state = GameState()

    result = orchestrator_agent._execute_tool("unknown_tool", {}, state)

    assert result.success is False
    assert "unknown tool" in result.error.lower()
