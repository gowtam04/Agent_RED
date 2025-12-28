# Pokemon Red AI Agent - Tool Schemas

This document contains all tool definitions for the Pokemon Red AI system, formatted for the Anthropic API.

---

## Table of Contents

1. [Shared Types & Enums](#shared-types--enums)
2. [Orchestrator Agent Tools](#orchestrator-agent-tools)
3. [Navigation Agent Tools](#navigation-agent-tools)
4. [Battle Agent Tools](#battle-agent-tools)
5. [Menu Agent Tools](#menu-agent-tools)
6. [Python Implementation Helper](#python-implementation-helper)

---

## Shared Types & Enums

These types are referenced across multiple tool schemas:

```python
# Enums
GameMode = Literal["OVERWORLD", "BATTLE", "MENU", "DIALOGUE"]
BattleType = Literal["WILD", "TRAINER", "GYM_LEADER", "ELITE_FOUR", "CHAMPION", "RIVAL"]
Direction = Literal["UP", "DOWN", "LEFT", "RIGHT"]
MoveCategory = Literal["PHYSICAL", "SPECIAL", "STATUS"]
Status = Literal["POISON", "BURN", "SLEEP", "FREEZE", "PARALYSIS"]
TileType = Literal["PATH", "GRASS", "WATER", "LEDGE", "DOOR", "CUT_TREE", "BOULDER", "WALL"]
MenuType = Literal["START_MENU", "BAG", "PARTY", "PC", "SHOP", "DIALOGUE", "YES_NO", "MOVE_LEARN"]

# Common object shapes used in tool responses
Pokemon = {
    "species": str,
    "level": int,
    "current_hp": int,
    "max_hp": int,
    "status": Optional[Status],
    "types": list[str],
    "moves": list[Move],
    "stats": Stats
}

Move = {
    "name": str,
    "type": str,
    "category": MoveCategory,
    "power": int,
    "accuracy": int,
    "pp_current": int,
    "pp_max": int,
    "effect": Optional[str]
}

Stats = {
    "hp": int,
    "attack": int,
    "defense": int,
    "special": int,  # Gen 1 combined Special
    "speed": int
}

Position = {
    "map": str,
    "x": int,
    "y": int
}
```

---

## Orchestrator Agent Tools

### 1. detect_game_mode

Analyzes the current screen/game state to determine which mode the game is in.

```json
{
  "name": "detect_game_mode",
  "description": "Analyzes the current game screen and memory state to determine the active game mode (OVERWORLD, BATTLE, MENU, or DIALOGUE). Returns the detected mode, any relevant submode information, and a confidence score.",
  "input_schema": {
    "type": "object",
    "properties": {
      "screen_data": {
        "type": "object",
        "description": "Current screen state data including pixel buffer or abstracted visual elements",
        "properties": {
          "pixels": {
            "type": "string",
            "description": "Base64 encoded screen image or reference to current frame"
          },
          "memory_snapshot": {
            "type": "object",
            "description": "Relevant memory addresses and their current values"
          }
        }
      }
    },
    "required": []
  }
}
```

**Response Schema:**
```json
{
  "mode": "BATTLE",
  "submode": "WILD | TRAINER | GYM_LEADER | ELITE_FOUR | null",
  "confidence": 0.98,
  "indicators": ["battle_ui_visible", "hp_bars_present", "move_menu_active"]
}
```

---

### 2. get_current_objective

Returns the current high-level objective based on game progress.

```json
{
  "name": "get_current_objective",
  "description": "Analyzes current game progress (badges, story flags, location) and returns the appropriate current objective with its details, prerequisites, and recommendations.",
  "input_schema": {
    "type": "object",
    "properties": {
      "badges": {
        "type": "array",
        "items": {"type": "string"},
        "description": "List of badges already obtained (e.g., ['Boulder', 'Cascade'])"
      },
      "story_flags": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Completed story events (e.g., ['GOT_POKEDEX', 'RESCUED_BILL'])"
      },
      "current_location": {
        "type": "string",
        "description": "Current map location (e.g., 'CERULEAN_CITY')"
      },
      "party_pokemon": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "species": {"type": "string"},
            "level": {"type": "integer"},
            "types": {"type": "array", "items": {"type": "string"}}
          }
        },
        "description": "Current party composition for objective analysis"
      }
    },
    "required": ["badges", "story_flags", "current_location"]
  }
}
```

**Response Schema:**
```json
{
  "objective": "defeat_gym",
  "target": "Misty",
  "location": "Cerulean City Gym",
  "prerequisites": ["HM01_CUT"],
  "recommended_level": 21,
  "type_advantage": ["Electric", "Grass"],
  "priority": 1
}
```

---

### 3. get_next_milestone

Determines the next major story milestone and the steps required to reach it.

```json
{
  "name": "get_next_milestone",
  "description": "Based on current game progress, determines the next major story milestone and breaks it down into actionable steps.",
  "input_schema": {
    "type": "object",
    "properties": {
      "badges": {
        "type": "array",
        "items": {"type": "string"},
        "description": "List of badges obtained"
      },
      "story_flags": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Completed story events"
      },
      "hms_obtained": {
        "type": "array",
        "items": {"type": "string"},
        "description": "HMs in possession (e.g., ['HM01_CUT', 'HM02_FLY'])"
      },
      "hms_usable": {
        "type": "array",
        "items": {"type": "string"},
        "description": "HMs that can be used (have badge + taught to Pokemon)"
      }
    },
    "required": ["badges", "story_flags"]
  }
}
```

**Response Schema:**
```json
{
  "milestone": "Defeat Misty",
  "milestone_type": "GYM_LEADER",
  "steps": [
    {"type": "navigate", "target": "Cerulean City", "optional": false},
    {"type": "catch_pokemon", "target": "Electric or Grass type", "optional": true},
    {"type": "grind", "target_level": 21, "optional": true},
    {"type": "navigate", "target": "Cerulean Gym", "optional": false},
    {"type": "defeat_trainer", "target": "Misty", "optional": false}
  ],
  "estimated_time_minutes": 30
}
```

---

### 4. check_requirements

Checks if all prerequisites are met for a given objective.

```json
{
  "name": "check_requirements",
  "description": "Evaluates whether all prerequisites (HMs, badges, items, Pokemon types) are met for a specific objective. Returns missing requirements and suggests sub-objectives to fulfill them.",
  "input_schema": {
    "type": "object",
    "properties": {
      "objective_type": {
        "type": "string",
        "enum": ["navigate", "defeat_gym", "defeat_trainer", "catch_pokemon", "get_item", "get_hm", "teach_hm"],
        "description": "Type of objective to check requirements for"
      },
      "objective_target": {
        "type": "string",
        "description": "Specific target (location, trainer name, Pokemon species, etc.)"
      },
      "current_state": {
        "type": "object",
        "properties": {
          "badges": {"type": "array", "items": {"type": "string"}},
          "hms_obtained": {"type": "array", "items": {"type": "string"}},
          "hms_usable": {"type": "array", "items": {"type": "string"}},
          "key_items": {"type": "array", "items": {"type": "string"}},
          "party_types": {"type": "array", "items": {"type": "string"}}
        },
        "description": "Current game state for requirement checking"
      }
    },
    "required": ["objective_type", "objective_target", "current_state"]
  }
}
```

**Response Schema:**
```json
{
  "can_proceed": false,
  "missing": [
    {
      "type": "hm",
      "name": "CUT",
      "status": "have_item_not_taught",
      "required_badge": "Cascade"
    },
    {
      "type": "pokemon_type",
      "name": "Electric",
      "status": "missing",
      "recommended_catch": ["Pikachu", "Voltorb"]
    }
  ],
  "sub_objectives": [
    {"type": "teach_hm", "move": "CUT", "priority": 1},
    {"type": "catch_pokemon", "filter": "type:Electric", "priority": 2}
  ]
}
```

---

### 5. route_to_agent

Determines which specialist agent should handle the current situation.

```json
{
  "name": "route_to_agent",
  "description": "Based on current game mode and objective, determines which specialist agent (Navigation, Battle, or Menu) should take control and provides the appropriate context for that agent.",
  "input_schema": {
    "type": "object",
    "properties": {
      "game_mode": {
        "type": "string",
        "enum": ["OVERWORLD", "BATTLE", "MENU", "DIALOGUE"],
        "description": "Current detected game mode"
      },
      "current_objective": {
        "type": "object",
        "properties": {
          "type": {"type": "string"},
          "target": {"type": "string"}
        },
        "description": "Current objective being worked on"
      },
      "game_state_summary": {
        "type": "object",
        "properties": {
          "party_avg_hp_percent": {"type": "number"},
          "fainted_count": {"type": "integer"},
          "location": {"type": "string"},
          "in_battle": {"type": "boolean"},
          "battle_type": {"type": "string"}
        },
        "description": "Summary of current game state"
      }
    },
    "required": ["game_mode", "current_objective"]
  }
}
```

**Response Schema:**
```json
{
  "agent": "BATTLE",
  "context": {
    "battle_type": "GYM_LEADER",
    "can_flee": false,
    "catch_priority": "none",
    "strategic_notes": "Misty's Starmie is fast and strong. Lead with Electric type.",
    "boss_battle": true,
    "escalate_to_opus": true
  }
}
```

---

### 6. update_game_state

Syncs and updates the shared game state after agent actions.

```json
{
  "name": "update_game_state",
  "description": "Updates the shared GameState object with new information from game memory, screen state, or agent action results.",
  "input_schema": {
    "type": "object",
    "properties": {
      "updates": {
        "type": "object",
        "properties": {
          "current_mode": {"type": "string", "enum": ["OVERWORLD", "BATTLE", "MENU", "DIALOGUE"]},
          "current_map": {"type": "string"},
          "player_position": {
            "type": "object",
            "properties": {
              "x": {"type": "integer"},
              "y": {"type": "integer"}
            }
          },
          "party": {
            "type": "array",
            "items": {"type": "object"}
          },
          "inventory": {"type": "object"},
          "money": {"type": "integer"},
          "badges": {"type": "array", "items": {"type": "string"}},
          "story_flags": {"type": "array", "items": {"type": "string"}}
        },
        "description": "Fields to update in the game state"
      },
      "source": {
        "type": "string",
        "enum": ["memory_read", "agent_report", "screen_parse"],
        "description": "Source of the state update"
      }
    },
    "required": ["updates", "source"]
  }
}
```

---

### 7. manage_objective_stack

Manages the objective stack (push, pop, peek operations).

```json
{
  "name": "manage_objective_stack",
  "description": "Manages the objective stack - push new objectives, pop completed ones, or peek at current state.",
  "input_schema": {
    "type": "object",
    "properties": {
      "operation": {
        "type": "string",
        "enum": ["push", "pop", "peek", "clear_completed"],
        "description": "Stack operation to perform"
      },
      "objective": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string",
            "enum": ["navigate", "defeat_gym", "defeat_trainer", "catch_pokemon", "get_item", "get_hm", "teach_hm", "heal", "grind", "shop"]
          },
          "target": {"type": "string"},
          "priority": {"type": "integer"},
          "requirements": {"type": "array", "items": {"type": "string"}}
        },
        "description": "Objective to push (required for push operation)"
      }
    },
    "required": ["operation"]
  }
}
```

**Response Schema:**
```json
{
  "operation_result": "success",
  "stack_size": 3,
  "top_objective": {
    "type": "catch_pokemon",
    "target": "Pikachu",
    "priority": 1
  },
  "full_stack": [
    {"type": "defeat_gym", "target": "Misty"},
    {"type": "teach_hm", "target": "CUT"},
    {"type": "catch_pokemon", "target": "Pikachu"}
  ]
}
```

---

## Navigation Agent Tools

### 1. get_current_position

Returns the player's current location in the game world.

```json
{
  "name": "get_current_position",
  "description": "Reads the player's current position from game memory, including map ID, coordinates, facing direction, and tile type.",
  "input_schema": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

**Response Schema:**
```json
{
  "map_id": "VIRIDIAN_FOREST",
  "map_name": "Viridian Forest",
  "x": 17,
  "y": 24,
  "facing": "DOWN",
  "tile_type": "GRASS",
  "indoor": false,
  "can_move": {
    "up": true,
    "down": true,
    "left": false,
    "right": true
  }
}
```

---

### 2. get_map_data

Retrieves the layout and properties of a specified map.

```json
{
  "name": "get_map_data",
  "description": "Retrieves comprehensive map data including dimensions, tile layout, connections to other maps, warp points, NPCs, items, and encounter information.",
  "input_schema": {
    "type": "object",
    "properties": {
      "map_id": {
        "type": "string",
        "description": "Map ID to retrieve data for. If not provided, uses current map."
      },
      "include_tiles": {
        "type": "boolean",
        "default": false,
        "description": "Whether to include full tile grid (large data)"
      },
      "include_npcs": {
        "type": "boolean",
        "default": true,
        "description": "Whether to include NPC positions and data"
      }
    },
    "required": []
  }
}
```

**Response Schema:**
```json
{
  "map_id": "VIRIDIAN_FOREST",
  "map_name": "Viridian Forest",
  "width": 32,
  "height": 48,
  "connections": {
    "north": {"map": "ROUTE_2_NORTH", "x_offset": 0},
    "south": {"map": "ROUTE_2_SOUTH", "x_offset": 0}
  },
  "warps": [
    {"x": 1, "y": 0, "destination_map": "ROUTE_2_GATE", "destination_x": 4, "destination_y": 7}
  ],
  "npcs": [
    {"x": 12, "y": 8, "npc_type": "TRAINER", "trainer_id": "BUG_CATCHER_1", "defeated": false},
    {"x": 20, "y": 15, "npc_type": "ITEM_BALL", "item": "POTION"}
  ],
  "grass_tiles_count": 156,
  "required_hms": [],
  "has_pokemon_center": false,
  "has_pokemart": false
}
```

---

### 3. find_path

Calculates an optimal path from current position to a target destination.

```json
{
  "name": "find_path",
  "description": "Calculates an optimal path between two points using A* pathfinding, accounting for obstacles, trainer line-of-sight, encounter tiles, and HM requirements. Supports cross-map routing.",
  "input_schema": {
    "type": "object",
    "properties": {
      "destination": {
        "type": "object",
        "properties": {
          "map": {"type": "string", "description": "Target map ID"},
          "x": {"type": "integer", "description": "Target X coordinate"},
          "y": {"type": "integer", "description": "Target Y coordinate"}
        },
        "required": ["map"],
        "description": "Destination location. If x/y omitted, finds entrance to map."
      },
      "from": {
        "type": "object",
        "properties": {
          "map": {"type": "string"},
          "x": {"type": "integer"},
          "y": {"type": "integer"}
        },
        "description": "Starting position. Defaults to current position if omitted."
      },
      "preferences": {
        "type": "object",
        "properties": {
          "avoid_grass": {
            "type": "boolean",
            "default": true,
            "description": "Prefer paths that minimize grass tiles (fewer encounters)"
          },
          "avoid_trainers": {
            "type": "boolean",
            "default": true,
            "description": "Avoid undefeated trainer line-of-sight"
          },
          "seek_trainers": {
            "type": "boolean",
            "default": false,
            "description": "Actively route through trainer battles"
          },
          "allowed_hms": {
            "type": "array",
            "items": {"type": "string"},
            "description": "HMs available for use (e.g., ['CUT', 'SURF'])"
          }
        }
      }
    },
    "required": ["destination"]
  }
}
```

**Response Schema:**
```json
{
  "path_found": true,
  "total_steps": 342,
  "segments": [
    {
      "map": "PEWTER_CITY",
      "moves": ["RIGHT", "RIGHT", "DOWN", "DOWN", "DOWN"],
      "steps": 5,
      "exit_via": "SOUTH"
    },
    {
      "map": "ROUTE_3",
      "moves": ["RIGHT", "RIGHT", "UP", "RIGHT"],
      "steps": 4,
      "trainers_in_path": ["YOUNGSTER_1"],
      "grass_tiles": 2,
      "exit_via": "EAST"
    }
  ],
  "trainers_in_path": ["YOUNGSTER_1", "LASS_1"],
  "estimated_encounters": 12,
  "hms_needed": [],
  "blocked_alternatives": [
    {"route": "via Route 9", "blocked_by": "CUT_TREE"}
  ]
}
```

---

### 4. get_interactables

Returns all interactable objects and NPCs near the player.

```json
{
  "name": "get_interactables",
  "description": "Scans the area around the player for interactable objects, NPCs, items, and environmental features. Returns what can be interacted with and relevant details.",
  "input_schema": {
    "type": "object",
    "properties": {
      "range": {
        "type": "integer",
        "default": 5,
        "description": "Tile radius to scan for interactables"
      }
    },
    "required": []
  }
}
```

**Response Schema:**
```json
{
  "facing_tile": {
    "type": "NPC",
    "npc_type": "TRAINER",
    "trainer_id": "BUG_CATCHER_1",
    "defeated": false,
    "can_interact": true,
    "line_of_sight": true
  },
  "adjacent": [
    {"direction": "LEFT", "type": "ITEM_BALL", "item": "ANTIDOTE", "obtained": false},
    {"direction": "RIGHT", "type": "LEDGE", "jumpable": true, "direction_allowed": "DOWN"}
  ],
  "nearby_trainers": [
    {
      "trainer_id": "BUG_CATCHER_2",
      "distance": 3,
      "defeated": false,
      "avoidable": true,
      "vision_direction": "LEFT",
      "vision_range": 4
    }
  ],
  "nearby_items": [
    {"x": 15, "y": 20, "item": "POTION", "type": "ITEM_BALL", "distance": 4}
  ],
  "nearby_doors": [
    {"x": 10, "y": 5, "destination": "PEWTER_GYM", "distance": 6}
  ]
}
```

---

### 5. execute_movement

Executes a sequence of movement inputs in the game.

```json
{
  "name": "execute_movement",
  "description": "Sends a sequence of controller inputs to move the player. Monitors for interruptions (battles, dialogues, warps) and reports where movement stopped.",
  "input_schema": {
    "type": "object",
    "properties": {
      "moves": {
        "type": "array",
        "items": {
          "type": "string",
          "enum": ["UP", "DOWN", "LEFT", "RIGHT", "A", "B", "START", "SELECT"]
        },
        "description": "Sequence of inputs to execute"
      },
      "stop_conditions": {
        "type": "array",
        "items": {
          "type": "string",
          "enum": ["BATTLE_START", "DIALOGUE_START", "WARP", "MENU_OPEN", "COLLISION"]
        },
        "default": ["BATTLE_START", "DIALOGUE_START", "WARP"],
        "description": "Conditions that should halt execution"
      },
      "frame_delay": {
        "type": "integer",
        "default": 4,
        "description": "Frames to wait between inputs"
      }
    },
    "required": ["moves"]
  }
}
```

**Response Schema:**
```json
{
  "moves_completed": 3,
  "moves_total": 5,
  "stopped_reason": "BATTLE_START",
  "stopped_at_move_index": 3,
  "new_position": {
    "map": "VIRIDIAN_FOREST",
    "x": 18,
    "y": 22
  },
  "event": {
    "type": "WILD_ENCOUNTER",
    "pokemon": "CATERPIE",
    "level": 4
  }
}
```

---

### 6. check_route_accessibility

Checks if a route between two locations is currently accessible.

```json
{
  "name": "check_route_accessibility",
  "description": "Checks whether a route between two maps is accessible given current HMs, badges, and story progress. Returns blockers and alternatives if not accessible.",
  "input_schema": {
    "type": "object",
    "properties": {
      "from_map": {
        "type": "string",
        "description": "Starting map ID"
      },
      "to_map": {
        "type": "string",
        "description": "Destination map ID"
      },
      "available_hms": {
        "type": "array",
        "items": {"type": "string"},
        "description": "HMs that can be used"
      },
      "story_flags": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Completed story events"
      }
    },
    "required": ["from_map", "to_map"]
  }
}
```

**Response Schema:**
```json
{
  "accessible": false,
  "blockers": [
    {
      "type": "HM_REQUIRED",
      "hm": "CUT",
      "location_description": "Route 9 - tree blocking path",
      "position": {"map": "ROUTE_9", "x": 5, "y": 12}
    }
  ],
  "alternative_routes": [
    {
      "via": ["CERULEAN_CITY", "ROUTE_5", "SAFFRON_CITY", "ROUTE_6", "VERMILION_CITY"],
      "accessible": false,
      "blocker": "SAFFRON_GATES_CLOSED"
    }
  ],
  "shortest_accessible_path": null
}
```

---

### 7. get_hidden_items

Returns known hidden item locations on a map.

```json
{
  "name": "get_hidden_items",
  "description": "Retrieves the locations of hidden items on the specified map from the static knowledge base. Tracks which have been obtained.",
  "input_schema": {
    "type": "object",
    "properties": {
      "map_id": {
        "type": "string",
        "description": "Map to check for hidden items. Defaults to current map."
      },
      "only_unobtained": {
        "type": "boolean",
        "default": true,
        "description": "Only return items not yet obtained"
      }
    },
    "required": []
  }
}
```

**Response Schema:**
```json
{
  "map_id": "CERULEAN_CITY",
  "hidden_items": [
    {"x": 15, "y": 23, "item": "RARE_CANDY", "obtained": false},
    {"x": 8, "y": 12, "item": "ETHER", "obtained": true}
  ],
  "total_hidden": 2,
  "remaining": 1
}
```

---

### 8. use_hm_in_field

Uses an HM move in the overworld (Cut tree, Surf on water, etc.).

```json
{
  "name": "use_hm_in_field",
  "description": "Activates an HM move in the overworld to clear an obstacle. Opens the Pokemon menu, selects the HM user, and uses the move.",
  "input_schema": {
    "type": "object",
    "properties": {
      "hm_move": {
        "type": "string",
        "enum": ["CUT", "FLY", "SURF", "STRENGTH", "FLASH"],
        "description": "The HM move to use"
      },
      "target_direction": {
        "type": "string",
        "enum": ["UP", "DOWN", "LEFT", "RIGHT", "CURRENT"],
        "description": "Direction of the target (tree, water, boulder). CURRENT for Fly/Flash."
      },
      "fly_destination": {
        "type": "string",
        "description": "Required for FLY - destination city name"
      }
    },
    "required": ["hm_move"]
  }
}
```

**Response Schema:**
```json
{
  "success": true,
  "hm_used": "CUT",
  "pokemon_used": "BULBASAUR",
  "effect": "Tree was cut down",
  "new_position": {"map": "ROUTE_9", "x": 6, "y": 12}
}
```

---

## Battle Agent Tools

### 1. get_pokemon_data

Retrieves comprehensive data about any Pokemon species.

```json
{
  "name": "get_pokemon_data",
  "description": "Retrieves complete Pokemon species data from the static knowledge base including base stats, types, evolution, learnset, TM compatibility, and catch rate.",
  "input_schema": {
    "type": "object",
    "properties": {
      "species": {
        "type": "string",
        "description": "Pokemon species name (e.g., 'PIKACHU', 'CHARIZARD')"
      },
      "dex_number": {
        "type": "integer",
        "description": "National dex number (alternative to species name)"
      }
    },
    "required": []
  }
}
```

**Response Schema:**
```json
{
  "species": "CHARIZARD",
  "dex_number": 6,
  "types": ["FIRE", "FLYING"],
  "base_stats": {
    "hp": 78,
    "attack": 84,
    "defense": 78,
    "special": 85,
    "speed": 100
  },
  "evolution": {
    "from": "CHARMELEON",
    "from_level": 36,
    "to": null
  },
  "learnset": [
    {"move": "SCRATCH", "level": 1},
    {"move": "GROWL", "level": 1},
    {"move": "EMBER", "level": 9},
    {"move": "LEER", "level": 15},
    {"move": "RAGE", "level": 24},
    {"move": "SLASH", "level": 36},
    {"move": "FLAMETHROWER", "level": 46},
    {"move": "FIRE_SPIN", "level": 55}
  ],
  "tm_compatibility": ["TM01_MEGA_PUNCH", "TM02_RAZOR_WIND", "TM06_TOXIC", "TM08_BODY_SLAM"],
  "hm_compatibility": ["HM01_CUT", "HM02_FLY", "HM04_STRENGTH"],
  "catch_rate": 45,
  "base_exp_yield": 209
}
```

---

### 2. calculate_type_effectiveness

Calculates type matchup multiplier for an attack.

```json
{
  "name": "calculate_type_effectiveness",
  "description": "Calculates the type effectiveness multiplier for an attack type against defender types. Uses Gen 1 type chart including the Ghost/Psychic bug.",
  "input_schema": {
    "type": "object",
    "properties": {
      "attack_type": {
        "type": "string",
        "description": "Type of the attacking move (e.g., 'WATER', 'ELECTRIC')"
      },
      "defender_types": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Types of the defending Pokemon (1 or 2 types)"
      }
    },
    "required": ["attack_type", "defender_types"]
  }
}
```

**Response Schema:**
```json
{
  "attack_type": "WATER",
  "defender_types": ["FIRE", "ROCK"],
  "multiplier": 4.0,
  "effectiveness": "super_effective_4x",
  "description": "Super effective against both types (4x damage)",
  "breakdown": {
    "vs_FIRE": 2.0,
    "vs_ROCK": 2.0
  }
}
```

---

### 3. estimate_damage

Estimates the damage range for a move.

```json
{
  "name": "estimate_damage",
  "description": "Calculates estimated damage range for a move, accounting for stats, stat stages, type effectiveness, STAB, and critical hit chance.",
  "input_schema": {
    "type": "object",
    "properties": {
      "attacker": {
        "type": "object",
        "properties": {
          "species": {"type": "string"},
          "level": {"type": "integer"},
          "attack": {"type": "integer"},
          "special": {"type": "integer"},
          "types": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["level", "attack", "special", "types"],
        "description": "Attacking Pokemon's relevant stats"
      },
      "defender": {
        "type": "object",
        "properties": {
          "species": {"type": "string"},
          "level": {"type": "integer"},
          "current_hp": {"type": "integer"},
          "max_hp": {"type": "integer"},
          "defense": {"type": "integer"},
          "special": {"type": "integer"},
          "types": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["current_hp", "max_hp", "defense", "special", "types"],
        "description": "Defending Pokemon's relevant stats"
      },
      "move": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "type": {"type": "string"},
          "category": {"type": "string", "enum": ["PHYSICAL", "SPECIAL", "STATUS"]},
          "power": {"type": "integer"},
          "accuracy": {"type": "integer"}
        },
        "required": ["type", "category", "power"],
        "description": "Move being used"
      },
      "attacker_stages": {
        "type": "object",
        "properties": {
          "attack": {"type": "integer", "minimum": -6, "maximum": 6},
          "special": {"type": "integer", "minimum": -6, "maximum": 6}
        },
        "default": {"attack": 0, "special": 0},
        "description": "Attacker's stat stage modifiers"
      },
      "defender_stages": {
        "type": "object",
        "properties": {
          "defense": {"type": "integer", "minimum": -6, "maximum": 6},
          "special": {"type": "integer", "minimum": -6, "maximum": 6}
        },
        "default": {"defense": 0, "special": 0},
        "description": "Defender's stat stage modifiers"
      }
    },
    "required": ["attacker", "defender", "move"]
  }
}
```

**Response Schema:**
```json
{
  "min_damage": 45,
  "max_damage": 53,
  "average_damage": 49,
  "percent_of_current_hp": {
    "min": 38.1,
    "max": 44.9,
    "average": 41.5
  },
  "can_ko": false,
  "guaranteed_ko": false,
  "turns_to_ko": {
    "min": 3,
    "max": 3,
    "average": 2.5
  },
  "crit_damage": {
    "min": 90,
    "max": 106
  },
  "crit_can_ko": true,
  "modifiers_applied": {
    "type_effectiveness": 2.0,
    "stab": 1.5,
    "stat_stages": 1.0
  }
}
```

---

### 4. calculate_catch_rate

Calculates the probability of catching a wild Pokemon.

```json
{
  "name": "calculate_catch_rate",
  "description": "Calculates catch probability using Gen 1 catch rate formula. Accounts for species catch rate, current HP, status conditions, and ball type.",
  "input_schema": {
    "type": "object",
    "properties": {
      "species": {
        "type": "string",
        "description": "Pokemon species name"
      },
      "current_hp": {
        "type": "integer",
        "description": "Pokemon's current HP"
      },
      "max_hp": {
        "type": "integer",
        "description": "Pokemon's maximum HP"
      },
      "status": {
        "type": "string",
        "enum": ["SLEEP", "FREEZE", "PARALYSIS", "BURN", "POISON", null],
        "description": "Current status condition (null if none)"
      },
      "ball_type": {
        "type": "string",
        "enum": ["POKE_BALL", "GREAT_BALL", "ULTRA_BALL", "MASTER_BALL", "SAFARI_BALL"],
        "description": "Type of Poke Ball to use"
      }
    },
    "required": ["species", "current_hp", "max_hp", "ball_type"]
  }
}
```

**Response Schema:**
```json
{
  "catch_probability": 0.47,
  "catch_percent": "47%",
  "expected_balls_needed": 2.1,
  "recommendation": "THROW_BALL",
  "improvements": {
    "if_hp_at_1": {"probability": 0.68, "improvement": "+21%"},
    "if_asleep": {"probability": 0.72, "improvement": "+25%"},
    "with_ultra_ball": {"probability": 0.63, "improvement": "+16%"}
  },
  "species_catch_rate": 190,
  "ball_modifier": 1.5
}
```

---

### 5. evaluate_switch_options

Analyzes all switching options against the current enemy.

```json
{
  "name": "evaluate_switch_options",
  "description": "Evaluates all available Pokemon as potential switches against the current enemy. Scores each option based on type matchup, HP, speed, and available moves.",
  "input_schema": {
    "type": "object",
    "properties": {
      "active_pokemon": {
        "type": "object",
        "properties": {
          "species": {"type": "string"},
          "current_hp": {"type": "integer"},
          "max_hp": {"type": "integer"},
          "types": {"type": "array", "items": {"type": "string"}},
          "moves": {"type": "array", "items": {"type": "object"}}
        },
        "description": "Currently active Pokemon"
      },
      "party": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "species": {"type": "string"},
            "current_hp": {"type": "integer"},
            "max_hp": {"type": "integer"},
            "types": {"type": "array", "items": {"type": "string"}},
            "speed": {"type": "integer"},
            "moves": {"type": "array", "items": {"type": "object"}}
          }
        },
        "description": "All party Pokemon"
      },
      "enemy_pokemon": {
        "type": "object",
        "properties": {
          "species": {"type": "string"},
          "level": {"type": "integer"},
          "types": {"type": "array", "items": {"type": "string"}},
          "known_moves": {"type": "array", "items": {"type": "string"}}
        },
        "description": "Current enemy Pokemon"
      }
    },
    "required": ["active_pokemon", "party", "enemy_pokemon"]
  }
}
```

**Response Schema:**
```json
{
  "current_matchup": {
    "pokemon": "PIKACHU",
    "score": -25,
    "rating": "POOR",
    "reason": "Ground-type enemy; Electric moves are immune"
  },
  "switch_options": [
    {
      "pokemon": "PIDGEOT",
      "party_index": 2,
      "score": 45,
      "rating": "GOOD",
      "reason": "Flying immune to Ground, has strong Flying STAB",
      "pros": ["Type immunity", "Higher speed"],
      "cons": ["Low HP (34%)", "No super effective moves"]
    },
    {
      "pokemon": "VENUSAUR",
      "party_index": 3,
      "score": 30,
      "rating": "DECENT",
      "reason": "Resists Ground, good bulk",
      "pros": ["Resists Ground 0.5x", "Has Razor Leaf"],
      "cons": ["Slower than enemy"]
    }
  ],
  "recommended_switch": {
    "pokemon": "PIDGEOT",
    "party_index": 2,
    "confidence": "HIGH"
  },
  "should_switch": true,
  "switching_penalty_note": "Switching costs one turn; enemy will attack"
}
```

---

### 6. get_best_move

Determines the optimal move for the current battle situation.

```json
{
  "name": "get_best_move",
  "description": "Analyzes all available moves and recommends the best choice for the current situation. Considers damage, accuracy, type effectiveness, PP, and secondary effects.",
  "input_schema": {
    "type": "object",
    "properties": {
      "active_pokemon": {
        "type": "object",
        "properties": {
          "species": {"type": "string"},
          "level": {"type": "integer"},
          "types": {"type": "array", "items": {"type": "string"}},
          "attack": {"type": "integer"},
          "special": {"type": "integer"},
          "speed": {"type": "integer"},
          "moves": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "name": {"type": "string"},
                "type": {"type": "string"},
                "category": {"type": "string"},
                "power": {"type": "integer"},
                "accuracy": {"type": "integer"},
                "pp_current": {"type": "integer"},
                "pp_max": {"type": "integer"},
                "effect": {"type": "string"}
              }
            }
          }
        },
        "description": "Currently active Pokemon with full move data"
      },
      "enemy_pokemon": {
        "type": "object",
        "properties": {
          "species": {"type": "string"},
          "level": {"type": "integer"},
          "current_hp_percent": {"type": "number"},
          "types": {"type": "array", "items": {"type": "string"}},
          "status": {"type": "string"}
        },
        "description": "Enemy Pokemon"
      },
      "battle_context": {
        "type": "object",
        "properties": {
          "is_trainer_battle": {"type": "boolean"},
          "can_catch": {"type": "boolean"},
          "want_to_catch": {"type": "boolean"},
          "enemy_remaining": {"type": "integer"}
        },
        "description": "Battle context for decision making"
      }
    },
    "required": ["active_pokemon", "enemy_pokemon"]
  }
}
```

**Response Schema:**
```json
{
  "recommended_move": {
    "name": "THUNDERBOLT",
    "index": 1,
    "score": 95
  },
  "reasoning": "Super effective (2x), high power (95), perfect accuracy, STAB bonus. Expected to KO in 1 hit.",
  "alternatives": [
    {
      "name": "THUNDER",
      "index": 2,
      "score": 78,
      "note": "Higher power (120) but only 70% accuracy - too risky"
    },
    {
      "name": "QUICK_ATTACK",
      "index": 0,
      "score": 45,
      "note": "Has priority, use if enemy is low HP and faster than us"
    }
  ],
  "avoid": [
    {
      "name": "THUNDER_WAVE",
      "index": 3,
      "reason": "Enemy is already paralyzed - would waste turn"
    }
  ],
  "ko_analysis": {
    "can_ko_this_turn": true,
    "guaranteed_ko": true
  }
}
```

---

### 7. should_catch_pokemon

Evaluates whether a wild Pokemon is worth catching.

```json
{
  "name": "should_catch_pokemon",
  "description": "Evaluates whether a wild Pokemon should be caught based on team composition needs, species value, and resource availability.",
  "input_schema": {
    "type": "object",
    "properties": {
      "wild_pokemon": {
        "type": "object",
        "properties": {
          "species": {"type": "string"},
          "level": {"type": "integer"},
          "types": {"type": "array", "items": {"type": "string"}}
        },
        "description": "The wild Pokemon encountered"
      },
      "current_party": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "species": {"type": "string"},
            "types": {"type": "array", "items": {"type": "string"}}
          }
        },
        "description": "Current party composition"
      },
      "available_balls": {
        "type": "object",
        "properties": {
          "POKE_BALL": {"type": "integer"},
          "GREAT_BALL": {"type": "integer"},
          "ULTRA_BALL": {"type": "integer"}
        },
        "description": "Available Poke Balls"
      },
      "current_objective": {
        "type": "string",
        "description": "Current objective (may need specific types)"
      },
      "upcoming_gym": {
        "type": "string",
        "description": "Next gym leader to face (for type coverage)"
      }
    },
    "required": ["wild_pokemon", "current_party", "available_balls"]
  }
}
```

**Response Schema:**
```json
{
  "should_catch": true,
  "priority": "HIGH",
  "reasons": [
    "No Electric type currently on team",
    "Pikachu is strong against upcoming Water gym (Misty)",
    "Evolves into powerful Raichu via Thunder Stone"
  ],
  "concerns": [
    "Low catch rate (190 - medium difficulty)",
    "May require 3-4 balls"
  ],
  "strategy": {
    "ball_recommendation": "GREAT_BALL",
    "prep_actions": [
      "Use Thunder Wave to paralyze first",
      "Weaken to yellow/red HP"
    ],
    "estimated_balls": 3
  },
  "alternative": "If catch fails, Voltorb is available at Power Plant later"
}
```

---

### 8. battle_execute_action

Executes a battle action (move, switch, item, catch, or run).

```json
{
  "name": "battle_execute_action",
  "description": "Executes a battle action by sending the appropriate controller inputs. Handles move selection, switching, item use, catching attempts, and fleeing.",
  "input_schema": {
    "type": "object",
    "properties": {
      "action_type": {
        "type": "string",
        "enum": ["MOVE", "SWITCH", "ITEM", "CATCH", "RUN"],
        "description": "Type of action to perform"
      },
      "move_index": {
        "type": "integer",
        "minimum": 0,
        "maximum": 3,
        "description": "For MOVE: Index of move to use (0-3)"
      },
      "switch_to_index": {
        "type": "integer",
        "minimum": 0,
        "maximum": 5,
        "description": "For SWITCH: Party index to switch to (0-5)"
      },
      "item": {
        "type": "string",
        "description": "For ITEM: Name of item to use"
      },
      "item_target_index": {
        "type": "integer",
        "description": "For ITEM: Party index of Pokemon to use item on"
      },
      "ball_type": {
        "type": "string",
        "enum": ["POKE_BALL", "GREAT_BALL", "ULTRA_BALL", "MASTER_BALL", "SAFARI_BALL"],
        "description": "For CATCH: Type of ball to throw"
      }
    },
    "required": ["action_type"]
  }
}
```

**Response Schema:**
```json
{
  "action_executed": "MOVE",
  "success": true,
  "turn_result": {
    "our_action": {
      "move": "THUNDERBOLT",
      "damage_dealt": 48,
      "critical_hit": false,
      "effect_triggered": null
    },
    "enemy_action": {
      "move": "TACKLE",
      "damage_dealt": 12,
      "critical_hit": false,
      "effect_triggered": null
    },
    "order": "we_moved_first"
  },
  "state_after": {
    "our_pokemon_hp": 43,
    "enemy_pokemon_hp": 0,
    "our_pokemon_status": null,
    "enemy_pokemon_status": null
  },
  "events": [
    {"type": "ENEMY_FAINTED", "pokemon": "RATTATA"}
  ],
  "battle_status": {
    "battle_over": false,
    "next_enemy": {"species": "RATICATE", "level": 24},
    "enemy_remaining": 1
  }
}
```

---

### 9. get_battle_state

Reads the current battle state from game memory.

```json
{
  "name": "get_battle_state",
  "description": "Reads and returns the complete current battle state including both Pokemon, HP, status, stat stages, and turn count.",
  "input_schema": {
    "type": "object",
    "properties": {
      "include_move_details": {
        "type": "boolean",
        "default": true,
        "description": "Include full move data for active Pokemon"
      }
    },
    "required": []
  }
}
```

**Response Schema:**
```json
{
  "battle_type": "TRAINER",
  "can_flee": false,
  "can_catch": false,
  "turn_number": 3,
  "our_side": {
    "active": {
      "species": "PIKACHU",
      "level": 25,
      "current_hp": 43,
      "max_hp": 55,
      "hp_percent": 78.2,
      "status": null,
      "types": ["ELECTRIC"],
      "moves": [
        {"name": "QUICK_ATTACK", "pp": 25, "pp_max": 30},
        {"name": "THUNDERBOLT", "pp": 12, "pp_max": 15},
        {"name": "THUNDER", "pp": 8, "pp_max": 10},
        {"name": "THUNDER_WAVE", "pp": 15, "pp_max": 20}
      ]
    },
    "stat_stages": {
      "attack": 0,
      "defense": 0,
      "special": 1,
      "speed": 0,
      "accuracy": 0,
      "evasion": 0
    },
    "party_remaining": 4,
    "party_summary": [
      {"species": "PIKACHU", "hp_percent": 78.2, "fainted": false},
      {"species": "CHARIZARD", "hp_percent": 100, "fainted": false},
      {"species": "BLASTOISE", "hp_percent": 65, "fainted": false},
      {"species": "ALAKAZAM", "hp_percent": 0, "fainted": true}
    ]
  },
  "enemy_side": {
    "active": {
      "species": "STARMIE",
      "level": 21,
      "current_hp_percent": 45,
      "status": null,
      "types": ["WATER", "PSYCHIC"]
    },
    "stat_stages": {
      "attack": 0,
      "defense": 0,
      "special": 0,
      "speed": 0
    },
    "trainer": {
      "name": "MISTY",
      "class": "GYM_LEADER",
      "pokemon_remaining": 1
    }
  }
}
```

---

## Menu Agent Tools

### 1. navigate_menu

Navigates through menu options with directional inputs.

```json
{
  "name": "navigate_menu",
  "description": "Sends navigation inputs to move through menus. Can move cursor, select options, or cancel/back out of menus.",
  "input_schema": {
    "type": "object",
    "properties": {
      "action": {
        "type": "string",
        "enum": ["move", "select", "cancel"],
        "description": "Type of navigation action"
      },
      "direction": {
        "type": "string",
        "enum": ["UP", "DOWN", "LEFT", "RIGHT"],
        "description": "For 'move' action: direction to move cursor"
      },
      "count": {
        "type": "integer",
        "default": 1,
        "description": "For 'move' action: number of times to press"
      }
    },
    "required": ["action"]
  }
}
```

**Response Schema:**
```json
{
  "action_executed": "move",
  "new_cursor_position": 2,
  "current_selection": "ITEM",
  "menu_type": "START_MENU",
  "available_options": ["POKEDEX", "POKEMON", "ITEM", "TRAINER", "SAVE", "OPTION"]
}
```

---

### 2. open_start_menu

Opens the start menu from the overworld.

```json
{
  "name": "open_start_menu",
  "description": "Opens the start menu by pressing the START button. Only works from overworld mode.",
  "input_schema": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

**Response Schema:**
```json
{
  "success": true,
  "menu_opened": true,
  "menu_type": "START_MENU",
  "options": ["POKEDEX", "POKEMON", "ITEM", "[PLAYER_NAME]", "SAVE", "OPTION"],
  "cursor_position": 0
}
```

---

### 3. get_inventory

Returns the current inventory state.

```json
{
  "name": "get_inventory",
  "description": "Reads and returns the player's complete inventory including regular items, key items, and TMs/HMs.",
  "input_schema": {
    "type": "object",
    "properties": {
      "category_filter": {
        "type": "string",
        "enum": ["all", "items", "key_items", "tms_hms", "balls", "healing"],
        "default": "all",
        "description": "Filter to specific item category"
      }
    },
    "required": []
  }
}
```

**Response Schema:**
```json
{
  "items": {
    "POTION": 5,
    "SUPER_POTION": 2,
    "ANTIDOTE": 3,
    "ESCAPE_ROPE": 1,
    "REPEL": 3
  },
  "balls": {
    "POKE_BALL": 10,
    "GREAT_BALL": 5
  },
  "key_items": ["BICYCLE", "TOWN_MAP", "SS_TICKET"],
  "tms_hms": {
    "HM01": {"move": "CUT", "taught": true},
    "HM02": {"move": "FLY", "taught": false},
    "TM28": {"move": "DIG", "taught": false}
  },
  "total_slots_used": 15,
  "max_slots": 20,
  "money": 24730
}
```

---

### 4. use_item

Uses an item from inventory.

```json
{
  "name": "use_item",
  "description": "Uses an item from the inventory. Handles healing items, status cures, repels, escape ropes, and teaching TMs/HMs.",
  "input_schema": {
    "type": "object",
    "properties": {
      "item": {
        "type": "string",
        "description": "Name of the item to use"
      },
      "target_pokemon": {
        "type": "string",
        "description": "Pokemon to use item on (name or party index). Required for healing items and TMs."
      },
      "context": {
        "type": "string",
        "enum": ["field", "battle"],
        "default": "field",
        "description": "Whether using in field or in battle"
      },
      "replace_move": {
        "type": "string",
        "description": "For TM/HM teaching when Pokemon has 4 moves - move to forget"
      }
    },
    "required": ["item"]
  }
}
```

**Response Schema:**
```json
{
  "success": true,
  "item_used": "SUPER_POTION",
  "target": "PIKACHU",
  "effect": {
    "type": "HP_RESTORE",
    "amount": 50,
    "hp_before": 23,
    "hp_after": 55,
    "hp_max": 55
  },
  "remaining_quantity": 1,
  "item_consumed": true
}
```

---

### 5. heal_at_pokemon_center

Executes the full Pokemon Center healing sequence.

```json
{
  "name": "heal_at_pokemon_center",
  "description": "Performs the complete Pokemon Center healing sequence: walking to the nurse, initiating dialogue, confirming heal, waiting for the jingle, and dismissing the final dialogue. Must already be inside the Pokemon Center.",
  "input_schema": {
    "type": "object",
    "properties": {
      "confirm_location": {
        "type": "boolean",
        "default": true,
        "description": "Verify we're in a Pokemon Center before attempting"
      }
    },
    "required": []
  }
}
```

**Response Schema:**
```json
{
  "success": true,
  "party_healed": true,
  "pokemon_restored": [
    {"species": "PIKACHU", "hp_before": 23, "hp_after": 55, "hp_max": 55},
    {"species": "CHARIZARD", "hp_before": 89, "hp_after": 150, "hp_max": 150}
  ],
  "pp_fully_restored": true,
  "status_cured": [
    {"species": "PIKACHU", "status_cured": "POISON"}
  ],
  "last_pokemon_center": "CERULEAN_CITY"
}
```

---

### 6. shop_buy

Purchases items from a Poke Mart.

```json
{
  "name": "shop_buy",
  "description": "Purchases items from a Poke Mart. Handles the full shopping sequence including navigating the shop menu, selecting items, specifying quantities, and confirming purchases.",
  "input_schema": {
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "item": {"type": "string", "description": "Item name to buy"},
            "quantity": {"type": "integer", "minimum": 1, "maximum": 99}
          },
          "required": ["item", "quantity"]
        },
        "description": "List of items and quantities to purchase"
      }
    },
    "required": ["items"]
  }
}
```

**Response Schema:**
```json
{
  "success": true,
  "items_bought": [
    {"item": "SUPER_POTION", "quantity": 5, "unit_price": 700, "total_cost": 3500},
    {"item": "GREAT_BALL", "quantity": 10, "unit_price": 600, "total_cost": 6000}
  ],
  "total_spent": 9500,
  "money_before": 24730,
  "money_after": 15230,
  "partial_purchase": false
}
```

---

### 7. shop_sell

Sells items to a Poke Mart.

```json
{
  "name": "shop_sell",
  "description": "Sells items at a Poke Mart. Navigates sell menu, selects items, and confirms sales.",
  "input_schema": {
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "item": {"type": "string", "description": "Item name to sell"},
            "quantity": {"type": "integer", "minimum": 1}
          },
          "required": ["item", "quantity"]
        },
        "description": "List of items and quantities to sell"
      }
    },
    "required": ["items"]
  }
}
```

**Response Schema:**
```json
{
  "success": true,
  "items_sold": [
    {"item": "NUGGET", "quantity": 1, "unit_value": 5000, "total_value": 5000},
    {"item": "ANTIDOTE", "quantity": 5, "unit_value": 50, "total_value": 250}
  ],
  "total_earned": 5250,
  "money_before": 15230,
  "money_after": 20480
}
```

---

### 8. get_shop_inventory

Returns items available at the current shop.

```json
{
  "name": "get_shop_inventory",
  "description": "Returns the list of items available for purchase at the current Poke Mart, along with their prices.",
  "input_schema": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

**Response Schema:**
```json
{
  "shop_location": "CERULEAN_CITY",
  "items_available": [
    {"item": "POKE_BALL", "price": 200, "can_afford": true, "max_buyable": 102},
    {"item": "SUPER_POTION", "price": 700, "can_afford": true, "max_buyable": 29},
    {"item": "ANTIDOTE", "price": 100, "can_afford": true, "max_buyable": 204},
    {"item": "PARLYZ_HEAL", "price": 200, "can_afford": true, "max_buyable": 102},
    {"item": "AWAKENING", "price": 250, "can_afford": true, "max_buyable": 81},
    {"item": "REPEL", "price": 350, "can_afford": true, "max_buyable": 58}
  ],
  "player_money": 20480
}
```

---

### 9. manage_party

Manages party Pokemon (view, reorder, check summary).

```json
{
  "name": "manage_party",
  "description": "Performs party management operations including viewing Pokemon, swapping positions, and checking summaries.",
  "input_schema": {
    "type": "object",
    "properties": {
      "action": {
        "type": "string",
        "enum": ["view", "swap", "view_summary", "view_moves"],
        "description": "Party management action to perform"
      },
      "position_1": {
        "type": "integer",
        "minimum": 0,
        "maximum": 5,
        "description": "For 'swap': First position (or pokemon to view)"
      },
      "position_2": {
        "type": "integer",
        "minimum": 0,
        "maximum": 5,
        "description": "For 'swap': Second position"
      }
    },
    "required": ["action"]
  }
}
```

**Response Schema:**
```json
{
  "success": true,
  "action": "swap",
  "result": {
    "new_party_order": [
      {"position": 0, "species": "CHARIZARD", "level": 36},
      {"position": 1, "species": "PIKACHU", "level": 25},
      {"position": 2, "species": "BLASTOISE", "level": 34},
      {"position": 3, "species": "ALAKAZAM", "level": 30},
      {"position": 4, "species": "SNORLAX", "level": 32},
      {"position": 5, "species": "LAPRAS", "level": 28}
    ]
  }
}
```

---

### 10. teach_move

Teaches a TM or HM to a Pokemon.

```json
{
  "name": "teach_move",
  "description": "Teaches a TM or HM move to a compatible Pokemon. Handles the full teaching flow including selecting the item, choosing the Pokemon, and optionally forgetting a move if at 4 moves.",
  "input_schema": {
    "type": "object",
    "properties": {
      "move_item": {
        "type": "string",
        "description": "TM or HM identifier (e.g., 'HM01', 'TM28')"
      },
      "target_pokemon": {
        "type": "string",
        "description": "Pokemon to teach the move to (species name or party index)"
      },
      "replace_move": {
        "type": "string",
        "description": "If Pokemon has 4 moves, which move to forget. Required if at 4 moves."
      }
    },
    "required": ["move_item", "target_pokemon"]
  }
}
```

**Response Schema:**
```json
{
  "success": true,
  "pokemon": "BULBASAUR",
  "move_learned": "CUT",
  "move_forgotten": "TACKLE",
  "tm_consumed": false,
  "is_hm": true,
  "new_moveset": ["VINE_WHIP", "RAZOR_LEAF", "SLEEP_POWDER", "CUT"]
}
```

---

### 11. pc_deposit_pokemon

Deposits a Pokemon into the PC storage.

```json
{
  "name": "pc_deposit_pokemon",
  "description": "Deposits a Pokemon from the party into PC storage. Must be at a Pokemon Center PC.",
  "input_schema": {
    "type": "object",
    "properties": {
      "pokemon": {
        "type": "string",
        "description": "Pokemon to deposit (species name or party index)"
      },
      "box": {
        "type": "integer",
        "minimum": 1,
        "maximum": 12,
        "description": "Box number to deposit into (1-12)"
      }
    },
    "required": ["pokemon"]
  }
}
```

**Response Schema:**
```json
{
  "success": true,
  "pokemon_deposited": "RATTATA",
  "deposited_to_box": 1,
  "box_space_remaining": 19,
  "party_size_after": 5
}
```

---

### 12. pc_withdraw_pokemon

Withdraws a Pokemon from PC storage.

```json
{
  "name": "pc_withdraw_pokemon",
  "description": "Withdraws a Pokemon from PC storage to the party. Party must have space (< 6 Pokemon).",
  "input_schema": {
    "type": "object",
    "properties": {
      "pokemon": {
        "type": "string",
        "description": "Pokemon to withdraw (species name)"
      },
      "box": {
        "type": "integer",
        "minimum": 1,
        "maximum": 12,
        "description": "Box number to withdraw from"
      }
    },
    "required": ["pokemon", "box"]
  }
}
```

**Response Schema:**
```json
{
  "success": true,
  "pokemon_withdrawn": "GYARADOS",
  "withdrawn_from_box": 3,
  "party_size_after": 6
}
```

---

### 13. handle_dialogue

Processes dialogue and makes choices when prompted.

```json
{
  "name": "handle_dialogue",
  "description": "Handles dialogue interactions - advancing text, making choices, or dismissing dialogue boxes.",
  "input_schema": {
    "type": "object",
    "properties": {
      "action": {
        "type": "string",
        "enum": ["advance", "choose", "cancel"],
        "description": "Dialogue action to perform"
      },
      "choice": {
        "type": "string",
        "description": "For 'choose' action: the choice to select (e.g., 'YES', 'NO', or choice text)"
      },
      "choice_index": {
        "type": "integer",
        "description": "For 'choose' action: alternative - index of choice (0-based)"
      }
    },
    "required": ["action"]
  }
}
```

**Response Schema:**
```json
{
  "action_executed": "advance",
  "dialogue_complete": false,
  "current_text": "Would you like to heal your Pokemon?",
  "choices_available": ["YES", "NO"],
  "awaiting_choice": true,
  "npc_speaking": "NURSE"
}
```

---

### 14. get_party_status

Returns detailed status of all party Pokemon.

```json
{
  "name": "get_party_status",
  "description": "Returns comprehensive status information for all Pokemon in the party including HP, status conditions, and PP.",
  "input_schema": {
    "type": "object",
    "properties": {
      "include_moves": {
        "type": "boolean",
        "default": false,
        "description": "Include full move details with PP"
      }
    },
    "required": []
  }
}
```

**Response Schema:**
```json
{
  "party_size": 6,
  "party": [
    {
      "position": 0,
      "species": "PIKACHU",
      "level": 25,
      "current_hp": 55,
      "max_hp": 55,
      "hp_percent": 100,
      "status": null,
      "types": ["ELECTRIC"],
      "moves": [
        {"name": "QUICK_ATTACK", "pp": 30, "pp_max": 30},
        {"name": "THUNDERBOLT", "pp": 15, "pp_max": 15},
        {"name": "THUNDER", "pp": 10, "pp_max": 10},
        {"name": "THUNDER_WAVE", "pp": 20, "pp_max": 20}
      ]
    }
  ],
  "fainted_count": 1,
  "total_hp_percent": 78.5,
  "status_conditions": [
    {"species": "VENUSAUR", "status": "POISON"}
  ],
  "low_pp_pokemon": [
    {"species": "ALAKAZAM", "total_pp_percent": 15}
  ]
}
```

---

## Python Implementation Helper

Here's a helper class to manage tool definitions and make API calls:

```python
"""
Pokemon Red AI Agent - Tool Definitions
"""

from typing import Any

# All tools organized by agent
ORCHESTRATOR_TOOLS = [
    {
        "name": "detect_game_mode",
        "description": "Analyzes the current game screen and memory state to determine the active game mode (OVERWORLD, BATTLE, MENU, or DIALOGUE).",
        "input_schema": {
            "type": "object",
            "properties": {
                "screen_data": {
                    "type": "object",
                    "description": "Current screen state data"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_current_objective",
        "description": "Analyzes current game progress and returns the appropriate current objective with its details and prerequisites.",
        "input_schema": {
            "type": "object",
            "properties": {
                "badges": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of badges obtained"
                },
                "story_flags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Completed story events"
                },
                "current_location": {
                    "type": "string",
                    "description": "Current map location"
                },
                "party_pokemon": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Current party composition"
                }
            },
            "required": ["badges", "story_flags", "current_location"]
        }
    },
    {
        "name": "get_next_milestone",
        "description": "Determines the next major story milestone and breaks it down into actionable steps.",
        "input_schema": {
            "type": "object",
            "properties": {
                "badges": {"type": "array", "items": {"type": "string"}},
                "story_flags": {"type": "array", "items": {"type": "string"}},
                "hms_obtained": {"type": "array", "items": {"type": "string"}},
                "hms_usable": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["badges", "story_flags"]
        }
    },
    {
        "name": "check_requirements",
        "description": "Evaluates whether all prerequisites are met for a specific objective.",
        "input_schema": {
            "type": "object",
            "properties": {
                "objective_type": {
                    "type": "string",
                    "enum": ["navigate", "defeat_gym", "defeat_trainer", "catch_pokemon", "get_item", "get_hm", "teach_hm"]
                },
                "objective_target": {"type": "string"},
                "current_state": {"type": "object"}
            },
            "required": ["objective_type", "objective_target", "current_state"]
        }
    },
    {
        "name": "route_to_agent",
        "description": "Determines which specialist agent should handle the current situation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "game_mode": {
                    "type": "string",
                    "enum": ["OVERWORLD", "BATTLE", "MENU", "DIALOGUE"]
                },
                "current_objective": {"type": "object"},
                "game_state_summary": {"type": "object"}
            },
            "required": ["game_mode", "current_objective"]
        }
    },
    {
        "name": "update_game_state",
        "description": "Updates the shared GameState object with new information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "updates": {"type": "object"},
                "source": {
                    "type": "string",
                    "enum": ["memory_read", "agent_report", "screen_parse"]
                }
            },
            "required": ["updates", "source"]
        }
    },
    {
        "name": "manage_objective_stack",
        "description": "Manages the objective stack - push, pop, or peek operations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["push", "pop", "peek", "clear_completed"]
                },
                "objective": {"type": "object"}
            },
            "required": ["operation"]
        }
    }
]

