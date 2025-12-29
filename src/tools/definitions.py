"""Tool definitions for all agents."""

ORCHESTRATOR_TOOLS = [
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
                            "description": "Base64 encoded screen image or reference to current frame",
                        },
                        "memory_snapshot": {
                            "type": "object",
                            "description": "Relevant memory addresses and their current values",
                        },
                    },
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_current_objective",
        "description": "Analyzes current game progress (badges, story flags, location) and returns the appropriate current objective with its details, prerequisites, and recommendations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "badges": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of badges already obtained (e.g., ['Boulder', 'Cascade'])",
                },
                "story_flags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Completed story events (e.g., ['GOT_POKEDEX', 'RESCUED_BILL'])",
                },
                "current_location": {
                    "type": "string",
                    "description": "Current map location (e.g., 'CERULEAN_CITY')",
                },
                "party_pokemon": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "species": {"type": "string"},
                            "level": {"type": "integer"},
                            "types": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                    "description": "Current party composition for objective analysis",
                },
            },
            "required": ["badges", "story_flags", "current_location"],
        },
    },
    {
        "name": "get_next_milestone",
        "description": "Based on current game progress, determines the next major story milestone and breaks it down into actionable steps.",
        "input_schema": {
            "type": "object",
            "properties": {
                "badges": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of badges obtained",
                },
                "story_flags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Completed story events",
                },
                "hms_obtained": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "HMs in possession (e.g., ['HM01_CUT', 'HM02_FLY'])",
                },
                "hms_usable": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "HMs that can be used (have badge + taught to Pokemon)",
                },
            },
            "required": ["badges", "story_flags"],
        },
    },
    {
        "name": "check_requirements",
        "description": "Evaluates whether all prerequisites (HMs, badges, items, Pokemon types) are met for a specific objective. Returns missing requirements and suggests sub-objectives to fulfill them.",
        "input_schema": {
            "type": "object",
            "properties": {
                "objective_type": {
                    "type": "string",
                    "enum": [
                        "navigate",
                        "defeat_gym",
                        "defeat_trainer",
                        "catch_pokemon",
                        "get_item",
                        "get_hm",
                        "teach_hm",
                    ],
                    "description": "Type of objective to check requirements for",
                },
                "objective_target": {
                    "type": "string",
                    "description": "Specific target (location, trainer name, Pokemon species, etc.)",
                },
                "current_state": {
                    "type": "object",
                    "properties": {
                        "badges": {"type": "array", "items": {"type": "string"}},
                        "hms_obtained": {"type": "array", "items": {"type": "string"}},
                        "hms_usable": {"type": "array", "items": {"type": "string"}},
                        "key_items": {"type": "array", "items": {"type": "string"}},
                        "party_types": {"type": "array", "items": {"type": "string"}},
                    },
                    "description": "Current game state for requirement checking",
                },
            },
            "required": ["objective_type", "objective_target", "current_state"],
        },
    },
    {
        "name": "route_to_agent",
        "description": "Based on current game mode and objective, determines which specialist agent (Navigation, Battle, or Menu) should take control and provides the appropriate context for that agent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "game_mode": {
                    "type": "string",
                    "enum": ["OVERWORLD", "BATTLE", "MENU", "DIALOGUE"],
                    "description": "Current detected game mode",
                },
                "current_objective": {
                    "type": "object",
                    "properties": {"type": {"type": "string"}, "target": {"type": "string"}},
                    "description": "Current objective being worked on",
                },
                "game_state_summary": {
                    "type": "object",
                    "properties": {
                        "party_avg_hp_percent": {"type": "number"},
                        "fainted_count": {"type": "integer"},
                        "location": {"type": "string"},
                        "in_battle": {"type": "boolean"},
                        "battle_type": {"type": "string"},
                    },
                    "description": "Summary of current game state",
                },
            },
            "required": ["game_mode", "current_objective"],
        },
    },
    {
        "name": "update_game_state",
        "description": "Updates the shared GameState object with new information from game memory, screen state, or agent action results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "updates": {
                    "type": "object",
                    "properties": {
                        "current_mode": {
                            "type": "string",
                            "enum": ["OVERWORLD", "BATTLE", "MENU", "DIALOGUE"],
                        },
                        "current_map": {"type": "string"},
                        "player_position": {
                            "type": "object",
                            "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
                        },
                        "party": {"type": "array", "items": {"type": "object"}},
                        "inventory": {"type": "object"},
                        "money": {"type": "integer"},
                        "badges": {"type": "array", "items": {"type": "string"}},
                        "story_flags": {"type": "array", "items": {"type": "string"}},
                    },
                    "description": "Fields to update in the game state",
                },
                "source": {
                    "type": "string",
                    "enum": ["memory_read", "agent_report", "screen_parse"],
                    "description": "Source of the state update",
                },
            },
            "required": ["updates", "source"],
        },
    },
    {
        "name": "manage_objective_stack",
        "description": "Manages the objective stack - push new objectives, pop completed ones, or peek at current state.",
        "input_schema": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["push", "pop", "peek", "clear_completed"],
                    "description": "Stack operation to perform",
                },
                "objective": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": [
                                "navigate",
                                "defeat_gym",
                                "defeat_trainer",
                                "catch_pokemon",
                                "get_item",
                                "get_hm",
                                "teach_hm",
                                "heal",
                                "grind",
                                "shop",
                            ],
                        },
                        "target": {"type": "string"},
                        "priority": {"type": "integer"},
                        "requirements": {"type": "array", "items": {"type": "string"}},
                    },
                    "description": "Objective to push (required for push operation)",
                },
            },
            "required": ["operation"],
        },
    },
]

