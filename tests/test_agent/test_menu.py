"""Tests for MenuAgent."""

import pytest

from src.agent import (
    GameState,
    MenuAgent,
    Move,
    Pokemon,
    Position,
    Stats,
)


@pytest.fixture
def menu_agent() -> MenuAgent:
    """Create a MenuAgent instance."""
    return MenuAgent(client=None)


@pytest.fixture
def sample_party() -> list[Pokemon]:
    """Create a sample party for testing."""
    return [
        Pokemon(
            species="PIKACHU",
            level=25,
            current_hp=30,
            max_hp=60,
            types=["ELECTRIC"],
            moves=[
                Move(
                    name="THUNDERBOLT",
                    type="ELECTRIC",
                    category="SPECIAL",
                    power=95,
                    accuracy=100,
                    pp_current=10,
                    pp_max=15,
                ),
            ],
            stats=Stats(hp=60, attack=55, defense=40, speed=90, special=50),
        ),
        Pokemon(
            species="SQUIRTLE",
            level=20,
            current_hp=50,
            max_hp=50,
            types=["WATER"],
            moves=[],
            stats=Stats(hp=50, attack=48, defense=65, speed=43, special=50),
        ),
    ]


def test_menu_agent_initialization(menu_agent: MenuAgent) -> None:
    """Test MenuAgent initialization."""
    assert menu_agent.AGENT_TYPE == "MENU"
    assert menu_agent.DEFAULT_MODEL == "haiku"
    assert "Menu agent" in menu_agent.SYSTEM_PROMPT


def test_register_tools(menu_agent: MenuAgent) -> None:
    """Test that tools are properly registered."""
    tools = menu_agent._register_tools()
    assert len(tools) == 14
    tool_names = [t["name"] for t in tools]
    assert "navigate_menu" in tool_names
    assert "heal_at_pokemon_center" in tool_names
    assert "shop_buy" in tool_names
    assert "get_party_status" in tool_names


def test_navigate_menu_no_emulator(menu_agent: MenuAgent) -> None:
    """Test menu navigation without emulator."""
    result = menu_agent._navigate_menu(
        {"action": "move", "direction": "DOWN", "count": 2},
        GameState(),
    )
    assert result.success is True
    assert result.result_data["executed"] is False


def test_open_start_menu_no_emulator(menu_agent: MenuAgent) -> None:
    """Test opening start menu without emulator."""
    result = menu_agent._open_start_menu({}, GameState())
    assert result.success is True
    assert result.result_data["executed"] is False


def test_get_inventory(menu_agent: MenuAgent) -> None:
    """Test getting inventory."""
    state = GameState()
    state.items = {
        "POTION": 5,
        "POKE_BALL": 10,
        "GREAT_BALL": 3,
        "TM01": 1,
    }
    state.key_items = ["BICYCLE", "TOWN_MAP"]

    result = menu_agent._get_inventory(
        {"category_filter": "all"},
        state,
    )
    assert result.success is True
    assert result.result_data["count"] == 4


def test_get_inventory_balls_filter(menu_agent: MenuAgent) -> None:
    """Test getting inventory with balls filter."""
    state = GameState()
    state.items = {
        "POTION": 5,
        "POKE_BALL": 10,
        "GREAT_BALL": 3,
    }

    result = menu_agent._get_inventory(
        {"category_filter": "balls"},
        state,
    )
    assert result.success is True
    assert result.result_data["count"] == 2
    assert "POKE_BALL" in result.result_data["items"]


def test_get_inventory_healing_filter(menu_agent: MenuAgent) -> None:
    """Test getting inventory with healing filter."""
    state = GameState()
    state.items = {
        "POTION": 5,
        "SUPER_POTION": 3,
        "POKE_BALL": 10,
        "ANTIDOTE": 2,
    }

    result = menu_agent._get_inventory(
        {"category_filter": "healing"},
        state,
    )
    assert result.success is True
    assert result.result_data["count"] == 3


def test_get_inventory_key_items(menu_agent: MenuAgent) -> None:
    """Test getting key items."""
    state = GameState()
    state.key_items = ["BICYCLE", "TOWN_MAP", "SS_TICKET"]

    result = menu_agent._get_inventory(
        {"category_filter": "key_items"},
        state,
    )
    assert result.success is True
    assert result.result_data["count"] == 3


def test_use_item_not_in_inventory(menu_agent: MenuAgent) -> None:
    """Test using item not in inventory."""
    state = GameState()
    state.items = {}

    result = menu_agent._use_item(
        {"item": "POTION"},
        state,
    )
    assert result.success is False
    assert "not in inventory" in result.error.lower()


def test_heal_at_pokemon_center(
    menu_agent: MenuAgent, sample_party: list[Pokemon]
) -> None:
    """Test Pokemon Center healing (mocked)."""
    state = GameState()
    state.party = sample_party

    # First Pokemon is at 50% HP
    assert state.party[0].current_hp == 30
    assert state.party[0].max_hp == 60

    result = menu_agent._heal_at_pokemon_center(
        {"confirm_location": False},
        state,
    )

    assert result.success is True
    assert result.result_data["party_healed"] is True
    # Pokemon should be fully healed
    assert state.party[0].current_hp == 60


def test_shop_buy(menu_agent: MenuAgent) -> None:
    """Test buying items."""
    state = GameState()
    state.money = 5000
    state.items = {}

    result = menu_agent._shop_buy(
        {"items": [{"item": "POKE_BALL", "quantity": 5}]},
        state,
    )

    assert result.success is True
    assert len(result.result_data["items_bought"]) > 0