NAVIGATION_TOOLS = [
    {
        "name": "get_current_position",
        "description": "Returns the player's current position including map, coordinates, and facing direction.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_map_data",
        "description": "Retrieves comprehensive map data including layout, connections, NPCs, and items.",
        "input_schema": {
            "type": "object",
            "properties": {
                "map_id": {"type": "string"},
                "include_tiles": {"type": "boolean", "default": False},
                "include_npcs": {"type": "boolean", "default": True}
            },
            "required": []
        }
    },
    {
        "name": "find_path",
        "description": "Calculates an optimal path between two points using A* pathfinding.",
        "input_schema": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "object",
                    "properties": {
                        "map": {"type": "string"},
                        "x": {"type": "integer"},
                        "y": {"type": "integer"}
                    },
                    "required": ["map"]
                },
                "from": {"type": "object"},
                "preferences": {
                    "type": "object",
                    "properties": {
                        "avoid_grass": {"type": "boolean", "default": True},
                        "avoid_trainers": {"type": "boolean", "default": True},
                        "seek_trainers": {"type": "boolean", "default": False},
                        "allowed_hms": {"type": "array", "items": {"type": "string"}}
                    }
                }
            },
            "required": ["destination"]
        }
    },
    {
        "name": "get_interactables",
        "description": "Scans the area around the player for interactable objects and NPCs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "range": {"type": "integer", "default": 5}
            },
            "required": []
        }
    },
    {
        "name": "execute_movement",
        "description": "Sends a sequence of controller inputs to move the player.",
        "input_schema": {
            "type": "object",
            "properties": {
                "moves": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["UP", "DOWN", "LEFT", "RIGHT", "A", "B", "START", "SELECT"]
                    }
                },
                "stop_conditions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["BATTLE_START", "DIALOGUE_START", "WARP"]
                },
                "frame_delay": {"type": "integer", "default": 4}
            },
            "required": ["moves"]
        }
    },
    {
        "name": "check_route_accessibility",
        "description": "Checks whether a route between two maps is currently accessible.",
        "input_schema": {
            "type": "object",
            "properties": {
                "from_map": {"type": "string"},
                "to_map": {"type": "string"},
                "available_hms": {"type": "array", "items": {"type": "string"}},
                "story_flags": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["from_map", "to_map"]
        }
    },
    {
        "name": "get_hidden_items",
        "description": "Retrieves the locations of hidden items on the specified map.",
        "input_schema": {
            "type": "object",
            "properties": {
                "map_id": {"type": "string"},
                "only_unobtained": {"type": "boolean", "default": True}
            },
            "required": []
        }
    },
    {
        "name": "use_hm_in_field",
        "description": "Activates an HM move in the overworld to clear an obstacle.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hm_move": {
                    "type": "string",
                    "enum": ["CUT", "FLY", "SURF", "STRENGTH", "FLASH"]
                },
                "target_direction": {
                    "type": "string",
                    "enum": ["UP", "DOWN", "LEFT", "RIGHT", "CURRENT"]
                },
                "fly_destination": {"type": "string"}
            },
            "required": ["hm_move"]
        }
    }
]

