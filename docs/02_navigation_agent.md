# Navigation Agent

## Model Configuration

| Setting | Value |
|---------|-------|
| **Model** | `claude-haiku-4-5-20251001` |
| **Reasoning** | Low complexity, mostly procedural |
| **Call Frequency** | ~5,000/hour (highest of all agents) |
| **Latency Tolerance** | Low (near real-time movement) |

**Why Haiku:** Navigation is the most frequently called agent. Most decisions are algorithmic (pathfinding, next step lookup). Speed is critical—we can't wait 2 seconds between each tile movement. Haiku's fast response time keeps gameplay smooth.

**Optimization Note:** Core pathfinding (A* algorithm) should be implemented in pure code. Haiku is only consulted for edge cases like "should I engage or avoid this trainer?"

---

## Overview

The Navigation Agent handles all overworld movement and exploration in Pokemon Red. It is responsible for pathfinding between locations, interacting with NPCs and objects, and managing encounters (deciding whether to seek or avoid them).

## Responsibilities

1. **Pathfinding** - Calculate routes between any two points in the game world
2. **Movement Execution** - Translate paths into controller inputs (up, down, left, right)
3. **Interaction** - Talk to NPCs, interact with objects, pick up items
4. **Encounter Management** - Navigate grass/caves strategically based on objectives
5. **Obstacle Detection** - Recognize when paths are blocked and why

---

## Tools

### 1. `get_current_position`

Returns the player's current location in the game world.

**Input:** None (reads from game state)

**Output:**
```python
{
    "map_id": "VIRIDIAN_FOREST",
    "map_name": "Viridian Forest",
    "x": 17,
    "y": 24,
    "facing": "DOWN",
    "tile_type": "GRASS",  # GRASS, PATH, WATER, LEDGE, DOOR, etc.
    "indoor": False
}
```

---

### 2. `get_map_data`

Retrieves the layout and properties of a given map.

**Input:** map_id or current map

**Output:**
```python
{
    "map_id": "VIRIDIAN_FOREST",
    "width": 32,
    "height": 48,
    "tiles": [...],  # 2D array of tile types
    "connections": {
        "north": "ROUTE_2_NORTH",
        "south": "ROUTE_2_SOUTH"
    },
    "warps": [
        {"x": 1, "y": 0, "destination": "ROUTE_2_GATE", "dest_x": 4, "dest_y": 7}
    ],
    "npcs": [
        {"x": 12, "y": 8, "type": "TRAINER", "trainer_id": "BUG_CATCHER_1"},
        {"x": 20, "y": 15, "type": "ITEM", "item": "POTION"}
    ],
    "grass_tiles": [(x, y), ...],  # All encounter tiles
    "required_hms": []  # HMs needed to traverse this map
}
```

---

### 3. `find_path`

Calculates a path from current position to a target.

**Input:**
```python
{
    "from": {"map": "PEWTER_CITY", "x": 10, "y": 5},  # Optional, defaults to current
    "to": {"map": "CERULEAN_CITY", "x": 15, "y": 20},
    "preferences": {
        "avoid_grass": True,      # Minimize encounters
        "avoid_trainers": False,  # We want to fight trainers for XP
        "allow_hms": ["CUT"]      # HMs we can use
    }
}
```

**Output:**
```python
{
    "path_found": True,
    "total_steps": 342,
    "segments": [
        {
            "map": "PEWTER_CITY",
            "moves": ["RIGHT", "RIGHT", "DOWN", "DOWN", "DOWN", ...],
            "exit_via": "SOUTH"
        },
        {
            "map": "ROUTE_3",
            "moves": [...],
            "trainers_in_path": ["YOUNGSTER_1", "LASS_1"],
            "exit_via": "EAST"
        },
        # ... more segments
    ],
    "blocked_paths": [],  # Alternatives that were blocked
    "estimated_encounters": 12  # Based on grass tiles crossed
}
```

---

### 4. `get_interactables`

Returns all interactable objects/NPCs within range.

**Input:** Current position and facing direction

**Output:**
```python
{
    "facing_tile": {
        "type": "NPC",
        "npc_type": "TRAINER",
        "trainer_id": "BUG_CATCHER_1",
        "defeated": False,
        "line_of_sight": True  # Will trigger if we enter their vision
    },
    "adjacent": [
        {"direction": "LEFT", "type": "ITEM_BALL", "item": "ANTIDOTE"},
        {"direction": "RIGHT", "type": "LEDGE", "jumpable": True}
    ],
    "nearby_trainers": [
        {"trainer_id": "BUG_CATCHER_2", "distance": 3, "avoidable": True}
    ]
}
```

