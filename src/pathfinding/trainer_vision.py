"""Trainer line-of-sight calculations for pathfinding."""

from collections.abc import Generator
from dataclasses import dataclass

# Direction vectors for trainer facing
DIRECTION_VECTORS = {
    "UP": (0, -1),
    "DOWN": (0, 1),
    "LEFT": (-1, 0),
    "RIGHT": (1, 0),
}

# Default trainer vision range in tiles
DEFAULT_VISION_RANGE = 4


@dataclass
class Trainer:
    """A trainer with position and vision data."""

    trainer_id: str
    x: int
    y: int
    facing: str  # UP, DOWN, LEFT, RIGHT
    vision_range: int = DEFAULT_VISION_RANGE
    trainer_class: str = ""
    team_index: int = 0

    @classmethod
    def from_dict(cls, data: dict, index: int = 0) -> "Trainer":
        """Create a Trainer from map data dict.

        Args:
            data: Trainer data from map JSON
            index: Trainer index for ID generation

        Returns:
            Trainer instance
        """
        # Generate a unique ID if not present
        trainer_id = data.get("trainer_id", f"trainer_{index}")

        # Normalize facing direction
        facing = data.get("facing", "DOWN").upper()
        if facing not in DIRECTION_VECTORS:
            facing = "DOWN"

        return cls(
            trainer_id=trainer_id,
            x=data.get("x", 0),
            y=data.get("y", 0),
            facing=facing,
            vision_range=data.get("vision_range", DEFAULT_VISION_RANGE),
            trainer_class=data.get("class", ""),
            team_index=data.get("team_index", 0),
        )


def get_vision_tiles(
    trainer: Trainer,
    collision_check: callable = None,
) -> Generator[tuple[int, int], None, None]:
    """Generate all tiles in a trainer's line of sight.

    Vision is a straight line from the trainer in their facing direction.
    Vision stops at the edge of the vision range or when hitting a wall.

    Args:
        trainer: The trainer to check
        collision_check: Optional function (x, y) -> bool that returns True if blocked

    Yields:
        (x, y) tuples of tiles in the trainer's vision
    """
    dx, dy = DIRECTION_VECTORS.get(trainer.facing, (0, 0))
    if dx == 0 and dy == 0:
        return

    x, y = trainer.x, trainer.y
    for _ in range(trainer.vision_range):
        x += dx
        y += dy

        # Check if blocked by collision
        if collision_check and collision_check(x, y):
            break

        yield x, y


def calculate_vision_zone(
    trainer: Trainer,
    width: int = 0,
    height: int = 0,
    collision_check: callable = None,
) -> set[tuple[int, int]]:
    """Calculate all tiles in a trainer's vision cone.

    Args:
        trainer: The trainer to check
        width: Map width (for bounds checking)
        height: Map height (for bounds checking)
        collision_check: Optional function (x, y) -> bool for collision

    Returns:
        Set of (x, y) tiles that trigger battle if stepped on
    """
    zone = set()

    for x, y in get_vision_tiles(trainer, collision_check):
        # Bounds check
        if width > 0 and (x < 0 or x >= width):
            break
        if height > 0 and (y < 0 or y >= height):
            break

        zone.add((x, y))

    return zone


def is_in_vision(
    x: int,
    y: int,
    trainer: Trainer,
    collision_check: callable = None,
) -> bool:
    """Check if a position is in a trainer's line of sight.

    Args:
        x: X coordinate to check
        y: Y coordinate to check
        trainer: The trainer to check against
        collision_check: Optional collision function

    Returns:
        True if the position would trigger a battle
    """
    for vx, vy in get_vision_tiles(trainer, collision_check):
        if vx == x and vy == y:
            return True
    return False


def get_all_trainer_zones(
    trainers: list[dict],
    defeated_trainers: set[str] | None = None,
    width: int = 0,
    height: int = 0,
    collision_check: callable = None,
) -> set[tuple[int, int]]:
    """Get all vision zones for undefeated trainers.

    Args:
        trainers: List of trainer data dicts from map JSON
        defeated_trainers: Set of trainer IDs that have been defeated
        width: Map width for bounds checking
        height: Map height for bounds checking
        collision_check: Optional collision function

    Returns:
        Set of (x, y) tiles to avoid
    """
    defeated = defeated_trainers or set()
    all_zones: set[tuple[int, int]] = set()

    for i, trainer_data in enumerate(trainers):
        trainer = Trainer.from_dict(trainer_data, i)

        # Skip defeated trainers
        if trainer.trainer_id in defeated:
            continue

        zone = calculate_vision_zone(
            trainer,
            width=width,
            height=height,
            collision_check=collision_check,
        )
        all_zones.update(zone)

    return all_zones


def get_safe_positions_around_trainer(
    trainer: Trainer,
    start_x: int,
    start_y: int,
    goal_x: int,
    goal_y: int,
) -> list[tuple[int, int]]:
    """Find waypoints to navigate around a trainer's vision.

    Returns a list of intermediate positions that avoid the trainer's
    line of sight while going from start to goal.

    Args:
        trainer: The trainer to avoid
        start_x: Starting X position
        start_y: Starting Y position
        goal_x: Goal X position
        goal_y: Goal Y position

    Returns:
        List of (x, y) waypoints, or empty list if direct path is safe
    """
    # Get vision zone
    zone = calculate_vision_zone(trainer)

    # Check if direct path is blocked
    direct_blocked = False
    for vx, vy in zone:
        # Simple check: is any vision tile between start and goal?
        if trainer.facing in ("UP", "DOWN"):
            # Vertical vision - check if we need to cross it horizontally
            if min(start_x, goal_x) <= vx <= max(start_x, goal_x):
                if min(start_y, goal_y) <= vy <= max(start_y, goal_y):
                    direct_blocked = True
                    break
        else:
            # Horizontal vision - check if we need to cross it vertically
            if min(start_y, goal_y) <= vy <= max(start_y, goal_y):
                if min(start_x, goal_x) <= vx <= max(start_x, goal_x):
                    direct_blocked = True
                    break

    if not direct_blocked:
        return []  # Direct path is safe

    # Generate waypoints to go around
    waypoints = []
    if trainer.facing in ("UP", "DOWN"):
        # Vision is vertical, detour horizontally
        detour_x = trainer.x + 2 if start_x > trainer.x else trainer.x - 2
        waypoints = [
            (detour_x, start_y),
            (detour_x, goal_y),
        ]
    else:
        # Vision is horizontal, detour vertically
        detour_y = trainer.y + 2 if start_y > trainer.y else trainer.y - 2
        waypoints = [
            (start_x, detour_y),
            (goal_x, detour_y),
        ]

    return waypoints
