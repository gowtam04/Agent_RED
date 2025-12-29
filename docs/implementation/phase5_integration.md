# Phase 5: Integration

## Objective
Integrate all components into a working system: update the game loop, enhance the state reader, and ensure all agents work together.

## Prerequisites
- Phase 1 complete (knowledge bases)
- Phase 2 complete (agent framework)
- Phase 3 complete (agent implementations)
- Phase 4 complete (pathfinding)

---

## Overview

This phase connects everything together:
1. Update `src/main.py` to use the Orchestrator-based game loop
2. Enhance `src/emulator/state_reader.py` with additional memory reads
3. Add proper error handling and recovery
4. Create integration tests
5. Add save state management

---

## 1. Updated Game Loop (`src/main.py`)

Replace the existing SimpleAgent-based loop with the Orchestrator pattern.

```python
"""Main entry point for the Pokemon Red AI Agent."""

import logging
import time
from pathlib import Path
from typing import Optional

from src.config import Settings
from src.emulator import EmulatorInterface
from src.emulator.state_reader import StateReader
from src.agent import AgentRegistry, GameState, Objective

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GameLoop:
    """Main game loop using multi-agent architecture."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.emulator = EmulatorInterface(
            rom_path=Path(self.settings.rom_path),
            headless=self.settings.headless,
            emulation_speed=self.settings.emulation_speed,
        )
        self.state_reader = StateReader(self.emulator)
        self.registry = AgentRegistry()
        self.state = GameState()

        # Timing
        self.last_checkpoint = time.time()
        self.checkpoint_interval = 300  # 5 minutes

        # Initial objective
        self._set_initial_objective()

    def _set_initial_objective(self) -> None:
        """Set the initial high-level objective."""
        # Default: become Pokemon Champion
        self.state.push_objective(Objective(
            type="become_champion",
            target="Elite Four",
            priority=1,
        ))

    def run(self) -> None:
        """Main game loop."""
        logger.info("Starting Pokemon Red AI Agent")

        try:
            while True:
                self._tick()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.emulator.close()

    def _tick(self) -> None:
        """Single iteration of the game loop."""
        # 1. Read current game state
        self._update_state()

        # 2. Get Orchestrator
        orchestrator = self.registry.get_agent("ORCHESTRATOR")

        # 3. Orchestrator decides what to do
        result = orchestrator.act(self.state)

        if not result.success:
            logger.warning(f"Orchestrator failed: {result.error}")
            self._handle_failure(result)
            return

        # 4. If Orchestrator routes to another agent, execute that agent
        if result.handoff_to:
            agent = self.registry.get_agent(result.handoff_to)

            # Check for Opus escalation
            if result.result_data.get("escalate_to_opus"):
                agent.model = "opus"

            agent_result = agent.act(self.state)

            if not agent_result.success:
                logger.warning(f"{result.handoff_to} agent failed: {agent_result.error}")
                self._handle_failure(agent_result)

            # Process new objectives from agent
            for obj in agent_result.new_objectives:
                self.state.push_objective(obj)

        # 5. Handle any new objectives from orchestrator
        for obj in result.new_objectives:
            self.state.push_objective(obj)

        # 6. Checkpoint periodically
        self._maybe_checkpoint()

        # 7. Small delay to prevent hammering
        time.sleep(0.1)

    def _update_state(self) -> None:
        """Update game state from emulator."""
        raw_state = self.state_reader.read_state()

        # Update position
        self.state.position.map_id = raw_state.map_id
        self.state.position.x = raw_state.player_x
        self.state.position.y = raw_state.player_y
        self.state.position.facing = raw_state.player_direction

        # Update party
        self.state.party = self._convert_party(raw_state.party)

        # Update progression
        self.state.badges = raw_state.badges
        self.state.money = raw_state.money

        # Detect game mode
        self.state.mode = self._detect_mode(raw_state)

        # Update battle state if in battle
        if self.state.mode == "BATTLE":
            self.state.battle = self._read_battle_state(raw_state)
        else:
            self.state.battle = None

    def _detect_mode(self, raw_state) -> str:
        """Detect current game mode."""
        if raw_state.battle_type > 0:
            return "BATTLE"
        if raw_state.in_menu:
            return "MENU"
        if raw_state.in_dialogue:
            return "DIALOGUE"
        return "OVERWORLD"

    def _convert_party(self, raw_party) -> list:
        """Convert raw party data to Pokemon objects."""
        from src.agent import Pokemon, Stats, Move

        party = []
        for p in raw_party:
            pokemon = Pokemon(
                species=p.species,
                level=p.level,
                current_hp=p.current_hp,
                max_hp=p.max_hp,
                types=p.types,
                moves=[
                    Move(
                        name=m.name,
                        type=m.type,
                        category=self._get_move_category(m.type),
                        power=m.power,
                        accuracy=m.accuracy,
                        pp_current=m.pp_current,
                        pp_max=m.pp_max,
                    )
                    for m in p.moves
                ],
                stats=Stats(
                    hp=p.max_hp,
                    attack=p.attack,
                    defense=p.defense,
                    speed=p.speed,
                    special=p.special,
                ),
                status=p.status,
            )
            party.append(pokemon)
        return party

    def _get_move_category(self, move_type: str) -> str:
        """Determine move category based on type (Gen 1 rules)."""
        special_types = {"FIRE", "WATER", "ELECTRIC", "GRASS", "ICE", "PSYCHIC", "DRAGON"}
        return "SPECIAL" if move_type in special_types else "PHYSICAL"

    def _read_battle_state(self, raw_state) -> "BattleState":
        """Read detailed battle state."""
        from src.agent import BattleState, Pokemon, Stats

        battle_type = "WILD"
        if raw_state.battle_type == 2:
            battle_type = "TRAINER"
            # TODO: Detect gym leader, elite four, etc.

        enemy = raw_state.enemy_pokemon
        enemy_pokemon = Pokemon(
            species=enemy.species,
            level=enemy.level,
            current_hp=enemy.current_hp,
            max_hp=enemy.max_hp,
            types=enemy.types,
            moves=[],  # Enemy moves not always known
            stats=Stats(enemy.max_hp, 0, 0, 0, 0),  # Limited info
        )

        return BattleState(
            battle_type=battle_type,
            can_flee=battle_type == "WILD",
            can_catch=battle_type == "WILD",
            turn_number=raw_state.battle_turn,
            our_pokemon=self.state.party[0],  # Active Pokemon
            enemy_pokemon=enemy_pokemon,
        )

    def _handle_failure(self, result) -> None:
        """Handle agent failure with recovery."""
        logger.error(f"Agent failure: {result.error}")

        # Try to recover by loading last checkpoint
        if hasattr(self, '_last_save_state') and self._last_save_state:
            logger.info("Loading last checkpoint...")
            self.emulator.load_state(self._last_save_state)
        else:
            logger.warning("No checkpoint available, continuing...")

    def _maybe_checkpoint(self) -> None:
        """Create checkpoint if enough time has passed."""
        now = time.time()
        if now - self.last_checkpoint > self.checkpoint_interval:
            logger.info("Creating checkpoint...")
            self._last_save_state = self.emulator.save_state()
            self.last_checkpoint = now


def main():
    """Entry point."""
    settings = Settings()
    game = GameLoop(settings)
    game.run()


if __name__ == "__main__":
    main()
```

