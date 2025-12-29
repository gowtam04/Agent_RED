# Phase 2: Agent Framework

## Objective
Build the multi-agent coordination infrastructure including base classes, shared state, and agent routing.

## Prerequisites
- Phase 1 complete (knowledge bases available in `data/`)
- Existing MVP code in `src/` (emulator interface, state reader)

---

## Deliverables

### 1. Shared Types (`src/agent/types.py`)

Define all shared types, enums, and dataclasses used across agents.

```python
"""Shared types for the Pokemon Red AI Agent system."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional

# Game Mode Detection
GameMode = Literal["OVERWORLD", "BATTLE", "MENU", "DIALOGUE"]

# Battle Types
BattleType = Literal["WILD", "TRAINER", "GYM_LEADER", "ELITE_FOUR", "CHAMPION", "RIVAL"]

# Directions
Direction = Literal["UP", "DOWN", "LEFT", "RIGHT"]

# Move Categories (Gen 1: determined by type)
MoveCategory = Literal["PHYSICAL", "SPECIAL", "STATUS"]

# Status Conditions
Status = Literal["POISON", "BURN", "SLEEP", "FREEZE", "PARALYSIS"]

# Tile Types
TileType = Literal["PATH", "GRASS", "WATER", "LEDGE", "DOOR", "CUT_TREE", "BOULDER", "WALL"]

# Menu Types
MenuType = Literal["START_MENU", "BAG", "PARTY", "PC", "SHOP", "DIALOGUE", "YES_NO", "MOVE_LEARN"]

# Agent Types
AgentType = Literal["ORCHESTRATOR", "NAVIGATION", "BATTLE", "MENU"]

# Model Selection
ModelType = Literal["haiku", "sonnet", "opus"]


@dataclass
class Position:
    """Player or entity position."""
    map_id: str
    x: int
    y: int
    facing: Direction = "DOWN"


@dataclass
class Stats:
    """Pokemon stats (Gen 1 style)."""
    hp: int
    attack: int
    defense: int
    speed: int
    special: int


@dataclass
class Move:
    """A Pokemon's move in battle."""
    name: str
    type: str
    category: MoveCategory
    power: int
    accuracy: int
    pp_current: int
    pp_max: int
    effect: Optional[str] = None


@dataclass
class Pokemon:
    """A Pokemon in the party or encountered."""
    species: str
    level: int
    current_hp: int
    max_hp: int
    types: list[str]
    moves: list[Move]
    stats: Stats
    status: Optional[Status] = None


@dataclass
class BattleState:
    """Current battle state."""
    battle_type: BattleType
    can_flee: bool
    can_catch: bool
    turn_number: int
    our_pokemon: Pokemon
    enemy_pokemon: Pokemon
    our_stat_stages: dict[str, int] = field(default_factory=dict)
    enemy_stat_stages: dict[str, int] = field(default_factory=dict)
    enemy_trainer: Optional[str] = None
    enemy_remaining: int = 1


@dataclass
class Objective:
    """An objective in the objective stack."""
    type: str  # navigate, defeat_gym, catch_pokemon, heal, grind, etc.
    target: str
    priority: int = 1
    requirements: list[str] = field(default_factory=list)
    completed: bool = False


@dataclass
class AgentResult:
    """Result returned by an agent after taking action."""
    success: bool
    action_taken: str
    result_data: dict = field(default_factory=dict)
    error: Optional[str] = None
    handoff_to: Optional[AgentType] = None
    new_objectives: list[Objective] = field(default_factory=list)
```

---

### 2. Enhanced Game State (`src/agent/state.py`)

Extend the existing GameState with objective management and more detailed tracking.

