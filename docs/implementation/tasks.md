# Implementation Tasks

## Legend
- ⬜ Not Started
- 🔄 In Progress
- ✅ Completed
- ❌ Blocked

---

## Phase 1: Knowledge Base ✅

### Setup
- ✅ Clone pret/pokered to `external/pokered`
- ✅ Create `data/` directory structure
- ✅ Create `scripts/` directory for extractors
- ✅ Create `src/knowledge/` package

### Core Extractors
- ✅ `scripts/extract_types.py` → `data/type_chart.json` (15 types, 82 matchups)
- ✅ `scripts/extract_moves.py` → `data/moves.json` (165 moves, 50 TMs, 5 HMs)
- ✅ `scripts/extract_pokemon.py` → `data/pokemon.json` (151 Pokemon)
- ✅ `scripts/extract_items.py` → `data/items.json` (81 items)

### Navigation Extractors
- ✅ `scripts/extract_maps.py` → `data/maps/*.json` (223 maps)
- ✅ `scripts/extract_trainers.py` → `data/trainers.json` (391 trainers, 38 bosses)
- ✅ `scripts/extract_wild.py` → `data/wild_encounters.json` (56 locations)
- ✅ `scripts/extract_shops.py` → `data/shops.json` (14 shops)

### Progression Data
- ✅ `data/hm_requirements.json` (manual - HM badge requirements)
- ✅ `data/story_progression.json` (manual - 24 milestones)

### Accessor Classes
- ✅ `src/knowledge/base.py` - KnowledgeBase interface
- ✅ `src/knowledge/type_chart.py`
- ✅ `src/knowledge/moves.py`
- ✅ `src/knowledge/pokemon.py`
- ✅ `src/knowledge/items.py`
- ✅ `src/knowledge/maps.py`
- ✅ `src/knowledge/trainers.py`
- ✅ `src/knowledge/shops.py`
- ✅ `src/knowledge/wild_encounters.py`
- ✅ `src/knowledge/hm_requirements.py`
- ✅ `src/knowledge/story_progression.py`

### Validation & Scripts
- ✅ `scripts/validate_data.py` (all checks pass)
- ✅ `scripts/extract_all.py` (master extraction pipeline)
- ⬜ `tests/test_knowledge/` unit tests

---

## Phase 2: Agent Framework ✅

### Types & State
- ✅ `src/agent/types.py` - Enums and dataclasses (GameMode, BattleType, Position, Stats, Move, Pokemon, BattleState, Objective, AgentResult)
- ✅ `src/agent/state.py` - GameState class with objective management
- ✅ `src/agent/objective.py` - ObjectiveStack + helper functions

### Base Infrastructure
- ✅ `src/agent/base.py` - BaseAgent abstract class with Claude API integration
- ✅ `src/agent/registry.py` - AgentRegistry with routing

### Tool Definitions
- ✅ `src/tools/__init__.py` - Module exports
- ✅ `src/tools/definitions.py` - All 38 tool schemas (7 orchestrator + 8 navigation + 9 battle + 14 menu)

### Package Setup
- ✅ `src/agent/__init__.py` with exports
- ✅ `tests/test_agent/test_types.py` (14 tests)
- ✅ `tests/test_agent/test_state.py` (15 tests)
- ✅ `tests/test_agent/test_objective.py` (11 tests)
- ✅ `tests/test_agent/test_registry.py` (12 tests)

---

## Phase 3: Agents ✅

### Orchestrator Agent
- ✅ `src/agent/orchestrator.py`
- ✅ Tool: `detect_game_mode`
- ✅ Tool: `get_current_objective`
- ✅ Tool: `get_next_milestone`
- ✅ Tool: `check_requirements`
- ✅ Tool: `route_to_agent`
- ✅ Tool: `update_game_state`
- ✅ Tool: `manage_objective_stack`

### Navigation Agent
- ✅ `src/agent/navigation.py`
- ✅ Tool: `get_current_position`
- ✅ Tool: `get_map_data`
- ✅ Tool: `find_path` (implemented with A* pathfinding)
- ✅ Tool: `get_interactables`
- ✅ Tool: `execute_movement`
- ✅ Tool: `check_route_accessibility`
- ✅ Tool: `get_hidden_items`
- ✅ Tool: `use_hm_in_field`

