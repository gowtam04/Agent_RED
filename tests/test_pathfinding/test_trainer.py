"""Tests for trainer vision calculations."""

import pytest
from src.pathfinding.trainer_vision import (
    Trainer,
    get_vision_tiles,
    calculate_vision_zone,
    is_in_vision,
    get_all_trainer_zones,
    get_safe_positions_around_trainer,
)


class TestTrainer:
    """Tests for Trainer dataclass."""

    def test_trainer_creation(self):
        """Test creating a Trainer instance."""
        trainer = Trainer(
            trainer_id="trainer_1",
            x=5,
            y=5,
            facing="DOWN",
            vision_range=4,
        )

        assert trainer.trainer_id == "trainer_1"
        assert trainer.x == 5
        assert trainer.y == 5
        assert trainer.facing == "DOWN"
        assert trainer.vision_range == 4

    def test_trainer_from_dict(self):
        """Test creating Trainer from dict data."""
        data = {
            "x": 10,
            "y": 15,
            "facing": "LEFT",
            "class": "BUG_CATCHER",
            "team_index": 2,
        }

        trainer = Trainer.from_dict(data, index=5)

        assert trainer.x == 10
        assert trainer.y == 15
        assert trainer.facing == "LEFT"
        assert trainer.trainer_class == "BUG_CATCHER"
        assert trainer.team_index == 2

    def test_trainer_from_dict_defaults(self):
        """Test Trainer from dict with missing fields."""
        data = {"x": 5, "y": 5}

        trainer = Trainer.from_dict(data)

        assert trainer.facing == "DOWN"  # Default
        assert trainer.vision_range == 4  # Default


class TestGetVisionTiles:
    """Tests for vision tile generation."""

    def test_vision_down(self):
        """Test vision tiles for down-facing trainer."""
        trainer = Trainer("t1", x=5, y=5, facing="DOWN", vision_range=4)
        tiles = list(get_vision_tiles(trainer))

        assert len(tiles) == 4
        assert (5, 6) in tiles
        assert (5, 7) in tiles
        assert (5, 8) in tiles
        assert (5, 9) in tiles

    def test_vision_up(self):
        """Test vision tiles for up-facing trainer."""
        trainer = Trainer("t1", x=5, y=10, facing="UP", vision_range=3)
        tiles = list(get_vision_tiles(trainer))

        assert len(tiles) == 3
        assert (5, 9) in tiles
        assert (5, 8) in tiles
        assert (5, 7) in tiles

    def test_vision_left(self):
        """Test vision tiles for left-facing trainer."""
        trainer = Trainer("t1", x=10, y=5, facing="LEFT", vision_range=2)
        tiles = list(get_vision_tiles(trainer))

        assert len(tiles) == 2
        assert (9, 5) in tiles
        assert (8, 5) in tiles

    def test_vision_right(self):
        """Test vision tiles for right-facing trainer."""
        trainer = Trainer("t1", x=0, y=5, facing="RIGHT", vision_range=3)
        tiles = list(get_vision_tiles(trainer))

        assert len(tiles) == 3
        assert (1, 5) in tiles
        assert (2, 5) in tiles
        assert (3, 5) in tiles

    def test_vision_blocked_by_collision(self):
        """Test vision stops at collision."""
        trainer = Trainer("t1", x=5, y=5, facing="DOWN", vision_range=4)

        # Collision check that blocks at y=7
        def collision_check(x, y):
            return y == 7

        tiles = list(get_vision_tiles(trainer, collision_check))

        # Should only have tile at y=6 before hitting wall at y=7
        assert len(tiles) == 1
        assert (5, 6) in tiles


class TestCalculateVisionZone:
    """Tests for vision zone calculation."""

    def test_basic_zone(self):
        """Test basic vision zone calculation."""
        trainer = Trainer("t1", x=5, y=5, facing="DOWN", vision_range=3)
        zone = calculate_vision_zone(trainer)

        assert len(zone) == 3
        assert (5, 6) in zone
        assert (5, 7) in zone
        assert (5, 8) in zone

    def test_zone_with_bounds(self):
        """Test vision zone respects map bounds."""
        trainer = Trainer("t1", x=5, y=8, facing="DOWN", vision_range=4)
        zone = calculate_vision_zone(trainer, width=10, height=10)

        # Can only see 1 tile (y=9) before hitting edge
        assert len(zone) == 1
        assert (5, 9) in zone


class TestIsInVision:
    """Tests for vision check function."""

    def test_in_vision(self):
        """Test position in trainer's vision."""
        trainer = Trainer("t1", x=5, y=5, facing="DOWN", vision_range=4)

        assert is_in_vision(5, 6, trainer) is True
        assert is_in_vision(5, 9, trainer) is True

    def test_not_in_vision(self):
        """Test position not in trainer's vision."""
        trainer = Trainer("t1", x=5, y=5, facing="DOWN", vision_range=4)

        # Behind trainer
        assert is_in_vision(5, 4, trainer) is False
        # To the side
        assert is_in_vision(6, 6, trainer) is False
        # Too far
        assert is_in_vision(5, 10, trainer) is False


class TestGetAllTrainerZones:
    """Tests for aggregating trainer zones."""

    def test_multiple_trainers(self):
        """Test zone aggregation for multiple trainers."""
        trainers = [
            {"x": 5, "y": 5, "facing": "DOWN"},
            {"x": 10, "y": 5, "facing": "LEFT"},
        ]

        zones = get_all_trainer_zones(trainers)

        # Should have tiles from both trainers
        assert (5, 6) in zones  # First trainer
        assert (9, 5) in zones  # Second trainer

    def test_defeated_trainers_excluded(self):
        """Test that defeated trainers are excluded."""
        trainers = [
            {"x": 5, "y": 5, "facing": "DOWN", "trainer_id": "t1"},
            {"x": 10, "y": 5, "facing": "LEFT", "trainer_id": "t2"},
        ]

        # Mark first trainer as defeated
        zones = get_all_trainer_zones(trainers, defeated_trainers={"t1"})

        # Should not have first trainer's tiles
        assert (5, 6) not in zones
        # Should have second trainer's tiles
        assert (9, 5) in zones

    def test_empty_trainer_list(self):
        """Test with no trainers."""
        zones = get_all_trainer_zones([])
        assert len(zones) == 0


class TestGetSafePositionsAroundTrainer:
    """Tests for finding safe paths around trainers."""

    def test_vertical_vision_horizontal_detour(self):
        """Test detouring around vertical vision."""
        trainer = Trainer("t1", x=5, y=5, facing="DOWN", vision_range=4)
        waypoints = get_safe_positions_around_trainer(
            trainer,
            start_x=5,
            start_y=2,
            goal_x=5,
            goal_y=10,
        )

        # Should suggest horizontal detour
        assert len(waypoints) > 0

    def test_no_detour_needed(self):
        """Test when direct path is safe."""
        trainer = Trainer("t1", x=5, y=5, facing="DOWN", vision_range=4)
        waypoints = get_safe_positions_around_trainer(
            trainer,
            start_x=0,
            start_y=0,
            goal_x=0,
            goal_y=10,
        )

        # Path doesn't cross vision, should be empty
        assert len(waypoints) == 0