```python
"""Enhanced game state with objective management."""

from dataclasses import dataclass, field
from typing import Optional
from .types import (
    GameMode, Position, Pokemon, BattleState, Objective, Status
)


@dataclass
class GameState:
    """Complete game state shared across all agents."""

    # Current mode
    mode: GameMode = "OVERWORLD"

    # Player position
    position: Position = field(default_factory=lambda: Position("PALLET_TOWN", 0, 0))

    # Party Pokemon (up to 6)
    party: list[Pokemon] = field(default_factory=list)

    # Battle state (None if not in battle)
    battle: Optional[BattleState] = None

    # Progression
    badges: list[str] = field(default_factory=list)
    story_flags: list[str] = field(default_factory=list)
    hms_obtained: list[str] = field(default_factory=list)
    hms_usable: list[str] = field(default_factory=list)  # Have badge + taught

    # Inventory
    money: int = 0
    items: dict[str, int] = field(default_factory=dict)
    key_items: list[str] = field(default_factory=list)

    # Objective stack
    objective_stack: list[Objective] = field(default_factory=list)

    # Session tracking
    last_pokemon_center: Optional[str] = None
    defeated_trainers: set[str] = field(default_factory=set)

    @property
    def current_objective(self) -> Optional[Objective]:
        """Return the top objective on the stack."""
        return self.objective_stack[-1] if self.objective_stack else None

    @property
    def party_hp_percent(self) -> float:
        """Average HP percentage of party."""
        if not self.party:
            return 0.0
        return sum(p.current_hp / p.max_hp for p in self.party) / len(self.party) * 100

    @property
    def fainted_count(self) -> int:
        """Number of fainted Pokemon."""
        return sum(1 for p in self.party if p.current_hp == 0)

    @property
    def needs_healing(self) -> bool:
        """Check if party needs healing."""
        return self.party_hp_percent < 50 or self.fainted_count > 0

    def push_objective(self, objective: Objective) -> None:
        """Push a new objective onto the stack."""
        self.objective_stack.append(objective)

    def pop_objective(self) -> Optional[Objective]:
        """Pop and return the top objective."""
        return self.objective_stack.pop() if self.objective_stack else None

    def has_badge(self, badge: str) -> bool:
        """Check if player has a specific badge."""
        return badge in self.badges

    def can_use_hm(self, hm: str) -> bool:
        """Check if player can use a specific HM in the field."""
        return hm in self.hms_usable
```

---

### 3. Base Agent Class (`src/agent/base.py`)

Abstract base class that all agents inherit from.

