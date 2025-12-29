#!/usr/bin/env python3
"""Extract Pokemon data from pokered ASM files."""

import json
import re
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
POKERED_PATH = PROJECT_ROOT / "external" / "pokered"
OUTPUT_PATH = PROJECT_ROOT / "data" / "pokemon.json"

# Source files/directories
BASE_STATS_DIR = POKERED_PATH / "data" / "pokemon" / "base_stats"
EVOS_MOVES_FILE = POKERED_PATH / "data" / "pokemon" / "evos_moves.asm"
DEX_CONSTANTS_FILE = POKERED_PATH / "constants" / "pokedex_constants.asm"
POKEMON_CONSTANTS_FILE = POKERED_PATH / "constants" / "pokemon_constants.asm"

# Type normalization
TYPE_NAME_MAP = {
    "PSYCHIC_TYPE": "PSYCHIC",
}


def normalize_type(type_name: str) -> str:
    """Normalize type name."""
    return TYPE_NAME_MAP.get(type_name, type_name)


def parse_dex_constants(file_path: Path) -> dict[str, int]:
    """Parse pokedex constants to get DEX_xxx -> number mapping."""
    dex_numbers = {}
    content = file_path.read_text()

    # Pattern: const DEX_NAME ; number
    pattern = re.compile(r"const\s+DEX_(\w+)\s*;\s*(\d+)")

    for match in pattern.finditer(content):
        name = match.group(1)
        number = int(match.group(2))
        dex_numbers[f"DEX_{name}"] = number
        # Also store without prefix for easier lookup
        dex_numbers[name] = number

    return dex_numbers


def parse_base_stats_file(file_path: Path, dex_numbers: dict[str, int]) -> dict | None:
    """Parse a single base stats file."""
    content = file_path.read_text()
    pokemon_name = file_path.stem.upper()

    # Handle special naming cases
    name_map = {
        "NIDORAN_F": "NIDORAN_F",
        "NIDORAN_M": "NIDORAN_M",
        "MR_MIME": "MR_MIME",
        "FARFETCHD": "FARFETCHD",
    }

    # Extract pokedex ID
    dex_match = re.search(r"db\s+DEX_(\w+)", content)
    if not dex_match:
        return None

    dex_name = dex_match.group(1)
    dex_number = dex_numbers.get(dex_name, 0)

    # Extract base stats (hp, atk, def, spd, spc)
    stats_match = re.search(
        r"db\s+(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\n\s*;\s*hp\s+atk\s+def\s+spd\s+spc",
        content
    )
    if not stats_match:
        return None

    base_stats = {
        "hp": int(stats_match.group(1)),
        "attack": int(stats_match.group(2)),
        "defense": int(stats_match.group(3)),
        "speed": int(stats_match.group(4)),
        "special": int(stats_match.group(5)),
    }

    # Extract types
    type_match = re.search(r"db\s+(\w+)\s*,\s*(\w+)\s*;\s*type", content)
    if not type_match:
        return None

    type1 = normalize_type(type_match.group(1))
    type2 = normalize_type(type_match.group(2))
    types = [type1] if type1 == type2 else [type1, type2]

    # Extract catch rate
    catch_match = re.search(r"db\s+(\d+)\s*;\s*catch\s*rate", content)
    catch_rate = int(catch_match.group(1)) if catch_match else 0

    # Extract base exp
    exp_match = re.search(r"db\s+(\d+)\s*;\s*base\s*exp", content)
    base_exp = int(exp_match.group(1)) if exp_match else 0

    # Extract TM/HM compatibility
    tmhm_match = re.search(r"tmhm\s+(.+?)(?:;\s*end|\n\s*\n|\ndb\s+0)", content, re.DOTALL)
    tm_compatibility = []
    hm_compatibility = []

    if tmhm_match:
        tmhm_content = tmhm_match.group(1)
        # Find all move names
        moves = re.findall(r"\b([A-Z][A-Z0-9_]+)\b", tmhm_content)
        # Filter to actual moves (not comments or macros)
        valid_moves = [m for m in moves if not m.startswith("GROWTH_") and m != "NO_MOVE"]

        # Map moves to TM/HM (we'll need moves.json for this)
        # For now, store the move names
        tm_compatibility = valid_moves

    return {
        "dex_number": dex_number,
        "name": dex_name,
        "types": types,
        "base_stats": base_stats,
        "catch_rate": catch_rate,
        "base_exp_yield": base_exp,
        "tm_hm_moves": tm_compatibility,  # Will convert to TM numbers later
    }


