#!/usr/bin/env python3
"""Extract collision and map connection data from pokered ASM files.

This script extracts:
1. Tileset collision data (walkable tile IDs)
2. Map-to-tileset assignments
3. Map connections (north/south/east/west)
4. Map dimensions (width/height)
5. Grass tile IDs per tileset

It updates existing map JSON files with this additional data.
"""

import json
import re
from pathlib import Path


# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
POKERED_PATH = PROJECT_ROOT / "external" / "pokered"
MAPS_OUTPUT_PATH = PROJECT_ROOT / "data" / "maps"

# Source files
COLLISION_FILE = POKERED_PATH / "data" / "tilesets" / "collision_tile_ids.asm"
TILESET_HEADERS_FILE = POKERED_PATH / "data" / "tilesets" / "tileset_headers.asm"
MAP_CONSTANTS_FILE = POKERED_PATH / "constants" / "map_constants.asm"
MAP_HEADERS_DIR = POKERED_PATH / "data" / "maps" / "headers"
LEDGE_TILES_FILE = POKERED_PATH / "data" / "tilesets" / "ledge_tiles.asm"


def camel_to_snake(name: str) -> str:
    """Convert CamelCase to UPPER_SNAKE_CASE.

    PalletTown -> PALLET_TOWN
    Route1 -> ROUTE_1
    MtMoon1F -> MT_MOON_1F
    """
    # Insert underscore before uppercase letters (except at start)
    result = re.sub(r"(?<!^)(?=[A-Z])", "_", name)
    # Handle numbers - insert underscore before them if preceded by letter
    result = re.sub(r"([a-zA-Z])(\d)", r"\1_\2", result)
    return result.upper()


def snake_to_camel(name: str) -> str:
    """Convert UPPER_SNAKE_CASE to CamelCase.

    PALLET_TOWN -> PalletTown
    ROUTE_1 -> Route1
    """
    parts = name.lower().split("_")
    return "".join(part.capitalize() for part in parts)


def normalize_map_name(name: str) -> str:
    """Normalize a map name to UPPER_NO_UNDERSCORE format (JSON style).

    PalletTown -> PALLETTOWN
    PALLET_TOWN -> PALLETTOWN
    PALLETTOWN -> PALLETTOWN
    """
    return name.replace("_", "").upper()


def build_name_mappings(
    dimensions: dict[str, dict],
    header_data: dict[str, dict],
) -> dict[str, dict]:
    """Build mappings from normalized names to original data.

    Returns a dict keyed by normalized names (like PALLETTOWN) containing:
    - dimensions from map_constants (keyed by PALLET_TOWN)
    - header data (keyed by PalletTown)
    """
    mappings: dict[str, dict] = {}

    # Map from constants (PALLET_TOWN format)
    for const_name, dims in dimensions.items():
        norm_name = normalize_map_name(const_name)
        if norm_name not in mappings:
            mappings[norm_name] = {}
        mappings[norm_name]["dimensions"] = dims
        mappings[norm_name]["const_name"] = const_name

    # Map from headers (PalletTown format)
    for header_name, data in header_data.items():
        norm_name = normalize_map_name(header_name)
        if norm_name not in mappings:
            mappings[norm_name] = {}
        mappings[norm_name]["header"] = data
        mappings[norm_name]["header_name"] = header_name

    return mappings


def parse_collision_tiles(file_path: Path) -> dict[str, set[int]]:
    """Parse collision_tile_ids.asm to get walkable tiles per tileset.

    The tiles listed are WALKABLE. Tiles not listed are blocked.

    Format:
        TilesetName_Coll::
            coll_tiles $00, $10, $1b, ...
    """
    content = file_path.read_text()
    tileset_collisions: dict[str, set[int]] = {}

    # Pattern to match tileset collision definitions
    # e.g., "Overworld_Coll::" followed by "coll_tiles $00, $10, ..."
    pattern = re.compile(
        r"(\w+)_Coll::\s*\n\s*coll_tiles\s+(.*?)(?=\n\w|\n\n|\Z)",
        re.MULTILINE | re.DOTALL,
    )

    for match in pattern.finditer(content):
        tileset_name = match.group(1)
        tiles_str = match.group(2)

        # Extract hex values
        tile_ids = set()
        for hex_match in re.finditer(r"\$([0-9a-fA-F]+)", tiles_str):
            tile_ids.add(int(hex_match.group(1), 16))

        if tile_ids:
            tileset_collisions[tileset_name] = tile_ids

    return tileset_collisions