---

### 5. `execute_movement`

Executes a sequence of moves in the game.

**Input:**
```python
{
    "moves": ["UP", "UP", "RIGHT", "A"],  # A = interact
    "stop_conditions": ["BATTLE_START", "DIALOGUE_START", "WARP"]
}
```

**Output:**
```python
{
    "moves_completed": 3,
    "stopped_reason": "BATTLE_START",
    "new_position": {"map": "VIRIDIAN_FOREST", "x": 18, "y": 22},
    "event": {"type": "WILD_ENCOUNTER", "pokemon": "CATERPIE", "level": 4}
}
```

---

### 6. `check_route_accessibility`

Checks if a route between two points is currently accessible.

**Input:**
```python
{
    "from": "CERULEAN_CITY",
    "to": "VERMILION_CITY"
}
```

**Output:**
```python
{
    "accessible": False,
    "blockers": [
        {
            "type": "HM_REQUIRED",
            "hm": "CUT",
            "location": "Route 9 tree",
            "alternative_route": None
        }
    ],
    "alternative": {
        "via": ["CERULEAN_CITY", "ROUTE_5", "SAFFRON_CITY", "ROUTE_6", "VERMILION_CITY"],
        "accessible": True,  # Assuming Saffron gates are open
        "notes": "Requires Saffron City access"
    }
}
```

---

### 7. `get_hidden_items`

Returns known hidden item locations on current or specified map.

**Input:** map_id (optional)

**Output:**
```python
{
    "hidden_items": [
        {"x": 15, "y": 23, "item": "RARE_CANDY", "obtained": False},
        {"x": 8, "y": 12, "item": "ETHER", "obtained": True}
    ]
}
```

---

## Map Knowledge Base

The Navigation Agent requires comprehensive map data:

```python
WORLD_GRAPH = {
    "PALLET_TOWN": {
        "connections": {
            "ROUTE_1": {"direction": "NORTH", "requirements": []},
            "ROUTE_21": {"direction": "SOUTH", "requirements": ["SURF"]}
        },
        "pokemon_center": True,
        "pokemart": False,
        "gym": False
    },
    "ROUTE_1": {
        "connections": {
            "PALLET_TOWN": {"direction": "SOUTH"},
            "VIRIDIAN_CITY": {"direction": "NORTH"}
        },
        "encounter_tiles": True,
        "trainers": []
    },
    # ... all ~150 maps
}

TRAINER_DATA = {
    "BUG_CATCHER_1": {
        "map": "VIRIDIAN_FOREST",
        "position": (12, 8),
        "vision_range": 4,
        "vision_direction": "DOWN",
        "team": [("WEEDLE", 9), ("CATERPIE", 9)],
        "prize_money": 90
    },
    # ... all trainers
}

CUT_TREES = [
    {"map": "ROUTE_9", "x": 5, "y": 12},
    {"map": "ROUTE_2", "x": 8, "y": 3},
    # ... all cuttable trees
]

STRENGTH_BOULDERS = [
    {"map": "VICTORY_ROAD_1F", "x": 10, "y": 15, "push_direction": "DOWN"},
    # ... all boulders
]
```

---

## Pathfinding Algorithm

The Navigation Agent uses a modified A* algorithm that:

1. **Treats maps as connected nodes** for high-level routing
2. **Uses tile-level pathfinding** within each map
3. **Weights tiles** based on preferences:

```python
TILE_WEIGHTS = {
    "PATH": 1,           # Preferred
    "GRASS": 5,          # Avoid if avoiding encounters
    "GRASS_SEEKING": 0.5, # Prefer if seeking encounters
    "TRAINER_LOS": 10,   # Avoid if avoiding trainers (or 0 if seeking)
    "LEDGE": 100,        # Can only go one way
    "WATER": float('inf') if not has_surf else 1,
    "CUT_TREE": float('inf') if not has_cut else 2
}
```

---

## Encounter Management Strategies

### Avoiding Encounters (when traversing to destination)
```python
def navigate_avoiding_encounters(destination):
    path = find_path(
        to=destination,
        preferences={"avoid_grass": True}
    )
    
    # If no grass-free path exists, minimize grass tiles
    if path.estimated_encounters > 0:
        # Use repel if available and valuable
        if "REPEL" in inventory and destination_important:
            use_item("REPEL")
    
    return execute_path(path)
```