NAVIGATION_TOOLS = [
    {
        "name": "get_current_position",
        "description": "Reads the player's current position from game memory, including map ID, coordinates, facing direction, and tile type.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_map_data",
        "description": "Retrieves comprehensive map data including dimensions, tile layout, connections to other maps, warp points, NPCs, items, and encounter information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "map_id": {
                    "type": "string",
                    "description": "Map ID to retrieve data for. If not provided, uses current map.",
                },
                "include_tiles": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether to include full tile grid (large data)",
                },
                "include_npcs": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to include NPC positions and data",
                },
            },
            "required": [],
        },
    },
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
                        "y": {"type": "integer", "description": "Target Y coordinate"},
                    },
                    "required": ["map"],
                    "description": "Destination location. If x/y omitted, finds entrance to map.",
                },
                "from": {
                    "type": "object",
                    "properties": {
                        "map": {"type": "string"},
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                    },
                    "description": "Starting position. Defaults to current position if omitted.",
                },
                "preferences": {
                    "type": "object",
                    "properties": {
                        "avoid_grass": {
                            "type": "boolean",
                            "default": True,
                            "description": "Prefer paths that minimize grass tiles (fewer encounters)",
                        },
                        "avoid_trainers": {
                            "type": "boolean",
                            "default": True,
                            "description": "Avoid undefeated trainer line-of-sight",
                        },
                        "seek_trainers": {
                            "type": "boolean",
                            "default": False,
                            "description": "Actively route through trainer battles",
                        },
                        "allowed_hms": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "HMs available for use (e.g., ['CUT', 'SURF'])",
                        },
                    },
                },
            },
            "required": ["destination"],
        },
    },
    {
        "name": "get_interactables",
        "description": "Scans the area around the player for interactable objects, NPCs, items, and environmental features. Returns what can be interacted with and relevant details.",
        "input_schema": {
            "type": "object",
            "properties": {
                "range": {
                    "type": "integer",
                    "default": 5,
                    "description": "Tile radius to scan for interactables",
                }
            },
            "required": [],
        },
    },
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
                        "enum": ["UP", "DOWN", "LEFT", "RIGHT", "A", "B", "START", "SELECT"],
                    },
                    "description": "Sequence of inputs to execute",
                },
                "stop_conditions": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "BATTLE_START",
                            "DIALOGUE_START",
                            "WARP",
                            "MENU_OPEN",
                            "COLLISION",
                        ],
                    },
                    "default": ["BATTLE_START", "DIALOGUE_START", "WARP"],
                    "description": "Conditions that should halt execution",
                },
                "frame_delay": {
                    "type": "integer",
                    "default": 4,
                    "description": "Frames to wait between inputs",
                },
            },
            "required": ["moves"],
        },
    },
    {
        "name": "check_route_accessibility",
        "description": "Checks whether a route between two maps is accessible given current HMs, badges, and story progress. Returns blockers and alternatives if not accessible.",
        "input_schema": {
            "type": "object",
            "properties": {
                "from_map": {"type": "string", "description": "Starting map ID"},
                "to_map": {"type": "string", "description": "Destination map ID"},
                "available_hms": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "HMs that can be used",
                },
                "story_flags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Completed story events",
                },
            },
            "required": ["from_map", "to_map"],
        },
    },
    {
        "name": "get_hidden_items",
        "description": "Retrieves the locations of hidden items on the specified map from the static knowledge base. Tracks which have been obtained.",
        "input_schema": {
            "type": "object",
            "properties": {
                "map_id": {
                    "type": "string",
                    "description": "Map to check for hidden items. Defaults to current map.",
                },
                "only_unobtained": {
                    "type": "boolean",
                    "default": True,
                    "description": "Only return items not yet obtained",
                },
            },
            "required": [],
        },
    },
    {
        "name": "use_hm_in_field",
        "description": "Activates an HM move in the overworld to clear an obstacle. Opens the Pokemon menu, selects the HM user, and uses the move.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hm_move": {
                    "type": "string",
                    "enum": ["CUT", "FLY", "SURF", "STRENGTH", "FLASH"],
                    "description": "The HM move to use",
                },
                "target_direction": {
                    "type": "string",
                    "enum": ["UP", "DOWN", "LEFT", "RIGHT", "CURRENT"],
                    "description": "Direction of the target (tree, water, boulder). CURRENT for Fly/Flash.",
                },
                "fly_destination": {
                    "type": "string",
                    "description": "Required for FLY - destination city name",
                },
            },
            "required": ["hm_move"],
        },
    },
]