def test_shop_buy_insufficient_funds(menu_agent: MenuAgent) -> None:
    """Test buying items with insufficient funds."""
    state = GameState()
    state.money = 100
    state.items = {}

    result = menu_agent._shop_buy(
        {"items": [{"item": "ULTRA_BALL", "quantity": 10}]},
        state,
    )

    assert result.success is True
    # Should not have bought anything due to insufficient funds
    assert len(result.result_data["items_bought"]) == 0


def test_shop_sell(menu_agent: MenuAgent) -> None:
    """Test selling items."""
    state = GameState()
    state.money = 1000
    state.items = {"POKE_BALL": 10}

    result = menu_agent._shop_sell(
        {"items": [{"item": "POKE_BALL", "quantity": 5}]},
        state,
    )

    assert result.success is True
    # Should have 5 left
    assert state.items["POKE_BALL"] == 5


def test_get_shop_inventory(menu_agent: MenuAgent) -> None:
    """Test getting shop inventory."""
    state = GameState()
    state.position = Position(map_id="VIRIDIAN_CITY_MART", x=5, y=5)

    result = menu_agent._get_shop_inventory({}, state)

    assert result.success is True
    assert "items" in result.result_data


def test_manage_party_view(
    menu_agent: MenuAgent, sample_party: list[Pokemon]
) -> None:
    """Test viewing party."""
    state = GameState()
    state.party = sample_party

    result = menu_agent._manage_party({"action": "view"}, state)

    assert result.success is True
    assert len(result.result_data["party"]) == 2


def test_manage_party_swap(
    menu_agent: MenuAgent, sample_party: list[Pokemon]
) -> None:
    """Test swapping party members."""
    state = GameState()
    state.party = sample_party

    assert state.party[0].species == "PIKACHU"
    assert state.party[1].species == "SQUIRTLE"

    result = menu_agent._manage_party(
        {"action": "swap", "position_1": 0, "position_2": 1},
        state,
    )

    assert result.success is True
    assert state.party[0].species == "SQUIRTLE"
    assert state.party[1].species == "PIKACHU"


def test_manage_party_view_summary(
    menu_agent: MenuAgent, sample_party: list[Pokemon]
) -> None:
    """Test viewing party member summary."""
    state = GameState()
    state.party = sample_party

    result = menu_agent._manage_party(
        {"action": "view_summary", "position_1": 0},
        state,
    )

    assert result.success is True
    assert result.result_data["pokemon"]["species"] == "PIKACHU"
    assert result.result_data["pokemon"]["level"] == 25


def test_manage_party_view_moves(
    menu_agent: MenuAgent, sample_party: list[Pokemon]
) -> None:
    """Test viewing party member moves."""
    state = GameState()
    state.party = sample_party

    result = menu_agent._manage_party(
        {"action": "view_moves", "position_1": 0},
        state,
    )

    assert result.success is True
    assert len(result.result_data["moves"]) == 1
    assert result.result_data["moves"][0]["name"] == "THUNDERBOLT"


def test_teach_move_no_target(menu_agent: MenuAgent) -> None:
    """Test teaching move to non-existent Pokemon."""
    state = GameState()
    state.party = []

    result = menu_agent._teach_move(
        {"move_item": "TM01", "target_pokemon": "PIKACHU"},
        state,
    )

    assert result.success is False
    assert "not found" in result.error.lower()


def test_pc_deposit_last_pokemon(
    menu_agent: MenuAgent, sample_party: list[Pokemon]
) -> None:
    """Test depositing last Pokemon (should fail)."""
    state = GameState()
    state.party = [sample_party[0]]  # Only one Pokemon

    result = menu_agent._pc_deposit_pokemon(
        {"pokemon": "0"},
        state,
    )

    assert result.success is False
    assert "last pokemon" in result.error.lower()


def test_pc_deposit_pokemon(
    menu_agent: MenuAgent, sample_party: list[Pokemon]
) -> None:
    """Test depositing Pokemon."""
    state = GameState()
    state.party = sample_party.copy()

    result = menu_agent._pc_deposit_pokemon(
        {"pokemon": "0", "box": 1},
        state,
    )

    assert result.success is True
    assert len(state.party) == 1


def test_pc_withdraw_party_full(menu_agent: MenuAgent) -> None:
    """Test withdrawing when party is full."""
    state = GameState()
    stats = Stats(hp=50, attack=50, defense=50, speed=50, special=50)
    state.party = [
        Pokemon(
            species=f"POKEMON{i}",
            level=10,
            current_hp=50,
            max_hp=50,
            types=["NORMAL"],
            moves=[],
            stats=stats,
        )
        for i in range(6)
    ]

    result = menu_agent._pc_withdraw_pokemon(
        {"pokemon": "PIKACHU", "box": 1},
        state,
    )

    assert result.success is False
    assert "full" in result.error.lower()


def test_handle_dialogue_no_emulator(menu_agent: MenuAgent) -> None:
    """Test handling dialogue without emulator."""
    result = menu_agent._handle_dialogue(
        {"action": "advance"},
        GameState(),
    )

    assert result.success is True
    assert result.result_data["executed"] is False


def test_get_party_status(
    menu_agent: MenuAgent, sample_party: list[Pokemon]
) -> None:
    """Test getting party status."""
    state = GameState()
    state.party = sample_party

    result = menu_agent._get_party_status(
        {"include_moves": True},
        state,
    )

    assert result.success is True
    assert result.result_data["party_size"] == 2
    assert result.result_data["fainted_count"] == 0
    # First Pokemon at 50% HP
    assert result.result_data["needs_healing"] is True


def test_get_party_status_no_moves(
    menu_agent: MenuAgent, sample_party: list[Pokemon]
) -> None:
    """Test getting party status without moves."""
    state = GameState()
    state.party = sample_party

    result = menu_agent._get_party_status(
        {"include_moves": False},
        state,
    )

    assert result.success is True
    assert "moves" not in result.result_data["party"][0]