BATTLE_TOOLS = [
    {
        "name": "get_pokemon_data",
        "description": "Retrieves complete Pokemon species data from the static knowledge base.",
        "input_schema": {
            "type": "object",
            "properties": {
                "species": {"type": "string"},
                "dex_number": {"type": "integer"}
            },
            "required": []
        }
    },
    {
        "name": "calculate_type_effectiveness",
        "description": "Calculates the type effectiveness multiplier for an attack against defender types.",
        "input_schema": {
            "type": "object",
            "properties": {
                "attack_type": {"type": "string"},
                "defender_types": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["attack_type", "defender_types"]
        }
    },
    {
        "name": "estimate_damage",
        "description": "Calculates estimated damage range for a move including all modifiers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "attacker": {"type": "object"},
                "defender": {"type": "object"},
                "move": {"type": "object"},
                "attacker_stages": {"type": "object"},
                "defender_stages": {"type": "object"}
            },
            "required": ["attacker", "defender", "move"]
        }
    },
    {
        "name": "calculate_catch_rate",
        "description": "Calculates catch probability using Gen 1 formula.",
        "input_schema": {
            "type": "object",
            "properties": {
                "species": {"type": "string"},
                "current_hp": {"type": "integer"},
                "max_hp": {"type": "integer"},
                "status": {"type": "string"},
                "ball_type": {"type": "string"}
            },
            "required": ["species", "current_hp", "max_hp", "ball_type"]
        }
    },
    {
        "name": "evaluate_switch_options",
        "description": "Evaluates all available Pokemon as potential switches against current enemy.",
        "input_schema": {
            "type": "object",
            "properties": {
                "active_pokemon": {"type": "object"},
                "party": {"type": "array", "items": {"type": "object"}},
                "enemy_pokemon": {"type": "object"}
            },
            "required": ["active_pokemon", "party", "enemy_pokemon"]
        }
    },
    {
        "name": "get_best_move",
        "description": "Analyzes all available moves and recommends the best choice.",
        "input_schema": {
            "type": "object",
            "properties": {
                "active_pokemon": {"type": "object"},
                "enemy_pokemon": {"type": "object"},
                "battle_context": {"type": "object"}
            },
            "required": ["active_pokemon", "enemy_pokemon"]
        }
    },
    {
        "name": "should_catch_pokemon",
        "description": "Evaluates whether a wild Pokemon should be caught based on team needs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "wild_pokemon": {"type": "object"},
                "current_party": {"type": "array", "items": {"type": "object"}},
                "available_balls": {"type": "object"},
                "current_objective": {"type": "string"},
                "upcoming_gym": {"type": "string"}
            },
            "required": ["wild_pokemon", "current_party", "available_balls"]
        }
    },
    {
        "name": "battle_execute_action",
        "description": "Executes a battle action (move, switch, item, catch, or run).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action_type": {
                    "type": "string",
                    "enum": ["MOVE", "SWITCH", "ITEM", "CATCH", "RUN"]
                },
                "move_index": {"type": "integer", "minimum": 0, "maximum": 3},
                "switch_to_index": {"type": "integer", "minimum": 0, "maximum": 5},
                "item": {"type": "string"},
                "item_target_index": {"type": "integer"},
                "ball_type": {"type": "string"}
            },
            "required": ["action_type"]
        }
    },
    {
        "name": "get_battle_state",
        "description": "Reads and returns the complete current battle state.",
        "input_schema": {
            "type": "object",
            "properties": {
                "include_move_details": {"type": "boolean", "default": True}
            },
            "required": []
        }
    }
]

