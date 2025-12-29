"""Objective stack management."""

from dataclasses import dataclass, field

from .types import Objective


@dataclass
class ObjectiveStack:
    """Manages the hierarchical objective stack."""

    _stack: list[Objective] = field(default_factory=list)

    def push(self, objective: Objective) -> None:
        """Push a new objective onto the stack."""
        self._stack.append(objective)

    def pop(self) -> Objective | None:
        """Pop and return the top objective."""
        return self._stack.pop() if self._stack else None

    def peek(self) -> Objective | None:
        """Return the top objective without removing it."""
        return self._stack[-1] if self._stack else None

    def is_empty(self) -> bool:
        """Check if the stack is empty."""
        return len(self._stack) == 0

    def size(self) -> int:
        """Return the number of objectives on the stack."""
        return len(self._stack)

    def clear_completed(self) -> int:
        """Remove all completed objectives. Returns count removed."""
        initial_size = len(self._stack)
        self._stack = [o for o in self._stack if not o.completed]
        return initial_size - len(self._stack)

    def get_all(self) -> list[Objective]:
        """Return all objectives (bottom to top)."""
        return list(self._stack)

    def mark_completed(self, objective_type: str, target: str) -> bool:
        """Mark a specific objective as completed."""
        for obj in self._stack:
            if obj.type == objective_type and obj.target == target:
                obj.completed = True
                return True
        return False


# Common objectives
def create_heal_objective() -> Objective:
    """Create a healing objective."""
    return Objective(
        type="heal",
        target="pokemon_center",
        priority=10,  # High priority
    )


def create_gym_objective(gym_leader: str, location: str) -> Objective:
    """Create a gym challenge objective."""
    return Objective(
        type="defeat_gym",
        target=gym_leader,
        priority=5,
        requirements=[f"navigate_to:{location}"],
    )


def create_catch_objective(species: str, reason: str) -> Objective:
    """Create a catch objective."""
    return Objective(
        type="catch_pokemon",
        target=species,
        priority=3,
        requirements=[reason],
    )