def parse_evos_moves(file_path: Path) -> dict[str, dict]:
    """Parse evolutions and learnsets from evos_moves.asm."""
    content = file_path.read_text()
    result = {}

    # Find all Pokemon EvosMoves sections
    pattern = re.compile(
        r"(\w+)EvosMoves:\s*\n; Evolutions\s*\n(.*?)(?=\w+EvosMoves:|\Z)",
        re.DOTALL
    )

    for match in pattern.finditer(content):
        pokemon_name = match.group(1).upper()
        section = match.group(2)

        # Parse evolutions
        evolutions = []
        evo_section = section.split("; Learnset")[0] if "; Learnset" in section else section.split("db 0")[0]

        # EVOLVE_LEVEL, level, species
        for evo_match in re.finditer(r"db\s+EVOLVE_LEVEL\s*,\s*(\d+)\s*,\s*(\w+)", evo_section):
            evolutions.append({
                "method": "LEVEL",
                "level": int(evo_match.group(1)),
                "to": evo_match.group(2),
            })

        # EVOLVE_ITEM, item, min_level, species
        for evo_match in re.finditer(r"db\s+EVOLVE_ITEM\s*,\s*(\w+)\s*,\s*\d+\s*,\s*(\w+)", evo_section):
            evolutions.append({
                "method": "ITEM",
                "item": evo_match.group(1),
                "to": evo_match.group(2),
            })

        # EVOLVE_TRADE, min_level, species
        for evo_match in re.finditer(r"db\s+EVOLVE_TRADE\s*,\s*\d+\s*,\s*(\w+)", evo_section):
            evolutions.append({
                "method": "TRADE",
                "to": evo_match.group(1),
            })

        # Parse learnset
        learnset = []
        learn_section = ""
        if "; Learnset" in section:
            learn_section = section.split("; Learnset")[1]
        else:
            # Find content after first "db 0"
            parts = section.split("db 0", 1)
            if len(parts) > 1:
                learn_section = parts[1]

        for learn_match in re.finditer(r"db\s+(\d+)\s*,\s*(\w+)", learn_section):
            level = int(learn_match.group(1))
            move = learn_match.group(2)
            if move != "0" and level > 0:
                learnset.append({"level": level, "move": move})

        result[pokemon_name] = {
            "evolutions": evolutions,
            "learnset": learnset,
        }

    return result


def load_tm_hm_mapping() -> dict[str, str]:
    """Load TM/HM mapping from moves.json if it exists."""
    moves_path = PROJECT_ROOT / "data" / "moves.json"
    if not moves_path.exists():
        return {}

    with open(moves_path) as f:
        data = json.load(f)

    # Invert the mapping: move_name -> TM/HM
    result = {}
    for tm_hm, move_name in data.get("tm_hm_mapping", {}).items():
        result[move_name] = tm_hm
    return result


def main():
    """Extract Pokemon and save to JSON."""
    print(f"Reading Pokemon data from {POKERED_PATH}...")

    # Parse dex constants
    dex_numbers = parse_dex_constants(DEX_CONSTANTS_FILE)
    print(f"Found {len(dex_numbers) // 2} Pokedex entries")

    # Load TM/HM mapping
    tm_hm_map = load_tm_hm_mapping()
    print(f"Loaded {len(tm_hm_map)} TM/HM mappings")

    # Parse base stats files
    pokemon = {}
    base_stats_files = list(BASE_STATS_DIR.glob("*.asm"))
    print(f"Found {len(base_stats_files)} base stats files")

    for file_path in base_stats_files:
        data = parse_base_stats_file(file_path, dex_numbers)
        if data:
            name = data["name"]
            pokemon[name] = data

    print(f"Parsed {len(pokemon)} Pokemon base stats")

    # Parse evolutions and learnsets
    evos_moves = parse_evos_moves(EVOS_MOVES_FILE)
    print(f"Parsed evolutions/learnsets for {len(evos_moves)} Pokemon")

    # Merge evos_moves into pokemon data
    for name, data in pokemon.items():
        if name in evos_moves:
            evo_data = evos_moves[name]
            data["evolutions"] = evo_data["evolutions"]
            data["learnset"] = evo_data["learnset"]
        else:
            data["evolutions"] = []
            data["learnset"] = []

        # Convert TM/HM moves to TM/HM numbers
        tm_moves = data.pop("tm_hm_moves", [])
        tm_compat = []
        hm_compat = []
        for move in tm_moves:
            if move in tm_hm_map:
                tm_hm = tm_hm_map[move]
                if tm_hm.startswith("TM"):
                    tm_compat.append(tm_hm)
                elif tm_hm.startswith("HM"):
                    hm_compat.append(tm_hm)
        data["tm_compatibility"] = sorted(tm_compat)
        data["hm_compatibility"] = sorted(hm_compat)

    # Validate
    errors = []
    if len(pokemon) != 151:
        errors.append(f"Expected 151 Pokemon, got {len(pokemon)}")

    # Check for missing dex numbers
    dex_set = {p["dex_number"] for p in pokemon.values()}
    missing_dex = set(range(1, 152)) - dex_set
    if missing_dex:
        errors.append(f"Missing Pokedex numbers: {sorted(missing_dex)}")

    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
        # Don't fail - just warn
        print("Continuing despite validation warnings...")

    # Save to JSON
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(pokemon, f, indent=2, sort_keys=True)

    print(f"Saved {len(pokemon)} Pokemon to {OUTPUT_PATH}")

    # Print examples
    print("\nExamples:")
    for name in ["PIKACHU", "CHARIZARD", "EEVEE", "MEW"]:
        if name in pokemon:
            p = pokemon[name]
            print(f"  #{p['dex_number']} {name}: {p['types']} "
                  f"HP:{p['base_stats']['hp']} ATK:{p['base_stats']['attack']}")
            if p["evolutions"]:
                for evo in p["evolutions"]:
                    print(f"    -> {evo['to']} via {evo['method']}")

    return 0


if __name__ == "__main__":
    exit(main())