MENU_TOOLS = [
    {
        "name": "navigate_menu",
        "description": "Sends navigation inputs to move through menus.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["move", "select", "cancel"]},
                "direction": {"type": "string", "enum": ["UP", "DOWN", "LEFT", "RIGHT"]},
                "count": {"type": "integer", "default": 1}
            },
            "required": ["action"]
        }
    },
    {
        "name": "open_start_menu",
        "description": "Opens the start menu by pressing START.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_inventory",
        "description": "Returns the player's complete inventory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category_filter": {
                    "type": "string",
                    "enum": ["all", "items", "key_items", "tms_hms", "balls", "healing"],
                    "default": "all"
                }
            },
            "required": []
        }
    },
    {
        "name": "use_item",
        "description": "Uses an item from the inventory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "item": {"type": "string"},
                "target_pokemon": {"type": "string"},
                "context": {"type": "string", "enum": ["field", "battle"], "default": "field"},
                "replace_move": {"type": "string"}
            },
            "required": ["item"]
        }
    },
    {
        "name": "heal_at_pokemon_center",
        "description": "Performs the complete Pokemon Center healing sequence.",
        "input_schema": {
            "type": "object",
            "properties": {
                "confirm_location": {"type": "boolean", "default": True}
            },
            "required": []
        }
    },
    {
        "name": "shop_buy",
        "description": "Purchases items from a Poke Mart.",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item": {"type": "string"},
                            "quantity": {"type": "integer", "minimum": 1, "maximum": 99}
                        },
                        "required": ["item", "quantity"]
                    }
                }
            },
            "required": ["items"]
        }
    },
    {
        "name": "shop_sell",
        "description": "Sells items at a Poke Mart.",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item": {"type": "string"},
                            "quantity": {"type": "integer", "minimum": 1}
                        },
                        "required": ["item", "quantity"]
                    }
                }
            },
            "required": ["items"]
        }
    },
    {
        "name": "get_shop_inventory",
        "description": "Returns items available at the current shop.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "manage_party",
        "description": "Performs party management operations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["view", "swap", "view_summary", "view_moves"]},
                "position_1": {"type": "integer", "minimum": 0, "maximum": 5},
                "position_2": {"type": "integer", "minimum": 0, "maximum": 5}
            },
            "required": ["action"]
        }
    },
    {
        "name": "teach_move",
        "description": "Teaches a TM or HM move to a compatible Pokemon.",
        "input_schema": {
            "type": "object",
            "properties": {
                "move_item": {"type": "string"},
                "target_pokemon": {"type": "string"},
                "replace_move": {"type": "string"}
            },
            "required": ["move_item", "target_pokemon"]
        }
    },
    {
        "name": "pc_deposit_pokemon",
        "description": "Deposits a Pokemon from party into PC storage.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pokemon": {"type": "string"},
                "box": {"type": "integer", "minimum": 1, "maximum": 12}
            },
            "required": ["pokemon"]
        }
    },
    {
        "name": "pc_withdraw_pokemon",
        "description": "Withdraws a Pokemon from PC storage to party.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pokemon": {"type": "string"},
                "box": {"type": "integer", "minimum": 1, "maximum": 12}
            },
            "required": ["pokemon", "box"]
        }
    },
    {
        "name": "handle_dialogue",
        "description": "Handles dialogue interactions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["advance", "choose", "cancel"]},
                "choice": {"type": "string"},
                "choice_index": {"type": "integer"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "get_party_status",
        "description": "Returns detailed status of all party Pokemon.",
        "input_schema": {
            "type": "object",
            "properties": {
                "include_moves": {"type": "boolean", "default": False}
            },
            "required": []
        }
    }
]


def get_tools_for_agent(agent: str) -> list[dict]:
    """Returns the tool definitions for a specific agent."""
    tools = {
        "orchestrator": ORCHESTRATOR_TOOLS,
        "navigation": NAVIGATION_TOOLS,
        "battle": BATTLE_TOOLS,
        "menu": MENU_TOOLS
    }
    return tools.get(agent.lower(), [])


def get_all_tools() -> dict[str, list[dict]]:
    """Returns all tools organized by agent."""
    return {
        "orchestrator": ORCHESTRATOR_TOOLS,
        "navigation": NAVIGATION_TOOLS,
        "battle": BATTLE_TOOLS,
        "menu": MENU_TOOLS
    }
```

---

## Tool Count Summary

| Agent | Tool Count | Notes |
|-------|------------|-------|
| Orchestrator | 7 | Strategic coordination tools |
| Navigation | 8 | Movement and pathfinding |
| Battle | 9 | Combat decision tools |
| Menu | 14 | UI interaction tools |
| **Total** | **38** | Across all agents |

---

## Versioning

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Initial | All tool schemas defined |