### Seeking Encounters (when grinding)
```python
def grind_encounters(target_level, pokemon_types=None):
    # Find best grinding spot
    spot = find_grinding_location(
        min_level=game_state.party_avg_level - 3,
        max_level=game_state.party_avg_level + 5,
        preferred_types=pokemon_types
    )
    
    # Navigate to spot
    navigate_to(spot)
    
    # Walk in grass until objective met
    while party_below_level(target_level):
        patrol_grass(spot)
        # Battle Agent handles encounters
        # Menu Agent heals when needed
```

---

## Control Flow

```python
def navigation_agent_loop(objective: Objective):
    """
    Main loop for Navigation Agent when in control.
    """
    while True:
        # Check current position
        pos = get_current_position()
        
        # Are we at destination?
        if at_destination(pos, objective.target):
            if objective.type == "navigate":
                return {"status": "COMPLETE"}
            elif objective.type == "interact":
                interact_with_target()
                return {"status": "COMPLETE"}
        
        # Calculate path
        path = find_path(to=objective.target)
        
        if not path.path_found:
            return {
                "status": "BLOCKED",
                "reason": path.blocked_paths[0]
            }
        
        # Execute next segment
        result = execute_movement(
            moves=path.segments[0].moves,
            stop_conditions=["BATTLE_START", "DIALOGUE_START"]
        )
        
        # Handle interruptions
        if result.stopped_reason == "BATTLE_START":
            return {"status": "BATTLE", "yield_to": "BATTLE_AGENT"}
        
        if result.stopped_reason == "DIALOGUE_START":
            return {"status": "DIALOGUE", "yield_to": "MENU_AGENT"}
```

---

## Trainer Avoidance Logic

```python
def can_avoid_trainer(trainer_id: str, current_pos: tuple) -> bool:
    trainer = TRAINER_DATA[trainer_id]
    
    # Calculate trainer's line of sight
    los_tiles = calculate_line_of_sight(
        trainer.position,
        trainer.vision_direction,
        trainer.vision_range
    )
    
    # Find path that doesn't cross LOS
    path = find_path(
        to=destination,
        blocked_tiles=los_tiles
    )
    
    return path.path_found


def calculate_line_of_sight(pos, direction, range):
    """Returns list of tiles the trainer can see."""
    tiles = []
    dx, dy = DIRECTION_DELTAS[direction]
    
    for i in range(1, range + 1):
        tile = (pos[0] + dx * i, pos[1] + dy * i)
        if is_solid_tile(tile):
            break  # LOS blocked by obstacle
        tiles.append(tile)
    
    return tiles
```

---

## Special Navigation Cases

### Ledges (One-Way)
```python
# Ledges can only be jumped DOWN
# The pathfinder must account for this
LEDGE_DIRECTIONS = {
    "ROUTE_3": [{"from": (10, 5), "to": (10, 6), "direction": "DOWN"}],
    # ...
}
```

### Warps and Doors
```python
# Track warp destinations for indoor/outdoor navigation
WARP_DATA = {
    ("PEWTER_CITY", 15, 10): ("PEWTER_GYM", 4, 13),  # Gym entrance
    ("PEWTER_GYM", 4, 13): ("PEWTER_CITY", 15, 11),  # Gym exit
    # ...
}
```

### Multi-Floor Buildings
```python
# Handle stairs/ladders in Pokemon Tower, Silph Co, etc.
FLOOR_CONNECTIONS = {
    "POKEMON_TOWER_1F": {"up_stairs": "POKEMON_TOWER_2F"},
    "POKEMON_TOWER_2F": {"up_stairs": "POKEMON_TOWER_3F", "down_stairs": "POKEMON_TOWER_1F"},
    # ...
}
```

---

## Integration with Other Agents

### → Orchestrator
- Receives: Destination objective, strategic preferences
- Returns: Completion status, encountered events, blockers

### → Battle Agent
- Yields control when: Wild encounter or trainer battle starts
- Resumes when: Battle complete

### → Menu Agent
- May request: "Need to heal before continuing" or "Need to use HM"
- Yields for: Cut trees, Surf water, Strength boulders

---

## Failure Modes

| Failure | Detection | Response |
|---------|-----------|----------|
| Path blocked by HM obstacle | `check_route_accessibility` returns blocker | Return to Orchestrator with HM requirement |
| Stuck in loop | Same position for N iterations | Try alternative path or report stuck |
| Trainer unavoidable | No path avoiding LOS | Either fight trainer or find different route |
| Out of Repels mid-route | Inventory check | Continue without, accept encounters |
