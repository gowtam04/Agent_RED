"""Tests for agent types."""

from src.agent import (
    AgentResult,
    BattleState,
    Move,
    Objective,
    Pokemon,
    Position,
    Stats,
)


def test_position_creation() -> None:
    """Test Position dataclass creation."""
    pos = Position("PALLET_TOWN", 5, 10, "UP")
    assert pos.map_id == "PALLET_TOWN"
    assert pos.x == 5
    assert pos.y == 10
    assert pos.facing == "UP"


def test_position_default_facing() -> None:
    """Test Position default facing direction."""
    pos = Position("ROUTE_1", 0, 0)
    assert pos.facing == "DOWN"


def test_stats_creation() -> None:
    """Test Stats dataclass creation."""
    stats = Stats(hp=55, attack=55, defense=30, speed=90, special=50)
    assert stats.hp == 55
    assert stats.attack == 55
    assert stats.defense == 30
    assert stats.speed == 90
    assert stats.special == 50


def test_move_creation() -> None:
    """Test Move dataclass creation."""
    move = Move(
        name="THUNDERBOLT",
        type="ELECTRIC",
        category="SPECIAL",
        power=95,
        accuracy=100,
        pp_current=15,
        pp_max=15,
        effect="10% chance to paralyze",
    )
    assert move.name == "THUNDERBOLT"
    assert move.type == "ELECTRIC"
    assert move.category == "SPECIAL"
    assert move.power == 95
    assert move.accuracy == 100
    assert move.pp_current == 15
    assert move.pp_max == 15
    assert move.effect == "10% chance to paralyze"


def test_move_no_effect() -> None:
    """Test Move with no effect."""
    move = Move(
        name="TACKLE",
        type="NORMAL",
        category="PHYSICAL",
        power=35,
        accuracy=95,
        pp_current=35,
        pp_max=35,
    )
    assert move.effect is None


def test_pokemon_creation() -> None:
    """Test Pokemon dataclass creation."""
    stats = Stats(hp=55, attack=55, defense=30, speed=90, special=50)
    moves = [
        Move("THUNDER_SHOCK", "ELECTRIC", "SPECIAL", 40, 100, 30, 30),
        Move("QUICK_ATTACK", "NORMAL", "PHYSICAL", 40, 100, 30, 30),
    ]
    pokemon = Pokemon(
        species="PIKACHU",
        level=25,
        current_hp=45,
        max_hp=55,
        types=["ELECTRIC"],
        moves=moves,
        stats=stats,
    )
    assert pokemon.species == "PIKACHU"
    assert pokemon.level == 25
    assert pokemon.current_hp == 45
    assert pokemon.max_hp == 55
    assert pokemon.types == ["ELECTRIC"]
    assert len(pokemon.moves) == 2
    assert pokemon.status is None


def test_pokemon_with_status() -> None:
    """Test Pokemon with status condition."""
    stats = Stats(hp=55, attack=55, defense=30, speed=90, special=50)
    pokemon = Pokemon(
        species="PIKACHU",
        level=25,
        current_hp=45,
        max_hp=55,
        types=["ELECTRIC"],
        moves=[],
        stats=stats,
        status="PARALYSIS",
    )
    assert pokemon.status == "PARALYSIS"


def test_objective_creation() -> None:
    """Test Objective dataclass creation."""
    obj = Objective(type="defeat_gym", target="Brock", priority=5)
    assert obj.type == "defeat_gym"
    assert obj.target == "Brock"
    assert obj.priority == 5
    assert obj.completed is False
    assert obj.requirements == []


def test_objective_with_requirements() -> None:
    """Test Objective with requirements."""
    obj = Objective(
        type="navigate",
        target="PEWTER_CITY",
        priority=3,
        requirements=["clear_viridian_forest"],
    )
    assert obj.requirements == ["clear_viridian_forest"]


def test_agent_result_success() -> None:
    """Test AgentResult for successful action."""
    result = AgentResult(
        success=True,
        action_taken="move_direction",
        result_data={"direction": "UP", "new_position": (5, 11)},
    )
    assert result.success is True
    assert result.action_taken == "move_direction"
    assert result.result_data["direction"] == "UP"
    assert result.error is None
    assert result.handoff_to is None
    assert result.new_objectives == []


def test_agent_result_failure() -> None:
    """Test AgentResult for failed action."""
    result = AgentResult(
        success=False,
        action_taken="use_hm",
        error="Cannot use CUT without CASCADE badge",
    )
    assert result.success is False
    assert result.error == "Cannot use CUT without CASCADE badge"


def test_agent_result_with_handoff() -> None:
    """Test AgentResult with agent handoff."""
    result = AgentResult(
        success=True,
        action_taken="detect_mode",
        handoff_to="BATTLE",
    )
    assert result.handoff_to == "BATTLE"


def test_battle_state_creation() -> None:
    """Test BattleState dataclass creation."""
    stats = Stats(hp=55, attack=55, defense=30, speed=90, special=50)
    our_pokemon = Pokemon(
        species="PIKACHU",
        level=25,
        current_hp=55,
        max_hp=55,
        types=["ELECTRIC"],
        moves=[],
        stats=stats,
    )
    enemy_stats = Stats(hp=44, attack=48, defense=65, speed=35, special=50)
    enemy_pokemon = Pokemon(
        species="GEODUDE",
        level=12,
        current_hp=44,
        max_hp=44,
        types=["ROCK", "GROUND"],
        moves=[],
        stats=enemy_stats,
    )
    battle = BattleState(
        battle_type="WILD",
        can_flee=True,
        can_catch=True,
        turn_number=1,
        our_pokemon=our_pokemon,
        enemy_pokemon=enemy_pokemon,
    )
    assert battle.battle_type == "WILD"
    assert battle.can_flee is True
    assert battle.can_catch is True
    assert battle.turn_number == 1
    assert battle.our_pokemon.species == "PIKACHU"
    assert battle.enemy_pokemon.species == "GEODUDE"
    assert battle.enemy_trainer is None
    assert battle.enemy_remaining == 1


def test_battle_state_trainer() -> None:
    """Test BattleState for trainer battle."""
    stats = Stats(hp=55, attack=55, defense=30, speed=90, special=50)
    pokemon = Pokemon(
        species="PIKACHU",
        level=25,
        current_hp=55,
        max_hp=55,
        types=["ELECTRIC"],
        moves=[],
        stats=stats,
    )
    battle = BattleState(
        battle_type="GYM_LEADER",
        can_flee=False,
        can_catch=False,
        turn_number=1,
        our_pokemon=pokemon,
        enemy_pokemon=pokemon,
        enemy_trainer="Brock",
        enemy_remaining=2,
    )
    assert battle.battle_type == "GYM_LEADER"
    assert battle.can_flee is False
    assert battle.can_catch is False
    assert battle.enemy_trainer == "Brock"
    assert battle.enemy_remaining == 2