def parse_tileset_headers(file_path: Path) -> dict[str, dict]:
    """Parse tileset_headers.asm to get grass tiles per tileset.

    Format:
        tileset Name, counter1, counter2, counter3, grass_tile, animations
    """
    content = file_path.read_text()
    tilesets: dict[str, dict] = {}

    # Pattern: tileset Name, ..., grass_tile, ...
    # grass_tile is the 5th argument (index 4)
    pattern = re.compile(
        r"tileset\s+(\w+)\s*,\s*"  # name
        r"([^,]+)\s*,\s*"  # counter1
        r"([^,]+)\s*,\s*"  # counter2
        r"([^,]+)\s*,\s*"  # counter3
        r"([^,]+)\s*,\s*"  # grass_tile
        r"(\w+)"  # animations
    )

    for match in pattern.finditer(content):
        name = match.group(1)
        grass_tile_str = match.group(5).strip()

        grass_tile = None
        if grass_tile_str != "-1":
            # Parse hex value
            if grass_tile_str.startswith("$"):
                grass_tile = int(grass_tile_str[1:], 16)
            elif grass_tile_str.isdigit():
                grass_tile = int(grass_tile_str)

        tilesets[name] = {
            "grass_tile": grass_tile,
        }

    return tilesets


def parse_map_constants(file_path: Path) -> dict[str, dict]:
    """Parse map_constants.asm to get map dimensions.

    Format:
        map_const PALLET_TOWN, 10, 9
    """
    content = file_path.read_text()
    map_info: dict[str, dict] = {}

    pattern = re.compile(r"map_const\s+(\w+)\s*,\s*(\d+)\s*,\s*(\d+)")

    for match in pattern.finditer(content):
        name = match.group(1)
        width = int(match.group(2))
        height = int(match.group(3))
        map_info[name] = {
            "width": width,
            "height": height,
        }

    return map_info


def parse_map_header(file_path: Path) -> dict:
    """Parse a map header file for tileset and connections.

    Format:
        map_header MapName, MAP_CONST, TILESET, CONNECTION_FLAGS
        connection north, DestMapName, DEST_CONST, offset
        end_map_header
    """
    content = file_path.read_text()
    result = {
        "tileset": None,
        "connections": {},
    }

    # Parse map_header line
    header_match = re.search(
        r"map_header\s+\w+\s*,\s*\w+\s*,\s*(\w+)\s*,",
        content,
    )
    if header_match:
        result["tileset"] = header_match.group(1)

    # Parse connections
    for match in re.finditer(
        r"connection\s+(north|south|east|west)\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*(-?\d+)",
        content,
    ):
        direction = match.group(1).upper()
        dest_map_camel = match.group(2)
        dest_map_const = match.group(3)
        offset = int(match.group(4))

        result["connections"][direction] = {
            "map": dest_map_const,
            "offset": offset,
        }

    return result


def parse_ledge_tiles(file_path: Path) -> dict[str, list[dict]]:
    """Parse ledge_tiles.asm to get ledge definitions.

    Format:
        db TILESET, tile_id, direction
    """
    if not file_path.exists():
        return {}

    content = file_path.read_text()
    ledges: dict[str, list[dict]] = {}

    # Pattern for ledge definitions
    pattern = re.compile(r"db\s+(\w+)\s*,\s*\$([0-9a-fA-F]+)\s*,\s*(\w+)")

    for match in pattern.finditer(content):
        tileset = match.group(1)
        tile_id = int(match.group(2), 16)
        direction = match.group(3)

        if tileset not in ledges:
            ledges[tileset] = []
        ledges[tileset].append({
            "tile_id": tile_id,
            "direction": direction,
        })

    return ledges


