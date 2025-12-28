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
class Pokemon:
    """Data for a single Pokemon."""

    species_id: int
    species_name: str
    level: int
    current_hp: int
    max_hp: int
    status: Optional[str] = None  # None, "POISON", "BURN", "SLEEP", etc.

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

        # Battle state
        BATTLE_TYPE = 0xD057  # 0=none, 1=wild, 2=trainer
        ENEMY_SPECIES = 0xCFE5
        ENEMY_LEVEL = 0xCFF3
        ENEMY_HP_CURRENT = 0xCFE6  # 2 bytes
        ENEMY_HP_MAX = 0xCFF4  # 2 bytes

        # Game state flags
        MENU_OPEN = 0xD730
        TEXT_BOX_OPEN = 0xC4F2

        # Progress
        MONEY = 0xD347  # 3 bytes, BCD encoded
        BADGES = 0xD356  # Bit flags

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
        current_hp = self._emu.read_memory_word(base + 1)
        level = self._emu.read_memory(base + 33)
        max_hp = self._emu.read_memory_word(base + 34)

        # Read status
        status_byte = self._emu.read_memory(base + 4)
        status = self._decode_status(status_byte)

        return Pokemon(
            species_id=species_id,
            species_name=self.POKEMON_NAMES.get(species_id, f"Pokemon#{species_id}"),
            level=level,
            current_hp=current_hp,
            max_hp=max_hp,
            status=status,
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
    # FULL STATE
    # ─────────────────────────────────────────────────────────

    def get_game_state(self) -> GameState:
        """Read the complete current game state."""
        mode = self.get_game_mode()
        position = self.get_position()
        party = self.get_party()
        badges = self.get_badges()
        money = self.get_money()
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
        )