---

## 2. Enhanced State Reader (`src/emulator/state_reader.py`)

Add additional memory reads for battle state, menu detection, and dialogue.

```python
"""Enhanced state reader for the Pokemon Red AI Agent."""

from dataclasses import dataclass, field
from typing import Optional, List

from .interface import EmulatorInterface


# Memory Addresses (Pokemon Red US)
class MemoryAddresses:
    # Player
    MAP_ID = 0xD35E
    PLAYER_X = 0xD362
    PLAYER_Y = 0xD361
    PLAYER_DIRECTION = 0xC109

    # Party
    PARTY_COUNT = 0xD163
    PARTY_SPECIES_START = 0xD164
    PARTY_DATA_START = 0xD16B

    # Battle
    BATTLE_TYPE = 0xD057  # 0=none, 1=wild, 2=trainer
    BATTLE_TURN = 0xCCD5
    ENEMY_SPECIES = 0xCFE5
    ENEMY_LEVEL = 0xCFF3
    ENEMY_HP_CURRENT = 0xCFE6  # 2 bytes
    ENEMY_HP_MAX = 0xCFF4  # 2 bytes
    ENEMY_STATUS = 0xCFE9

    # Player Pokemon in battle
    BATTLE_MON_SPECIES = 0xD014
    BATTLE_MON_HP = 0xD015  # 2 bytes
    BATTLE_MON_STATUS = 0xD018

    # Progression
    BADGES = 0xD356
    MONEY = 0xD347  # 3 bytes BCD

    # Menu/Dialogue
    MENU_OPEN = 0xD730  # Various flags
    TEXT_BOX_ID = 0xCF94
    DIALOGUE_INDEX = 0xCF8B

    # Inventory
    BAG_ITEM_COUNT = 0xD31D
    BAG_ITEMS_START = 0xD31E


@dataclass
class RawPokemon:
    species: str
    level: int
    current_hp: int
    max_hp: int
    status: Optional[str]
    types: List[str]
    attack: int
    defense: int
    speed: int
    special: int
    moves: List["RawMove"] = field(default_factory=list)


@dataclass
class RawMove:
    name: str
    type: str
    power: int
    accuracy: int
    pp_current: int
    pp_max: int


@dataclass
class RawGameState:
    # Position
    map_id: str
    player_x: int
    player_y: int
    player_direction: str

    # Party
    party: List[RawPokemon]

    # Progression
    badges: List[str]
    money: int

    # Battle
    battle_type: int  # 0=none, 1=wild, 2=trainer
    battle_turn: int
    enemy_pokemon: Optional[RawPokemon]

    # UI State
    in_menu: bool
    in_dialogue: bool


class StateReader:
    """Reads game state from emulator memory."""

    # Species ID to name mapping (partial)
    SPECIES_NAMES = {
        1: "BULBASAUR", 2: "IVYSAUR", 3: "VENUSAUR",
        4: "CHARMANDER", 5: "CHARMELEON", 6: "CHARIZARD",
        7: "SQUIRTLE", 8: "WARTORTLE", 9: "BLASTOISE",
        25: "PIKACHU", 26: "RAICHU",
        # ... complete mapping
    }

    # Direction byte to name
    DIRECTIONS = {
        0: "DOWN", 4: "UP", 8: "LEFT", 12: "RIGHT"
    }

    # Status byte to name
    STATUS_MAP = {
        0x00: None,
        0x04: "POISON",
        0x08: "BURN",
        0x10: "FREEZE",
        0x20: "PARALYSIS",
        0x40: "SLEEP",
    }

    # Badge names by bit position
    BADGE_NAMES = [
        "BOULDER", "CASCADE", "THUNDER", "RAINBOW",
        "SOUL", "MARSH", "VOLCANO", "EARTH"
    ]

    def __init__(self, emulator: EmulatorInterface):
        self.emulator = emulator

    def read_state(self) -> RawGameState:
        """Read complete game state."""
        return RawGameState(
            # Position
            map_id=self._read_map_id(),
            player_x=self._read_byte(MemoryAddresses.PLAYER_X),
            player_y=self._read_byte(MemoryAddresses.PLAYER_Y),
            player_direction=self._read_direction(),

            # Party
            party=self._read_party(),

            # Progression
            badges=self._read_badges(),
            money=self._read_money(),

            # Battle
            battle_type=self._read_byte(MemoryAddresses.BATTLE_TYPE),
            battle_turn=self._read_byte(MemoryAddresses.BATTLE_TURN),
            enemy_pokemon=self._read_enemy_pokemon(),

            # UI State
            in_menu=self._is_menu_open(),
            in_dialogue=self._is_dialogue_active(),
        )

    def _read_byte(self, address: int) -> int:
        """Read a single byte from memory."""
        return self.emulator.read_memory(address)

    def _read_word(self, address: int) -> int:
        """Read a 16-bit word (little endian)."""
        low = self.emulator.read_memory(address)
        high = self.emulator.read_memory(address + 1)
        return (high << 8) | low

    def _read_map_id(self) -> str:
        """Read current map ID."""
        map_byte = self._read_byte(MemoryAddresses.MAP_ID)
        # TODO: Map byte to map name using knowledge base
        return f"MAP_{map_byte:02X}"

    def _read_direction(self) -> str:
        """Read player facing direction."""
        dir_byte = self._read_byte(MemoryAddresses.PLAYER_DIRECTION)
        return self.DIRECTIONS.get(dir_byte, "DOWN")

    def _read_party(self) -> List[RawPokemon]:
        """Read party Pokemon."""
        party = []
        count = self._read_byte(MemoryAddresses.PARTY_COUNT)

        for i in range(min(count, 6)):
            species_id = self._read_byte(MemoryAddresses.PARTY_SPECIES_START + i)

            # Read Pokemon data structure (44 bytes per Pokemon)
            base = MemoryAddresses.PARTY_DATA_START + (i * 44)

            pokemon = RawPokemon(
                species=self.SPECIES_NAMES.get(species_id, f"UNKNOWN_{species_id}"),
                level=self._read_byte(base + 33),
                current_hp=self._read_word(base + 1),
                max_hp=self._read_word(base + 34),
                status=self._read_status(base + 4),
                types=self._read_types(base + 5),
                attack=self._read_word(base + 36),
                defense=self._read_word(base + 38),
                speed=self._read_word(base + 40),
                special=self._read_word(base + 42),
                moves=self._read_pokemon_moves(base + 8),
            )
            party.append(pokemon)

        return party

    def _read_status(self, address: int) -> Optional[str]:
        """Read status condition."""
        status_byte = self._read_byte(address)
        if status_byte & 0x07:  # Sleep turns
            return "SLEEP"
        return self.STATUS_MAP.get(status_byte & 0xF8)

    def _read_types(self, address: int) -> List[str]:
        """Read Pokemon types."""
        type_names = [
            "NORMAL", "FIGHTING", "FLYING", "POISON", "GROUND",
            "ROCK", "BUG", "GHOST", "FIRE", "", "", "", "", "", "",
            "", "", "", "", "", "FIRE", "WATER", "GRASS", "ELECTRIC",
            "PSYCHIC", "ICE", "DRAGON"
        ]
        type1 = self._read_byte(address)
        type2 = self._read_byte(address + 1)

        types = [type_names[type1]] if type1 < len(type_names) else ["NORMAL"]
        if type1 != type2:
            types.append(type_names[type2] if type2 < len(type_names) else "NORMAL")

        return types

    def _read_pokemon_moves(self, address: int) -> List[RawMove]:
        """Read Pokemon's moves."""
        from src.knowledge import Moves

        moves = []
        moves_kb = Moves()

        for i in range(4):
            move_id = self._read_byte(address + i)
            if move_id == 0:
                continue

            pp = self._read_byte(address + 4 + i)  # PP is 4 bytes after moves

            # Look up move data
            move_data = moves_kb.get_by_id(move_id)
            if move_data:
                moves.append(RawMove(
                    name=move_data["name"],
                    type=move_data["type"],
                    power=move_data["power"],
                    accuracy=move_data["accuracy"],
                    pp_current=pp & 0x3F,  # Lower 6 bits
                    pp_max=move_data["pp"],
                ))

        return moves

    def _read_badges(self) -> List[str]:
        """Read obtained badges."""
        badge_byte = self._read_byte(MemoryAddresses.BADGES)
        badges = []
        for i, name in enumerate(self.BADGE_NAMES):
            if badge_byte & (1 << i):
                badges.append(name)
        return badges

    def _read_money(self) -> int:
        """Read money (BCD encoded)."""
        b1 = self._read_byte(MemoryAddresses.MONEY)
        b2 = self._read_byte(MemoryAddresses.MONEY + 1)
        b3 = self._read_byte(MemoryAddresses.MONEY + 2)

        # Decode BCD
        money = 0
        for b in [b1, b2, b3]:
            money = money * 100 + ((b >> 4) * 10) + (b & 0x0F)
        return money

    def _read_enemy_pokemon(self) -> Optional[RawPokemon]:
        """Read enemy Pokemon in battle."""
        battle_type = self._read_byte(MemoryAddresses.BATTLE_TYPE)
        if battle_type == 0:
            return None

        species_id = self._read_byte(MemoryAddresses.ENEMY_SPECIES)

        return RawPokemon(
            species=self.SPECIES_NAMES.get(species_id, f"UNKNOWN_{species_id}"),
            level=self._read_byte(MemoryAddresses.ENEMY_LEVEL),
            current_hp=self._read_word(MemoryAddresses.ENEMY_HP_CURRENT),
            max_hp=self._read_word(MemoryAddresses.ENEMY_HP_MAX),
            status=self._read_status(MemoryAddresses.ENEMY_STATUS),
            types=[],  # Would need to look up from knowledge base
            attack=0, defense=0, speed=0, special=0,  # Unknown for wild
        )

    def _is_menu_open(self) -> bool:
        """Check if a menu is currently open."""
        # Various menu flags at 0xD730
        flags = self._read_byte(MemoryAddresses.MENU_OPEN)
        return (flags & 0x08) != 0  # Bit 3 indicates menu

    def _is_dialogue_active(self) -> bool:
        """Check if dialogue is being displayed."""
        text_box = self._read_byte(MemoryAddresses.TEXT_BOX_ID)
        return text_box != 0
```