def update_map_json(
    map_path: Path,
    name_mappings: dict[str, dict],
    collision_data: dict[str, set[int]],
    tileset_info: dict[str, dict],
) -> bool:
    """Update a map JSON file with collision and connection data."""
    if not map_path.exists():
        return False

    with open(map_path) as f:
        map_data = json.load(f)

    map_id = map_data.get("map_id", "")
    norm_name = normalize_map_name(map_id)

    # Look up data using normalized name
    mapping = name_mappings.get(norm_name, {})

    # Get dimensions from map_constants
    dims = mapping.get("dimensions")
    if dims:
        map_data["width"] = dims["width"]
        map_data["height"] = dims["height"]

    # Get header data (tileset, connections)
    header = mapping.get("header")
    if header:
        if header.get("tileset"):
            map_data["tileset"] = header["tileset"]
        if header.get("connections"):
            map_data["connections"] = header["connections"]

    # Get collision info based on tileset
    # Note: Headers use UPPERCASE (OVERWORLD), collision uses CamelCase (Overworld)
    tileset_name = map_data.get("tileset")
    if tileset_name:
        # Try to find matching tileset in collision data
        tileset_variants = [
            tileset_name,
            tileset_name.capitalize(),
            tileset_name.title(),
            snake_to_camel(tileset_name),
        ]
        for variant in tileset_variants:
            if variant in collision_data:
                walkable_tiles = collision_data[variant]
                map_data["walkable_tiles"] = sorted(list(walkable_tiles))
                break

    # Get grass tile info (same name matching issue)
    if tileset_name:
        for variant in tileset_variants:
            if variant in tileset_info:
                grass_tile = tileset_info[variant].get("grass_tile")
                if grass_tile is not None:
                    map_data["grass_tile"] = grass_tile
                break

    # Save updated data
    with open(map_path, "w") as f:
        json.dump(map_data, f, indent=2)

    return True


def main():
    """Extract collision data and update map files."""
    print("Extracting collision and map data from pokered...")
    print(f"  Source: {POKERED_PATH}")
    print(f"  Output: {MAPS_OUTPUT_PATH}")
    print()

    # 1. Parse collision tiles
    print("Parsing collision tiles...")
    collision_data = parse_collision_tiles(COLLISION_FILE)
    print(f"  Found {len(collision_data)} tileset collision definitions")
    for name, tiles in list(collision_data.items())[:3]:
        print(f"    {name}: {len(tiles)} walkable tiles")

    # 2. Parse tileset headers (grass tiles)
    print("\nParsing tileset headers...")
    tileset_info = parse_tileset_headers(TILESET_HEADERS_FILE)
    print(f"  Found {len(tileset_info)} tilesets")
    grass_count = sum(1 for t in tileset_info.values() if t.get("grass_tile"))
    print(f"  {grass_count} tilesets have grass tiles")

    # 3. Parse map constants (dimensions)
    print("\nParsing map constants...")
    dimensions = parse_map_constants(MAP_CONSTANTS_FILE)
    print(f"  Found {len(dimensions)} map dimension entries")

    # 4. Parse map headers (tilesets, connections)
    print("\nParsing map headers...")
    header_files = list(MAP_HEADERS_DIR.glob("*.asm"))
    header_data: dict[str, dict] = {}
    connection_count = 0
    for header_file in header_files:
        map_name = header_file.stem
        data = parse_map_header(header_file)
        header_data[map_name] = data
        connection_count += len(data.get("connections", {}))
    print(f"  Parsed {len(header_data)} map headers")
    print(f"  Found {connection_count} map connections")

    # 5. Parse ledge tiles
    print("\nParsing ledge tiles...")
    ledge_data = parse_ledge_tiles(LEDGE_TILES_FILE)
    ledge_count = sum(len(v) for v in ledge_data.values())
    print(f"  Found {ledge_count} ledge definitions in {len(ledge_data)} tilesets")

    # 6. Build name mappings
    print("\nBuilding name mappings...")
    name_mappings = build_name_mappings(dimensions, header_data)
    print(f"  Built mappings for {len(name_mappings)} maps")

    # 7. Update map JSON files
    print("\nUpdating map JSON files...")
    map_files = list(MAPS_OUTPUT_PATH.glob("*.json"))
    updated = 0
    for map_file in map_files:
        if map_file.name == "index.json":
            continue
        if update_map_json(
            map_file,
            name_mappings,
            collision_data,
            tileset_info,
        ):
            updated += 1

    print(f"  Updated {updated} map files")

    # 7. Print examples
    print("\nExamples:")
    for map_name in ["PALLETTOWN", "VIRIDIANFOREST", "ROUTE1"]:
        # Try to find the file with different naming conventions
        for name_variant in [map_name, map_name.replace("_", "")]:
            map_file = MAPS_OUTPUT_PATH / f"{name_variant}.json"
            if map_file.exists():
                with open(map_file) as f:
                    data = json.load(f)
                print(f"  {name_variant}:")
                print(f"    Dimensions: {data.get('width', '?')}x{data.get('height', '?')}")
                print(f"    Tileset: {data.get('tileset', 'None')}")
                print(f"    Connections: {list(data.get('connections', {}).keys())}")
                print(f"    Walkable tiles: {len(data.get('walkable_tiles', []))} types")
                break

    print("\nDone!")
    return 0


if __name__ == "__main__":
    exit(main())
