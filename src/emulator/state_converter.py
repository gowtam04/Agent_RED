"""Converts emulator raw state to agent semantic state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from src.agent.types import (
    BattleState as AgentBattleState,
    BattleType,
    GameMode as AgentGameMode,
    Move,
    MoveCategory,
    Pokemon as AgentPokemon,
    Position as AgentPosition,
    Stats,
)
from src.knowledge import MoveData, PokemonData

if TYPE_CHECKING:
    from src.agent.state import GameState as AgentGameState
    from src.emulator.state_reader import (
        BattleState as EmulatorBattleState,
        GameMode as EmulatorGameMode,
        GameState as EmulatorGameState,
        Pokemon as EmulatorPokemon,
    )


# Map constants file path
MAP_CONSTANTS_PATH = Path(__file__).parent.parent.parent / "data" / "maps" / "map_constants.json"


class StateConverter:
    """Converts emulator raw state to agent semantic state.

    This adapter bridges the gap between:
    - EmulatorGameState: Raw data read from memory (int map_id, minimal Pokemon data)
    - AgentGameState: Semantic state for agent decision-making (str map names, full Pokemon data)
    """

    def __init__(
        self,
        pokemon_data: PokemonData | None = None,
        move_data: MoveData | None = None,
    ):
        """Initialize the converter.

        Args:
            pokemon_data: Pokemon knowledge base accessor.
            move_data: Move knowledge base accessor.
        """
        self._pokemon_data = pokemon_data or PokemonData()
        self._move_data = move_data or MoveData()
        self._map_id_to_name = self._load_map_constants()

    def _load_map_constants(self) -> dict[int, str]:
        """Load map ID to name mapping from JSON."""
        try:
            with open(MAP_CONSTANTS_PATH) as f:
                data = json.load(f)
            # Convert string keys to int
            return {int(k): v for k, v in data.get("id_to_name", {}).items()}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def convert(
        self,
        raw: EmulatorGameState,
        agent_state: AgentGameState,
    ) -> None:
        """Convert emulator state and update agent state in-place.

        This updates the agent_state with data from the raw emulator state,
        while preserving agent-only fields like objectives, story_flags, etc.

        Args:
            raw: The raw emulator game state.
            agent_state: The agent game state to update (modified in-place).
        """
        # Convert game mode
        agent_state.mode = self._convert_mode(raw.mode)

        # Convert position
        agent_state.position = self._convert_position(raw.position)

        # Convert party
        agent_state.party = [
            self._convert_pokemon(p) for p in raw.party if p is not None
        ]

        # Sync progression data
        agent_state.badges = list(raw.badges)
        agent_state.money = raw.money

        # Convert battle state if in battle
        if raw.battle is not None:
            agent_state.battle = self._convert_battle_state(raw.battle, agent_state.party)
        else:
            agent_state.battle = None

        # Convert inventory
        agent_state.items = {}
        agent_state.key_items = []
        for inv_item in raw.inventory:
            item_name = inv_item.item_name
            # Check if it's a key item (rough heuristic - proper check needs knowledge base)
            key_item_names = {
                "BICYCLE", "TOWN_MAP", "POKEDEX", "OLD_AMBER", "DOME_FOSSIL",
                "HELIX_FOSSIL", "SECRET_KEY", "BIKE_VOUCHER", "CARD_KEY", "SS_TICKET",
                "GOLD_TEETH", "COIN_CASE", "OAKS_PARCEL", "ITEMFINDER", "SILPH_SCOPE",
                "POKE_FLUTE", "LIFT_KEY", "EXP_ALL", "OLD_ROD", "GOOD_ROD", "SUPER_ROD",
            }
            if item_name in key_item_names:
                if item_name not in agent_state.key_items:
                    agent_state.key_items.append(item_name)
            else:
                agent_state.items[item_name] = inv_item.count

        # Note: Agent-only fields are NOT touched:
        # - objective_stack (managed by orchestrator)
        # - story_flags (managed by progression tracking)
        # - hms_obtained, hms_usable (managed by game events)
        # - last_pokemon_center (managed by heal tracking)
        # - defeated_trainers (managed by battle completion)

    def _convert_mode(self, mode: EmulatorGameMode) -> AgentGameMode:
        """Convert emulator GameMode enum to agent GameMode literal."""
        mode_map: dict[str, AgentGameMode] = {
            "OVERWORLD": "OVERWORLD",
            "BATTLE": "BATTLE",
            "MENU": "MENU",
            "DIALOGUE": "DIALOGUE",
        }
        return mode_map.get(mode.name, "OVERWORLD")

    def _convert_position(self, pos) -> AgentPosition:
        """Convert emulator Position to agent Position."""
        map_name = self._map_id_to_name.get(pos.map_id, f"MAP_{pos.map_id:02X}")
        return AgentPosition(
            map_id=map_name,
            x=pos.x,
            y=pos.y,
            facing=pos.facing,
        )

    def _convert_pokemon(self, poke: EmulatorPokemon) -> AgentPokemon:
        """Convert emulator Pokemon to agent Pokemon with full data."""
        species_name = poke.species_name

        # Look up types from knowledge base
        pokemon_info = self._pokemon_data.get(species_name)
        types = pokemon_info.get("types", ["NORMAL"]) if pokemon_info else ["NORMAL"]

        # Use actual stats from memory if available, otherwise fall back to base stats
        if poke.stats is not None:
            stats = Stats(
                hp=poke.max_hp,
                attack=poke.stats.attack,
                defense=poke.stats.defense,
                speed=poke.stats.speed,
                special=poke.stats.special,
            )
        else:
            base_stats = pokemon_info.get("base_stats", {}) if pokemon_info else {}
            stats = Stats(
                hp=poke.max_hp,
                attack=base_stats.get("attack", 0),
                defense=base_stats.get("defense", 0),
                speed=base_stats.get("speed", 0),
                special=base_stats.get("special", 0),
            )

        # Convert moves from memory
        moves: list[Move] = []
        for raw_move in poke.moves:
            move = self.convert_move_id_to_move(raw_move.move_id, raw_move.pp_current)
            if move is not None:
                moves.append(move)

        return AgentPokemon(
            species=species_name,
            level=poke.level,
            current_hp=poke.current_hp,
            max_hp=poke.max_hp,
            types=types,
            moves=moves,
            stats=stats,
            status=poke.status,
        )

    def _convert_battle_state(
        self,
        battle: EmulatorBattleState,
        party: list[AgentPokemon],
    ) -> AgentBattleState:
        """Convert emulator BattleState to agent BattleState."""
        # Determine battle type
        battle_type: BattleType = "WILD" if battle.battle_type == "WILD" else "TRAINER"

        # Get our active Pokemon (first in party)
        our_pokemon = party[0] if party else self._create_empty_pokemon()

        # Create enemy Pokemon
        pokemon_info = self._pokemon_data.get(battle.enemy_species_name)
        enemy_types = pokemon_info.get("types", ["NORMAL"]) if pokemon_info else ["NORMAL"]

        # Estimate enemy max HP from percentage (rough estimate)
        estimated_max_hp = 100  # Default
        if battle.enemy_hp_percent > 0:
            estimated_max_hp = int(100 / battle.enemy_hp_percent * 100) if battle.enemy_hp_percent < 100 else 100
        estimated_current_hp = int(estimated_max_hp * battle.enemy_hp_percent / 100)

        enemy_pokemon = AgentPokemon(
            species=battle.enemy_species_name,
            level=battle.enemy_level,
            current_hp=estimated_current_hp,
            max_hp=estimated_max_hp,
            types=enemy_types,
            moves=[],  # Enemy moves not known
            stats=Stats(hp=estimated_max_hp, attack=0, defense=0, speed=0, special=0),
            status=None,
        )

        return AgentBattleState(
            battle_type=battle_type,
            can_flee=battle_type == "WILD",
            can_catch=battle_type == "WILD",
            turn_number=0,  # Will be populated after StateReader enhancement
            our_pokemon=our_pokemon,
            enemy_pokemon=enemy_pokemon,
            our_stat_stages={},
            enemy_stat_stages={},
            enemy_trainer=None,
            enemy_remaining=1,
        )

    def _create_empty_pokemon(self) -> AgentPokemon:
        """Create a placeholder empty Pokemon."""
        return AgentPokemon(
            species="UNKNOWN",
            level=1,
            current_hp=0,
            max_hp=0,
            types=["NORMAL"],
            moves=[],
            stats=Stats(hp=0, attack=0, defense=0, speed=0, special=0),
            status=None,
        )

    def convert_move_id_to_move(self, move_id: int, pp_current: int) -> Move | None:
        """Convert a move ID to a Move object using knowledge base.

        Args:
            move_id: The move ID from memory.
            pp_current: Current PP for this move.

        Returns:
            Move object or None if move not found.
        """
        if move_id == 0:
            return None

        move_data = self._move_data.get_by_id(move_id)
        if not move_data:
            return None

        category: MoveCategory
        if move_data.get("category") == "PHYSICAL":
            category = "PHYSICAL"
        elif move_data.get("category") == "SPECIAL":
            category = "SPECIAL"
        else:
            category = "STATUS"

        return Move(
            name=move_data["name"],
            type=move_data.get("type", "NORMAL"),
            category=category,
            power=move_data.get("power", 0),
            accuracy=move_data.get("accuracy", 100),
            pp_current=pp_current,
            pp_max=move_data.get("pp", 0),
            effect=move_data.get("effect"),
        )
