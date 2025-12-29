#!/usr/bin/env python3
"""Extract move data from pokered ASM files."""

import json
import re
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
POKERED_PATH = PROJECT_ROOT / "external" / "pokered"
OUTPUT_PATH = PROJECT_ROOT / "data" / "moves.json"

# Source files
MOVES_FILE = POKERED_PATH / "data" / "moves" / "moves.asm"
MOVE_CONSTANTS_FILE = POKERED_PATH / "constants" / "move_constants.asm"
ITEM_CONSTANTS_FILE = POKERED_PATH / "constants" / "item_constants.asm"

# Gen 1 type categories
PHYSICAL_TYPES = {"NORMAL", "FIGHTING", "FLYING", "GROUND", "ROCK", "BUG", "GHOST", "POISON"}
SPECIAL_TYPES = {"FIRE", "WATER", "ELECTRIC", "GRASS", "ICE", "PSYCHIC", "DRAGON"}

# High crit moves (Gen 1)
HIGH_CRIT_MOVES = {
    "KARATE_CHOP", "RAZOR_LEAF", "CRABHAMMER", "SLASH"
}

# Effect chance mappings
EFFECT_CHANCES = {
    "BURN_SIDE_EFFECT1": 10,
    "BURN_SIDE_EFFECT2": 30,
    "FREEZE_SIDE_EFFECT1": 10,
    "PARALYZE_SIDE_EFFECT1": 10,
    "PARALYZE_SIDE_EFFECT2": 30,
    "POISON_SIDE_EFFECT1": 20,
    "POISON_SIDE_EFFECT2": 40,
    "FLINCH_SIDE_EFFECT1": 10,
    "FLINCH_SIDE_EFFECT2": 30,
    "CONFUSION_SIDE_EFFECT": 10,
    "ATTACK_DOWN_SIDE_EFFECT": 33,
    "DEFENSE_DOWN_SIDE_EFFECT": 33,
    "SPEED_DOWN_SIDE_EFFECT": 33,
    "SPECIAL_DOWN_SIDE_EFFECT": 33,
}

# Type normalization
TYPE_NAME_MAP = {
    "PSYCHIC_TYPE": "PSYCHIC",
}


def normalize_type(type_name: str) -> str:
    """Normalize type name."""
    return TYPE_NAME_MAP.get(type_name, type_name)


def get_category(type_name: str, power: int) -> str:
    """Determine move category based on Gen 1 rules."""
    if power == 0:
        return "STATUS"
    norm_type = normalize_type(type_name)
    if norm_type in PHYSICAL_TYPES:
        return "PHYSICAL"
    elif norm_type in SPECIAL_TYPES:
        return "SPECIAL"
    return "PHYSICAL"  # Default


def parse_move_constants(file_path: Path) -> dict[str, int]:
    """Parse move constants to get move IDs."""
    move_ids = {}
    content = file_path.read_text()

    # Pattern: const MOVE_NAME  ; XX
    pattern = re.compile(r"const\s+(\w+)\s*;\s*([0-9a-fA-F]+)")

    for match in pattern.finditer(content):
        name = match.group(1)
        hex_id = match.group(2)
        if name != "NO_MOVE":
            move_ids[name] = int(hex_id, 16)

    return move_ids


