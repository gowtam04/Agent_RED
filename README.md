# Pokemon Red AI Agent

An autonomous AI agent that plays Pokemon Red using Claude. The agent controls a PyBoy Game Boy emulator, reads game state from memory, and makes strategic decisions via Claude's tool calling API.

## Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Multi-Agent System](#multi-agent-system)
- [Data Flow](#data-flow)
- [Knowledge Base](#knowledge-base)
- [Pathfinding](#pathfinding)
- [Web Dashboard](#web-dashboard)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running](#running)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Development](#development)
- [License](#license)

## Features

- **Multi-Agent Architecture**: Specialized agents for navigation, battle, and menu handling
- **PyBoy Integration**: Runs Pokemon Red in a visible emulator window or headless mode
- **Memory Reading**: Extracts comprehensive game state (position, party, battles, badges, inventory) from memory
- **Claude-Powered Decisions**: Uses Claude Haiku, Sonnet, and Opus for different complexity levels
- **A* Pathfinding**: Cross-map navigation with trainer avoidance and grass minimization
- **Knowledge Base**: Complete Pokemon Red data extracted from the pokered disassembly
- **Web Dashboard**: Real-time React dashboard with WebSocket streaming
- **Auto-Checkpoints**: Periodic save states for recovery
- **Opus Escalation**: Automatically uses Claude Opus for boss battles (Gym Leaders, Elite Four)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        Web Dashboard (React)                         │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────────────┐   │    │
│  │  │  Game    │ │  Agent   │ │   Party &    │ │   Event Log &    │   │    │
│  │  │  Screen  │ │ Thoughts │ │   Inventory  │ │   Statistics     │   │    │
│  │  │ (Live)   │ │  Panel   │ │    Status    │ │                  │   │    │
│  │  └──────────┘ └──────────┘ └──────────────┘ └──────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                     ▲                                        │
│                                     │ WebSocket                              │
└─────────────────────────────────────┼────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────┼────────────────────────────────────────┐
│                              BACKEND SERVER                                  │
│  ┌──────────────────────────────────┴───────────────────────────────────┐   │
│  │                      FastAPI Application                              │   │
│  │  • WebSocket endpoint (/ws/game-state)                               │   │
│  │  • REST endpoints (/api/*)                                           │   │
│  │  • Static file serving                                               │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                     │                                        │
│  ┌──────────────────────────────────┴───────────────────────────────────┐   │
│  │                      Game Engine (Async Core)                         │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │ Orchestrator│  │ Navigation  │  │   Battle    │  │    Menu     │ │   │
│  │  │    Agent    │  │    Agent    │  │    Agent    │  │    Agent    │ │   │
│  │  │  (Sonnet)   │  │   (Haiku)   │  │(Sonnet/Opus)│  │   (Haiku)   │ │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘ │   │
│  │         └────────────────┴────────────────┴────────────────┘        │   │
│  │                                  │                                   │   │
│  │                          ┌──────┴──────┐                            │   │
│  │                          │  GameState  │                            │   │
│  │                          │   Manager   │                            │   │
│  │                          └──────┬──────┘                            │   │
│  └─────────────────────────────────┼────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────┴────────────────────────────────────┐   │
│  │                      Emulator Interface Layer                         │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │   │
│  │  │    PyBoy        │  │  State Reader   │  │   Input Controller  │  │   │
│  │  │   Instance      │  │  (Memory →      │  │   (Commands →       │  │   │
│  │  │                 │  │   GameState)    │  │    Button Presses)  │  │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │                         Data Layer                                    │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │  Knowledge  │  │   Event     │  │   Save      │  │   Config    │ │   │
│  │  │    Base     │  │    Log      │  │   States    │  │    Store    │ │   │
│  │  │   (JSON)    │  │  (SQLite)   │  │  (Binary)   │  │   (YAML)    │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTPS
                                      ▼
                    ┌──────────────────────────────────┐
                    │        Anthropic API             │
                    │  Claude Haiku / Sonnet / Opus   │
                    └──────────────────────────────────┘
```

## Multi-Agent System

The AI uses a hierarchical multi-agent architecture where an orchestrator routes to specialized agents based on game context.

```
                    ┌─────────────────────────┐
                    │    OrchestratorAgent    │
                    │       (Sonnet)          │
                    │                         │
                    │ • Mode detection        │
                    │ • Objective management  │
                    │ • Agent routing         │
                    │ • Health monitoring     │
                    └───────────┬─────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            │                   │                   │
            ▼                   ▼                   ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│ NavigationAgent   │ │   BattleAgent     │ │    MenuAgent      │
│    (Haiku)        │ │  (Sonnet/Opus)    │ │     (Haiku)       │
│                   │ │                   │ │                   │
│ • A* pathfinding  │ │ • Type analysis   │ │ • Pokemon Center  │
│ • Trainer avoid   │ │ • Move selection  │ │ • Item management │
│ • HM usage        │ │ • Switch logic    │ │ • Shopping        │
│ • Grass minimize  │ │ • Catch decisions │ │ • PC operations   │
└───────────────────┘ └───────────────────┘ └───────────────────┘
```

### Agent Details

| Agent | Model | Tools | Purpose |
|-------|-------|-------|---------|
| **OrchestratorAgent** | Sonnet | 7 | Central coordination, mode detection, objective management, agent routing |
| **NavigationAgent** | Haiku | 8 | Movement, A* pathfinding, HM usage (Cut, Surf, Strength), trainer avoidance |
| **BattleAgent** | Sonnet/Opus | 9 | Type effectiveness, damage calculation, move selection, catch decisions |
| **MenuAgent** | Haiku | 14 | Pokemon Center healing, shopping, party management, PC operations |

**Opus Escalation**: BattleAgent automatically switches to Claude Opus for gym leaders, Elite Four, and Champion battles for more strategic thinking.

### Tool Distribution

- **Orchestrator Tools (7)**: `detect_game_mode`, `get_current_objective`, `get_next_milestone`, `check_requirements`, `route_to_agent`, `update_game_state`, `manage_objective_stack`
- **Navigation Tools (8)**: `get_current_position`, `get_map_data`, `find_path`, `get_interactables`, `execute_movement`, `check_route_accessibility`, `get_hidden_items`, `use_hm_in_field`
- **Battle Tools (9)**: `get_pokemon_data`, `calculate_type_effectiveness`, `estimate_damage`, `calculate_catch_rate`, `evaluate_switch_options`, `get_best_move`, `should_catch_pokemon`, `battle_execute_action`, `get_battle_state`
- **Menu Tools (14)**: `navigate_menu`, `open_start_menu`, `get_inventory`, `use_item`, `heal_at_pokemon_center`, `shop_buy`, `shop_sell`, `get_shop_inventory`, `manage_party`, `teach_move`, `pc_deposit_pokemon`, `pc_withdraw_pokemon`, `handle_dialogue`, `get_party_status`

## Data Flow

```
EmulatorInterface (PyBoy)
        │
        ▼
StateReader (memory addresses) ──▶ EmulatorGameState (raw data)
        │
        ▼
StateConverter ──▶ AgentGameState (enriched with types, moves, stats)
        │
        ▼
Orchestrator (Sonnet) ──▶ routes by game mode
        │
    ┌───┴────────────┬───────────────┐
    ▼                ▼               ▼
Navigation        Battle           Menu
 (Haiku)      (Sonnet/Opus)      (Haiku)
        │
        ▼
AgentResult ──▶ Button/Movement actions
        │
        ▼
EmulatorInterface (execute)
```

### Two GameState Types

| Type | Location | Purpose |
|------|----------|---------|
| `EmulatorGameState` | `src/emulator/state_reader.py` | Raw data from memory (int map_id, minimal Pokemon info) |
| `AgentGameState` | `src/agent/state.py` | Semantic state for agents (str map names, full Pokemon data, objectives) |

## Knowledge Base

Game data extracted from the [pret/pokered](https://github.com/pret/pokered) disassembly into JSON files.

| Data | File | Contents |
|------|------|----------|
| **Type Chart** | `type_chart.json` | 15 types, 82 matchups (Gen 1 Ghost/Psychic bug preserved) |
| **Moves** | `moves.json` | 165 moves with power, accuracy, PP, TM/HM mappings |
| **Pokemon** | `pokemon.json` | 151 Pokemon with base stats, types, evolutions, learnsets |
| **Items** | `items.json` | 81 items with prices and categories |
| **Maps** | `maps/*.json` | 223 maps with collision data, warps, trainers, items |
| **Trainers** | `trainers.json` | 391 trainer teams (38 bosses flagged) |
| **Wild Encounters** | `wild_encounters.json` | 56 locations with encounter tables |
| **Shops** | `shops.json` | 14 shop inventories |
| **HM Requirements** | `hm_requirements.json` | Badge requirements for field HMs |
| **Story Progression** | `story_progression.json` | 24 story milestones |

### Usage Example

```python
from src.knowledge import TypeChart, PokemonData, MoveData

# Type effectiveness
types = TypeChart()
effectiveness = types.get_effectiveness("FIRE", "GRASS")  # 2.0 (super effective)

# Pokemon data
pokemon = PokemonData()
pikachu = pokemon.get("PIKACHU")  # {stats, types, learnset, evolution}

# Move data
moves = MoveData()
thunder = moves.get("THUNDERBOLT")  # {type, power, accuracy, pp}
```

## Pathfinding

The `src/pathfinding/` module provides A* navigation with cross-map routing.

```python
from src.pathfinding import find_path, CrossMapRouter, TileWeights

# High-level convenience function
result = find_path(
    from_map="PALLETTOWN", from_x=5, from_y=5,
    to_map="VIRIDIANCITY",
    hms_available=["CUT"],
    avoid_grass=True,
    avoid_trainers=True,
)

if result.success:
    for map_id, moves in result.segments:
        print(f"{map_id}: {moves}")  # ["UP", "UP", "RIGHT", ...]
```

### Pathfinding Components

| Component | File | Purpose |
|-----------|------|---------|
| **A* Algorithm** | `astar.py` | Core pathfinding with configurable tile weights |
| **MapGraph** | `graph.py` | Loads collision data from map JSON files |
| **TileType/Weights** | `tiles.py` | Tile classifications, cost configuration |
| **TrainerVision** | `trainer_vision.py` | Calculates trainer line-of-sight zones |
| **CrossMapRouter** | `cross_map.py` | BFS for map sequence, then A* per segment |

### Tile Weights

```python
TileWeights(
    grass=5.0,          # Discourage tall grass (encounters)
    trainer_adjacent=100.0,  # Heavily avoid trainer sight lines
    ledge=2.0,          # One-way jumps have slight penalty
)
```

## Web Dashboard

Real-time React dashboard for monitoring the agent.

```
┌────────────────────────────────────────────────────────────────────┐
│  Pokemon Red AI Agent                              [▶ Play] [⏸ Pause]│
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────┐  ┌──────────────────────────────────────┐ │
│  │                     │  │ Agent Thoughts                        │ │
│  │    Game Screen      │  │                                       │ │
│  │     (160x144)       │  │ "Heading to Pewter City to challenge │ │
│  │                     │  │  Brock. Party is healthy at 85% HP.  │ │
│  │                     │  │  Using Route 2 to avoid trainers."   │ │
│  └─────────────────────┘  └──────────────────────────────────────┘ │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Party: Pikachu L14 ████████ | Pidgey L12 ██████░░           │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────┐  ┌──────────────────────────────────────┐ │
│  │ Objectives          │  │ Event Log                            │ │
│  │ ☑ Get Boulder Badge │  │ 10:23:45 Defeated Bug Catcher        │ │
│  │ ☐ Beat Misty        │  │ 10:22:30 Entered Viridian Forest     │ │
│  │ ☐ Get HM01 Cut      │  │ 10:21:15 Healed at Pokemon Center    │ │
│  └─────────────────────┘  └──────────────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────┤
│ Badges: 1 | Money: $3420 | Location: Route 2 | Agent: Navigation  │
└────────────────────────────────────────────────────────────────────┘
```

### Dashboard Components

| Component | Description |
|-----------|-------------|
| **GameScreen** | Live emulator display (160x144 scaled up) |
| **AgentThoughts** | Current agent reasoning and decisions |
| **PartyStatus** | HP bars and status for all party Pokemon |
| **Objectives** | Current goal stack with completion status |
| **EventLog** | Timestamped history of actions and events |
| **StatsBar** | Badges, money, location, active agent, playtime |
| **Controls** | Play/Pause, speed control, save/load state |

## Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/) for dependency management
- Node.js 18+ (for dashboard)
- SDL2 library (for PyBoy display)
- Anthropic API key
- Pokemon Red ROM file (you must provide your own legally obtained copy)

### Installing SDL2

**macOS:**
```bash
brew install sdl2
```

**Ubuntu/Debian:**
```bash
sudo apt-get install libsdl2-dev
```

**Windows:**
SDL2 is typically bundled with PyBoy on Windows.

## Setup

1. **Clone and enter the project:**
   ```bash
   cd Project_RED
   ```

2. **Install Python dependencies:**
   ```bash
   poetry install
   ```

3. **Install frontend dependencies and build:**
   ```bash
   cd ui && npm install && npm run build && cd ..
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```

5. **Add your ROM file:**
   ```bash
   cp /path/to/pokemon_red.gb roms/pokemon_red.gb
   ```

## Running

### Console Mode (No Dashboard)

```bash
poetry run python -m src.main
# or
poetry run pokemon-agent
```

### Web Dashboard Mode

```bash
poetry run pokemon-dashboard
# Open browser to http://localhost:8000
```

### Frontend Development (Hot Reload)

```bash
cd ui && npm run dev
```

## Configuration

Edit `.env` to customize behavior:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (required) | Your Anthropic API key |
| `ROM_PATH` | `roms/pokemon_red.gb` | Path to ROM file |
| `EMULATION_SPEED` | `1` | Speed multiplier (0=max, 1=normal) |
| `HEADLESS` | `false` | Run without display window |
| `AGENT_MODEL` | `claude-sonnet-4-5-20250929` | Default Claude model |
| `INITIAL_OBJECTIVE` | `become_champion` | Starting goal: `become_champion`, `defeat_gym`, `catch_pokemon` |
| `INITIAL_OBJECTIVE_TARGET` | `Elite Four` | Target for objective |
| `USE_OPUS_FOR_BOSSES` | `true` | Auto-escalate to Opus for boss battles |
| `CHECKPOINT_INTERVAL_SECONDS` | `300` | Auto-save interval |
| `LOG_LEVEL` | `INFO` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_TO_FILE` | `true` | Write logs to `logs/` directory |

## Project Structure

```
Project_RED/
├── data/                       # Knowledge base JSON files
│   ├── maps/                   # 223 map files with collision data
│   ├── type_chart.json         # Type effectiveness matrix
│   ├── moves.json              # Move data
│   ├── pokemon.json            # Pokemon data
│   ├── items.json              # Item data
│   ├── trainers.json           # Trainer teams
│   ├── wild_encounters.json    # Encounter tables
│   ├── shops.json              # Shop inventories
│   ├── hm_requirements.json    # HM badge requirements
│   └── story_progression.json  # Story milestones
│
├── docs/                       # Documentation
│   └── pokemon_red_agent_technical_design.md
│
├── roms/                       # ROM files (gitignored)
│
├── src/
│   ├── agent/                  # Multi-agent system
│   │   ├── orchestrator.py     # Central coordinator (Sonnet)
│   │   ├── navigation.py       # Movement agent (Haiku)
│   │   ├── battle.py           # Battle agent (Sonnet/Opus)
│   │   ├── menu.py             # Menu agent (Haiku)
│   │   ├── base.py             # Base agent class
│   │   ├── registry.py         # Agent registration
│   │   ├── state.py            # AgentGameState
│   │   ├── objective.py        # Objective management
│   │   └── types.py            # Type definitions
│   │
│   ├── api/                    # FastAPI backend
│   │   ├── main.py             # Endpoints and WebSocket
│   │   ├── models.py           # Pydantic models
│   │   └── broadcaster.py      # WebSocket state broadcasting
│   │
│   ├── emulator/               # PyBoy integration
│   │   ├── interface.py        # PyBoy wrapper
│   │   ├── state_reader.py     # Memory reading
│   │   └── state_converter.py  # Raw → enriched state
│   │
│   ├── engine/                 # Game loop
│   │   └── game_engine.py      # Main game loop
│   │
│   ├── knowledge/              # Data accessors
│   │   ├── type_chart.py       # Type effectiveness
│   │   ├── moves.py            # Move data
│   │   ├── pokemon.py          # Pokemon data
│   │   ├── items.py            # Item data
│   │   ├── maps.py             # Map data
│   │   ├── trainers.py         # Trainer data
│   │   ├── wild_encounters.py  # Encounter data
│   │   ├── shops.py            # Shop data
│   │   ├── hm_requirements.py  # HM requirements
│   │   └── story_progression.py # Story milestones
│   │
│   ├── pathfinding/            # A* navigation
│   │   ├── astar.py            # A* algorithm
│   │   ├── cross_map.py        # Multi-map routing
│   │   ├── graph.py            # Map graph
│   │   ├── tiles.py            # Tile types and weights
│   │   └── trainer_vision.py   # Trainer LoS calculation
│   │
│   ├── tools/                  # Agent tool definitions
│   │   └── definitions.py      # 38 tools across all agents
│   │
│   ├── config.py               # Configuration management
│   ├── main.py                 # Console entry point
│   ├── dashboard.py            # Dashboard entry point
│   ├── recovery.py             # Failure recovery
│   └── logging_config.py       # Structured logging
│
├── ui/                         # React dashboard
│   ├── src/
│   │   ├── components/         # React components
│   │   │   ├── GameScreen/     # Live game display
│   │   │   ├── AgentThoughts/  # Agent reasoning panel
│   │   │   ├── PartyStatus/    # Party HP bars
│   │   │   ├── Objectives/     # Goal tracking
│   │   │   ├── EventLog/       # Action history
│   │   │   ├── Controls/       # Play/pause controls
│   │   │   └── Statistics/     # Stats footer
│   │   ├── hooks/              # Custom hooks
│   │   ├── stores/             # Zustand state
│   │   └── types/              # TypeScript types
│   ├── package.json
│   └── vite.config.ts
│
├── scripts/                    # Utility scripts
│   ├── extract_all.py          # Extract data from pokered
│   └── validate_data.py        # Validate extracted data
│
├── tests/                      # Test suite
├── pyproject.toml              # Python dependencies
├── .env.example                # Environment template
└── README.md
```

## Development

### Commands

```bash
# Install dependencies
poetry install

# Run console agent
poetry run python -m src.main

# Run web dashboard
poetry run pokemon-dashboard

# Build frontend
cd ui && npm install && npm run build

# Frontend dev server (hot reload)
cd ui && npm run dev

# Linting and formatting
poetry run ruff check src
poetry run ruff format src

# Type checking
poetry run mypy src

# Run tests
poetry run pytest
poetry run pytest tests/test_file.py::test_name  # Single test

# Re-extract game data from pokered disassembly
poetry run python scripts/extract_all.py

# Validate extracted data
poetry run python scripts/validate_data.py
```

### Key Memory Addresses (Pokemon Red US)

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

## License

This project is for educational purposes. You must provide your own legally obtained ROM file.