```python
"""Base agent class with common functionality."""

from abc import ABC, abstractmethod
from typing import Any, Optional
import anthropic

from .types import AgentType, AgentResult, ModelType
from .state import GameState


class BaseAgent(ABC):
    """Base class for all specialized agents."""

    # Override in subclasses
    AGENT_TYPE: AgentType = "ORCHESTRATOR"
    DEFAULT_MODEL: ModelType = "sonnet"
    SYSTEM_PROMPT: str = ""

    def __init__(
        self,
        client: Optional[anthropic.Anthropic] = None,
        model: Optional[ModelType] = None,
    ):
        self.client = client or anthropic.Anthropic()
        self.model = model or self.DEFAULT_MODEL
        self.tools = self._register_tools()
        self.conversation_history: list[dict] = []

    @abstractmethod
    def _register_tools(self) -> list[dict]:
        """Return the tool definitions for this agent."""
        pass

    @abstractmethod
    def act(self, state: GameState) -> AgentResult:
        """Take an action based on the current game state."""
        pass

    def _get_model_id(self) -> str:
        """Convert model type to full model ID."""
        model_map = {
            "haiku": "claude-3-haiku-20240307",
            "sonnet": "claude-sonnet-4-20250514",
            "opus": "claude-opus-4-20250514",
        }
        return model_map[self.model]

    def _call_claude(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> anthropic.types.Message:
        """Make an API call to Claude."""
        return self.client.messages.create(
            model=self._get_model_id(),
            max_tokens=max_tokens,
            system=system or self.SYSTEM_PROMPT,
            tools=self.tools,
            messages=messages,
        )

    def _format_state_for_prompt(self, state: GameState) -> str:
        """Format the game state as a human-readable string for the prompt."""
        lines = [
            f"=== GAME STATE ===",
            f"Mode: {state.mode}",
            f"Location: {state.position.map_id} ({state.position.x}, {state.position.y})",
            f"Facing: {state.position.facing}",
            f"",
            f"=== PARTY ({len(state.party)} Pokemon) ===",
        ]

        for i, pokemon in enumerate(state.party):
            status = f" [{pokemon.status}]" if pokemon.status else ""
            hp_pct = pokemon.current_hp / pokemon.max_hp * 100
            lines.append(
                f"{i+1}. {pokemon.species} Lv{pokemon.level} "
                f"HP: {pokemon.current_hp}/{pokemon.max_hp} ({hp_pct:.0f}%){status}"
            )

        lines.extend([
            f"",
            f"=== PROGRESS ===",
            f"Badges: {', '.join(state.badges) if state.badges else 'None'}",
            f"Money: ${state.money}",
            f"HMs usable: {', '.join(state.hms_usable) if state.hms_usable else 'None'}",
        ])

        if state.current_objective:
            lines.extend([
                f"",
                f"=== CURRENT OBJECTIVE ===",
                f"Type: {state.current_objective.type}",
                f"Target: {state.current_objective.target}",
            ])

        if state.battle:
            lines.extend([
                f"",
                f"=== BATTLE ===",
                f"Type: {state.battle.battle_type}",
                f"Enemy: {state.battle.enemy_pokemon.species} Lv{state.battle.enemy_pokemon.level}",
                f"Enemy HP: ~{state.battle.enemy_pokemon.current_hp / state.battle.enemy_pokemon.max_hp * 100:.0f}%",
            ])

        return "\n".join(lines)

    def _process_tool_calls(
        self,
        response: anthropic.types.Message,
        state: GameState,
    ) -> AgentResult:
        """Process tool calls from Claude's response."""
        for block in response.content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input

                # Execute the tool
                result = self._execute_tool(tool_name, tool_input, state)
                return result

        # No tool call - extract text response
        text = ""
        for block in response.content:
            if block.type == "text":
                text = block.text
                break

        return AgentResult(
            success=True,
            action_taken="response",
            result_data={"text": text},
        )

    @abstractmethod
    def _execute_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        state: GameState,
    ) -> AgentResult:
        """Execute a specific tool. Implement in subclass."""
        pass
```

---

### 4. Agent Registry (`src/agent/registry.py`)

Registry for instantiating and routing to appropriate agents.

```python
"""Agent registry for routing and instantiation."""

from typing import Optional
import anthropic

from .types import AgentType, GameMode, ModelType
from .state import GameState
from .base import BaseAgent


class AgentRegistry:
    """Registry for managing agent instances and routing."""

    def __init__(self, client: Optional[anthropic.Anthropic] = None):
        self.client = client or anthropic.Anthropic()
        self._agents: dict[AgentType, BaseAgent] = {}

    def get_agent(self, agent_type: AgentType) -> BaseAgent:
        """Get or create an agent instance."""
        if agent_type not in self._agents:
            self._agents[agent_type] = self._create_agent(agent_type)
        return self._agents[agent_type]

    def _create_agent(self, agent_type: AgentType) -> BaseAgent:
        """Create a new agent instance."""
        # Import here to avoid circular imports
        from .orchestrator import OrchestratorAgent
        from .navigation import NavigationAgent
        from .battle import BattleAgent
        from .menu import MenuAgent

        agent_classes = {
            "ORCHESTRATOR": OrchestratorAgent,
            "NAVIGATION": NavigationAgent,
            "BATTLE": BattleAgent,
            "MENU": MenuAgent,
        }

        return agent_classes[agent_type](client=self.client)

    def route_by_mode(self, mode: GameMode) -> AgentType:
        """Determine which agent should handle the current mode."""
        mode_routing = {
            "OVERWORLD": "NAVIGATION",
            "BATTLE": "BATTLE",
            "MENU": "MENU",
            "DIALOGUE": "MENU",
        }
        return mode_routing[mode]

    def should_escalate_to_opus(self, state: GameState) -> bool:
        """Check if we should use Opus for the current battle."""
        if not state.battle:
            return False

        boss_types = {"GYM_LEADER", "ELITE_FOUR", "CHAMPION"}
        return state.battle.battle_type in boss_types
```

---

