# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

An AI agent that plays Pokemon Red using Claude. The agent controls a PyBoy Game Boy emulator, reads game state from memory, and makes decisions via Claude's tool calling API.

## Commands

```bash
# Install dependencies
poetry install

# Run the agent
poetry run python -m src.main
# or
poetry run pokemon-agent

# Linting and formatting
poetry run ruff check src
poetry run ruff format src

# Type checking
poetry run mypy src

# Run tests
poetry run pytest
poetry run pytest tests/test_file.py::test_name  # single test

# Re-extract all game data from pokered disassembly
poetry run python scripts/extract_all.py

# Validate extracted data
poetry run python scripts/validate_data.py
```

## Architecture

### Data Flow (MVP)

```
StateReader (memory) → GameState → SimpleAgent (Claude API) → Action → EmulatorInterface (PyBoy)
```

1. `StateReader` reads memory addresses to build `GameState` dataclass
2. `SimpleAgent.get_action()` formats state and calls Claude API with tools
3. Claude returns a tool call (e.g., `press_button` with `button: "A"`)
4. `GameLoop._execute_action()` translates to `EmulatorInterface` method calls
5. Emulator advances frames, loop repeats

### Multi-Agent System (In Progress)

```
Orchestrator (Sonnet) → detects mode, manages objectives
    ├── Navigation (Haiku) → pathfinding, movement
    ├── Battle (Sonnet/Opus) → move selection, catching
    └── Menu (Haiku) → healing, shopping, inventory
```

**Framework (Complete):** Types, GameState, BaseAgent, AgentRegistry, ObjectiveStack, 38 tool definitions in `src/agent/` and `src/tools/`.

**Agents (Phase 3):** Specialized agent implementations pending.

See `docs/implementation/plan.md` for phase status and `docs/implementation/tasks.md` for task tracking.

### Agent Framework Types

```python
from src.agent import (
    # Types
    GameMode, BattleType, Direction, Position, Stats, Move, Pokemon,
    BattleState, Objective, AgentResult,
    # Classes
    GameState, BaseAgent, AgentRegistry, ObjectiveStack,
)

# Game state with objective management
state = GameState()
state.push_objective(Objective(type="defeat_gym", target="Brock"))

# Agent routing by game mode
registry = AgentRegistry()
agent_type = registry.route_by_mode("BATTLE")  # Returns "BATTLE"
```

### Tool Definitions

38 tools defined in `src/tools/definitions.py`:
- `ORCHESTRATOR_TOOLS` (7): detect_game_mode, get_current_objective, route_to_agent, etc.
- `NAVIGATION_TOOLS` (8): get_current_position, find_path, execute_movement, etc.
- `BATTLE_TOOLS` (9): calculate_type_effectiveness, estimate_damage, get_best_move, etc.
- `MENU_TOOLS` (14): heal_at_pokemon_center, shop_buy, use_item, etc.

## Knowledge Base

Game data is extracted from the `pret/pokered` disassembly repository into JSON files in `data/`, with Python accessor classes in `src/knowledge/`.

| Accessor Class | Data File | Contents |
|----------------|-----------|----------|
| `TypeChart` | `type_chart.json` | 15 types, 82 matchups (Gen 1 Ghost/Psychic bug preserved) |
| `MoveData` | `moves.json` | 165 moves with TM/HM mappings |
| `PokemonData` | `pokemon.json` | 151 Pokemon with stats, evolutions, learnsets |
| `ItemData` | `items.json` | 81 items with prices and categories |
| `MapData` | `maps/*.json` | 223 maps with warps, trainers, items |
| `TrainerData` | `trainers.json` | 391 trainer teams (38 bosses) |
| `WildEncounters` | `wild_encounters.json` | 56 locations with encounter tables |
| `ShopData` | `shops.json` | 14 shop inventories |
| `HMRequirements` | `hm_requirements.json` | HM badge requirements |
| `StoryProgression` | `story_progression.json` | 24 story milestones |

Usage:
```python
from src.knowledge import TypeChart, PokemonData, MoveData

types = TypeChart()
effectiveness = types.get_effectiveness("FIRE", "GRASS")  # 2.0

pokemon = PokemonData()
pikachu = pokemon.get("PIKACHU")  # stats, types, learnset

moves = MoveData()
thunder = moves.get("THUNDERBOLT")  # type, power, accuracy, PP
```

## Key Memory Addresses (Pokemon Red US)

```python
MAP_ID = 0xD35E           # Current map
PLAYER_X = 0xD362         # X position
PLAYER_Y = 0xD361         # Y position
PLAYER_DIRECTION = 0xC109 # Facing direction
BATTLE_TYPE = 0xD057      # 0=none, 1=wild, 2=trainer
PARTY_COUNT = 0xD163      # Number of Pokemon
PARTY_SPECIES = 0xD164    # Species IDs (6 bytes)
BADGES = 0xD356           # Bit flags for 8 badges
MONEY = 0xD347            # BCD encoded (3 bytes)
```

## Environment Variables

Required in `.env`:
- `ANTHROPIC_API_KEY` - Claude API key

Optional:
- `ROM_PATH` - Path to pokemon_red.gb (default: `roms/pokemon_red.gb`)
- `EMULATION_SPEED` - 0=unlimited, 1=normal (default: 1)
- `HEADLESS` - Run without display (default: false)
- `AGENT_MODEL` - Claude model (default: claude-sonnet-4-5-20250929)

## ROM File

Place your legally obtained Pokemon Red ROM at `roms/pokemon_red.gb`. ROM files are gitignored.
