# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI agent that plays Pokemon Red using Claude. The agent controls a PyBoy Game Boy emulator, reads game state from memory, and makes decisions via Claude's tool calling API.

## Commands

```bash
# Install dependencies
poetry install

# Run the agent
poetry run python -m src.main
# or
poetry run pokemon-agent

# Linting
poetry run ruff check src
poetry run ruff format src

# Type checking
poetry run mypy src

# Run tests
poetry run pytest
poetry run pytest tests/test_file.py::test_name  # single test
```

## Architecture

### Current MVP (Implemented)

```
src/main.py          → Game loop: read state → call Claude → execute action → repeat
src/config.py        → Pydantic settings loaded from .env
src/emulator/
  interface.py       → PyBoy wrapper (button presses, frame control, memory access)
  state_reader.py    → Extracts GameState from memory addresses (position, party, mode, badges)
src/agent/
  simple_agent.py    → Single Claude agent using tool calling (press_button, move_direction, wait)
```

**Data Flow:**
1. `StateReader` reads memory addresses to build `GameState` dataclass
2. `SimpleAgent.get_action()` formats state and calls Claude API with tools
3. Claude returns a tool call (e.g., `press_button` with `button: "A"`)
4. `GameLoop._execute_action()` translates to `EmulatorInterface` method calls
5. Emulator advances frames, loop repeats

### Target Architecture (Planned in docs/)

Multi-agent system with specialized agents:
- **Orchestrator** (Sonnet): Detects game mode, manages objectives, routes to specialists
- **Navigation** (Haiku): Pathfinding, movement, NPC interaction
- **Battle** (Sonnet/Opus): Move selection, catching, fleeing
- **Menu** (Haiku): Healing, shopping, inventory management

See `docs/00_overview.md` for the full architecture and `docs/pokemon_red_agent_technical_design.md` for implementation details.

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
