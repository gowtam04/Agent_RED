#!/usr/bin/env python3
"""Extract map data from pokered ASM files."""

import json
import re
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
POKERED_PATH = PROJECT_ROOT / "external" / "pokered"
OUTPUT_PATH = PROJECT_ROOT / "data" / "maps"

# Source directories
HEADERS_DIR = POKERED_PATH / "data" / "maps" / "headers"
OBJECTS_DIR = POKERED_PATH / "data" / "maps" / "objects"
MAP_CONSTANTS_FILE = POKERED_PATH / "constants" / "map_constants.asm"


def parse_map_constants(file_path: Path) -> dict[str, int]:
    """Parse map constants to get map IDs."""
    map_ids = {}
    content = file_path.read_text()

    # Pattern: map_const MAP_NAME, width, height
    pattern = re.compile(r"map_const\s+(\w+)\s*,\s*(\d+)\s*,\s*(\d+)")

    map_id = 0
    for match in pattern.finditer(content):
        name = match.group(1)
        width = int(match.group(2))
        height = int(match.group(3))
        map_ids[name] = {
            "id": map_id,
            "width": width,
            "height": height,
        }
        map_id += 1

    return map_ids


def parse_map_objects(file_path: Path) -> dict:
    """Parse a map objects file for warps and items."""
    content = file_path.read_text()
    map_name = file_path.stem.upper()

    result = {
        "warps": [],
        "items": [],
        "trainers": [],
    }

    # Parse warps: warp_event x, y, DESTINATION, warp_id
    for match in re.finditer(r"warp_event\s+(\d+)\s*,\s*(\d+)\s*,\s*(\w+)\s*,\s*(\d+)", content):
        result["warps"].append({
            "x": int(match.group(1)),
            "y": int(match.group(2)),
            "destination_map": match.group(3),
            "destination_warp_id": int(match.group(4)),
        })

    # Parse items: object_event x, y, SPRITE_POKE_BALL, ..., ITEM_NAME
    for match in re.finditer(r"object_event\s+(\d+)\s*,\s*(\d+)\s*,\s*SPRITE_POKE_BALL[^,]*,[^,]*,[^,]*,[^,]*,\s*(\w+)", content):
        item = match.group(3)
        if not item.startswith("TEXT_"):
            result["items"].append({
                "x": int(match.group(1)),
                "y": int(match.group(2)),
                "item": item,
            })

    # Parse trainers: object_event x, y, SPRITE, ..., OPP_CLASS, team_index
    for match in re.finditer(r"object_event\s+(\d+)\s*,\s*(\d+)[^,]*,[^,]*,\s*(\w+)[^,]*,[^,]*,\s*OPP_(\w+)\s*,\s*(\d+)", content):
        result["trainers"].append({
            "x": int(match.group(1)),
            "y": int(match.group(2)),
            "facing": match.group(3),
            "class": match.group(4),
            "team_index": int(match.group(5)),
        })

    return result


def main():
    """Extract maps and save to JSON."""
    print(f"Reading map data from {POKERED_PATH}...")

    # Parse map constants
    map_info = parse_map_constants(MAP_CONSTANTS_FILE)
    print(f"Found {len(map_info)} maps in constants")

    # Parse map objects
    object_files = list(OBJECTS_DIR.glob("*.asm"))
    print(f"Found {len(object_files)} map object files")

    maps = {}
    for file_path in object_files:
        map_name = file_path.stem
        map_name_upper = map_name.upper()

        # Get base info from constants
        base_info = map_info.get(map_name_upper, {})

        # Parse objects
        objects = parse_map_objects(file_path)

        maps[map_name_upper] = {
            "map_id": map_name_upper,
            "display_name": map_name.replace("_", " ").title(),
            "width": base_info.get("width", 0),
            "height": base_info.get("height", 0),
            "warps": objects["warps"],
            "items": objects["items"],
            "trainers": objects["trainers"],
        }

    print(f"Processed {len(maps)} maps with object data")

    # Create output directory
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

    # Save index
    index = {
        "maps": sorted(maps.keys()),
        "map_count": len(maps),
    }
    with open(OUTPUT_PATH / "index.json", "w") as f:
        json.dump(index, f, indent=2)

    # Save individual map files
    for map_name, map_data in maps.items():
        with open(OUTPUT_PATH / f"{map_name}.json", "w") as f:
            json.dump(map_data, f, indent=2)

    print(f"Saved to {OUTPUT_PATH}/")

    # Print examples
    print("\nExamples:")
    for map_name in ["VIRIDIANFOREST", "PEWTER_GYM", "PALLET_TOWN"]:
        if map_name in maps:
            m = maps[map_name]
            print(f"  {map_name}: {m['width']}x{m['height']}, "
                  f"{len(m['warps'])} warps, {len(m['items'])} items, {len(m['trainers'])} trainers")

    return 0


if __name__ == "__main__":
    exit(main())
