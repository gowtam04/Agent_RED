#!/usr/bin/env python3
"""Extract type effectiveness chart from pokered ASM files."""

import json
import re
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
POKERED_PATH = PROJECT_ROOT / "external" / "pokered"
OUTPUT_PATH = PROJECT_ROOT / "data" / "type_chart.json"

# Source file
TYPE_MATCHUPS_FILE = POKERED_PATH / "data" / "types" / "type_matchups.asm"

# Effectiveness constants
EFFECTIVENESS_MAP = {
    "SUPER_EFFECTIVE": 2.0,
    "NOT_VERY_EFFECTIVE": 0.5,
    "NO_EFFECT": 0.0,
}

# Type name normalization (PSYCHIC_TYPE -> PSYCHIC)
TYPE_NAME_MAP = {
    "PSYCHIC_TYPE": "PSYCHIC",
}

# All Gen 1 types for validation
GEN1_TYPES = [
    "NORMAL", "FIRE", "WATER", "ELECTRIC", "GRASS", "ICE",
    "FIGHTING", "POISON", "GROUND", "FLYING", "PSYCHIC",
    "BUG", "ROCK", "GHOST", "DRAGON"
]


def normalize_type(type_name: str) -> str:
    """Normalize type name (e.g., PSYCHIC_TYPE -> PSYCHIC)."""
    return TYPE_NAME_MAP.get(type_name, type_name)


def parse_type_matchups(file_path: Path) -> dict[str, dict[str, float]]:
    """Parse type_matchups.asm and return effectiveness dictionary."""
    type_chart: dict[str, dict[str, float]] = {}

    content = file_path.read_text()

    # Pattern: db ATTACKER, DEFENDER, EFFECTIVENESS
    pattern = re.compile(
        r"db\s+(\w+)\s*,\s*(\w+)\s*,\s*(\w+)",
        re.IGNORECASE
    )

    for match in pattern.finditer(content):
        attacker = normalize_type(match.group(1).upper())
        defender = normalize_type(match.group(2).upper())
        effectiveness_str = match.group(3).upper()

        # Skip if not a valid effectiveness constant
        if effectiveness_str not in EFFECTIVENESS_MAP:
            continue

        effectiveness = EFFECTIVENESS_MAP[effectiveness_str]

        # Initialize attacker dict if needed
        if attacker not in type_chart:
            type_chart[attacker] = {}

        type_chart[attacker][defender] = effectiveness

    return type_chart


def validate_type_chart(type_chart: dict[str, dict[str, float]]) -> list[str]:
    """Validate the extracted type chart."""
    errors = []

    # Check all types are present (at least as attacker or defender)
    all_types_found = set()
    for attacker, matchups in type_chart.items():
        all_types_found.add(attacker)
        for defender in matchups:
            all_types_found.add(defender)

    missing_types = set(GEN1_TYPES) - all_types_found
    if missing_types:
        errors.append(f"Missing types: {missing_types}")

    # Check Ghost -> Psychic bug is preserved (should be 0.0, not 2.0)
    ghost_vs_psychic = type_chart.get("GHOST", {}).get("PSYCHIC")
    if ghost_vs_psychic != 0.0:
        errors.append(f"Ghost vs Psychic should be 0.0 (Gen 1 bug), got {ghost_vs_psychic}")

    return errors


def main():
    """Extract type chart and save to JSON."""
    print(f"Reading {TYPE_MATCHUPS_FILE}...")

    if not TYPE_MATCHUPS_FILE.exists():
        print(f"ERROR: File not found: {TYPE_MATCHUPS_FILE}")
        return 1

    type_chart = parse_type_matchups(TYPE_MATCHUPS_FILE)

    # Validate
    errors = validate_type_chart(type_chart)
    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
        return 1

    # Count matchups
    total_matchups = sum(len(v) for v in type_chart.values())
    print(f"Extracted {len(type_chart)} attacking types with {total_matchups} matchups")

    # Save to JSON
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(type_chart, f, indent=2, sort_keys=True)

    print(f"Saved to {OUTPUT_PATH}")

    # Print some examples
    print("\nExamples:")
    print(f"  FIRE vs GRASS: {type_chart.get('FIRE', {}).get('GRASS', 1.0)}x")
    print(f"  WATER vs FIRE: {type_chart.get('WATER', {}).get('FIRE', 1.0)}x")
    print(f"  GHOST vs PSYCHIC: {type_chart.get('GHOST', {}).get('PSYCHIC', 1.0)}x (Gen 1 bug!)")
    print(f"  NORMAL vs GHOST: {type_chart.get('NORMAL', {}).get('GHOST', 1.0)}x")

    return 0


if __name__ == "__main__":
    exit(main())