### 5. Objective Stack Manager (`src/agent/objective.py`)

Dedicated class for managing the objective stack with prerequisite handling.

```python
"""Objective stack management."""

from dataclasses import dataclass, field
from typing import Optional

from .types import Objective


@dataclass
class ObjectiveStack:
    """Manages the hierarchical objective stack."""

    _stack: list[Objective] = field(default_factory=list)

    def push(self, objective: Objective) -> None:
        """Push a new objective onto the stack."""
        self._stack.append(objective)

    def pop(self) -> Optional[Objective]:
        """Pop and return the top objective."""
        return self._stack.pop() if self._stack else None

    def peek(self) -> Optional[Objective]:
        """Return the top objective without removing it."""
        return self._stack[-1] if self._stack else None

    def is_empty(self) -> bool:
        """Check if the stack is empty."""
        return len(self._stack) == 0

    def size(self) -> int:
        """Return the number of objectives on the stack."""
        return len(self._stack)

    def clear_completed(self) -> int:
        """Remove all completed objectives. Returns count removed."""
        initial_size = len(self._stack)
        self._stack = [o for o in self._stack if not o.completed]
        return initial_size - len(self._stack)

    def get_all(self) -> list[Objective]:
        """Return all objectives (bottom to top)."""
        return list(self._stack)

    def mark_completed(self, objective_type: str, target: str) -> bool:
        """Mark a specific objective as completed."""
        for obj in self._stack:
            if obj.type == objective_type and obj.target == target:
                obj.completed = True
                return True
        return False


# Common objectives
def create_heal_objective() -> Objective:
    """Create a healing objective."""
    return Objective(
        type="heal",
        target="pokemon_center",
        priority=10,  # High priority
    )


def create_gym_objective(gym_leader: str, location: str) -> Objective:
    """Create a gym challenge objective."""
    return Objective(
        type="defeat_gym",
        target=gym_leader,
        priority=5,
        requirements=[f"navigate_to:{location}"],
    )


def create_catch_objective(species: str, reason: str) -> Objective:
    """Create a catch objective."""
    return Objective(
        type="catch_pokemon",
        target=species,
        priority=3,
        requirements=[reason],
    )
```

---

### 6. Tool Definitions (`src/tools/definitions.py`)

Copy the tool schemas from `docs/05_tool_schemas.md` for each agent.

```python
"""Tool definitions for all agents."""

ORCHESTRATOR_TOOLS = [
    {
        "name": "detect_game_mode",
        "description": "Analyzes the current game screen and memory state to determine the active game mode.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_current_objective",
        "description": "Returns the current objective from the objective stack.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
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
                }
            },
            "required": ["game_mode"]
        }
    },
    {
        "name": "manage_objective_stack",
        "description": "Push, pop, or peek at the objective stack.",
        "input_schema": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["push", "pop", "peek", "clear_completed"]
                },
                "objective": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "target": {"type": "string"},
                        "priority": {"type": "integer"}
                    }
                }
            },
            "required": ["operation"]
        }
    },
    # ... (copy remaining from docs/05_tool_schemas.md)
]

NAVIGATION_TOOLS = [
    # ... (copy from docs/05_tool_schemas.md)
]

BATTLE_TOOLS = [
    # ... (copy from docs/05_tool_schemas.md)
]

MENU_TOOLS = [
    # ... (copy from docs/05_tool_schemas.md)
]


def get_tools_for_agent(agent_type: str) -> list[dict]:
    """Get tool definitions for a specific agent type."""
    tools = {
        "ORCHESTRATOR": ORCHESTRATOR_TOOLS,
        "NAVIGATION": NAVIGATION_TOOLS,
        "BATTLE": BATTLE_TOOLS,
        "MENU": MENU_TOOLS,
    }
    return tools.get(agent_type, [])
```

---

### 7. Package Structure

Create `__init__.py` files:

