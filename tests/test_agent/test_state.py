"""Tests for GameState."""

from src.agent import GameState, Move, Objective, Pokemon, Position, Stats


def test_game_state_defaults() -> None:
    """Test GameState default values."""
    state = GameState()
    assert state.mode == "OVERWORLD"
    assert state.position.map_id == "PALLET_TOWN"
    assert state.party == []
    assert state.battle is None
    assert state.badges == []
    assert state.story_flags == []
    assert state.money == 0
    assert state.objective_stack == []


def test_game_state_objectives() -> None:
    """Test GameState objective stack operations."""
    state = GameState()

    obj = Objective(type="heal", target="pokemon_center")
    state.push_objective(obj)

    assert state.current_objective == obj
    assert state.pop_objective() == obj
    assert state.current_objective is None


def test_game_state_multiple_objectives() -> None:
    """Test GameState with multiple objectives."""
    state = GameState()

    obj1 = Objective(type="navigate", target="PEWTER_CITY", priority=3)
    obj2 = Objective(type="defeat_gym", target="Brock", priority=5)
    obj3 = Objective(type="heal", target="pokemon_center", priority=10)

    state.push_objective(obj1)
    state.push_objective(obj2)
    state.push_objective(obj3)

    # Top of stack should be the last pushed
    assert state.current_objective == obj3
    assert state.pop_objective() == obj3
    assert state.current_objective == obj2


def test_party_hp_percent() -> None:
    """Test party HP percentage calculation."""
    state = GameState()
    stats = Stats(hp=55, attack=55, defense=30, speed=90, special=50)

    state.party = [
        Pokemon(
            species="PIKACHU",
            level=25,
            current_hp=30,
            max_hp=55,
            types=["ELECTRIC"],
            moves=[],
            stats=stats,
        )
    ]
    expected = (30 / 55) * 100
    assert abs(state.party_hp_percent - expected) < 0.01


def test_party_hp_percent_multiple() -> None:
    """Test party HP percentage with multiple Pokemon."""
    state = GameState()
    stats = Stats(hp=100, attack=100, defense=100, speed=100, special=100)

    state.party = [
        Pokemon(
            species="POKEMON1",
            level=50,
            current_hp=50,
            max_hp=100,
            types=["NORMAL"],
            moves=[],
            stats=stats,
        ),
        Pokemon(
            species="POKEMON2",
            level=50,
            current_hp=100,
            max_hp=100,
            types=["NORMAL"],
            moves=[],
            stats=stats,
        ),
    ]
    # Average: (50/100 + 100/100) / 2 = 0.75 = 75%
    assert abs(state.party_hp_percent - 75.0) < 0.01


def test_party_hp_percent_empty() -> None:
    """Test party HP percentage with empty party."""
    state = GameState()
    assert state.party_hp_percent == 0.0


def test_fainted_count() -> None:
    """Test fainted Pokemon count."""
    state = GameState()
    stats = Stats(hp=100, attack=100, defense=100, speed=100, special=100)

    state.party = [
        Pokemon(
            species="POKEMON1",
            level=50,
            current_hp=0,  # Fainted
            max_hp=100,
            types=["NORMAL"],
            moves=[],
            stats=stats,
        ),
        Pokemon(
            species="POKEMON2",
            level=50,
            current_hp=50,  # Not fainted
            max_hp=100,
            types=["NORMAL"],
            moves=[],
            stats=stats,
        ),
        Pokemon(
            species="POKEMON3",
            level=50,
            current_hp=0,  # Fainted
            max_hp=100,
            types=["NORMAL"],
            moves=[],
            stats=stats,
        ),
    ]
    assert state.fainted_count == 2


def test_needs_healing_low_hp() -> None:
    """Test needs_healing when HP is low."""
    state = GameState()
    stats = Stats(hp=100, attack=100, defense=100, speed=100, special=100)

    state.party = [
        Pokemon(
            species="POKEMON1",
            level=50,
            current_hp=40,  # 40%
            max_hp=100,
            types=["NORMAL"],
            moves=[],
            stats=stats,
        )
    ]
    assert state.needs_healing is True


def test_needs_healing_fainted() -> None:
    """Test needs_healing when a Pokemon is fainted."""
    state = GameState()
    stats = Stats(hp=100, attack=100, defense=100, speed=100, special=100)

    state.party = [
        Pokemon(
            species="POKEMON1",
            level=50,
            current_hp=0,  # Fainted
            max_hp=100,
            types=["NORMAL"],
            moves=[],
            stats=stats,
        ),
        Pokemon(
            species="POKEMON2",
            level=50,
            current_hp=100,  # Full HP
            max_hp=100,
            types=["NORMAL"],
            moves=[],
            stats=stats,
        ),
    ]
    # Average HP is 50%, but there's a fainted Pokemon
    assert state.needs_healing is True


def test_needs_healing_healthy() -> None:
    """Test needs_healing when party is healthy."""
    state = GameState()
    stats = Stats(hp=100, attack=100, defense=100, speed=100, special=100)

    state.party = [
        Pokemon(
            species="POKEMON1",
            level=50,
            current_hp=80,  # 80%
            max_hp=100,
            types=["NORMAL"],
            moves=[],
            stats=stats,
        )
    ]
    assert state.needs_healing is False


def test_has_badge() -> None:
    """Test badge checking."""
    state = GameState()
    state.badges = ["BOULDER", "CASCADE"]

    assert state.has_badge("BOULDER") is True
    assert state.has_badge("CASCADE") is True
    assert state.has_badge("THUNDER") is False


def test_can_use_hm() -> None:
    """Test HM usage checking."""
    state = GameState()
    state.hms_obtained = ["CUT", "FLY"]
    state.hms_usable = ["CUT"]  # Have badge + taught

    assert state.can_use_hm("CUT") is True
    assert state.can_use_hm("FLY") is False  # Obtained but not usable
    assert state.can_use_hm("SURF") is False


def test_game_state_with_position() -> None:
    """Test GameState with custom position."""
    pos = Position("CERULEAN_CITY", 10, 20, "LEFT")
    state = GameState(position=pos)

    assert state.position.map_id == "CERULEAN_CITY"
    assert state.position.x == 10
    assert state.position.y == 20
    assert state.position.facing == "LEFT"


def test_game_state_defeated_trainers() -> None:
    """Test defeated trainers tracking."""
    state = GameState()
    state.defeated_trainers.add("TRAINER_ROUTE1_1")
    state.defeated_trainers.add("TRAINER_ROUTE1_2")

    assert "TRAINER_ROUTE1_1" in state.defeated_trainers
    assert "TRAINER_ROUTE1_3" not in state.defeated_trainers


def test_game_state_items() -> None:
    """Test inventory management."""
    state = GameState()
    state.items = {"POTION": 5, "POKE_BALL": 10}
    state.key_items = ["TOWN_MAP", "BICYCLE"]

    assert state.items["POTION"] == 5
    assert "TOWN_MAP" in state.key_items