BATTLE_TOOLS = [
    {
        "name": "get_pokemon_data",
        "description": "Retrieves complete Pokemon species data from the static knowledge base including base stats, types, evolution, learnset, TM compatibility, and catch rate.",
        "input_schema": {
            "type": "object",
            "properties": {
                "species": {
                    "type": "string",
                    "description": "Pokemon species name (e.g., 'PIKACHU', 'CHARIZARD')",
                },
                "dex_number": {
                    "type": "integer",
                    "description": "National dex number (alternative to species name)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "calculate_type_effectiveness",
        "description": "Calculates the type effectiveness multiplier for an attack type against defender types. Uses Gen 1 type chart including the Ghost/Psychic bug.",
        "input_schema": {
            "type": "object",
            "properties": {
                "attack_type": {
                    "type": "string",
                    "description": "Type of the attacking move (e.g., 'WATER', 'ELECTRIC')",
                },
                "defender_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Types of the defending Pokemon (1 or 2 types)",
                },
            },
            "required": ["attack_type", "defender_types"],
        },
    },
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
                        "types": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["level", "attack", "special", "types"],
                    "description": "Attacking Pokemon's relevant stats",
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
                        "types": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["current_hp", "max_hp", "defense", "special", "types"],
                    "description": "Defending Pokemon's relevant stats",
                },
                "move": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "category": {"type": "string", "enum": ["PHYSICAL", "SPECIAL", "STATUS"]},
                        "power": {"type": "integer"},
                        "accuracy": {"type": "integer"},
                    },
                    "required": ["type", "category", "power"],
                    "description": "Move being used",
                },
                "attacker_stages": {
                    "type": "object",
                    "properties": {
                        "attack": {"type": "integer", "minimum": -6, "maximum": 6},
                        "special": {"type": "integer", "minimum": -6, "maximum": 6},
                    },
                    "default": {"attack": 0, "special": 0},
                    "description": "Attacker's stat stage modifiers",
                },
                "defender_stages": {
                    "type": "object",
                    "properties": {
                        "defense": {"type": "integer", "minimum": -6, "maximum": 6},
                        "special": {"type": "integer", "minimum": -6, "maximum": 6},
                    },
                    "default": {"defense": 0, "special": 0},
                    "description": "Defender's stat stage modifiers",
                },
            },
            "required": ["attacker", "defender", "move"],
        },
    },
    {
        "name": "calculate_catch_rate",
        "description": "Calculates the probability of catching a wild Pokemon using Gen 1 catch rate formula. Accounts for species catch rate, current HP, status conditions, and ball type.",
        "input_schema": {
            "type": "object",
            "properties": {
                "species": {"type": "string", "description": "Pokemon species name"},
                "current_hp": {"type": "integer", "description": "Pokemon's current HP"},
                "max_hp": {"type": "integer", "description": "Pokemon's maximum HP"},
                "status": {
                    "type": "string",
                    "enum": ["SLEEP", "FREEZE", "PARALYSIS", "BURN", "POISON"],
                    "description": "Current status condition (null if none)",
                },
                "ball_type": {
                    "type": "string",
                    "enum": [
                        "POKE_BALL",
                        "GREAT_BALL",
                        "ULTRA_BALL",
                        "MASTER_BALL",
                        "SAFARI_BALL",
                    ],
                    "description": "Type of Poke Ball to use",
                },
            },
            "required": ["species", "current_hp", "max_hp", "ball_type"],
        },
    },
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
                        "moves": {"type": "array", "items": {"type": "object"}},
                    },
                    "description": "Currently active Pokemon",
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
                            "moves": {"type": "array", "items": {"type": "object"}},
                        },
                    },
                    "description": "All party Pokemon",
                },
                "enemy_pokemon": {
                    "type": "object",
                    "properties": {
                        "species": {"type": "string"},
                        "level": {"type": "integer"},
                        "types": {"type": "array", "items": {"type": "string"}},
                        "known_moves": {"type": "array", "items": {"type": "string"}},
                    },
                    "description": "Current enemy Pokemon",
                },
            },
            "required": ["active_pokemon", "party", "enemy_pokemon"],
        },
    },
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
                                    "effect": {"type": "string"},
                                },
                            },
                        },
                    },
                    "description": "Currently active Pokemon with full move data",
                },
                "enemy_pokemon": {
                    "type": "object",
                    "properties": {
                        "species": {"type": "string"},
                        "level": {"type": "integer"},
                        "current_hp_percent": {"type": "number"},
                        "types": {"type": "array", "items": {"type": "string"}},
                        "status": {"type": "string"},
                    },
                    "description": "Enemy Pokemon",
                },
                "battle_context": {
                    "type": "object",
                    "properties": {
                        "is_trainer_battle": {"type": "boolean"},
                        "can_catch": {"type": "boolean"},
                        "want_to_catch": {"type": "boolean"},
                        "enemy_remaining": {"type": "integer"},
                    },
                    "description": "Battle context for decision making",
                },
            },
            "required": ["active_pokemon", "enemy_pokemon"],
        },
    },
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
                        "types": {"type": "array", "items": {"type": "string"}},
                    },
                    "description": "The wild Pokemon encountered",
                },
                "current_party": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "species": {"type": "string"},
                            "types": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                    "description": "Current party composition",
                },
                "available_balls": {
                    "type": "object",
                    "properties": {
                        "POKE_BALL": {"type": "integer"},
                        "GREAT_BALL": {"type": "integer"},
                        "ULTRA_BALL": {"type": "integer"},
                    },
                    "description": "Available Poke Balls",
                },
                "current_objective": {
                    "type": "string",
                    "description": "Current objective (may need specific types)",
                },
                "upcoming_gym": {
                    "type": "string",
                    "description": "Next gym leader to face (for type coverage)",
                },
            },
            "required": ["wild_pokemon", "current_party", "available_balls"],
        },
    },
    {
        "name": "battle_execute_action",
        "description": "Executes a battle action by sending the appropriate controller inputs. Handles move selection, switching, item use, catching attempts, and fleeing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action_type": {
                    "type": "string",
                    "enum": ["MOVE", "SWITCH", "ITEM", "CATCH", "RUN"],
                    "description": "Type of action to perform",
                },
                "move_index": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 3,
                    "description": "For MOVE: Index of move to use (0-3)",
                },
                "switch_to_index": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 5,
                    "description": "For SWITCH: Party index to switch to (0-5)",
                },
                "item": {"type": "string", "description": "For ITEM: Name of item to use"},
                "item_target_index": {
                    "type": "integer",
                    "description": "For ITEM: Party index of Pokemon to use item on",
                },
                "ball_type": {
                    "type": "string",
                    "enum": [
                        "POKE_BALL",
                        "GREAT_BALL",
                        "ULTRA_BALL",
                        "MASTER_BALL",
                        "SAFARI_BALL",
                    ],
                    "description": "For CATCH: Type of ball to throw",
                },
            },
            "required": ["action_type"],
        },
    },
    {
        "name": "get_battle_state",
        "description": "Reads and returns the complete current battle state including both Pokemon, HP, status, stat stages, and turn count.",
        "input_schema": {
            "type": "object",
            "properties": {
                "include_move_details": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include full move data for active Pokemon",
                }
            },
            "required": [],
        },
    },
]