---

## 3. Startup Objective Configuration

Allow configuring the initial objective:

```python
# src/config.py additions

class Settings(BaseSettings):
    # ... existing settings ...

    # Game objective
    initial_objective: str = "become_champion"
    initial_objective_target: str = "Elite Four"

    # Agent settings
    use_opus_for_bosses: bool = True
    checkpoint_interval_seconds: int = 300


# In GameLoop._set_initial_objective():
def _set_initial_objective(self) -> None:
    """Set the initial high-level objective."""
    objective_map = {
        "become_champion": Objective(
            type="become_champion",
            target=self.settings.initial_objective_target,
            priority=1,
        ),
        "defeat_gym": Objective(
            type="defeat_gym",
            target=self.settings.initial_objective_target,
            priority=5,
        ),
        "catch_pokemon": Objective(
            type="catch_pokemon",
            target=self.settings.initial_objective_target,
            priority=3,
        ),
    }

    obj = objective_map.get(
        self.settings.initial_objective,
        objective_map["become_champion"]
    )
    self.state.push_objective(obj)
```

---

## 4. Integration Tests

**`tests/test_integration/test_game_loop.py`:**
```python
"""Integration tests for the game loop."""

import pytest
from unittest.mock import Mock, patch

from src.main import GameLoop
from src.agent import GameState, Objective


@pytest.fixture
def mock_emulator():
    """Create a mock emulator."""
    with patch("src.main.EmulatorInterface") as MockEmu:
        mock = MockEmu.return_value
        mock.read_memory.return_value = 0
        yield mock


@pytest.fixture
def game_loop(mock_emulator):
    """Create a GameLoop with mocked dependencies."""
    with patch("src.main.Settings") as MockSettings:
        MockSettings.return_value = Mock(
            rom_path="test.gb",
            headless=True,
            emulation_speed=0,
            initial_objective="become_champion",
            initial_objective_target="Elite Four",
        )
        return GameLoop()


def test_initial_objective(game_loop):
    """Test that initial objective is set."""
    assert game_loop.state.current_objective is not None
    assert game_loop.state.current_objective.type == "become_champion"


def test_mode_detection_overworld(game_loop, mock_emulator):
    """Test overworld mode detection."""
    mock_emulator.read_memory.side_effect = lambda addr: {
        0xD057: 0,  # No battle
        0xD730: 0,  # No menu
        0xCF94: 0,  # No dialogue
    }.get(addr, 0)

    game_loop._update_state()
    assert game_loop.state.mode == "OVERWORLD"


def test_mode_detection_battle(game_loop, mock_emulator):
    """Test battle mode detection."""
    mock_emulator.read_memory.side_effect = lambda addr: {
        0xD057: 1,  # Wild battle
    }.get(addr, 0)

    game_loop._update_state()
    assert game_loop.state.mode == "BATTLE"


def test_routing_to_navigation(game_loop):
    """Test that overworld routes to navigation agent."""
    game_loop.state.mode = "OVERWORLD"

    orchestrator = game_loop.registry.get_agent("ORCHESTRATOR")
    result = orchestrator._route_to_agent({"game_mode": "OVERWORLD"}, game_loop.state)

    assert result.result_data["agent"] == "NAVIGATION"


def test_routing_to_battle(game_loop):
    """Test that battle mode routes to battle agent."""
    game_loop.state.mode = "BATTLE"

    orchestrator = game_loop.registry.get_agent("ORCHESTRATOR")
    result = orchestrator._route_to_agent({"game_mode": "BATTLE"}, game_loop.state)

    assert result.result_data["agent"] == "BATTLE"
```

