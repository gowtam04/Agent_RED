# Pokemon Red AI Agent - Technical Design Document

## Document Information

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Status | Draft |
| Last Updated | December 2024 |
| Author | AI Architecture Team |

---

## Table of Contents

1. [Overview](#1-overview)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Component Design](#4-component-design)
5. [Data Flow](#5-data-flow)
6. [User Interface](#6-user-interface)
7. [Deployment Architecture](#7-deployment-architecture)
8. [Development Setup](#8-development-setup)
9. [Project Structure](#9-project-structure)
10. [API Specifications](#10-api-specifications)
11. [Configuration](#11-configuration)
12. [Testing Strategy](#12-testing-strategy)
13. [Performance Considerations](#13-performance-considerations)
14. [Future Enhancements](#14-future-enhancements)

---

## 1. Overview

### 1.1 Purpose

This document defines the technical architecture and technology stack for the Pokemon Red AI Agent system—an autonomous AI that plays and completes Pokemon Red using Claude models for decision-making.

### 1.2 Goals

| Goal | Description |
|------|-------------|
| **Watchable** | Real-time UI showing game screen, agent decisions, and system state |
| **Debuggable** | Full logging, replay capability, and state inspection |
| **Modular** | Clean separation between emulation, agents, and UI |
| **Scalable** | Support for multiple concurrent runs (for testing/comparison) |
| **Maintainable** | Modern Python practices, typed, tested |

### 1.3 Non-Goals (v1)

- Mobile support
- Multi-user authentication
- Cloud deployment (local-first)
- Real-time multiplayer viewing
- Training/learning capabilities

### 1.4 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Emulator | PyBoy | Native Python, excellent API, sufficient accuracy |
| Backend Framework | FastAPI | Async-native, WebSocket support, auto-docs |
| Frontend Framework | React + TypeScript | Component-based, strong typing, large ecosystem |
| State Streaming | WebSocket | Low latency, bidirectional, real-time updates |
| Database | SQLite | Simple, file-based, sufficient for logging |
| Configuration | YAML | Human-readable, supports comments |

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                  │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        Web Dashboard (React)                         │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────────────┐   │    │
│  │  │  Game    │ │  Agent   │ │   Party &    │ │   Event Log &    │   │    │
│  │  │  Screen  │ │ Thoughts │ │   Inventory  │ │   Statistics     │   │    │
│  │  │ (Live)   │ │  Panel   │ │    Status    │ │                  │   │    │
│  │  └──────────┘ └──────────┘ └──────────────┘ └──────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                     ▲                                        │
│                                     │ WebSocket (wss://)                     │
└─────────────────────────────────────┼────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────┼────────────────────────────────────────┐
│                              BACKEND SERVER                                  │
│                                     │                                        │
│  ┌──────────────────────────────────┴───────────────────────────────────┐   │
│  │                      FastAPI Application                              │   │
│  │                                                                       │   │
│  │  • WebSocket endpoint (/ws/game-state)                               │   │
│  │  • REST endpoints (/api/*)                                           │   │
│  │  • Static file serving (/static/*)                                   │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                     │                                        │
│  ┌──────────────────────────────────┴───────────────────────────────────┐   │
│  │                      Game Engine (Async Core)                         │   │
│  │                                                                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │ Orchestrator│  │ Navigation  │  │   Battle    │  │    Menu     │ │   │
│  │  │    Agent    │  │    Agent    │  │    Agent    │  │    Agent    │ │   │
│  │  │  (Sonnet)   │  │   (Haiku)   │  │(Sonnet/Opus)│  │   (Haiku)   │ │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘ │   │
│  │         │                │                │                │        │   │
│  │         └────────────────┴────────────────┴────────────────┘        │   │
│  │                                  │                                   │   │
│  │                          ┌──────┴──────┐                            │   │
│  │                          │  GameState  │                            │   │
│  │                          │  Manager    │                            │   │
│  │                          └──────┬──────┘                            │   │
│  └─────────────────────────────────┼────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────┴────────────────────────────────────┐   │
│  │                      Emulator Interface Layer                         │   │
│  │                                                                       │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │   │
│  │  │    PyBoy        │  │  State Reader   │  │   Input Controller  │  │   │
│  │  │   Instance      │  │  (Memory →      │  │   (Commands →       │  │   │
│  │  │                 │  │   GameState)    │  │    Button Presses)  │  │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │                         Data Layer                                    │   │
│  │                                                                       │   │
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
                    │                                  │
                    │  Claude Haiku / Sonnet / Opus   │
                    └──────────────────────────────────┘
```

### 2.2 Component Interaction Sequence

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            MAIN GAME LOOP                                 │
│                                                                           │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐              │
│   │  Read   │───▶│ Detect  │───▶│  Route  │───▶│ Execute │──┐           │
│   │  State  │    │  Mode   │    │  Agent  │    │ Action  │  │           │
│   └─────────┘    └─────────┘    └─────────┘    └─────────┘  │           │
│        ▲                                                     │           │
│        └─────────────────────────────────────────────────────┘           │
│                           (~10-30 iterations/sec)                        │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                          UI UPDATE LOOP                                   │
│                                                                           │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│   │  Collect    │───▶│  Serialize  │───▶│   Push via  │                 │
│   │  State      │    │  to JSON    │    │  WebSocket  │                 │
│   └─────────────┘    └─────────────┘    └─────────────┘                 │
│                                                                           │
│                           (~15-30 updates/sec)                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Layer Responsibilities

| Layer | Responsibility | Key Classes |
|-------|---------------|-------------|
| **UI Layer** | Display, user interaction | React components |
| **API Layer** | HTTP/WS endpoints, serialization | FastAPI routers |
| **Game Engine** | Agent coordination, game loop | `GameEngine`, `AgentOrchestrator` |
| **Agent Layer** | AI decision making | `NavigationAgent`, `BattleAgent`, etc. |
| **Emulator Layer** | Game I/O, state reading | `GameInterface`, `StateReader` |
| **Data Layer** | Persistence, knowledge | `KnowledgeBase`, `EventLogger` |

---

## 3. Technology Stack

### 3.1 Stack Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
├─────────────────────────────────────────────────────────────────┤
│  React 18          │ UI Framework                               │
│  TypeScript 5      │ Type Safety                                │
│  Vite              │ Build Tool                                 │
│  TailwindCSS       │ Styling                                    │
│  Zustand           │ State Management                           │
│  React Query       │ Server State / Caching                     │
│  Recharts          │ Statistics Visualization                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND                                  │
├─────────────────────────────────────────────────────────────────┤
│  Python 3.11+      │ Runtime                                    │
│  FastAPI           │ Web Framework                              │
│  Uvicorn           │ ASGI Server                                │
│  Pydantic 2        │ Data Validation                            │
│  PyBoy             │ Game Boy Emulator                          │
│  Anthropic SDK     │ Claude API Client                          │
│  SQLAlchemy 2      │ ORM (for event logging)                    │
│  aiosqlite         │ Async SQLite                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      DEVELOPMENT                                 │
├─────────────────────────────────────────────────────────────────┤
│  Poetry            │ Python Dependency Management               │
│  pnpm              │ Node Package Manager                       │
│  Ruff              │ Python Linting                             │
│  mypy              │ Python Type Checking                       │
│  pytest            │ Python Testing                             │
│  pytest-asyncio    │ Async Test Support                         │
│  Vitest            │ Frontend Testing                           │
│  Pre-commit        │ Git Hooks                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      INFRASTRUCTURE                              │
├─────────────────────────────────────────────────────────────────┤
│  Docker            │ Containerization                           │
│  Docker Compose    │ Local Orchestration                        │
│  SQLite            │ Event/Log Database                         │
│  Redis (optional)  │ Caching / Pub-Sub (future)                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Backend Dependencies

```toml
# pyproject.toml
[tool.poetry]
name = "pokemon-red-agent"
version = "1.0.0"
description = "AI agent that plays Pokemon Red using Claude"
python = "^3.11"

[tool.poetry.dependencies]
python = "^3.11"

# Web Framework
fastapi = "^0.109.0"
uvicorn = { extras = ["standard"], version = "^0.27.0" }
websockets = "^12.0"
python-multipart = "^0.0.6"

# Data Validation
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"

# Emulator
pyboy = "^2.0.0"

# AI
anthropic = "^0.18.0"

# Database
sqlalchemy = "^2.0.25"
aiosqlite = "^0.19.0"

# Utilities
pyyaml = "^6.0.1"
structlog = "^24.1.0"
pillow = "^10.2.0"
numpy = "^1.26.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.23.0"
pytest-cov = "^4.1.0"
ruff = "^0.1.0"
mypy = "^1.8.0"
pre-commit = "^3.6.0"
httpx = "^0.26.0"  # For testing FastAPI
```

### 3.3 Frontend Dependencies

```json
{
  "name": "pokemon-red-agent-ui",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest",
    "lint": "eslint . --ext ts,tsx"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "zustand": "^4.5.0",
    "@tanstack/react-query": "^5.17.0",
    "recharts": "^2.10.0",
    "lucide-react": "^0.312.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "vitest": "^1.2.0",
    "eslint": "^8.56.0",
    "@typescript-eslint/eslint-plugin": "^6.19.0",
    "@typescript-eslint/parser": "^6.19.0"
  }
}
```

### 3.4 Technology Rationale

| Technology | Why Chosen | Alternatives Considered |
|------------|------------|------------------------|
| **FastAPI** | Async-native, automatic OpenAPI docs, excellent WebSocket support, Pydantic integration | Flask (no native async), Django (too heavy) |
| **PyBoy** | Native Python API, headless mode, save states, variable speed, active development | BizHawk (requires Lua bridge), RetroArch (complex setup) |
| **React** | Component-based, huge ecosystem, team familiarity, excellent TypeScript support | Vue (smaller ecosystem), Svelte (less mature) |
| **TypeScript** | Type safety catches bugs early, better IDE support, self-documenting | Plain JS (too error-prone for complex state) |
| **Zustand** | Simple API, no boilerplate, excellent TypeScript support, small bundle | Redux (too verbose), MobX (magic can be confusing) |
| **TailwindCSS** | Rapid prototyping, consistent design, no CSS file management | CSS Modules (slower), Styled Components (runtime cost) |
| **SQLite** | Zero configuration, file-based, sufficient for logging, easy backups | PostgreSQL (overkill), MongoDB (not needed) |
| **Poetry** | Dependency locking, virtual env management, modern Python standard | pip+venv (no locking), conda (heavy) |

---

## 4. Component Design

### 4.1 Emulator Interface Layer

```python
# src/emulator/interface.py

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional
import numpy as np
from pyboy import PyBoy
from pyboy.utils import WindowEvent


class GameMode(Enum):
    OVERWORLD = auto()
    BATTLE = auto()
    MENU = auto()
    DIALOGUE = auto()
    TRANSITION = auto()


class Button(Enum):
    A = auto()
    B = auto()
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    START = auto()
    SELECT = auto()


@dataclass
class Position:
    map_id: int
    map_name: str
    x: int
    y: int
    facing: str


@dataclass
class PokemonData:
    species_id: int
    species_name: str
    level: int
    current_hp: int
    max_hp: int
    status: Optional[str]
    moves: list[dict]
    stats: dict


@dataclass
class GameState:
    """Complete game state snapshot."""
    # Mode
    mode: GameMode
    
    # Position
    position: Position
    
    # Party
    party: list[PokemonData]
    party_count: int
    
    # Battle (if in battle)
    in_battle: bool
    battle_type: Optional[str]
    enemy_pokemon: Optional[PokemonData]
    
    # Inventory
    money: int
    items: dict[str, int]
    badges: list[str]
    
    # Meta
    frame_count: int
    play_time_seconds: int


class GameInterface:
    """
    Main interface between the AI agents and the Pokemon Red game.
    Wraps PyBoy emulator with Pokemon-specific functionality.
    """
    
    # Memory addresses for Pokemon Red (US)
    class Addresses:
        # Player position
        MAP_ID = 0xD35E
        PLAYER_Y = 0xD361
        PLAYER_X = 0xD362
        PLAYER_DIRECTION = 0xC109
        
        # Party data
        PARTY_COUNT = 0xD163
        PARTY_SPECIES = 0xD164
        PARTY_DATA_START = 0xD16B
        PARTY_NICKNAMES = 0xD2B5
        
        # Battle state
        BATTLE_TYPE = 0xD057
        ENEMY_SPECIES = 0xCFE5
        ENEMY_LEVEL = 0xCFF3
        ENEMY_HP = 0xCFE6
        
        # Game state
        MONEY = 0xD347
        BADGES = 0xD356
        
        # Menu / UI state
        MENU_OPEN = 0xD730
        TEXT_BOX_OPEN = 0xC4F2
    
    # Button mapping to PyBoy events
    BUTTON_MAP = {
        Button.A: (WindowEvent.PRESS_BUTTON_A, WindowEvent.RELEASE_BUTTON_A),
        Button.B: (WindowEvent.PRESS_BUTTON_B, WindowEvent.RELEASE_BUTTON_B),
        Button.UP: (WindowEvent.PRESS_ARROW_UP, WindowEvent.RELEASE_ARROW_UP),
        Button.DOWN: (WindowEvent.PRESS_ARROW_DOWN, WindowEvent.RELEASE_ARROW_DOWN),
        Button.LEFT: (WindowEvent.PRESS_ARROW_LEFT, WindowEvent.RELEASE_ARROW_LEFT),
        Button.RIGHT: (WindowEvent.PRESS_ARROW_RIGHT, WindowEvent.RELEASE_ARROW_RIGHT),
        Button.START: (WindowEvent.PRESS_BUTTON_START, WindowEvent.RELEASE_BUTTON_START),
        Button.SELECT: (WindowEvent.PRESS_BUTTON_SELECT, WindowEvent.RELEASE_BUTTON_SELECT),
    }
    
    def __init__(
        self,
        rom_path: str,
        speed: int = 1,
        headless: bool = False,
        sound: bool = False
    ):
        """
        Initialize the game interface.
        
        Args:
            rom_path: Path to Pokemon Red ROM file
            speed: Emulation speed multiplier (0 = unlimited)
            headless: Run without display window
            sound: Enable sound emulation
        """
        window_type = "headless" if headless else "SDL2"
        self.pyboy = PyBoy(
            rom_path,
            window_type=window_type,
            sound=sound,
            cgb=False  # Original Game Boy mode
        )
        self.pyboy.set_emulation_speed(speed)
        self._frame_count = 0
    
    # ─────────────────────────────────────────────────────────
    # FRAME CONTROL
    # ─────────────────────────────────────────────────────────
    
    def tick(self, frames: int = 1) -> None:
        """Advance emulation by N frames."""
        for _ in range(frames):
            self.pyboy.tick()
            self._frame_count += 1
    
    def get_frame_count(self) -> int:
        """Get total frames elapsed."""
        return self._frame_count
    
    # ─────────────────────────────────────────────────────────
    # INPUT CONTROL
    # ─────────────────────────────────────────────────────────
    
    def press_button(self, button: Button, hold_frames: int = 8) -> None:
        """
        Press a button for specified frames.
        
        Args:
            button: Button to press
            hold_frames: How long to hold (default 8 = ~133ms)
        """
        press_event, release_event = self.BUTTON_MAP[button]
        self.pyboy.send_input(press_event)
        self.tick(hold_frames)
        self.pyboy.send_input(release_event)
        self.tick(4)  # Small delay after release
    
    def press_sequence(self, buttons: list[Button], delay_frames: int = 4) -> None:
        """Press a sequence of buttons with delays between."""
        for button in buttons:
            self.press_button(button)
            self.tick(delay_frames)
    
    def move_direction(self, direction: str, tiles: int = 1) -> None:
        """
        Move player in a direction.
        
        Args:
            direction: "UP", "DOWN", "LEFT", or "RIGHT"
            tiles: Number of tiles to move
        """
        button = Button[direction]
        for _ in range(tiles):
            self.press_button(button, hold_frames=16)  # ~16 frames per tile
            self.tick(8)  # Wait for movement to complete
    
    # ─────────────────────────────────────────────────────────
    # STATE READING
    # ─────────────────────────────────────────────────────────
    
    def read_memory(self, address: int) -> int:
        """Read single byte from memory."""
        return self.pyboy.get_memory_value(address)
    
    def read_memory_word(self, address: int) -> int:
        """Read 16-bit little-endian value."""
        lo = self.read_memory(address)
        hi = self.read_memory(address + 1)
        return (hi << 8) | lo
    
    def read_memory_range(self, start: int, length: int) -> bytes:
        """Read range of bytes from memory."""
        return bytes(self.read_memory(start + i) for i in range(length))
    
    def get_game_mode(self) -> GameMode:
        """Detect current game mode from memory."""
        battle_type = self.read_memory(self.Addresses.BATTLE_TYPE)
        menu_open = self.read_memory(self.Addresses.MENU_OPEN)
        text_box = self.read_memory(self.Addresses.TEXT_BOX_OPEN)
        
        if battle_type != 0:
            return GameMode.BATTLE
        if menu_open != 0:
            return GameMode.MENU
        if text_box != 0:
            return GameMode.DIALOGUE
        
        return GameMode.OVERWORLD
    
    def get_position(self) -> Position:
        """Get player's current position."""
        map_id = self.read_memory(self.Addresses.MAP_ID)
        direction_byte = self.read_memory(self.Addresses.PLAYER_DIRECTION)
        
        direction_map = {0: "DOWN", 4: "UP", 8: "LEFT", 12: "RIGHT"}
        facing = direction_map.get(direction_byte, "DOWN")
        
        return Position(
            map_id=map_id,
            map_name=self._get_map_name(map_id),
            x=self.read_memory(self.Addresses.PLAYER_X),
            y=self.read_memory(self.Addresses.PLAYER_Y),
            facing=facing
        )
    
    def get_party(self) -> list[PokemonData]:
        """Read full party data."""
        party = []
        count = self.read_memory(self.Addresses.PARTY_COUNT)
        
        for i in range(min(count, 6)):
            pokemon = self._read_party_pokemon(i)
            party.append(pokemon)
        
        return party
    
    def get_game_state(self) -> GameState:
        """Get complete current game state."""
        mode = self.get_game_mode()
        position = self.get_position()
        party = self.get_party()
        
        # Battle state
        in_battle = mode == GameMode.BATTLE
        enemy_pokemon = None
        battle_type = None
        
        if in_battle:
            battle_type = self._get_battle_type()
            enemy_pokemon = self._read_enemy_pokemon()
        
        return GameState(
            mode=mode,
            position=position,
            party=party,
            party_count=len(party),
            in_battle=in_battle,
            battle_type=battle_type,
            enemy_pokemon=enemy_pokemon,
            money=self._read_money(),
            items=self._read_inventory(),
            badges=self._read_badges(),
            frame_count=self._frame_count,
            play_time_seconds=self._frame_count // 60
        )
    
    # ─────────────────────────────────────────────────────────
    # SCREEN CAPTURE
    # ─────────────────────────────────────────────────────────
    
    def get_screen(self) -> np.ndarray:
        """Get current screen as numpy array (160x144 RGB)."""
        return self.pyboy.screen_ndarray()
    
    def get_screen_bytes(self) -> bytes:
        """Get screen as PNG bytes for transmission."""
        from PIL import Image
        import io
        
        screen = self.get_screen()
        # Scale up 3x for better visibility
        img = Image.fromarray(screen)
        img = img.resize((480, 432), Image.NEAREST)
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    # ─────────────────────────────────────────────────────────
    # SAVE STATES
    # ─────────────────────────────────────────────────────────
    
    def save_state(self) -> bytes:
        """Create save state for checkpointing."""
        import io
        buffer = io.BytesIO()
        self.pyboy.save_state(buffer)
        return buffer.getvalue()
    
    def load_state(self, state: bytes) -> None:
        """Restore from save state."""
        import io
        buffer = io.BytesIO(state)
        self.pyboy.load_state(buffer)
    
    # ─────────────────────────────────────────────────────────
    # CLEANUP
    # ─────────────────────────────────────────────────────────
    
    def close(self) -> None:
        """Cleanup resources."""
        self.pyboy.stop()
    
    # ─────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────────────
    
    def _read_party_pokemon(self, index: int) -> PokemonData:
        """Read a single party Pokemon's data."""
        # Pokemon data structure is 44 bytes per Pokemon
        base = self.Addresses.PARTY_DATA_START + (index * 44)
        
        species_id = self.read_memory(self.Addresses.PARTY_SPECIES + index)
        
        return PokemonData(
            species_id=species_id,
            species_name=self._get_pokemon_name(species_id),
            level=self.read_memory(base + 33),
            current_hp=self.read_memory_word(base + 1),
            max_hp=self.read_memory_word(base + 34),
            status=self._decode_status(self.read_memory(base + 4)),
            moves=self._read_pokemon_moves(base),
            stats=self._read_pokemon_stats(base)
        )
    
    def _read_enemy_pokemon(self) -> PokemonData:
        """Read enemy Pokemon data in battle."""
        species_id = self.read_memory(self.Addresses.ENEMY_SPECIES)
        
        return PokemonData(
            species_id=species_id,
            species_name=self._get_pokemon_name(species_id),
            level=self.read_memory(self.Addresses.ENEMY_LEVEL),
            current_hp=self.read_memory_word(self.Addresses.ENEMY_HP),
            max_hp=0,  # Calculate from stats if needed
            status=None,
            moves=[],
            stats={}
        )
    
    def _get_map_name(self, map_id: int) -> str:
        """Look up map name from ID."""
        # This would use the knowledge base in production
        return f"MAP_{map_id}"
    
    def _get_pokemon_name(self, species_id: int) -> str:
        """Look up Pokemon name from ID."""
        # This would use the knowledge base in production
        return f"POKEMON_{species_id}"
    
    def _decode_status(self, status_byte: int) -> Optional[str]:
        """Decode status condition from byte."""
        if status_byte == 0:
            return None
        if status_byte & 0x40:
            return "PARALYSIS"
        if status_byte & 0x20:
            return "FREEZE"
        if status_byte & 0x10:
            return "BURN"
        if status_byte & 0x08:
            return "POISON"
        if status_byte & 0x07:
            return "SLEEP"
        return None
    
    def _read_money(self) -> int:
        """Read player's money (BCD encoded)."""
        raw = self.read_memory_range(self.Addresses.MONEY, 3)
        # Convert from BCD
        return (
            ((raw[0] >> 4) * 100000 + (raw[0] & 0xF) * 10000) +
            ((raw[1] >> 4) * 1000 + (raw[1] & 0xF) * 100) +
            ((raw[2] >> 4) * 10 + (raw[2] & 0xF))
        )
    
    def _read_badges(self) -> list[str]:
        """Read obtained badges."""
        badge_byte = self.read_memory(self.Addresses.BADGES)
        badge_names = [
            "BOULDER", "CASCADE", "THUNDER", "RAINBOW",
            "SOUL", "MARSH", "VOLCANO", "EARTH"
        ]
        return [name for i, name in enumerate(badge_names) if badge_byte & (1 << i)]
    
    def _read_inventory(self) -> dict[str, int]:
        """Read player inventory."""
        # Simplified - full implementation would read all item slots
        return {}
    
    def _read_pokemon_moves(self, base: int) -> list[dict]:
        """Read Pokemon's moves."""
        # Simplified - full implementation would decode move data
        return []
    
    def _read_pokemon_stats(self, base: int) -> dict:
        """Read Pokemon's stats."""
        # Simplified - full implementation would read all stats
        return {}
    
    def _get_battle_type(self) -> str:
        """Determine type of battle."""
        battle_type = self.read_memory(self.Addresses.BATTLE_TYPE)
        if battle_type == 1:
            return "WILD"
        if battle_type == 2:
            return "TRAINER"
        return "UNKNOWN"
```

### 4.2 Agent Layer

```python
# src/agents/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional
from anthropic import Anthropic

from ..emulator.interface import GameState


@dataclass
class AgentAction:
    """Represents an action the agent wants to take."""
    action_type: str  # "MOVE", "PRESS", "WAIT", etc.
    parameters: dict[str, Any]
    reasoning: str
    confidence: float


@dataclass
class AgentResponse:
    """Response from an agent after processing."""
    action: AgentAction
    should_yield: bool  # True if control should return to orchestrator
    yield_reason: Optional[str]
    state_updates: dict[str, Any]


class BaseAgent(ABC):
    """Base class for all AI agents."""
    
    def __init__(
        self,
        client: Anthropic,
        model: str,
        system_prompt: str,
        knowledge_base: dict
    ):
        self.client = client
        self.model = model
        self.system_prompt = system_prompt
        self.knowledge_base = knowledge_base
    
    @abstractmethod
    async def process(self, game_state: GameState, context: dict) -> AgentResponse:
        """
        Process the current game state and return an action.
        
        Args:
            game_state: Current state of the game
            context: Additional context from orchestrator
            
        Returns:
            AgentResponse with action to take
        """
        pass
    
    async def _call_claude(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None
    ) -> dict:
        """Make a call to Claude API."""
        kwargs = {
            "model": self.model,
            "max_tokens": 2048,
            "system": self.system_prompt,
            "messages": messages
        }
        
        if tools:
            kwargs["tools"] = tools
        
        response = await self.client.messages.create(**kwargs)
        return response
    
    def _format_game_state(self, game_state: GameState) -> str:
        """Format game state for inclusion in prompt."""
        return f"""
Current Game State:
- Mode: {game_state.mode.name}
- Location: {game_state.position.map_name} ({game_state.position.x}, {game_state.position.y})
- Facing: {game_state.position.facing}
- Party: {len(game_state.party)} Pokemon
- Lead Pokemon: {game_state.party[0].species_name if game_state.party else 'None'} 
  (HP: {game_state.party[0].current_hp}/{game_state.party[0].max_hp if game_state.party else 'N/A'})
- Badges: {', '.join(game_state.badges) if game_state.badges else 'None'}
- Money: ${game_state.money}
"""


# src/agents/navigation.py

class NavigationAgent(BaseAgent):
    """Agent responsible for overworld movement and navigation."""
    
    async def process(self, game_state: GameState, context: dict) -> AgentResponse:
        destination = context.get("destination")
        avoid_encounters = context.get("avoid_encounters", True)
        
        # Build prompt
        messages = [{
            "role": "user",
            "content": f"""
{self._format_game_state(game_state)}

Objective: Navigate to {destination}
Preferences:
- Avoid wild encounters: {avoid_encounters}

Determine the next movement action to take.
"""
        }]
        
        # Call Claude
        response = await self._call_claude(messages, tools=self._get_tools())
        
        # Parse response and return action
        return self._parse_response(response)
    
    def _get_tools(self) -> list[dict]:
        """Get tool definitions for navigation."""
        return [
            {
                "name": "move",
                "description": "Move the player in a direction",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "direction": {
                            "type": "string",
                            "enum": ["UP", "DOWN", "LEFT", "RIGHT"]
                        },
                        "tiles": {
                            "type": "integer",
                            "default": 1
                        }
                    },
                    "required": ["direction"]
                }
            },
            {
                "name": "interact",
                "description": "Interact with object/NPC in front of player",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
    
    def _parse_response(self, response: dict) -> AgentResponse:
        """Parse Claude's response into an AgentResponse."""
        # Implementation would extract tool calls and reasoning
        pass


# src/agents/battle.py

class BattleAgent(BaseAgent):
    """Agent responsible for combat decisions."""
    
    async def process(self, game_state: GameState, context: dict) -> AgentResponse:
        battle_type = context.get("battle_type", "WILD")
        can_flee = context.get("can_flee", True)
        catch_priority = context.get("catch_priority", "LOW")
        
        # Build prompt with battle-specific information
        messages = [{
            "role": "user",
            "content": f"""
{self._format_game_state(game_state)}

Battle Type: {battle_type}
Can Flee: {can_flee}
Catch Priority: {catch_priority}

Enemy Pokemon: {game_state.enemy_pokemon.species_name if game_state.enemy_pokemon else 'Unknown'}
Enemy Level: {game_state.enemy_pokemon.level if game_state.enemy_pokemon else '?'}
Enemy HP: ~{self._estimate_hp_percent(game_state)}%

Your Pokemon's Moves: {self._format_moves(game_state.party[0]) if game_state.party else 'None'}

Determine the best battle action to take.
"""
        }]
        
        response = await self._call_claude(messages, tools=self._get_tools())
        return self._parse_response(response)
    
    def _get_tools(self) -> list[dict]:
        """Get tool definitions for battle."""
        return [
            {
                "name": "use_move",
                "description": "Use a move in battle",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "move_index": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 3
                        }
                    },
                    "required": ["move_index"]
                }
            },
            {
                "name": "switch_pokemon",
                "description": "Switch to a different Pokemon",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "party_index": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 5
                        }
                    },
                    "required": ["party_index"]
                }
            },
            {
                "name": "use_item",
                "description": "Use an item in battle",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "item_name": {"type": "string"}
                    },
                    "required": ["item_name"]
                }
            },
            {
                "name": "flee",
                "description": "Attempt to flee from battle",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "throw_pokeball",
                "description": "Attempt to catch the wild Pokemon",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ball_type": {
                            "type": "string",
                            "enum": ["POKE_BALL", "GREAT_BALL", "ULTRA_BALL"]
                        }
                    },
                    "required": ["ball_type"]
                }
            }
        ]
```

### 4.3 Game Engine

```python
# src/engine/game_engine.py

import asyncio
from dataclasses import dataclass, field
from typing import Optional, Callable
from datetime import datetime
import structlog

from ..emulator.interface import GameInterface, GameState, GameMode
from ..agents.orchestrator import OrchestratorAgent
from ..agents.navigation import NavigationAgent
from ..agents.battle import BattleAgent
from ..agents.menu import MenuAgent


logger = structlog.get_logger()


@dataclass
class EngineConfig:
    """Configuration for the game engine."""
    rom_path: str
    emulation_speed: int = 1
    headless: bool = False
    target_fps: int = 30
    checkpoint_interval: int = 300  # Seconds between auto-saves
    max_stuck_frames: int = 1800  # ~30 seconds at 60fps


@dataclass
class EngineState:
    """Current state of the game engine."""
    running: bool = False
    paused: bool = False
    current_agent: str = "orchestrator"
    objective_stack: list[dict] = field(default_factory=list)
    start_time: Optional[datetime] = None
    total_frames: int = 0
    api_calls: int = 0
    last_checkpoint: Optional[bytes] = None


class GameEngine:
    """
    Core game engine that coordinates between emulator and agents.
    
    Responsible for:
    - Running the main game loop
    - Coordinating agent handoffs
    - Managing checkpoints and recovery
    - Broadcasting state updates
    """
    
    def __init__(
        self,
        config: EngineConfig,
        orchestrator: OrchestratorAgent,
        navigation: NavigationAgent,
        battle: BattleAgent,
        menu: MenuAgent
    ):
        self.config = config
        self.state = EngineState()
        
        # Initialize emulator
        self.game = GameInterface(
            rom_path=config.rom_path,
            speed=config.emulation_speed,
            headless=config.headless
        )
        
        # Agents
        self.orchestrator = orchestrator
        self.agents = {
            "navigation": navigation,
            "battle": battle,
            "menu": menu
        }
        
        # Event callbacks
        self._state_callbacks: list[Callable[[dict], None]] = []
        self._event_callbacks: list[Callable[[dict], None]] = []
    
    # ─────────────────────────────────────────────────────────
    # LIFECYCLE
    # ─────────────────────────────────────────────────────────
    
    async def start(self) -> None:
        """Start the game engine."""
        logger.info("Starting game engine")
        self.state.running = True
        self.state.start_time = datetime.now()
        
        # Create initial checkpoint
        self.state.last_checkpoint = self.game.save_state()
        
        # Start main loop
        await self._main_loop()
    
    async def stop(self) -> None:
        """Stop the game engine gracefully."""
        logger.info("Stopping game engine")
        self.state.running = False
        self.game.close()
    
    def pause(self) -> None:
        """Pause the game loop."""
        self.state.paused = True
        logger.info("Game paused")
    
    def resume(self) -> None:
        """Resume the game loop."""
        self.state.paused = False
        logger.info("Game resumed")
    
    # ─────────────────────────────────────────────────────────
    # MAIN LOOP
    # ─────────────────────────────────────────────────────────
    
    async def _main_loop(self) -> None:
        """Main game loop."""
        frame_time = 1.0 / self.config.target_fps
        last_checkpoint_time = datetime.now()
        
        while self.state.running:
            loop_start = datetime.now()
            
            if self.state.paused:
                await asyncio.sleep(0.1)
                continue
            
            try:
                # 1. Read current game state
                game_state = self.game.get_game_state()
                self.state.total_frames = game_state.frame_count
                
                # 2. Let orchestrator decide what to do
                orchestrator_response = await self.orchestrator.process(
                    game_state,
                    {"objective_stack": self.state.objective_stack}
                )
                
                self.state.api_calls += 1
                
                # 3. Update objective stack if needed
                for op in orchestrator_response.stack_operations:
                    self._apply_stack_operation(op)
                
                # 4. Route to appropriate agent
                agent_name = orchestrator_response.route_to
                if agent_name and agent_name in self.agents:
                    self.state.current_agent = agent_name
                    agent = self.agents[agent_name]
                    
                    agent_response = await agent.process(
                        game_state,
                        orchestrator_response.agent_context
                    )
                    
                    self.state.api_calls += 1
                    
                    # 5. Execute the action
                    await self._execute_action(agent_response.action)
                
                # 6. Broadcast state update
                await self._broadcast_state(game_state)
                
                # 7. Periodic checkpoint
                if (datetime.now() - last_checkpoint_time).seconds > self.config.checkpoint_interval:
                    self.state.last_checkpoint = self.game.save_state()
                    last_checkpoint_time = datetime.now()
                    logger.info("Checkpoint saved")
                
            except Exception as e:
                logger.error("Error in game loop", error=str(e))
                await self._handle_error(e)
            
            # Maintain target frame rate
            elapsed = (datetime.now() - loop_start).total_seconds()
            if elapsed < frame_time:
                await asyncio.sleep(frame_time - elapsed)
    
    # ─────────────────────────────────────────────────────────
    # ACTION EXECUTION
    # ─────────────────────────────────────────────────────────
    
    async def _execute_action(self, action: dict) -> None:
        """Execute an agent action on the emulator."""
        action_type = action.get("action_type")
        params = action.get("parameters", {})
        
        if action_type == "MOVE":
            direction = params.get("direction")
            tiles = params.get("tiles", 1)
            self.game.move_direction(direction, tiles)
            
        elif action_type == "PRESS":
            button = params.get("button")
            from ..emulator.interface import Button
            self.game.press_button(Button[button])
            
        elif action_type == "WAIT":
            frames = params.get("frames", 60)
            self.game.tick(frames)
            
        elif action_type == "SEQUENCE":
            buttons = params.get("buttons", [])
            from ..emulator.interface import Button
            for btn_name in buttons:
                self.game.press_button(Button[btn_name])
        
        # Log action
        self._emit_event({
            "type": "ACTION_EXECUTED",
            "action": action_type,
            "parameters": params,
            "timestamp": datetime.now().isoformat()
        })
    
    # ─────────────────────────────────────────────────────────
    # STATE BROADCASTING
    # ─────────────────────────────────────────────────────────
    
    def on_state_update(self, callback: Callable[[dict], None]) -> None:
        """Register callback for state updates."""
        self._state_callbacks.append(callback)
    
    def on_event(self, callback: Callable[[dict], None]) -> None:
        """Register callback for game events."""
        self._event_callbacks.append(callback)
    
    async def _broadcast_state(self, game_state: GameState) -> None:
        """Broadcast current state to all listeners."""
        state_dict = {
            "game": self._serialize_game_state(game_state),
            "engine": {
                "running": self.state.running,
                "paused": self.state.paused,
                "current_agent": self.state.current_agent,
                "objective_stack": self.state.objective_stack,
                "total_frames": self.state.total_frames,
                "api_calls": self.state.api_calls,
                "uptime_seconds": (datetime.now() - self.state.start_time).seconds
                    if self.state.start_time else 0
            },
            "screen": self._get_screen_base64()
        }
        
        for callback in self._state_callbacks:
            try:
                callback(state_dict)
            except Exception as e:
                logger.error("State callback error", error=str(e))
    
    def _emit_event(self, event: dict) -> None:
        """Emit an event to all listeners."""
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error("Event callback error", error=str(e))
    
    def _serialize_game_state(self, state: GameState) -> dict:
        """Serialize game state to JSON-compatible dict."""
        return {
            "mode": state.mode.name,
            "position": {
                "map_id": state.position.map_id,
                "map_name": state.position.map_name,
                "x": state.position.x,
                "y": state.position.y,
                "facing": state.position.facing
            },
            "party": [
                {
                    "species": p.species_name,
                    "level": p.level,
                    "hp": p.current_hp,
                    "max_hp": p.max_hp,
                    "status": p.status
                }
                for p in state.party
            ],
            "in_battle": state.in_battle,
            "battle_type": state.battle_type,
            "enemy": {
                "species": state.enemy_pokemon.species_name,
                "level": state.enemy_pokemon.level
            } if state.enemy_pokemon else None,
            "money": state.money,
            "badges": state.badges
        }
    
    def _get_screen_base64(self) -> str:
        """Get screen as base64-encoded PNG."""
        import base64
        png_bytes = self.game.get_screen_bytes()
        return base64.b64encode(png_bytes).decode('utf-8')
    
    # ─────────────────────────────────────────────────────────
    # ERROR HANDLING
    # ─────────────────────────────────────────────────────────
    
    async def _handle_error(self, error: Exception) -> None:
        """Handle errors in the game loop."""
        logger.error("Handling game loop error", error=str(error))
        
        # Try to recover from checkpoint
        if self.state.last_checkpoint:
            logger.info("Attempting recovery from checkpoint")
            self.game.load_state(self.state.last_checkpoint)
        
        self._emit_event({
            "type": "ERROR",
            "message": str(error),
            "recovered": self.state.last_checkpoint is not None,
            "timestamp": datetime.now().isoformat()
        })
    
    # ─────────────────────────────────────────────────────────
    # OBJECTIVE STACK
    # ─────────────────────────────────────────────────────────
    
    def _apply_stack_operation(self, operation: dict) -> None:
        """Apply an operation to the objective stack."""
        op_type = operation.get("type")
        
        if op_type == "PUSH":
            self.state.objective_stack.append(operation.get("objective"))
        elif op_type == "POP":
            if self.state.objective_stack:
                self.state.objective_stack.pop()
        elif op_type == "CLEAR":
            self.state.objective_stack.clear()
```

### 4.4 API Layer

```python
# src/api/main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from typing import Optional
import structlog

from ..engine.game_engine import GameEngine, EngineConfig
from ..agents import create_agents
from .models import (
    GameStatus,
    ControlCommand,
    ConfigUpdate,
    EventLog
)


logger = structlog.get_logger()


# Global engine instance
engine: Optional[GameEngine] = None
connected_clients: set[WebSocket] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global engine
    
    # Startup
    logger.info("Starting Pokemon Red AI Agent")
    
    # Initialize engine (lazy - started via API)
    yield
    
    # Shutdown
    if engine and engine.state.running:
        await engine.stop()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Pokemon Red AI Agent",
    description="AI that plays Pokemon Red using Claude",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
# WEBSOCKET ENDPOINT
# ─────────────────────────────────────────────────────────────

@app.websocket("/ws/game-state")
async def websocket_game_state(websocket: WebSocket):
    """
    WebSocket endpoint for real-time game state streaming.
    
    Clients receive:
    - Game state updates (~15-30 fps)
    - Agent decision logs
    - System events
    """
    await websocket.accept()
    connected_clients.add(websocket)
    logger.info("WebSocket client connected", total_clients=len(connected_clients))
    
    try:
        while True:
            # Handle incoming messages (commands from UI)
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=0.1
                )
                await handle_ws_message(websocket, json.loads(data))
            except asyncio.TimeoutError:
                pass
            
            # State is pushed via callbacks, not pulled here
            await asyncio.sleep(0.033)  # ~30fps check rate
            
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        logger.info("WebSocket client disconnected", total_clients=len(connected_clients))


async def handle_ws_message(websocket: WebSocket, message: dict):
    """Handle incoming WebSocket messages."""
    msg_type = message.get("type")
    
    if msg_type == "PING":
        await websocket.send_json({"type": "PONG"})
    
    elif msg_type == "COMMAND":
        command = message.get("command")
        await process_command(command)


async def broadcast_to_clients(data: dict):
    """Broadcast data to all connected WebSocket clients."""
    if not connected_clients:
        return
    
    message = json.dumps(data)
    disconnected = set()
    
    for client in connected_clients:
        try:
            await client.send_text(message)
        except Exception:
            disconnected.add(client)
    
    # Clean up disconnected clients
    connected_clients.difference_update(disconnected)


# ─────────────────────────────────────────────────────────────
# REST ENDPOINTS
# ─────────────────────────────────────────────────────────────

@app.get("/api/status", response_model=GameStatus)
async def get_status():
    """Get current game and engine status."""
    if not engine:
        return GameStatus(
            running=False,
            paused=False,
            current_mode="NOT_STARTED",
            current_agent="none",
            total_frames=0,
            api_calls=0,
            uptime_seconds=0
        )
    
    return GameStatus(
        running=engine.state.running,
        paused=engine.state.paused,
        current_mode=engine.game.get_game_mode().name if engine.game else "UNKNOWN",
        current_agent=engine.state.current_agent,
        total_frames=engine.state.total_frames,
        api_calls=engine.state.api_calls,
        uptime_seconds=(datetime.now() - engine.state.start_time).seconds
            if engine.state.start_time else 0
    )


@app.post("/api/start")
async def start_game(config: Optional[ConfigUpdate] = None):
    """Start the game engine."""
    global engine
    
    if engine and engine.state.running:
        raise HTTPException(400, "Game already running")
    
    # Create engine with config
    engine_config = EngineConfig(
        rom_path=config.rom_path if config else "pokemon_red.gb",
        emulation_speed=config.speed if config else 1,
        headless=False
    )
    
    # Create agents
    agents = create_agents()
    
    engine = GameEngine(
        config=engine_config,
        orchestrator=agents["orchestrator"],
        navigation=agents["navigation"],
        battle=agents["battle"],
        menu=agents["menu"]
    )
    
    # Register broadcast callback
    engine.on_state_update(lambda state: asyncio.create_task(broadcast_to_clients({
        "type": "STATE_UPDATE",
        "data": state
    })))
    
    engine.on_event(lambda event: asyncio.create_task(broadcast_to_clients({
        "type": "EVENT",
        "data": event
    })))
    
    # Start in background
    asyncio.create_task(engine.start())
    
    return {"status": "started"}


@app.post("/api/stop")
async def stop_game():
    """Stop the game engine."""
    if not engine or not engine.state.running:
        raise HTTPException(400, "Game not running")
    
    await engine.stop()
    return {"status": "stopped"}


@app.post("/api/pause")
async def pause_game():
    """Pause the game."""
    if not engine or not engine.state.running:
        raise HTTPException(400, "Game not running")
    
    engine.pause()
    return {"status": "paused"}


@app.post("/api/resume")
async def resume_game():
    """Resume the game."""
    if not engine:
        raise HTTPException(400, "Game not running")
    
    engine.resume()
    return {"status": "resumed"}


@app.post("/api/command")
async def send_command(command: ControlCommand):
    """Send a control command to the engine."""
    await process_command(command.dict())
    return {"status": "command_sent"}


@app.get("/api/events", response_model=list[EventLog])
async def get_events(limit: int = 100, offset: int = 0):
    """Get recent events from the log."""
    # Would query SQLite database
    return []


@app.post("/api/save-state")
async def save_game_state():
    """Create a named save state."""
    if not engine:
        raise HTTPException(400, "Game not running")
    
    state = engine.game.save_state()
    # Save to file with timestamp
    return {"status": "saved", "size_bytes": len(state)}


@app.post("/api/load-state")
async def load_game_state(state_name: str):
    """Load a named save state."""
    if not engine:
        raise HTTPException(400, "Game not running")
    
    # Load from file
    # engine.game.load_state(state_data)
    return {"status": "loaded"}


async def process_command(command: dict):
    """Process a control command."""
    cmd_type = command.get("type")
    
    if cmd_type == "SET_SPEED":
        speed = command.get("speed", 1)
        if engine:
            engine.game.pyboy.set_emulation_speed(speed)
    
    elif cmd_type == "MANUAL_INPUT":
        # Allow manual button presses for testing
        button = command.get("button")
        if engine and button:
            from ..emulator.interface import Button
            engine.game.press_button(Button[button])


# ─────────────────────────────────────────────────────────────
# STATIC FILES (UI)
# ─────────────────────────────────────────────────────────────

# Mount static files last (catch-all)
app.mount("/", StaticFiles(directory="ui/dist", html=True), name="static")
```

---

## 5. Data Flow

### 5.1 Real-Time State Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA FLOW DIAGRAM                                  │
└─────────────────────────────────────────────────────────────────────────────┘

1. GAME STATE READING (Every Frame)
   ┌─────────┐    Memory Read     ┌─────────────┐    Transform    ┌──────────┐
   │  PyBoy  │ ─────────────────▶ │ StateReader │ ──────────────▶ │ GameState│
   │ Memory  │                    │             │                  │  Object  │
   └─────────┘                    └─────────────┘                  └──────────┘
                                                                        │
2. AGENT DECISION                                                       │
   ┌──────────┐    GameState     ┌─────────────┐    API Call    ┌──────▼──────┐
   │ GameState│ ───────────────▶ │   Agent     │ ─────────────▶ │   Claude    │
   │  Object  │                  │  (Python)   │                │    API      │
   └──────────┘                  └─────────────┘                └─────────────┘
                                       │                              │
                                       │◀─────────── Response ────────┘
                                       │
3. ACTION EXECUTION                    │
   ┌─────────────┐    Command    ┌─────▼─────┐    Input Event   ┌─────────┐
   │   Agent     │ ────────────▶ │  Input    │ ───────────────▶ │  PyBoy  │
   │  Response   │               │ Controller│                  │         │
   └─────────────┘               └───────────┘                  └─────────┘

4. UI UPDATE (15-30 fps)
   ┌──────────┐    Serialize    ┌───────────┐   WebSocket    ┌────────────┐
   │ GameState│ ──────────────▶ │   JSON    │ ─────────────▶ │   React    │
   │ + Screen │                 │  Message  │                │     UI     │
   └──────────┘                 └───────────┘                └────────────┘
```

### 5.2 WebSocket Message Types

| Direction | Type | Description | Frequency |
|-----------|------|-------------|-----------|
| Server→Client | `STATE_UPDATE` | Full game state + screen | 15-30/sec |
| Server→Client | `EVENT` | Game events (battle start, level up) | As needed |
| Server→Client | `AGENT_THOUGHT` | Agent reasoning/decisions | Per decision |
| Client→Server | `COMMAND` | Control commands (pause, speed) | User-initiated |
| Client→Server | `PING` | Connection keepalive | Every 30sec |

### 5.3 State Update Payload

```typescript
interface StateUpdate {
  type: "STATE_UPDATE";
  data: {
    game: {
      mode: "OVERWORLD" | "BATTLE" | "MENU" | "DIALOGUE";
      position: {
        map_id: number;
        map_name: string;
        x: number;
        y: number;
        facing: string;
      };
      party: Array<{
        species: string;
        level: number;
        hp: number;
        max_hp: number;
        status: string | null;
      }>;
      in_battle: boolean;
      battle_type: string | null;
      enemy: {
        species: string;
        level: number;
      } | null;
      money: number;
      badges: string[];
    };
    engine: {
      running: boolean;
      paused: boolean;
      current_agent: string;
      objective_stack: Array<{
        type: string;
        target: string;
        priority: number;
      }>;
      total_frames: number;
      api_calls: number;
      uptime_seconds: number;
    };
    screen: string; // Base64 PNG
  };
}
```

---

## 6. User Interface

### 6.1 UI Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Pokemon Red AI Agent                                    [⏸️ Pause] [⚙️]    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────┐  ┌─────────────────────────────────────────┐  │
│  │                         │  │  AGENT THOUGHTS                         │  │
│  │                         │  │  ─────────────────────────────────────  │  │
│  │      GAME SCREEN        │  │  [Orchestrator] Detected: OVERWORLD    │  │
│  │       (480x432)         │  │  Current objective: Defeat Brock       │  │
│  │                         │  │  Routing to: Navigation Agent          │  │
│  │      Live Feed          │  │                                         │  │
│  │                         │  │  [Navigation] Planning path to          │  │
│  │                         │  │  Pewter City Gym                        │  │
│  │                         │  │  Distance: 23 tiles                     │  │
│  │                         │  │  Action: Move RIGHT                     │  │
│  │                         │  │                                         │  │
│  └─────────────────────────┘  └─────────────────────────────────────────┘  │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  PARTY STATUS                                                           ││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     ││
│  │  │ SQUIRTLE │ │ PIDGEY   │ │ RATTATA  │ │ (empty)  │ │ (empty)  │ ... ││
│  │  │ Lv.12    │ │ Lv.8     │ │ Lv.6     │ │          │ │          │     ││
│  │  │ ████░░░  │ │ ██████░  │ │ █████░░  │ │          │ │          │     ││
│  │  │ 28/35 HP │ │ 24/28 HP │ │ 18/22 HP │ │          │ │          │     ││
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘     ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌────────────────────────────┐  ┌────────────────────────────────────────┐ │
│  │  OBJECTIVES                │  │  EVENT LOG                             │ │
│  │  ─────────────────────────  │  │  ────────────────────────────────────  │ │
│  │  🎯 Defeat Brock           │  │  12:34:56 Entered Pewter City          │ │
│  │    └─ Navigate to Gym      │  │  12:34:48 Wild RATTATA fled            │ │
│  │  📍 Get 8 Badges           │  │  12:34:32 Caught PIDGEY (Lv.5)        │ │
│  │  🏆 Become Champion        │  │  12:33:15 Healed at Pokemon Center    │ │
│  │                            │  │  12:32:44 Battle won: Bug Catcher     │ │
│  └────────────────────────────┘  └────────────────────────────────────────┘ │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  STATISTICS    Frames: 125,432  │  API Calls: 847  │  Uptime: 01:23:45 ││
│  │                Speed: 2x        │  Badges: 0/8     │  Money: $3,450    ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Component Structure

```
ui/src/
├── components/
│   ├── GameScreen/
│   │   ├── GameScreen.tsx       # Live game display
│   │   └── GameScreen.css
│   ├── AgentThoughts/
│   │   ├── AgentThoughts.tsx    # Agent decision log
│   │   └── ThoughtBubble.tsx
│   ├── PartyStatus/
│   │   ├── PartyStatus.tsx      # Pokemon party display
│   │   ├── PokemonCard.tsx
│   │   └── HPBar.tsx
│   ├── Objectives/
│   │   ├── ObjectiveStack.tsx   # Current objectives
│   │   └── ObjectiveItem.tsx
│   ├── EventLog/
│   │   ├── EventLog.tsx         # Scrolling event log
│   │   └── EventItem.tsx
│   ├── Controls/
│   │   ├── ControlBar.tsx       # Play/pause, speed, settings
│   │   └── SpeedSelector.tsx
│   └── Statistics/
│       └── StatsBar.tsx         # Frame count, API calls, etc.
├── hooks/
│   ├── useGameState.ts          # WebSocket state management
│   ├── useWebSocket.ts          # WebSocket connection
│   └── useEventLog.ts           # Event history
├── stores/
│   └── gameStore.ts             # Zustand store
├── types/
│   └── game.ts                  # TypeScript interfaces
├── utils/
│   └── formatters.ts            # Display formatting
├── App.tsx
├── main.tsx
└── index.css
```

### 6.3 Key React Components

```typescript
// ui/src/components/GameScreen/GameScreen.tsx

import { useGameState } from '../../hooks/useGameState';
import { memo } from 'react';

export const GameScreen = memo(function GameScreen() {
  const { screen } = useGameState();
  
  return (
    <div className="game-screen-container">
      <div className="game-screen">
        {screen ? (
          <img 
            src={`data:image/png;base64,${screen}`}
            alt="Game Screen"
            className="pixel-perfect"
          />
        ) : (
          <div className="game-screen-placeholder">
            No game running
          </div>
        )}
      </div>
      <div className="screen-overlay">
        {/* Optional: Position indicators, click-to-move */}
      </div>
    </div>
  );
});


// ui/src/components/AgentThoughts/AgentThoughts.tsx

import { useGameState } from '../../hooks/useGameState';
import { ThoughtBubble } from './ThoughtBubble';

export function AgentThoughts() {
  const { thoughts, currentAgent } = useGameState();
  
  return (
    <div className="agent-thoughts">
      <div className="thoughts-header">
        <h3>Agent Thoughts</h3>
        <span className="current-agent">{currentAgent}</span>
      </div>
      <div className="thoughts-list">
        {thoughts.map((thought, i) => (
          <ThoughtBubble key={i} thought={thought} />
        ))}
      </div>
    </div>
  );
}


// ui/src/hooks/useGameState.ts

import { create } from 'zustand';
import { useEffect } from 'react';

interface GameState {
  connected: boolean;
  game: GameData | null;
  engine: EngineData | null;
  screen: string | null;
  thoughts: AgentThought[];
  events: GameEvent[];
}

interface GameStore extends GameState {
  setConnected: (connected: boolean) => void;
  updateState: (state: Partial<GameState>) => void;
  addThought: (thought: AgentThought) => void;
  addEvent: (event: GameEvent) => void;
}

export const useGameStore = create<GameStore>((set) => ({
  connected: false,
  game: null,
  engine: null,
  screen: null,
  thoughts: [],
  events: [],
  
  setConnected: (connected) => set({ connected }),
  
  updateState: (state) => set((prev) => ({ ...prev, ...state })),
  
  addThought: (thought) => set((prev) => ({
    thoughts: [...prev.thoughts.slice(-49), thought]
  })),
  
  addEvent: (event) => set((prev) => ({
    events: [...prev.events.slice(-99), event]
  })),
}));


export function useGameState() {
  const store = useGameStore();
  
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/game-state');
    
    ws.onopen = () => {
      store.setConnected(true);
    };
    
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      
      if (message.type === 'STATE_UPDATE') {
        store.updateState({
          game: message.data.game,
          engine: message.data.engine,
          screen: message.data.screen,
        });
      } else if (message.type === 'EVENT') {
        store.addEvent(message.data);
      } else if (message.type === 'AGENT_THOUGHT') {
        store.addThought(message.data);
      }
    };
    
    ws.onclose = () => {
      store.setConnected(false);
    };
    
    return () => ws.close();
  }, []);
  
  return store;
}
```

---

## 7. Deployment Architecture

### 7.1 Local Development

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DEVELOPMENT SETUP                                 │
│                                                                          │
│   Terminal 1 (Backend)              Terminal 2 (Frontend)               │
│   ┌────────────────────┐           ┌────────────────────┐               │
│   │ poetry run uvicorn │           │ pnpm dev           │               │
│   │ src.api.main:app   │           │                    │               │
│   │ --reload           │           │ Vite dev server    │               │
│   │ --port 8000        │           │ Port 5173          │               │
│   └────────────────────┘           └────────────────────┘               │
│            │                                 │                           │
│            │ Hot Reload                      │ HMR                       │
│            ▼                                 ▼                           │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │                         Browser                                 │    │
│   │                    http://localhost:5173                        │    │
│   │                                                                 │    │
│   │  React App ◄──── WebSocket ────► FastAPI ◄──── PyBoy           │    │
│   └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Docker Deployment

```yaml
# docker-compose.yml

version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data          # Persistent data
      - ./roms:/app/roms:ro       # ROM files (read-only)
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - ROM_PATH=/app/roms/pokemon_red.gb
      - DATABASE_URL=sqlite:///app/data/events.db
    restart: unless-stopped

  # Optional: Redis for future scaling
  # redis:
  #   image: redis:alpine
  #   ports:
  #     - "6379:6379"
```

```dockerfile
# Dockerfile

FROM python:3.11-slim

# Install system dependencies for PyBoy
RUN apt-get update && apt-get install -y \
    libsdl2-dev \
    libsdl2-ttf-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction

# Build frontend
COPY ui/package.json ui/pnpm-lock.yaml ./ui/
RUN cd ui && npm install -g pnpm && pnpm install

COPY ui/ ./ui/
RUN cd ui && pnpm build

# Copy backend
COPY src/ ./src/
COPY knowledge_base/ ./knowledge_base/

# Expose port
EXPOSE 8000

# Run
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 7.3 Production Considerations

| Concern | Solution |
|---------|----------|
| **API Key Security** | Environment variables, never in code |
| **ROM Legality** | User must provide their own ROM |
| **Save State Storage** | Local filesystem or S3-compatible storage |
| **Logging** | Structured logging to file + stdout |
| **Monitoring** | Prometheus metrics endpoint (future) |
| **Rate Limiting** | Anthropic SDK handles API rate limits |

---

## 8. Development Setup

### 8.1 Prerequisites

| Requirement | Version | Installation |
|-------------|---------|--------------|
| Python | 3.11+ | pyenv or system |
| Node.js | 18+ | nvm or system |
| Poetry | Latest | `pip install poetry` |
| pnpm | Latest | `npm install -g pnpm` |
| SDL2 | Latest | `apt install libsdl2-dev` |

### 8.2 Initial Setup

```bash
# Clone repository
git clone https://github.com/your-org/pokemon-red-agent.git
cd pokemon-red-agent

# Backend setup
poetry install
poetry shell

# Frontend setup
cd ui
pnpm install
cd ..

# Environment configuration
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Place ROM file
cp /path/to/pokemon_red.gb roms/

# Initialize database
python -m src.db.init

# Run development servers
# Terminal 1:
poetry run uvicorn src.api.main:app --reload --port 8000

# Terminal 2:
cd ui && pnpm dev
```

### 8.3 Environment Variables

```bash
# .env

# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional
ROM_PATH=roms/pokemon_red.gb
DATABASE_URL=sqlite:///data/events.db
LOG_LEVEL=INFO
EMULATION_SPEED=1
HEADLESS=false

# Development
DEBUG=true
RELOAD=true
```

### 8.4 Development Commands

```bash
# Backend
poetry run pytest                    # Run tests
poetry run pytest --cov=src          # With coverage
poetry run ruff check src            # Lint
poetry run ruff format src           # Format
poetry run mypy src                  # Type check

# Frontend
cd ui
pnpm test                            # Run tests
pnpm lint                            # Lint
pnpm build                           # Production build

# Full stack
./scripts/dev.sh                     # Start both servers
./scripts/test.sh                    # Run all tests
```

---

## 9. Project Structure

```
pokemon-red-agent/
├── README.md
├── LICENSE
├── pyproject.toml                 # Python dependencies
├── poetry.lock
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── Dockerfile
├── docker-compose.yml
│
├── docs/                          # Documentation
│   ├── architecture.md
│   ├── api.md
│   └── agents.md
│
├── roms/                          # ROM files (gitignored)
│   └── .gitkeep
│
├── data/                          # Runtime data (gitignored)
│   ├── saves/                     # Save states
│   ├── logs/                      # Log files
│   └── events.db                  # SQLite database
│
├── knowledge_base/                # Static game data
│   ├── pokemon.json
│   ├── moves.json
│   ├── type_chart.json
│   ├── maps/
│   │   ├── maps.json
│   │   └── tiles/
│   ├── trainers.json
│   ├── items.json
│   ├── shops.json
│   ├── wild_encounters.json
│   ├── hm_requirements.json
│   └── story_progression.json
│
├── src/                           # Backend source
│   ├── __init__.py
│   ├── config.py                  # Configuration loading
│   │
│   ├── emulator/                  # Emulator interface
│   │   ├── __init__.py
│   │   ├── interface.py           # GameInterface class
│   │   ├── memory_map.py          # Memory address constants
│   │   └── state_reader.py        # State reading utilities
│   │
│   ├── agents/                    # AI agents
│   │   ├── __init__.py
│   │   ├── base.py                # BaseAgent class
│   │   ├── orchestrator.py        # OrchestratorAgent
│   │   ├── navigation.py          # NavigationAgent
│   │   ├── battle.py              # BattleAgent
│   │   ├── menu.py                # MenuAgent
│   │   └── prompts/               # System prompts
│   │       ├── orchestrator.txt
│   │       ├── navigation.txt
│   │       ├── battle.txt
│   │       ├── battle_boss.txt
│   │       └── menu.txt
│   │
│   ├── engine/                    # Game engine
│   │   ├── __init__.py
│   │   ├── game_engine.py         # Main engine class
│   │   ├── action_executor.py     # Action execution
│   │   └── checkpoint.py          # Save state management
│   │
│   ├── knowledge/                 # Knowledge base access
│   │   ├── __init__.py
│   │   ├── loader.py              # JSON loading
│   │   ├── pokemon.py             # Pokemon data access
│   │   ├── moves.py               # Move data access
│   │   ├── maps.py                # Map data access
│   │   └── types.py               # Type chart access
│   │
│   ├── api/                       # FastAPI application
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI app
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── game.py            # Game control endpoints
│   │   │   ├── events.py          # Event log endpoints
│   │   │   └── config.py          # Configuration endpoints
│   │   ├── websocket.py           # WebSocket handlers
│   │   └── models.py              # Pydantic models
│   │
│   ├── db/                        # Database
│   │   ├── __init__.py
│   │   ├── init.py                # Database initialization
│   │   ├── models.py              # SQLAlchemy models
│   │   └── repository.py          # Data access layer
│   │
│   └── utils/                     # Utilities
│       ├── __init__.py
│       ├── logging.py             # Logging setup
│       └── serialization.py       # JSON serialization
│
├── ui/                            # Frontend source
│   ├── index.html
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   │
│   ├── public/
│   │   └── favicon.ico
│   │
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css
│       │
│       ├── components/
│       │   ├── GameScreen/
│       │   ├── AgentThoughts/
│       │   ├── PartyStatus/
│       │   ├── Objectives/
│       │   ├── EventLog/
│       │   ├── Controls/
│       │   └── Statistics/
│       │
│       ├── hooks/
│       │   ├── useGameState.ts
│       │   ├── useWebSocket.ts
│       │   └── useControls.ts
│       │
│       ├── stores/
│       │   └── gameStore.ts
│       │
│       ├── types/
│       │   └── game.ts
│       │
│       └── utils/
│           └── formatters.ts
│
├── tests/                         # Tests
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures
│   │
│   ├── unit/
│   │   ├── test_emulator.py
│   │   ├── test_agents.py
│   │   └── test_engine.py
│   │
│   ├── integration/
│   │   ├── test_api.py
│   │   └── test_game_loop.py
│   │
│   └── e2e/
│       └── test_scenarios.py
│
└── scripts/                       # Utility scripts
    ├── dev.sh                     # Start dev servers
    ├── test.sh                    # Run all tests
    ├── build.sh                   # Build for production
    └── extract_knowledge.py       # Extract data from pokered
```

---

## 10. API Specifications

### 10.1 REST Endpoints

#### Game Control

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | Get current game status |
| POST | `/api/start` | Start the game engine |
| POST | `/api/stop` | Stop the game engine |
| POST | `/api/pause` | Pause the game |
| POST | `/api/resume` | Resume the game |
| POST | `/api/command` | Send control command |

#### State Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/state` | Get current game state |
| GET | `/api/party` | Get party Pokemon |
| GET | `/api/inventory` | Get inventory |
| GET | `/api/objectives` | Get objective stack |

#### Save States

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/saves` | List save states |
| POST | `/api/saves` | Create save state |
| POST | `/api/saves/{id}/load` | Load save state |
| DELETE | `/api/saves/{id}` | Delete save state |

#### Events & History

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/events` | Get event log |
| GET | `/api/statistics` | Get run statistics |

### 10.2 WebSocket Protocol

#### Connection

```
ws://localhost:8000/ws/game-state
```

#### Server → Client Messages

```typescript
// State update (15-30 fps)
{
  "type": "STATE_UPDATE",
  "data": {
    "game": { ... },
    "engine": { ... },
    "screen": "base64..."
  }
}

// Game event
{
  "type": "EVENT",
  "data": {
    "event_type": "BATTLE_START",
    "details": { ... },
    "timestamp": "2024-01-15T12:34:56Z"
  }
}

// Agent thought
{
  "type": "AGENT_THOUGHT",
  "data": {
    "agent": "navigation",
    "thought": "Planning path to Pewter Gym",
    "action": "MOVE_RIGHT",
    "confidence": 0.95
  }
}
```

#### Client → Server Messages

```typescript
// Control command
{
  "type": "COMMAND",
  "command": {
    "type": "SET_SPEED",
    "speed": 2
  }
}

// Keep-alive
{
  "type": "PING"
}
```

### 10.3 OpenAPI Documentation

FastAPI automatically generates OpenAPI documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 11. Configuration

### 11.1 Application Configuration

```yaml
# config/default.yaml

app:
  name: "Pokemon Red AI Agent"
  version: "1.0.0"
  debug: false

emulator:
  rom_path: "roms/pokemon_red.gb"
  speed: 1
  headless: false
  sound: false

engine:
  target_fps: 30
  checkpoint_interval: 300  # seconds
  max_stuck_frames: 1800

agents:
  orchestrator:
    model: "claude-sonnet-4-5-20250929"
    temperature: 0.3
  navigation:
    model: "claude-haiku-4-5-20251001"
    temperature: 0.2
  battle:
    model: "claude-sonnet-4-5-20250929"
    model_boss: "claude-opus-4-5-20251101"
    temperature: 0.4
  menu:
    model: "claude-haiku-4-5-20251001"
    temperature: 0.1

api:
  host: "0.0.0.0"
  port: 8000
  cors_origins:
    - "http://localhost:5173"
    - "http://localhost:3000"

database:
  url: "sqlite:///data/events.db"

logging:
  level: "INFO"
  format: "json"
  file: "data/logs/app.log"
```

### 11.2 Environment Override

Environment variables override config file values:

```bash
POKEMON_AGENT_EMULATOR__SPEED=2
POKEMON_AGENT_AGENTS__BATTLE__TEMPERATURE=0.5
POKEMON_AGENT_API__PORT=9000
```

---

## 12. Testing Strategy

### 12.1 Test Pyramid

```
                    ┌───────────────┐
                    │     E2E       │  ~10 tests
                    │  Full game    │  (slow, comprehensive)
                    │  scenarios    │
                    └───────────────┘
               ┌─────────────────────────┐
               │      Integration        │  ~50 tests
               │  API, WebSocket,        │  (medium speed)
               │  Agent + Emulator       │
               └─────────────────────────┘
          ┌───────────────────────────────────┐
          │            Unit Tests             │  ~200 tests
          │  State reading, agent logic,      │  (fast, isolated)
          │  serialization, utilities         │
          └───────────────────────────────────┘
```

### 12.2 Test Categories

| Category | Focus | Tools |
|----------|-------|-------|
| Unit | Individual functions, classes | pytest, pytest-mock |
| Integration | API endpoints, WebSocket | pytest, httpx, pytest-asyncio |
| E2E | Full game scenarios | pytest, save states |
| Snapshot | Agent responses | pytest-snapshot |

### 12.3 Test Fixtures

```python
# tests/conftest.py

import pytest
from pathlib import Path
from src.emulator.interface import GameInterface

@pytest.fixture
def game_interface():
    """Provide a fresh game interface for testing."""
    rom_path = Path("roms/pokemon_red.gb")
    if not rom_path.exists():
        pytest.skip("ROM file not available")
    
    interface = GameInterface(str(rom_path), headless=True)
    yield interface
    interface.close()

@pytest.fixture
def save_state_at_pewter():
    """Load a save state positioned at Pewter City."""
    return Path("tests/fixtures/pewter_city.state").read_bytes()

@pytest.fixture
def mock_claude_response():
    """Mock Claude API responses for agent testing."""
    return {
        "content": [
            {
                "type": "tool_use",
                "name": "move",
                "input": {"direction": "RIGHT", "tiles": 1}
            }
        ]
    }
```

---

## 13. Performance Considerations

### 13.1 Bottlenecks & Solutions

| Bottleneck | Impact | Solution |
|------------|--------|----------|
| Claude API latency | ~500ms-2s per call | Batch decisions, cache when possible |
| Screen encoding | ~10ms per frame | Encode in background thread |
| WebSocket broadcast | Blocks main loop | Async broadcast, rate limit |
| Memory reading | Negligible | N/A |
| Database writes | ~1ms per event | Batch writes, async |

### 13.2 Optimization Strategies

```python
# 1. Background screen encoding
class ScreenEncoder:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._last_screen: Optional[str] = None
    
    async def get_screen_base64(self, pyboy) -> str:
        """Encode screen in background thread."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._encode_screen,
            pyboy.screen_ndarray()
        )

# 2. Rate-limited broadcasting
class RateLimitedBroadcaster:
    def __init__(self, max_fps: int = 30):
        self.min_interval = 1.0 / max_fps
        self._last_broadcast = 0
    
    async def broadcast_if_due(self, data: dict):
        now = time.time()
        if now - self._last_broadcast >= self.min_interval:
            await self._broadcast(data)
            self._last_broadcast = now

# 3. Agent response caching
class AgentCache:
    """Cache identical state → action mappings."""
    def __init__(self, max_size: int = 1000):
        self._cache = LRUCache(max_size)
    
    def get_cached_action(self, state_hash: str) -> Optional[Action]:
        return self._cache.get(state_hash)
    
    def cache_action(self, state_hash: str, action: Action):
        self._cache[state_hash] = action
```

### 13.3 Resource Usage Targets

| Resource | Target | Maximum |
|----------|--------|---------|
| CPU | <50% (single core) | 100% |
| Memory | <500MB | 1GB |
| API calls/hour | ~500-1000 | 2000 |
| WebSocket bandwidth | <1MB/s | 5MB/s |

---

## 14. Future Enhancements

### 14.1 Planned Features (v2)

| Feature | Description | Priority |
|---------|-------------|----------|
| Multi-run comparison | Compare different agent configurations | High |
| Replay system | Record and playback runs | High |
| Manual override | Take control from AI temporarily | Medium |
| Statistics dashboard | Detailed analytics and charts | Medium |
| Discord integration | Stream to Discord channel | Low |

### 14.2 Scalability Path

```
v1.0 (Current)              v2.0 (Future)
┌─────────────────┐         ┌─────────────────┐
│ Single instance │         │ Multi-instance  │
│ Local only      │  ───▶   │ Cloud optional  │
│ SQLite          │         │ PostgreSQL      │
│ File storage    │         │ S3 storage      │
└─────────────────┘         └─────────────────┘

v3.0 (Eventual)
┌─────────────────┐
│ Distributed     │
│ Multiple games  │
│ Tournament mode │
│ Public API      │
└─────────────────┘
```

### 14.3 Research Extensions

| Extension | Description |
|-----------|-------------|
| Alternative models | Compare Claude vs GPT-4 vs local models |
| Reinforcement learning | Hybrid AI + RL approach |
| Speedrun optimization | Optimize for completion time |
| Nuzlocke mode | Add permadeath challenge rules |

---

## Appendix A: Memory Map Reference

```python
# Key Pokemon Red (US) memory addresses

PLAYER_ADDRESSES = {
    "MAP_ID": 0xD35E,
    "PLAYER_Y": 0xD361,
    "PLAYER_X": 0xD362,
    "PLAYER_DIRECTION": 0xC109,
    "PLAYER_MOVING": 0xC108,
}

PARTY_ADDRESSES = {
    "PARTY_COUNT": 0xD163,
    "PARTY_SPECIES_LIST": 0xD164,  # 6 bytes
    "PARTY_DATA_START": 0xD16B,    # 44 bytes per Pokemon
    "PARTY_NICKNAMES": 0xD2B5,     # 11 bytes per nickname
}

BATTLE_ADDRESSES = {
    "BATTLE_TYPE": 0xD057,
    "ENEMY_SPECIES": 0xCFE5,
    "ENEMY_HP": 0xCFE6,            # 2 bytes
    "ENEMY_LEVEL": 0xCFF3,
    "ENEMY_STATUS": 0xCFE9,
    "PLAYER_SELECTED_MOVE": 0xCCDC,
    "ENEMY_MOVE": 0xCFCC,
}

INVENTORY_ADDRESSES = {
    "MONEY": 0xD347,               # 3 bytes, BCD
    "ITEM_COUNT": 0xD31D,
    "ITEMS_START": 0xD31E,         # 2 bytes per item (id, quantity)
    "PC_ITEM_COUNT": 0xD53A,
}

PROGRESS_ADDRESSES = {
    "BADGES": 0xD356,              # Bit flags
    "EVENT_FLAGS": 0xD747,         # Multiple bytes
    "POKEDEX_OWNED": 0xD2F7,       # Bit flags
    "POKEDEX_SEEN": 0xD30A,        # Bit flags
}

MENU_ADDRESSES = {
    "MENU_OPEN": 0xD730,
    "MENU_ITEM_INDEX": 0xCC26,
    "TEXT_BOX_OPEN": 0xC4F2,
    "CURRENT_BOX": 0xDA80,
}
```

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **Agent** | AI component responsible for specific game domain (navigation, battle, etc.) |
| **Orchestrator** | Central coordinator that routes control between agents |
| **GameState** | Complete snapshot of current game state |
| **Knowledge Base** | Static JSON data about Pokemon, moves, maps, etc. |
| **Save State** | Emulator snapshot for checkpointing/recovery |
| **PyBoy** | Python Game Boy emulator library |
| **HM** | Hidden Machine - teaches field moves like Cut, Surf |
| **STAB** | Same Type Attack Bonus (1.5x damage) |

---

*End of Technical Design Document*