def parse_tm_hm_mapping(file_path: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Parse TM and HM mappings."""
    tm_mapping = {}
    hm_mapping = {}
    content = file_path.read_text()

    # Parse HMs: add_hm MOVE_NAME
    hm_pattern = re.compile(r"add_hm\s+(\w+)")
    hm_number = 1
    for match in hm_pattern.finditer(content):
        move_name = match.group(1)
        hm_mapping[move_name] = f"HM{hm_number:02d}"
        hm_number += 1

    # Parse TMs: add_tm MOVE_NAME  ; $XX (must be followed by hex comment)
    tm_pattern = re.compile(r"add_tm\s+(\w+)\s*;\s*\$[0-9a-fA-F]+")
    tm_number = 1
    for match in tm_pattern.finditer(content):
        move_name = match.group(1)
        tm_mapping[move_name] = f"TM{tm_number:02d}"
        tm_number += 1

    return tm_mapping, hm_mapping


def parse_moves(file_path: Path, move_ids: dict[str, int],
                tm_mapping: dict[str, str], hm_mapping: dict[str, str]) -> dict:
    """Parse moves.asm and return move data dictionary."""
    moves = {}
    content = file_path.read_text()

    # Pattern: move NAME, EFFECT, POWER, TYPE, ACCURACY, PP
    pattern = re.compile(
        r"move\s+(\w+)\s*,\s*(\w+)\s*,\s*(\d+)\s*,\s*(\w+)\s*,\s*(\d+)\s*,\s*(\d+)"
    )

    for match in pattern.finditer(content):
        name = match.group(1)
        effect = match.group(2)
        power = int(match.group(3))
        type_name = normalize_type(match.group(4).upper())
        accuracy = int(match.group(5))
        pp = int(match.group(6))

        move_id = move_ids.get(name, 0)
        category = get_category(type_name, power)
        high_crit = name in HIGH_CRIT_MOVES
        effect_chance = EFFECT_CHANCES.get(effect)

        move_data = {
            "id": move_id,
            "name": name,
            "type": type_name,
            "category": category,
            "power": power,
            "accuracy": accuracy,
            "pp": pp,
            "effect": effect,
        }

        if effect_chance is not None:
            move_data["effect_chance"] = effect_chance

        if high_crit:
            move_data["high_crit"] = True

        if name in tm_mapping:
            move_data["is_tm"] = tm_mapping[name]
        if name in hm_mapping:
            move_data["is_hm"] = hm_mapping[name]

        moves[name] = move_data

    return moves


def create_tm_hm_index(tm_mapping: dict[str, str], hm_mapping: dict[str, str]) -> dict:
    """Create TM/HM to move mapping."""
    index = {}
    for move, tm in tm_mapping.items():
        index[tm] = move
    for move, hm in hm_mapping.items():
        index[hm] = move
    return index


def main():
    """Extract moves and save to JSON."""
    print(f"Reading move data from {POKERED_PATH}...")

    # Parse move IDs
    move_ids = parse_move_constants(MOVE_CONSTANTS_FILE)
    print(f"Found {len(move_ids)} move constants")

    # Parse TM/HM mappings
    tm_mapping, hm_mapping = parse_tm_hm_mapping(ITEM_CONSTANTS_FILE)
    print(f"Found {len(tm_mapping)} TMs and {len(hm_mapping)} HMs")

    # Parse moves
    moves = parse_moves(MOVES_FILE, move_ids, tm_mapping, hm_mapping)
    print(f"Extracted {len(moves)} moves")

    # Create TM/HM index
    tm_hm_index = create_tm_hm_index(tm_mapping, hm_mapping)

    # Combine into output
    output = {
        "moves": moves,
        "tm_hm_mapping": tm_hm_index,
    }

    # Validate
    errors = []
    if len(moves) < 165:
        errors.append(f"Expected at least 165 moves, got {len(moves)}")
    if len(tm_mapping) != 50:
        errors.append(f"Expected 50 TMs, got {len(tm_mapping)}")
    if len(hm_mapping) != 5:
        errors.append(f"Expected 5 HMs, got {len(hm_mapping)}")

    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
        return 1

    # Save to JSON
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2, sort_keys=True)

    print(f"Saved to {OUTPUT_PATH}")

    # Print examples
    print("\nExamples:")
    for move_name in ["THUNDERBOLT", "EARTHQUAKE", "PSYCHIC_M", "SURF", "CUT"]:
        if move_name in moves:
            m = moves[move_name]
            tm_hm = m.get("is_tm") or m.get("is_hm") or "N/A"
            print(f"  {move_name}: {m['type']} {m['category']} "
                  f"Pow:{m['power']} Acc:{m['accuracy']} PP:{m['pp']} TM/HM:{tm_hm}")

    return 0


if __name__ == "__main__":
    exit(main())