**`tests/test_integration/test_full_cycle.py`:**
```python
"""Full cycle integration tests with save states."""

import pytest
from pathlib import Path


@pytest.fixture
def save_state_path():
    """Path to a test save state."""
    return Path("tests/fixtures/test_save.state")


@pytest.mark.skipif(
    not Path("tests/fixtures/test_save.state").exists(),
    reason="Test save state not available"
)
def test_battle_cycle(save_state_path):
    """Test a complete battle cycle from save state."""
    from src.main import GameLoop

    # Load save state at start of a wild battle
    game = GameLoop()
    game.emulator.load_state(save_state_path)

    # Update state
    game._update_state()
    assert game.state.mode == "BATTLE"

    # Run a few ticks
    for _ in range(5):
        game._tick()

    # Battle should have progressed or ended
    game._update_state()
    # Assert based on expected outcome
```

---

## 5. CLI Entry Point

Update `pyproject.toml` for the new entry point:

```toml
[tool.poetry.scripts]
pokemon-agent = "src.main:main"
```

---

## 6. Logging Configuration

Add proper logging:

```python
# src/logging_config.py

import logging
import sys
from pathlib import Path


def setup_logging(log_dir: Path = Path("logs"), level: int = logging.INFO):
    """Configure logging for the application."""

    log_dir.mkdir(exist_ok=True)

    # Create formatters
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_formatter = logging.Formatter(
        "%(levelname)s: %(message)s"
    )

    # File handler
    file_handler = logging.FileHandler(log_dir / "agent.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Reduce noise from libraries
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
```