MENU_TOOLS = [
    {
        "name": "navigate_menu",
        "description": "Sends navigation inputs to move through menus. Can move cursor, select options, or cancel/back out of menus.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["move", "select", "cancel"],
                    "description": "Type of navigation action",
                },
                "direction": {
                    "type": "string",
                    "enum": ["UP", "DOWN", "LEFT", "RIGHT"],
                    "description": "For 'move' action: direction to move cursor",
                },
                "count": {
                    "type": "integer",
                    "default": 1,
                    "description": "For 'move' action: number of times to press",
                },
            },
            "required": ["action"],
        },
    },
    {
        "name": "open_start_menu",
        "description": "Opens the start menu from the overworld by pressing the START button.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
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
                    "description": "Filter to specific item category",
                }
            },
            "required": [],
        },
    },
    {
        "name": "use_item",
        "description": "Uses an item from the inventory. Handles healing items, status cures, repels, escape ropes, and teaching TMs/HMs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "item": {"type": "string", "description": "Name of the item to use"},
                "target_pokemon": {
                    "type": "string",
                    "description": "Pokemon to use item on (name or party index). Required for healing items and TMs.",
                },
                "context": {
                    "type": "string",
                    "enum": ["field", "battle"],
                    "default": "field",
                    "description": "Whether using in field or in battle",
                },
                "replace_move": {
                    "type": "string",
                    "description": "For TM/HM teaching when Pokemon has 4 moves - move to forget",
                },
            },
            "required": ["item"],
        },
    },
    {
        "name": "heal_at_pokemon_center",
        "description": "Performs the complete Pokemon Center healing sequence: walking to the nurse, initiating dialogue, confirming heal, waiting for jingle, and dismissing final dialogue.",
        "input_schema": {
            "type": "object",
            "properties": {
                "confirm_location": {
                    "type": "boolean",
                    "default": True,
                    "description": "Verify we're in a Pokemon Center before attempting",
                }
            },
            "required": [],
        },
    },
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
                            "quantity": {"type": "integer", "minimum": 1, "maximum": 99},
                        },
                        "required": ["item", "quantity"],
                    },
                    "description": "List of items and quantities to purchase",
                }
            },
            "required": ["items"],
        },
    },
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
                            "quantity": {"type": "integer", "minimum": 1},
                        },
                        "required": ["item", "quantity"],
                    },
                    "description": "List of items and quantities to sell",
                }
            },
            "required": ["items"],
        },
    },
    {
        "name": "get_shop_inventory",
        "description": "Returns items available for purchase at the current Poke Mart, along with their prices.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "manage_party",
        "description": "Manages party Pokemon (view, reorder, check summary).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["view", "swap", "view_summary", "view_moves"],
                    "description": "Party management action to perform",
                },
                "position_1": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 5,
                    "description": "For 'swap': First position (or pokemon to view)",
                },
                "position_2": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 5,
                    "description": "For 'swap': Second position",
                },
            },
            "required": ["action"],
        },
    },
    {
        "name": "teach_move",
        "description": "Teaches a TM or HM to a Pokemon. Handles the full teaching flow including selecting the item, choosing the Pokemon, and optionally forgetting a move if at 4 moves.",
        "input_schema": {
            "type": "object",
            "properties": {
                "move_item": {
                    "type": "string",
                    "description": "TM or HM identifier (e.g., 'HM01', 'TM28')",
                },
                "target_pokemon": {
                    "type": "string",
                    "description": "Pokemon to teach the move to (species name or party index)",
                },
                "replace_move": {
                    "type": "string",
                    "description": "If Pokemon has 4 moves, which move to forget. Required if at 4 moves.",
                },
            },
            "required": ["move_item", "target_pokemon"],
        },
    },
    {
        "name": "pc_deposit_pokemon",
        "description": "Deposits a Pokemon into the PC storage from the party.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pokemon": {
                    "type": "string",
                    "description": "Pokemon to deposit (species name or party index)",
                },
                "box": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 12,
                    "description": "Box number to deposit into (1-12)",
                },
            },
            "required": ["pokemon"],
        },
    },
    {
        "name": "pc_withdraw_pokemon",
        "description": "Withdraws a Pokemon from PC storage to the party.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pokemon": {
                    "type": "string",
                    "description": "Pokemon to withdraw (species name)",
                },
                "box": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 12,
                    "description": "Box number to withdraw from",
                },
            },
            "required": ["pokemon", "box"],
        },
    },
    {
        "name": "handle_dialogue",
        "description": "Processes dialogue and makes choices when prompted.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["advance", "choose", "cancel"],
                    "description": "Dialogue action to perform",
                },
                "choice": {
                    "type": "string",
                    "description": "For 'choose' action: the choice to select (e.g., 'YES', 'NO', or choice text)",
                },
                "choice_index": {
                    "type": "integer",
                    "description": "For 'choose' action: alternative - index of choice (0-based)",
                },
            },
            "required": ["action"],
        },
    },
    {
        "name": "get_party_status",
        "description": "Returns detailed status of all party Pokemon including HP, status conditions, and PP.",
        "input_schema": {
            "type": "object",
            "properties": {
                "include_moves": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include full move details with PP",
                }
            },
            "required": [],
        },
    },
]


def get_tools_for_agent(agent_type: str) -> list[dict[str, object]]:
    """Get tool definitions for a specific agent type."""
    tools: dict[str, list[dict[str, object]]] = {
        "ORCHESTRATOR": ORCHESTRATOR_TOOLS,  # type: ignore[dict-item]
        "NAVIGATION": NAVIGATION_TOOLS,  # type: ignore[dict-item]
        "BATTLE": BATTLE_TOOLS,  # type: ignore[dict-item]
        "MENU": MENU_TOOLS,  # type: ignore[dict-item]
    }
    return tools.get(agent_type, [])
