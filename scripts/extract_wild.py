#!/usr/bin/env python3
"""Extract wild encounter data from pokered ASM files."""

import json
import re
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
POKERED_PATH = PROJECT_ROOT / "external" / "pokered"
OUTPUT_PATH = PROJECT_ROOT / "data" / "wild_encounters.json"

# Source directory
WILD_MAPS_DIR = POKERED_PATH / "data" / "wild" / "maps"

# Gen 1 slot probabilities
SLOT_PROBABILITIES = [20, 20, 15, 10, 10, 10, 5, 5, 4, 1]


def parse_wild_encounters_file(file_path: Path) -> dict | None:
    """Parse a single wild encounters file."""
    content = file_path.read_text()
    map_name = file_path.stem

    result = {
        "map_id": map_name.upper(),
        "grass": None,
        "water": None,
    }

    # Parse grass encounters
    grass_match = re.search(
        r"def_grass_wildmons\s+(\d+)\s*;.*?\n(.*?)end_grass_wildmons",
        content, re.DOTALL
    )
    if grass_match:
        encounter_rate = int(grass_match.group(1))
        if encounter_rate > 0:
            pokemon_section = grass_match.group(2)
            pokemon = []
            slot = 1
            for match in re.finditer(r"db\s+(\d+)\s*,\s*(\w+)", pokemon_section):
                level = int(match.group(1))
                species = match.group(2)
                prob = SLOT_PROBABILITIES[slot - 1] if slot <= 10 else 0
                pokemon.append({
                    "slot": slot,
                    "species": species,
                    "level": level,
                    "probability": prob,
                })
                slot += 1
            result["grass"] = {
                "encounter_rate": encounter_rate,
                "pokemon": pokemon,
            }

    # Parse water encounters
    water_match = re.search(
        r"def_water_wildmons\s+(\d+)\s*;.*?\n(.*?)end_water_wildmons",
        content, re.DOTALL
    )
    if water_match:
        encounter_rate = int(water_match.group(1))
        if encounter_rate > 0:
            pokemon_section = water_match.group(2)
            pokemon = []
            slot = 1
            for match in re.finditer(r"db\s+(\d+)\s*,\s*(\w+)", pokemon_section):
                level = int(match.group(1))
                species = match.group(2)
                prob = SLOT_PROBABILITIES[slot - 1] if slot <= 10 else 0
                pokemon.append({
                    "slot": slot,
                    "species": species,
                    "level": level,
                    "probability": prob,
                })
                slot += 1
            result["water"] = {
                "encounter_rate": encounter_rate,
                "pokemon": pokemon,
            }

    # Only return if there are encounters
    if result["grass"] or result["water"]:
        return result
    return None


def main():
    """Extract wild encounters and save to JSON."""
    print(f"Reading wild encounter data from {WILD_MAPS_DIR}...")

    # Parse all wild encounter files
    encounters = {}
    wild_files = list(WILD_MAPS_DIR.glob("*.asm"))
    print(f"Found {len(wild_files)} wild encounter files")

    for file_path in wild_files:
        data = parse_wild_encounters_file(file_path)
        if data:
            map_id = data["map_id"]
            # Convert to uppercase and replace spaces/special chars
            map_id = map_id.upper().replace(" ", "_")
            encounters[map_id] = data

    print(f"Parsed {len(encounters)} locations with wild encounters")

    # Save to JSON
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(encounters, f, indent=2, sort_keys=True)

    print(f"Saved to {OUTPUT_PATH}")

    # Print examples
    print("\nExamples:")
    for map_name in ["ROUTE1", "VIRIDIANFOREST", "MTMOON1F"]:
        if map_name in encounters:
            enc = encounters[map_name]
            if enc.get("grass"):
                grass = enc["grass"]
                print(f"  {map_name} (grass, rate {grass['encounter_rate']}):")
                for p in grass["pokemon"][:3]:
                    print(f"    Slot {p['slot']}: Lv{p['level']} {p['species']} ({p['probability']}%)")

    return 0


if __name__ == "__main__":
    exit(main())