---

## 7. Error Recovery

Add robust error handling:

```python
# src/recovery.py

from dataclasses import dataclass
from typing import Optional
import logging

from src.agent import GameState, Objective

logger = logging.getLogger(__name__)


@dataclass
class RecoveryAction:
    """An action to recover from a failure."""
    type: str
    description: str
    objective: Optional[Objective] = None


def diagnose_failure(state: GameState, error: str) -> RecoveryAction:
    """Diagnose a failure and recommend recovery action."""

    # Common failure patterns
    if "stuck" in error.lower() or "no path" in error.lower():
        # Navigation stuck
        return RecoveryAction(
            type="fly_to_pokemon_center",
            description="Use Fly to return to last Pokemon Center",
            objective=Objective(type="fly", target=state.last_pokemon_center or "PALLET_TOWN"),
        )

    if "fainted" in error.lower() or state.fainted_count == len(state.party):
        # Party wiped
        return RecoveryAction(
            type="wait_for_respawn",
            description="Wait for respawn at Pokemon Center",
        )

    if "underleveled" in error.lower():
        # Need grinding
        return RecoveryAction(
            type="grind",
            description="Grind for experience",
            objective=Objective(type="grind", target="level_up", priority=8),
        )

    if "no money" in error.lower():
        # Broke
        return RecoveryAction(
            type="grind_money",
            description="Battle trainers for money",
            objective=Objective(type="grind", target="money", priority=7),
        )

    # Default: reload checkpoint
    return RecoveryAction(
        type="reload_checkpoint",
        description="Reload last checkpoint",
    )


def execute_recovery(action: RecoveryAction, game_loop: "GameLoop") -> bool:
    """Execute a recovery action."""
    logger.info(f"Executing recovery: {action.description}")

    if action.type == "reload_checkpoint":
        if hasattr(game_loop, '_last_save_state') and game_loop._last_save_state:
            game_loop.emulator.load_state(game_loop._last_save_state)
            return True
        return False

    if action.type == "fly_to_pokemon_center":
        if action.objective:
            game_loop.state.push_objective(action.objective)
        return True

    if action.type == "wait_for_respawn":
        # Just wait - game will respawn at Pokemon Center
        import time
        time.sleep(2)
        return True

    if action.type in ("grind", "grind_money"):
        if action.objective:
            game_loop.state.push_objective(action.objective)
        return True

    return False
```

---

## Success Criteria

- [ ] Game loop runs with Orchestrator as entry point
- [ ] Mode detection works (OVERWORLD/BATTLE/MENU/DIALOGUE)
- [ ] Agents route correctly based on mode
- [ ] Battle agent escalates to Opus for gym leaders
- [ ] State reader extracts all necessary data
- [ ] Checkpoints save every 5 minutes
- [ ] Error recovery handles common failures
- [ ] Integration tests pass
- [ ] Can run `poetry run pokemon-agent` and see agent playing

---

## Final Testing Checklist

1. [ ] Start game from fresh save - agent gets starter
2. [ ] Agent navigates Route 1 to Viridian City
3. [ ] Agent battles wild Pokemon appropriately
4. [ ] Agent heals at Pokemon Center when low
5. [ ] Agent progresses through first gym
6. [ ] Agent handles menu navigation correctly
7. [ ] Agent recovers from failures gracefully
8. [ ] Opus is used for gym leader battles
9. [ ] Logging captures agent decisions
10. [ ] Checkpoints allow resuming after crash

---

## Notes

- Test with actual ROM file for full validation
- Some memory addresses may vary by ROM version
- Consider adding metrics/telemetry for debugging
- The full species mapping should be loaded from knowledge base
