"""Game state reader for Pokemon Red - extracts game state from memory."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .interface import EmulatorInterface


class GameMode(Enum):
    """Current game mode/context."""

    OVERWORLD = auto()  # Walking around in the world
    BATTLE = auto()  # In a Pokemon battle
    MENU = auto()  # In the start menu or sub-menu
    DIALOGUE = auto()  # Talking to NPC or reading sign
    TITLE_SCREEN = auto()  # At title/start screen
    UNKNOWN = auto()  # Unable to determine


@dataclass
class Position:
    """Player's current position in the game world."""

    map_id: int
    x: int
    y: int
    facing: str  # "UP", "DOWN", "LEFT", "RIGHT"

    def __str__(self) -> str:
        return f"Map {self.map_id} at ({self.x}, {self.y}) facing {self.facing}"


@dataclass
class RawMove:
    """Raw move data read from memory."""

    move_id: int
    pp_current: int
    pp_ups: int = 0  # Number of PP Ups applied (0-3)


@dataclass
class RawStats:
    """Raw stats read from memory."""

    attack: int
    defense: int
    speed: int
    special: int


@dataclass
class Pokemon:
    """Data for a single Pokemon."""

    species_id: int
    species_name: str
    level: int
    current_hp: int
    max_hp: int
    status: Optional[str] = None  # None, "POISON", "BURN", "SLEEP", etc.
    moves: list[RawMove] = field(default_factory=list)
    stats: Optional[RawStats] = None

    @property
    def hp_percent(self) -> float:
        """Get HP as a percentage."""
        if self.max_hp == 0:
            return 0.0
        return (self.current_hp / self.max_hp) * 100

    @property
    def is_fainted(self) -> bool:
        """Check if Pokemon has fainted."""
        return self.current_hp == 0

    def __str__(self) -> str:
        status = f" [{self.status}]" if self.status else ""
        return f"{self.species_name} Lv.{self.level} ({self.current_hp}/{self.max_hp} HP){status}"


@dataclass
class BattleState:
    """State of the current battle (if in battle)."""

    battle_type: str  # "WILD", "TRAINER"
    enemy_species_id: int
    enemy_species_name: str
    enemy_level: int
    enemy_hp_percent: float  # Estimated, since we can't always read exact HP

    def __str__(self) -> str:
        return f"{self.battle_type} battle vs {self.enemy_species_name} Lv.{self.enemy_level}"


@dataclass
class InventoryItem:
    """An item in the player's bag."""

    item_id: int
    item_name: str
    count: int


@dataclass
class GameState:
    """Complete snapshot of the current game state."""

    mode: GameMode
    position: Position
    party: list[Pokemon] = field(default_factory=list)
    party_count: int = 0
    badges: list[str] = field(default_factory=list)
    badge_count: int = 0
    money: int = 0
    frame_count: int = 0
    battle: Optional[BattleState] = None
    inventory: list[InventoryItem] = field(default_factory=list)

    @property
    def in_battle(self) -> bool:
        """Check if currently in a battle."""
        return self.mode == GameMode.BATTLE

    @property
    def lead_pokemon(self) -> Optional[Pokemon]:
        """Get the first Pokemon in the party."""
        return self.party[0] if self.party else None

    @property
    def party_hp_percent(self) -> float:
        """Get average HP percentage of party."""
        if not self.party:
            return 0.0
        total_hp = sum(p.current_hp for p in self.party)
        total_max = sum(p.max_hp for p in self.party)
        if total_max == 0:
            return 0.0
        return (total_hp / total_max) * 100

    def summary(self) -> str:
        """Get a human-readable summary of the game state."""
        lines = [
            f"Mode: {self.mode.name}",
            f"Location: {self.position}",
            f"Party ({self.party_count}): {', '.join(str(p) for p in self.party) or 'Empty'}",
            f"Badges: {', '.join(self.badges) if self.badges else 'None'} ({self.badge_count})",
            f"Money: ${self.money:,}",
        ]
        if self.battle:
            lines.append(f"Battle: {self.battle}")
        return "\n".join(lines)


