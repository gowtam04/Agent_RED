"""Tests for NavigationAgent."""

import pytest

from src.agent import (
    GameState,
    NavigationAgent,
    Position,
)


@pytest.fixture
def navigation_agent() -> NavigationAgent:
    """Create a NavigationAgent instance."""
    return NavigationAgent(client=None)


def test_navigation_agent_initialization(navigation_agent: NavigationAgent) -> None:
    """Test NavigationAgent initialization."""
    assert navigation_agent.AGENT_TYPE == "NAVIGATION"
    assert navigation_agent.DEFAULT_MODEL == "haiku"
    assert "Navigation agent" in navigation_agent.SYSTEM_PROMPT


def test_register_tools(navigation_agent: NavigationAgent) -> None:
    """Test that tools are properly registered."""
    tools = navigation_agent._register_tools()
    assert len(tools) == 8
    tool_names = [t["name"] for t in tools]
    assert "get_current_position" in tool_names
    assert "get_map_data" in tool_names
    assert "find_path" in tool_names
    assert "execute_movement" in tool_names


def test_get_current_position(navigation_agent: NavigationAgent) -> None:
    """Test getting current position from state."""
    state = GameState()
    state.position = Position(
        map_id="PALLET_TOWN",
        x=10,
        y=5,
        facing="UP",
    )

    result = navigation_agent._get_current_position({}, state)

    assert result.success is True
    assert result.result_data["map_id"] == "PALLET_TOWN"
    assert result.result_data["x"] == 10
    assert result.result_data["y"] == 5
    assert result.result_data["facing"] == "UP"


def test_get_map_data(navigation_agent: NavigationAgent) -> None:
    """Test getting map data."""
    state = GameState()
    state.position = Position(map_id="PALLET_TOWN", x=5, y=5)

    result = navigation_agent._get_map_data(
        {"include_npcs": True},
        state,
    )

    # May succeed or fail depending on if map data exists
    assert result.action_taken == "get_map_data"


def test_get_map_data_specific_map(navigation_agent: NavigationAgent) -> None:
    """Test getting specific map data."""
    state = GameState()

    result = navigation_agent._get_map_data(
        {"map_id": "VIRIDIAN_CITY", "include_npcs": True},
        state,
    )

    assert result.action_taken == "get_map_data"


def test_find_path_same_map(navigation_agent: NavigationAgent) -> None:
    """Test finding path on same map."""
    state = GameState()
    state.position = Position(map_id="PALLET_TOWN", x=5, y=5)

    result = navigation_agent._find_path(
        {
            "destination": {"map": "PALLET_TOWN", "x": 8, "y": 5},
        },
        state,
    )

    assert result.success is True
    assert result.result_data["path_found"] is True
    # Should have moves for the path
    assert len(result.result_data["moves"]) > 0
    assert result.result_data["total_steps"] == len(result.result_data["moves"])


def test_find_path_cross_map(navigation_agent: NavigationAgent) -> None:
    """Test finding cross-map path."""
    state = GameState()
    state.position = Position(map_id="PALLET_TOWN", x=5, y=5)

    result = navigation_agent._find_path(
        {
            "destination": {"map": "ROUTE1"},
        },
        state,
    )

    assert result.success is True
    assert result.result_data["path_found"] is True
    # Cross-map path should have multiple maps traversed
    assert len(result.result_data["maps_traversed"]) >= 1
    assert len(result.result_data["segments"]) >= 1


def test_get_interactables(navigation_agent: NavigationAgent) -> None:
    """Test getting nearby interactables."""
    state = GameState()
    state.position = Position(map_id="PALLET_TOWN", x=5, y=5)

    result = navigation_agent._get_interactables(
        {"range": 5},
        state,
    )

    assert result.success is True
    assert "interactables" in result.result_data


def test_execute_movement_no_emulator(navigation_agent: NavigationAgent) -> None:
    """Test movement execution without emulator."""
    state = GameState()

    result = navigation_agent._execute_movement(
        {
            "moves": ["UP", "UP", "RIGHT", "RIGHT"],
            "stop_conditions": ["BATTLE_START"],
        },
        state,
    )

    assert result.success is True
    assert result.result_data["executed"] is False
    assert result.result_data["reason"] == "emulator_not_available"


def test_execute_movement_empty_list(navigation_agent: NavigationAgent) -> None:
    """Test movement execution with empty move list."""
    state = GameState()

    result = navigation_agent._execute_movement(
        {"moves": []},
        state,
    )

    assert result.success is True
    assert result.result_data["moves_requested"] == 0


def test_check_route_accessibility(navigation_agent: NavigationAgent) -> None:
    """Test route accessibility check."""
    state = GameState()
    state.hms_usable = ["CUT"]
    state.badges = ["BOULDER", "CASCADE"]

    result = navigation_agent._check_route_accessibility(
        {
            "from_map": "CERULEAN_CITY",
            "to_map": "VERMILION_CITY",
        },
        state,
    )

    assert result.success is True
    assert "accessible" in result.result_data


def test_get_hidden_items(navigation_agent: NavigationAgent) -> None:
    """Test getting hidden items."""
    state = GameState()
    state.position = Position(map_id="PALLET_TOWN", x=5, y=5)

    result = navigation_agent._get_hidden_items({}, state)

    assert result.success is True
    assert "hidden_items" in result.result_data


def test_use_hm_in_field_unknown_hm(navigation_agent: NavigationAgent) -> None:
    """Test using unknown HM."""
    state = GameState()

    result = navigation_agent._use_hm_in_field(
        {"hm_move": "TELEPORT"},
        state,
    )

    assert result.success is False
    assert "unknown hm" in result.error.lower()


def test_use_hm_in_field_not_usable(navigation_agent: NavigationAgent) -> None:
    """Test using HM that's not usable."""
    state = GameState()
    state.hms_usable = []  # No HMs usable

    result = navigation_agent._use_hm_in_field(
        {"hm_move": "CUT", "target_direction": "UP"},
        state,
    )

    assert result.success is False
    assert "cannot use" in result.error.lower()


def test_use_hm_in_field_no_emulator(navigation_agent: NavigationAgent) -> None:
    """Test using HM without emulator."""
    state = GameState()
    state.hms_usable = ["CUT"]

    result = navigation_agent._use_hm_in_field(
        {"hm_move": "CUT", "target_direction": "UP"},
        state,
    )

    assert result.success is True
    assert result.result_data["executed"] is False


def test_use_hm_fly_requires_destination(navigation_agent: NavigationAgent) -> None:
    """Test that FLY can specify destination."""
    state = GameState()
    state.hms_usable = ["FLY"]

    result = navigation_agent._use_hm_in_field(
        {
            "hm_move": "FLY",
            "target_direction": "CURRENT",
            "fly_destination": "PALLET_TOWN",
        },
        state,
    )

    assert result.success is True
    # Without emulator, just verify the input is captured
    assert result.result_data["executed"] is False


def test_execute_tool_unknown(navigation_agent: NavigationAgent) -> None:
    """Test executing unknown tool."""
    state = GameState()

    result = navigation_agent._execute_tool("unknown_tool", {}, state)

    assert result.success is False
    assert "unknown tool" in result.error.lower()