**`src/agent/__init__.py`:**
```python
"""Agent module for Pokemon Red AI."""

from .types import (
    GameMode, BattleType, Direction, MoveCategory, Status,
    Position, Stats, Move, Pokemon, BattleState, Objective, AgentResult,
    AgentType, ModelType,
)
from .state import GameState
from .base import BaseAgent
from .registry import AgentRegistry
from .objective import ObjectiveStack

__all__ = [
    "GameMode", "BattleType", "Direction", "MoveCategory", "Status",
    "Position", "Stats", "Move", "Pokemon", "BattleState", "Objective", "AgentResult",
    "AgentType", "ModelType",
    "GameState",
    "BaseAgent",
    "AgentRegistry",
    "ObjectiveStack",
]
```

**`src/tools/__init__.py`:**
```python
"""Tool definitions module."""

from .definitions import (
    ORCHESTRATOR_TOOLS,
    NAVIGATION_TOOLS,
    BATTLE_TOOLS,
    MENU_TOOLS,
    get_tools_for_agent,
)

__all__ = [
    "ORCHESTRATOR_TOOLS",
    "NAVIGATION_TOOLS",
    "BATTLE_TOOLS",
    "MENU_TOOLS",
    "get_tools_for_agent",
]
```

---

## Directory Structure After Phase 2

```
src/
├── agent/
│   ├── __init__.py
│   ├── types.py         # Enums, dataclasses
│   ├── state.py         # GameState
│   ├── base.py          # BaseAgent
│   ├── registry.py      # AgentRegistry
│   └── objective.py     # ObjectiveStack
├── tools/
│   ├── __init__.py
│   └── definitions.py   # All tool schemas
├── knowledge/           # From Phase 1
├── emulator/            # Existing
└── main.py              # Existing (updated in Phase 5)
```

---

## Testing

Create tests for the framework:

**`tests/test_agent/test_types.py`:**
```python
def test_position_creation():
    from src.agent import Position
    pos = Position("PALLET_TOWN", 5, 10, "UP")
    assert pos.map_id == "PALLET_TOWN"
    assert pos.x == 5
    assert pos.y == 10
    assert pos.facing == "UP"

def test_objective_creation():
    from src.agent import Objective
    obj = Objective(type="defeat_gym", target="Brock", priority=5)
    assert obj.type == "defeat_gym"
    assert obj.completed == False
```

**`tests/test_agent/test_state.py`:**
```python
def test_game_state_objectives():
    from src.agent import GameState, Objective
    state = GameState()

    obj = Objective(type="heal", target="pokemon_center")
    state.push_objective(obj)

    assert state.current_objective == obj
    assert state.pop_objective() == obj
    assert state.current_objective is None

def test_party_hp_percent():
    from src.agent import GameState, Pokemon, Move, Stats
    state = GameState()
    state.party = [
        Pokemon(
            species="PIKACHU", level=25,
            current_hp=30, max_hp=55,
            types=["ELECTRIC"], moves=[],
            stats=Stats(55, 55, 30, 90, 50)
        )
    ]
    assert state.party_hp_percent == (30/55) * 100
```

**`tests/test_agent/test_registry.py`:**
```python
def test_route_by_mode():
    from src.agent import AgentRegistry
    registry = AgentRegistry()

    assert registry.route_by_mode("OVERWORLD") == "NAVIGATION"
    assert registry.route_by_mode("BATTLE") == "BATTLE"
    assert registry.route_by_mode("MENU") == "MENU"
```

---

## Success Criteria

- [ ] All type definitions in `src/agent/types.py`
- [ ] `GameState` with objective stack management
- [ ] `BaseAgent` abstract class with Claude API integration
- [ ] `AgentRegistry` for routing
- [ ] `ObjectiveStack` helper class
- [ ] All tool definitions copied from docs
- [ ] Package `__init__.py` files created
- [ ] Unit tests pass for all components
- [ ] Type checking passes (`mypy src/agent`)
- [ ] Linting passes (`ruff check src/agent`)

---

## Notes

- This phase does NOT implement the actual agents - just the framework
- Agents will be implemented in Phases 3 (agents) and Phase 4 (tools)
- The `BaseAgent._execute_tool()` method is abstract and implemented per agent
- Tool definitions should be copied verbatim from `docs/05_tool_schemas.md`