### Battle Agent
- ✅ `src/agent/battle.py`
- ✅ Tool: `get_pokemon_data`
- ✅ Tool: `calculate_type_effectiveness`
- ✅ Tool: `estimate_damage`
- ✅ Tool: `calculate_catch_rate`
- ✅ Tool: `evaluate_switch_options`
- ✅ Tool: `get_best_move`
- ✅ Tool: `should_catch_pokemon`
- ✅ Tool: `battle_execute_action`
- ✅ Tool: `get_battle_state`
- ✅ Opus escalation for boss battles

### Menu Agent
- ✅ `src/agent/menu.py`
- ✅ Tool: `navigate_menu`
- ✅ Tool: `open_start_menu`
- ✅ Tool: `get_inventory`
- ✅ Tool: `use_item`
- ✅ Tool: `heal_at_pokemon_center`
- ✅ Tool: `shop_buy`
- ✅ Tool: `shop_sell`
- ✅ Tool: `get_shop_inventory`
- ✅ Tool: `manage_party`
- ✅ Tool: `teach_move`
- ✅ Tool: `pc_deposit_pokemon`
- ✅ Tool: `pc_withdraw_pokemon`
- ✅ Tool: `handle_dialogue`
- ✅ Tool: `get_party_status`

### Testing
- ✅ `tests/test_agent/test_orchestrator.py` (22 tests)
- ✅ `tests/test_agent/test_navigation.py` (17 tests)
- ✅ `tests/test_agent/test_battle.py` (19 tests)
- ✅ `tests/test_agent/test_menu.py` (24 tests)

---

## Phase 4: Pathfinding ✅

### Data Extraction
- ✅ `scripts/extract_collision.py` - Extract collision data from pokered
- ✅ Updated `data/maps/*.json` with width, height, tileset, connections, walkable tiles (223 maps)

### Core Algorithm
- ✅ `src/pathfinding/__init__.py` - Module exports + `find_path()` convenience function
- ✅ `src/pathfinding/tiles.py` - TileType enum, TileWeights dataclass, weight calculations
- ✅ `src/pathfinding/graph.py` - Node, Edge, MapGraph class
- ✅ `src/pathfinding/astar.py` - A* implementation with PathResult

### Advanced Features
- ✅ `src/pathfinding/trainer_vision.py` - Trainer vision cone calculations
- ✅ `src/pathfinding/cross_map.py` - CrossMapRouter for multi-map paths

### Integration
- ✅ Updated `src/agent/navigation.py` - `_find_path` uses real CrossMapRouter

### Testing
- ✅ `tests/test_pathfinding/test_tiles.py` (14 tests)
- ✅ `tests/test_pathfinding/test_astar.py` (20 tests)
- ✅ `tests/test_pathfinding/test_cross_map.py` (17 tests)
- ✅ `tests/test_pathfinding/test_trainer.py` (18 tests)

---

## Phase 5: Integration

### Game Loop
- ⬜ Update `src/main.py` with Orchestrator pattern
- ⬜ Add objective initialization
- ⬜ Implement agent handoff

### State Reader
- ⬜ Enhance `src/emulator/state_reader.py`
- ⬜ Add enemy Pokemon reading
- ⬜ Add menu/dialogue detection
- ⬜ Add move/PP reading

### Error Handling
- ⬜ `src/recovery.py` - Failure diagnosis
- ⬜ Checkpoint system
- ⬜ Auto-recovery logic

### Configuration
- ⬜ Update `src/config.py` with new settings
- ⬜ `src/logging_config.py`

### Testing
- ⬜ `tests/test_integration/test_game_loop.py`
- ⬜ `tests/test_integration/test_full_cycle.py`
- ⬜ End-to-end test with save states

---

## Milestones

### M1: Data Ready ✅
- ✅ All knowledge bases extracted and validated

### M2: Framework Ready ✅
- ✅ Agent framework complete, agents can be instantiated

### M3: Agents Working ✅
- ✅ All agents implement their tools (138 tests passing)

### M4: Navigation Working ✅
- ✅ A* pathfinding integrated with Navigation agent

### M5: Full Integration
- ⬜ Complete game loop running with all agents

### M6: First Gym
- ⬜ Agent can defeat Brock

---

## Current Focus

**Active Tasks:**
(none yet)

**Completed:**
- Phase 4: Pathfinding ✅ (69 new tests, 207 total tests passing)

**Next Up:**
1. Start Phase 5: Integration (connect all agents to game loop)

---

## Blockers

(none currently)

---

## Notes

- Update this file as tasks are completed
- Mark tasks with assignee when work begins
- Add blockers section if issues arise
