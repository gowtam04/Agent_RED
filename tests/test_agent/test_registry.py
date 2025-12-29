"""Tests for AgentRegistry."""

import pytest

from src.agent import AgentRegistry, BattleState, GameState, Move, Pokemon, Stats


def test_route_by_mode_overworld() -> None:
    """Test routing OVERWORLD mode to NAVIGATION agent."""
    registry = AgentRegistry()
    assert registry.route_by_mode("OVERWORLD") == "NAVIGATION"


def test_route_by_mode_battle() -> None:
    """Test routing BATTLE mode to BATTLE agent."""
    registry = AgentRegistry()
    assert registry.route_by_mode("BATTLE") == "BATTLE"


def test_route_by_mode_menu() -> None:
    """Test routing MENU mode to MENU agent."""
    registry = AgentRegistry()
    assert registry.route_by_mode("MENU") == "MENU"


def test_route_by_mode_dialogue() -> None:
    """Test routing DIALOGUE mode to MENU agent."""
    registry = AgentRegistry()
    assert registry.route_by_mode("DIALOGUE") == "MENU"


def test_should_escalate_to_opus_no_battle() -> None:
    """Test escalation check when not in battle."""
    registry = AgentRegistry()
    state = GameState()
    assert registry.should_escalate_to_opus(state) is False


def test_should_escalate_to_opus_wild_battle() -> None:
    """Test escalation for wild battle (should not escalate)."""
    registry = AgentRegistry()
    stats = Stats(hp=100, attack=100, defense=100, speed=100, special=100)
    pokemon = Pokemon(
        species="PIKACHU",
        level=25,
        current_hp=100,
        max_hp=100,
        types=["ELECTRIC"],
        moves=[],
        stats=stats,
    )
    state = GameState(
        battle=BattleState(
            battle_type="WILD",
            can_flee=True,
            can_catch=True,
            turn_number=1,
            our_pokemon=pokemon,
            enemy_pokemon=pokemon,
        )
    )
    assert registry.should_escalate_to_opus(state) is False


def test_should_escalate_to_opus_trainer_battle() -> None:
    """Test escalation for regular trainer battle (should not escalate)."""
    registry = AgentRegistry()
    stats = Stats(hp=100, attack=100, defense=100, speed=100, special=100)
    pokemon = Pokemon(
        species="PIKACHU",
        level=25,
        current_hp=100,
        max_hp=100,
        types=["ELECTRIC"],
        moves=[],
        stats=stats,
    )
    state = GameState(
        battle=BattleState(
            battle_type="TRAINER",
            can_flee=False,
            can_catch=False,
            turn_number=1,
            our_pokemon=pokemon,
            enemy_pokemon=pokemon,
        )
    )
    assert registry.should_escalate_to_opus(state) is False


def test_should_escalate_to_opus_gym_leader() -> None:
    """Test escalation for gym leader battle (should escalate)."""
    registry = AgentRegistry()
    stats = Stats(hp=100, attack=100, defense=100, speed=100, special=100)
    pokemon = Pokemon(
        species="PIKACHU",
        level=25,
        current_hp=100,
        max_hp=100,
        types=["ELECTRIC"],
        moves=[],
        stats=stats,
    )
    state = GameState(
        battle=BattleState(
            battle_type="GYM_LEADER",
            can_flee=False,
            can_catch=False,
            turn_number=1,
            our_pokemon=pokemon,
            enemy_pokemon=pokemon,
            enemy_trainer="Brock",
        )
    )
    assert registry.should_escalate_to_opus(state) is True


def test_should_escalate_to_opus_elite_four() -> None:
    """Test escalation for Elite Four battle (should escalate)."""
    registry = AgentRegistry()
    stats = Stats(hp=100, attack=100, defense=100, speed=100, special=100)
    pokemon = Pokemon(
        species="PIKACHU",
        level=25,
        current_hp=100,
        max_hp=100,
        types=["ELECTRIC"],
        moves=[],
        stats=stats,
    )
    state = GameState(
        battle=BattleState(
            battle_type="ELITE_FOUR",
            can_flee=False,
            can_catch=False,
            turn_number=1,
            our_pokemon=pokemon,
            enemy_pokemon=pokemon,
            enemy_trainer="Lorelei",
        )
    )
    assert registry.should_escalate_to_opus(state) is True


def test_should_escalate_to_opus_champion() -> None:
    """Test escalation for Champion battle (should escalate)."""
    registry = AgentRegistry()
    stats = Stats(hp=100, attack=100, defense=100, speed=100, special=100)
    pokemon = Pokemon(
        species="PIKACHU",
        level=25,
        current_hp=100,
        max_hp=100,
        types=["ELECTRIC"],
        moves=[],
        stats=stats,
    )
    state = GameState(
        battle=BattleState(
            battle_type="CHAMPION",
            can_flee=False,
            can_catch=False,
            turn_number=1,
            our_pokemon=pokemon,
            enemy_pokemon=pokemon,
            enemy_trainer="Blue",
        )
    )
    assert registry.should_escalate_to_opus(state) is True


def test_get_agent_orchestrator() -> None:
    """Test that get_agent returns correct agent type for ORCHESTRATOR."""
    registry = AgentRegistry()
    agent = registry.get_agent("ORCHESTRATOR")
    assert agent.AGENT_TYPE == "ORCHESTRATOR"


def test_get_agent_all_types() -> None:
    """Test get_agent returns correct agent for all types."""
    registry = AgentRegistry()

    expected_types = {
        "ORCHESTRATOR": "ORCHESTRATOR",
        "NAVIGATION": "NAVIGATION",
        "BATTLE": "BATTLE",
        "MENU": "MENU",
    }

    for agent_type, expected in expected_types.items():
        agent = registry.get_agent(agent_type)  # type: ignore
        assert agent.AGENT_TYPE == expected