class StateReader:
    """
    Reads game state from Pokemon Red memory.

    Memory addresses are for Pokemon Red (US) version.
    """

    # ─────────────────────────────────────────────────────────
    # MEMORY ADDRESSES
    # ─────────────────────────────────────────────────────────

    class Addr:
        """Memory addresses for Pokemon Red (US)."""

        # Player position
        MAP_ID = 0xD35E
        PLAYER_Y = 0xD361
        PLAYER_X = 0xD362
        PLAYER_DIRECTION = 0xC109

        # Party data
        PARTY_COUNT = 0xD163
        PARTY_SPECIES = 0xD164  # 6 bytes, one per slot
        PARTY_DATA_START = 0xD16B  # 44 bytes per Pokemon

        # Party Pokemon structure offsets (from base of each Pokemon's data)
        # Each Pokemon is 44 bytes
        POKE_SPECIES = 0x00
        POKE_HP_CURRENT = 0x01  # 2 bytes
        POKE_STATUS = 0x04
        POKE_TYPE1 = 0x05
        POKE_TYPE2 = 0x06
        POKE_MOVE1 = 0x08
        POKE_MOVE2 = 0x09
        POKE_MOVE3 = 0x0A
        POKE_MOVE4 = 0x0B
        POKE_EXP = 0x0E  # 3 bytes
        POKE_HP_EV = 0x11  # 2 bytes
        POKE_ATK_EV = 0x13  # 2 bytes
        POKE_DEF_EV = 0x15  # 2 bytes
        POKE_SPD_EV = 0x17  # 2 bytes
        POKE_SPC_EV = 0x19  # 2 bytes
        POKE_IVS = 0x1B  # 2 bytes
        POKE_PP1 = 0x1D
        POKE_PP2 = 0x1E
        POKE_PP3 = 0x1F
        POKE_PP4 = 0x20
        POKE_LEVEL = 0x21
        POKE_HP_MAX = 0x22  # 2 bytes
        POKE_ATK = 0x24  # 2 bytes
        POKE_DEF = 0x26  # 2 bytes
        POKE_SPD = 0x28  # 2 bytes
        POKE_SPC = 0x2A  # 2 bytes

        # Battle state
        BATTLE_TYPE = 0xD057  # 0=none, 1=wild, 2=trainer
        BATTLE_TURN = 0xCCD5
        ENEMY_SPECIES = 0xCFE5
        ENEMY_LEVEL = 0xCFF3
        ENEMY_HP_CURRENT = 0xCFE6  # 2 bytes
        ENEMY_HP_MAX = 0xCFF4  # 2 bytes
        ENEMY_STATUS = 0xCFE9

        # Game state flags
        MENU_OPEN = 0xD730
        TEXT_BOX_OPEN = 0xC4F2
        DIALOGUE_INDEX = 0xCF8B
        TEXT_BOX_ID = 0xCF94

        # Progress
        MONEY = 0xD347  # 3 bytes, BCD encoded
        BADGES = 0xD356  # Bit flags

        # Inventory
        BAG_ITEM_COUNT = 0xD31D
        BAG_ITEMS_START = 0xD31E  # Item ID, Count pairs

    # Pokemon species names (Gen 1, indices 1-151)
    # Simplified list - full implementation would load from knowledge base
    POKEMON_NAMES = {
        0: "???",
        1: "BULBASAUR",
        2: "IVYSAUR",
        3: "VENUSAUR",
        4: "CHARMANDER",
        5: "CHARMELEON",
        6: "CHARIZARD",
        7: "SQUIRTLE",
        8: "WARTORTLE",
        9: "BLASTOISE",
        10: "CATERPIE",
        11: "METAPOD",
        12: "BUTTERFREE",
        13: "WEEDLE",
        14: "KAKUNA",
        15: "BEEDRILL",
        16: "PIDGEY",
        17: "PIDGEOTTO",
        18: "PIDGEOT",
        19: "RATTATA",
        20: "RATICATE",
        21: "SPEAROW",
        22: "FEAROW",
        23: "EKANS",
        24: "ARBOK",
        25: "PIKACHU",
        26: "RAICHU",
        27: "SANDSHREW",
        28: "SANDSLASH",
        29: "NIDORAN♀",
        30: "NIDORINA",
        31: "NIDOQUEEN",
        32: "NIDORAN♂",
        33: "NIDORINO",
        34: "NIDOKING",
        35: "CLEFAIRY",
        36: "CLEFABLE",
        37: "VULPIX",
        38: "NINETALES",
        39: "JIGGLYPUFF",
        40: "WIGGLYTUFF",
        41: "ZUBAT",
        42: "GOLBAT",
        43: "ODDISH",
        44: "GLOOM",
        45: "VILEPLUME",
        46: "PARAS",
        47: "PARASECT",
        48: "VENONAT",
        49: "VENOMOTH",
        50: "DIGLETT",
        51: "DUGTRIO",
        52: "MEOWTH",
        53: "PERSIAN",
        54: "PSYDUCK",
        55: "GOLDUCK",
        56: "MANKEY",
        57: "PRIMEAPE",
        58: "GROWLITHE",
        59: "ARCANINE",
        60: "POLIWAG",
        61: "POLIWHIRL",
        62: "POLIWRATH",
        63: "ABRA",
        64: "KADABRA",
        65: "ALAKAZAM",
        66: "MACHOP",
        67: "MACHOKE",
        68: "MACHAMP",
        69: "BELLSPROUT",
        70: "WEEPINBELL",
        71: "VICTREEBEL",
        72: "TENTACOOL",
        73: "TENTACRUEL",
        74: "GEODUDE",
        75: "GRAVELER",
        76: "GOLEM",
        77: "PONYTA",
        78: "RAPIDASH",
        79: "SLOWPOKE",
        80: "SLOWBRO",
        81: "MAGNEMITE",
        82: "MAGNETON",
        83: "FARFETCH'D",
        84: "DODUO",
        85: "DODRIO",
        86: "SEEL",
        87: "DEWGONG",
        88: "GRIMER",
        89: "MUK",
        90: "SHELLDER",
        91: "CLOYSTER",
        92: "GASTLY",
        93: "HAUNTER",
        94: "GENGAR",
        95: "ONIX",
        96: "DROWZEE",
        97: "HYPNO",
        98: "KRABBY",
        99: "KINGLER",
        100: "VOLTORB",
        101: "ELECTRODE",
        102: "EXEGGCUTE",
        103: "EXEGGUTOR",
        104: "CUBONE",
        105: "MAROWAK",
        106: "HITMONLEE",
        107: "HITMONCHAN",
        108: "LICKITUNG",
        109: "KOFFING",
        110: "WEEZING",
        111: "RHYHORN",
        112: "RHYDON",
        113: "CHANSEY",
        114: "TANGELA",
        115: "KANGASKHAN",
        116: "HORSEA",
        117: "SEADRA",
        118: "GOLDEEN",
        119: "SEAKING",
        120: "STARYU",
        121: "STARMIE",
        122: "MR. MIME",
        123: "SCYTHER",
        124: "JYNX",
        125: "ELECTABUZZ",
        126: "MAGMAR",
        127: "PINSIR",
        128: "TAUROS",
        129: "MAGIKARP",
        130: "GYARADOS",
        131: "LAPRAS",
        132: "DITTO",
        133: "EEVEE",
        134: "VAPOREON",
        135: "JOLTEON",
        136: "FLAREON",
        137: "PORYGON",
        138: "OMANYTE",
        139: "OMASTAR",
        140: "KABUTO",
        141: "KABUTOPS",
        142: "AERODACTYL",
        143: "SNORLAX",
        144: "ARTICUNO",
        145: "ZAPDOS",
        146: "MOLTRES",
        147: "DRATINI",
        148: "DRAGONAIR",
        149: "DRAGONITE",
        150: "MEWTWO",
        151: "MEW",
    }

    BADGE_NAMES = [
        "BOULDER",
        "CASCADE",
        "THUNDER",
        "RAINBOW",
        "SOUL",
        "MARSH",
        "VOLCANO",
        "EARTH",
    ]

    DIRECTION_MAP = {
        0: "DOWN",
        4: "UP",
        8: "LEFT",
        12: "RIGHT",
    }

    def __init__(self, emulator: "EmulatorInterface"):
        """
        Initialize the state reader.

        Args:
            emulator: The emulator interface to read from
        """
        self._emu = emulator

    # ─────────────────────────────────────────────────────────
    # POSITION READING
    # ─────────────────────────────────────────────────────────

    def get_position(self) -> Position:
        """Read the player's current position."""
        map_id = self._emu.read_memory(self.Addr.MAP_ID)
        x = self._emu.read_memory(self.Addr.PLAYER_X)
        y = self._emu.read_memory(self.Addr.PLAYER_Y)
        direction_byte = self._emu.read_memory(self.Addr.PLAYER_DIRECTION)
        facing = self.DIRECTION_MAP.get(direction_byte, "DOWN")

        return Position(map_id=map_id, x=x, y=y, facing=facing)

    # ─────────────────────────────────────────────────────────
    # MODE DETECTION
    # ─────────────────────────────────────────────────────────

    def get_game_mode(self) -> GameMode:
        """Detect the current game mode."""
        battle_type = self._emu.read_memory(self.Addr.BATTLE_TYPE)
        if battle_type != 0:
            return GameMode.BATTLE

        menu_open = self._emu.read_memory(self.Addr.MENU_OPEN)
        if menu_open != 0:
            return GameMode.MENU

        text_box = self._emu.read_memory(self.Addr.TEXT_BOX_OPEN)
        if text_box != 0:
            return GameMode.DIALOGUE

        return GameMode.OVERWORLD

    # ─────────────────────────────────────────────────────────
    # PARTY READING
    # ─────────────────────────────────────────────────────────

    def get_party(self) -> list[Pokemon]:
        """Read the player's Pokemon party."""
        party = []
        count = min(self._emu.read_memory(self.Addr.PARTY_COUNT), 6)

        for i in range(count):
            pokemon = self._read_party_pokemon(i)
            if pokemon:
                party.append(pokemon)

        return party

    def _read_party_pokemon(self, index: int) -> Optional[Pokemon]:
        """Read data for a single party Pokemon."""
        # Get species ID from the species list
        species_id = self._emu.read_memory(self.Addr.PARTY_SPECIES + index)
        if species_id == 0 or species_id == 0xFF:
            return None

        # Pokemon data structure is 44 bytes per Pokemon
        base = self.Addr.PARTY_DATA_START + (index * 44)

        # Read HP and level
        current_hp = self._emu.read_memory_word(base + self.Addr.POKE_HP_CURRENT)
        level = self._emu.read_memory(base + self.Addr.POKE_LEVEL)
        max_hp = self._emu.read_memory_word(base + self.Addr.POKE_HP_MAX)

        # Read status
        status_byte = self._emu.read_memory(base + self.Addr.POKE_STATUS)
        status = self._decode_status(status_byte)

        # Read moves
        moves = self._read_pokemon_moves(base)

        # Read stats
        stats = self._read_pokemon_stats(base)

        return Pokemon(
            species_id=species_id,
            species_name=self.POKEMON_NAMES.get(species_id, f"Pokemon#{species_id}"),
            level=level,
            current_hp=current_hp,
            max_hp=max_hp,
            status=status,
            moves=moves,
            stats=stats,
        )

    def _read_pokemon_moves(self, base: int) -> list[RawMove]:
        """Read the 4 moves for a Pokemon."""
        moves = []
        move_offsets = [
            self.Addr.POKE_MOVE1,
            self.Addr.POKE_MOVE2,
            self.Addr.POKE_MOVE3,
            self.Addr.POKE_MOVE4,
        ]
        pp_offsets = [
            self.Addr.POKE_PP1,
            self.Addr.POKE_PP2,
            self.Addr.POKE_PP3,
            self.Addr.POKE_PP4,
        ]

        for move_offset, pp_offset in zip(move_offsets, pp_offsets):
            move_id = self._emu.read_memory(base + move_offset)
            if move_id == 0:
                continue  # Empty move slot

            pp_byte = self._emu.read_memory(base + pp_offset)
            # PP byte format: upper 2 bits = PP Ups applied, lower 6 bits = current PP
            pp_ups = (pp_byte >> 6) & 0x03
            pp_current = pp_byte & 0x3F

            moves.append(RawMove(
                move_id=move_id,
                pp_current=pp_current,
                pp_ups=pp_ups,
            ))

        return moves

    def _read_pokemon_stats(self, base: int) -> RawStats:
        """Read the calculated stats for a Pokemon."""
        return RawStats(
            attack=self._emu.read_memory_word(base + self.Addr.POKE_ATK),
            defense=self._emu.read_memory_word(base + self.Addr.POKE_DEF),
            speed=self._emu.read_memory_word(base + self.Addr.POKE_SPD),
            special=self._emu.read_memory_word(base + self.Addr.POKE_SPC),
        )

    def _decode_status(self, status_byte: int) -> Optional[str]:
        """Decode status condition from status byte."""
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

    # ─────────────────────────────────────────────────────────
    # BATTLE STATE
    # ─────────────────────────────────────────────────────────

    def get_battle_state(self) -> Optional[BattleState]:
        """Read the current battle state (if in battle)."""
        battle_type_byte = self._emu.read_memory(self.Addr.BATTLE_TYPE)
        if battle_type_byte == 0:
            return None

        battle_type = "WILD" if battle_type_byte == 1 else "TRAINER"

        enemy_species = self._emu.read_memory(self.Addr.ENEMY_SPECIES)
        enemy_level = self._emu.read_memory(self.Addr.ENEMY_LEVEL)
        enemy_hp = self._emu.read_memory_word(self.Addr.ENEMY_HP_CURRENT)
        enemy_max_hp = self._emu.read_memory_word(self.Addr.ENEMY_HP_MAX)

        hp_percent = (enemy_hp / enemy_max_hp * 100) if enemy_max_hp > 0 else 0

        return BattleState(
            battle_type=battle_type,
            enemy_species_id=enemy_species,
            enemy_species_name=self.POKEMON_NAMES.get(enemy_species, f"Pokemon#{enemy_species}"),
            enemy_level=enemy_level,
            enemy_hp_percent=hp_percent,
        )

    # ─────────────────────────────────────────────────────────
    # PROGRESS READING
    # ─────────────────────────────────────────────────────────

    def get_badges(self) -> list[str]:
        """Read the player's obtained badges."""
        badge_byte = self._emu.read_memory(self.Addr.BADGES)
        badges = []
        for i, name in enumerate(self.BADGE_NAMES):
            if badge_byte & (1 << i):
                badges.append(name)
        return badges

    def get_money(self) -> int:
        """Read the player's money (BCD encoded)."""
        raw = self._emu.read_memory_range(self.Addr.MONEY, 3)
        # Convert from BCD (Binary-Coded Decimal)
        return (
            ((raw[0] >> 4) * 100000 + (raw[0] & 0xF) * 10000)
            + ((raw[1] >> 4) * 1000 + (raw[1] & 0xF) * 100)
            + ((raw[2] >> 4) * 10 + (raw[2] & 0xF))
        )

    # ─────────────────────────────────────────────────────────
    # INVENTORY READING
    # ─────────────────────────────────────────────────────────

    # Item ID to name mapping (Gen 1)
    # Key items and common items - for full list, use knowledge base
    ITEM_NAMES = {
        0x00: "???",
        0x01: "MASTER_BALL",
        0x02: "ULTRA_BALL",
        0x03: "GREAT_BALL",
        0x04: "POKE_BALL",
        0x05: "TOWN_MAP",
        0x06: "BICYCLE",
        0x07: "?????",
        0x08: "SAFARI_BALL",
        0x09: "POKEDEX",
        0x0A: "MOON_STONE",
        0x0B: "ANTIDOTE",
        0x0C: "BURN_HEAL",
        0x0D: "ICE_HEAL",
        0x0E: "AWAKENING",
        0x0F: "PARLYZ_HEAL",
        0x10: "FULL_RESTORE",
        0x11: "MAX_POTION",
        0x12: "HYPER_POTION",
        0x13: "SUPER_POTION",
        0x14: "POTION",
        0x15: "BOULDERBADGE",
        0x16: "CASCADEBADGE",
        0x17: "THUNDERBADGE",
        0x18: "RAINBOWBADGE",
        0x19: "SOULBADGE",
        0x1A: "MARSHBADGE",
        0x1B: "VOLCANOBADGE",
        0x1C: "EARTHBADGE",
        0x1D: "ESCAPE_ROPE",
        0x1E: "REPEL",
        0x1F: "OLD_AMBER",
        0x20: "FIRE_STONE",
        0x21: "THUNDER_STONE",
        0x22: "WATER_STONE",
        0x23: "HP_UP",
        0x24: "PROTEIN",
        0x25: "IRON",
        0x26: "CARBOS",
        0x27: "CALCIUM",
        0x28: "RARE_CANDY",
        0x29: "DOME_FOSSIL",
        0x2A: "HELIX_FOSSIL",
        0x2B: "SECRET_KEY",
        0x2C: "?????",
        0x2D: "BIKE_VOUCHER",
        0x2E: "X_ACCURACY",
        0x2F: "LEAF_STONE",
        0x30: "CARD_KEY",
        0x31: "NUGGET",
        0x32: "PP_UP",
        0x33: "POKE_DOLL",
        0x34: "FULL_HEAL",
        0x35: "REVIVE",
        0x36: "MAX_REVIVE",
        0x37: "GUARD_SPEC",
        0x38: "SUPER_REPEL",
        0x39: "MAX_REPEL",
        0x3A: "DIRE_HIT",
        0x3B: "COIN",
        0x3C: "FRESH_WATER",
        0x3D: "SODA_POP",
        0x3E: "LEMONADE",
        0x3F: "SS_TICKET",
        0x40: "GOLD_TEETH",
        0x41: "X_ATTACK",
        0x42: "X_DEFEND",
        0x43: "X_SPEED",
        0x44: "X_SPECIAL",
        0x45: "COIN_CASE",
        0x46: "OAKS_PARCEL",
        0x47: "ITEMFINDER",
        0x48: "SILPH_SCOPE",
        0x49: "POKE_FLUTE",
        0x4A: "LIFT_KEY",
        0x4B: "EXP_ALL",
        0x4C: "OLD_ROD",
        0x4D: "GOOD_ROD",
        0x4E: "SUPER_ROD",
        0x4F: "PP_UP",
        0x50: "ETHER",
        0x51: "MAX_ETHER",
        0x52: "ELIXER",
        0x53: "MAX_ELIXER",
        # TM/HMs start at different indices in Gen 1
        0xC4: "HM01",  # Cut
        0xC5: "HM02",  # Fly
        0xC6: "HM03",  # Surf
        0xC7: "HM04",  # Strength
        0xC8: "HM05",  # Flash
    }

    def get_inventory(self) -> list[InventoryItem]:
        """Read the player's bag inventory."""
        inventory = []
        item_count = self._emu.read_memory(self.Addr.BAG_ITEM_COUNT)

        # Limit to reasonable max (bag can hold 20 unique items)
        item_count = min(item_count, 20)

        for i in range(item_count):
            # Each item entry is 2 bytes: item_id, count
            addr = self.Addr.BAG_ITEMS_START + (i * 2)
            item_id = self._emu.read_memory(addr)
            count = self._emu.read_memory(addr + 1)

            if item_id == 0xFF or item_id == 0:
                break  # End of list marker

            item_name = self.ITEM_NAMES.get(item_id, f"ITEM_{item_id:02X}")
            inventory.append(InventoryItem(
                item_id=item_id,
                item_name=item_name,
                count=count,
            ))

        return inventory

    # ─────────────────────────────────────────────────────────
    # FULL STATE
    # ─────────────────────────────────────────────────────────

    def get_game_state(self) -> GameState:
        """Read the complete current game state."""
        mode = self.get_game_mode()
        position = self.get_position()
        party = self.get_party()
        badges = self.get_badges()
        money = self.get_money()
        inventory = self.get_inventory()
        battle = self.get_battle_state() if mode == GameMode.BATTLE else None

        return GameState(
            mode=mode,
            position=position,
            party=party,
            party_count=len(party),
            badges=badges,
            badge_count=len(badges),
            money=money,
            frame_count=self._emu.frame_count,
            battle=battle,
            inventory=inventory,
        )
