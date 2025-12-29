"""Tests for ObjectiveStack."""

from src.agent import Objective
from src.agent.objective import (
    ObjectiveStack,
    create_catch_objective,
    create_gym_objective,
    create_heal_objective,
)


def test_objective_stack_empty() -> None:
    """Test empty ObjectiveStack."""
    stack = ObjectiveStack()
    assert stack.is_empty() is True
    assert stack.size() == 0
    assert stack.peek() is None
    assert stack.pop() is None


def test_objective_stack_push_pop() -> None:
    """Test push and pop operations."""
    stack = ObjectiveStack()
    obj = Objective(type="heal", target="pokemon_center")

    stack.push(obj)
    assert stack.is_empty() is False
    assert stack.size() == 1
    assert stack.peek() == obj

    popped = stack.pop()
    assert popped == obj
    assert stack.is_empty() is True


def test_objective_stack_lifo() -> None:
    """Test LIFO behavior."""
    stack = ObjectiveStack()
    obj1 = Objective(type="navigate", target="PEWTER_CITY")
    obj2 = Objective(type="defeat_gym", target="Brock")
    obj3 = Objective(type="heal", target="pokemon_center")

    stack.push(obj1)
    stack.push(obj2)
    stack.push(obj3)

    assert stack.pop() == obj3
    assert stack.pop() == obj2
    assert stack.pop() == obj1


def test_objective_stack_peek() -> None:
    """Test peek doesn't remove element."""
    stack = ObjectiveStack()
    obj = Objective(type="catch_pokemon", target="PIKACHU")

    stack.push(obj)
    assert stack.peek() == obj
    assert stack.size() == 1  # Still there
    assert stack.peek() == obj  # Can peek again


def test_objective_stack_get_all() -> None:
    """Test get_all returns all objectives."""
    stack = ObjectiveStack()
    obj1 = Objective(type="navigate", target="PEWTER_CITY")
    obj2 = Objective(type="defeat_gym", target="Brock")

    stack.push(obj1)
    stack.push(obj2)

    all_objs = stack.get_all()
    assert len(all_objs) == 2
    assert all_objs[0] == obj1  # Bottom of stack
    assert all_objs[1] == obj2  # Top of stack


def test_objective_stack_clear_completed() -> None:
    """Test clearing completed objectives."""
    stack = ObjectiveStack()
    obj1 = Objective(type="navigate", target="PEWTER_CITY")
    obj2 = Objective(type="defeat_gym", target="Brock", completed=True)
    obj3 = Objective(type="heal", target="pokemon_center", completed=True)
    obj4 = Objective(type="grind", target="level_20")

    stack.push(obj1)
    stack.push(obj2)
    stack.push(obj3)
    stack.push(obj4)

    removed = stack.clear_completed()
    assert removed == 2
    assert stack.size() == 2

    remaining = stack.get_all()
    assert obj1 in remaining
    assert obj4 in remaining
    assert obj2 not in remaining
    assert obj3 not in remaining


def test_objective_stack_mark_completed() -> None:
    """Test marking specific objective as completed."""
    stack = ObjectiveStack()
    obj1 = Objective(type="navigate", target="PEWTER_CITY")
    obj2 = Objective(type="defeat_gym", target="Brock")

    stack.push(obj1)
    stack.push(obj2)

    result = stack.mark_completed("navigate", "PEWTER_CITY")
    assert result is True
    assert obj1.completed is True
    assert obj2.completed is False


def test_objective_stack_mark_completed_not_found() -> None:
    """Test marking non-existent objective."""
    stack = ObjectiveStack()
    obj = Objective(type="navigate", target="PEWTER_CITY")
    stack.push(obj)

    result = stack.mark_completed("heal", "pokemon_center")
    assert result is False


def test_create_heal_objective() -> None:
    """Test heal objective creation helper."""
    obj = create_heal_objective()
    assert obj.type == "heal"
    assert obj.target == "pokemon_center"
    assert obj.priority == 10
    assert obj.completed is False


def test_create_gym_objective() -> None:
    """Test gym objective creation helper."""
    obj = create_gym_objective("Brock", "PEWTER_GYM")
    assert obj.type == "defeat_gym"
    assert obj.target == "Brock"
    assert obj.priority == 5
    assert "navigate_to:PEWTER_GYM" in obj.requirements


def test_create_catch_objective() -> None:
    """Test catch objective creation helper."""
    obj = create_catch_objective("PIKACHU", "team_coverage")
    assert obj.type == "catch_pokemon"
    assert obj.target == "PIKACHU"
    assert obj.priority == 3
    assert "team_coverage" in obj.requirements
