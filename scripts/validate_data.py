#!/usr/bin/env python3
"""Validate extracted game data for consistency."""

import json
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_PATH = PROJECT_ROOT / "data"


def load_json(filename: str) -> dict | list:
    """Load a JSON file from the data directory."""
    with open(DATA_PATH / filename) as f:
        return json.load(f)


def validate_type_chart() -> list[str]:
    """Validate type chart data."""
    errors = []
    type_chart = load_json("type_chart.json")

    # Check we have all 15 Gen 1 types
    expected_types = {
        "NORMAL", "FIRE", "WATER", "ELECTRIC", "GRASS", "ICE",
        "FIGHTING", "POISON", "GROUND", "FLYING", "PSYCHIC",
        "BUG", "ROCK", "GHOST", "DRAGON"
    }

    all_types = set(type_chart.keys())
    for matchups in type_chart.values():
        all_types.update(matchups.keys())

    missing = expected_types - all_types
    if missing:
        errors.append(f"Type chart missing types: {missing}")

    # Check Ghost vs Psychic bug
    ghost_vs_psychic = type_chart.get("GHOST", {}).get("PSYCHIC")
    if ghost_vs_psychic != 0.0:
        errors.append(f"Ghost vs Psychic should be 0.0 (Gen 1 bug), got {ghost_vs_psychic}")

    return errors


def validate_pokemon() -> list[str]:
    """Validate Pokemon data."""
    errors = []
    pokemon = load_json("pokemon.json")
    moves = load_json("moves.json")["moves"]

    # Check we have 151 Pokemon
    if len(pokemon) != 151:
        errors.append(f"Expected 151 Pokemon, got {len(pokemon)}")

    # Check Pokedex numbers 1-151
    dex_numbers = {p["dex_number"] for p in pokemon.values()}
    missing_dex = set(range(1, 152)) - dex_numbers
    if missing_dex:
        errors.append(f"Missing Pokedex numbers: {sorted(missing_dex)}")

    # Check evolution targets exist
    for name, data in pokemon.items():
        for evo in data.get("evolutions", []):
            target = evo.get("to")
            if target and target not in pokemon:
                errors.append(f"{name} evolves to unknown Pokemon: {target}")

    # Check learnset moves exist
    for name, data in pokemon.items():
        for learn in data.get("learnset", []):
            move = learn.get("move")
            if move and move not in moves:
                errors.append(f"{name} learns unknown move: {move}")

    return errors


def validate_moves() -> list[str]:
    """Validate move data."""
    errors = []
    data = load_json("moves.json")
    moves = data["moves"]
    tm_hm = data["tm_hm_mapping"]

    # Check we have enough moves
    if len(moves) < 165:
        errors.append(f"Expected at least 165 moves, got {len(moves)}")

    # Check TM/HM count
    tms = [k for k in tm_hm.keys() if k.startswith("TM")]
    hms = [k for k in tm_hm.keys() if k.startswith("HM")]

    if len(tms) != 50:
        errors.append(f"Expected 50 TMs, got {len(tms)}")
    if len(hms) != 5:
        errors.append(f"Expected 5 HMs, got {len(hms)}")

    # Check TM/HM moves exist
    for tm_hm_id, move_name in tm_hm.items():
        if move_name not in moves:
            errors.append(f"{tm_hm_id} references unknown move: {move_name}")

    return errors


def validate_trainers() -> list[str]:
    """Validate trainer data."""
    errors = []
    trainers = load_json("trainers.json")
    pokemon = load_json("pokemon.json")

    # Check trainer team Pokemon exist
    for trainer_id, data in trainers.items():
        for member in data.get("team", []):
            species = member.get("species")
            if species and species not in pokemon:
                errors.append(f"Trainer {trainer_id} has unknown Pokemon: {species}")

    # Check gym leaders exist
    gym_leaders = [t for t in trainers.values() if t.get("boss_type") == "GYM_LEADER"]
    if len(gym_leaders) < 8:
        errors.append(f"Expected at least 8 Gym Leader teams, got {len(gym_leaders)}")

    return errors


def validate_wild_encounters() -> list[str]:
    """Validate wild encounter data."""
    errors = []
    encounters = load_json("wild_encounters.json")
    pokemon = load_json("pokemon.json")

    # Check encounter Pokemon exist
    for map_id, data in encounters.items():
        for enc_type in ["grass", "water"]:
            if data.get(enc_type):
                for slot in data[enc_type].get("pokemon", []):
                    species = slot.get("species")
                    if species and species not in pokemon:
                        errors.append(f"{map_id} has unknown encounter: {species}")

    return errors


def main():
    """Run all validations."""
    print("Validating extracted data...\n")

    all_errors = []

    validators = [
        ("Type Chart", validate_type_chart),
        ("Pokemon", validate_pokemon),
        ("Moves", validate_moves),
        ("Trainers", validate_trainers),
        ("Wild Encounters", validate_wild_encounters),
    ]

    for name, validator in validators:
        try:
            errors = validator()
            if errors:
                print(f"❌ {name}: {len(errors)} error(s)")
                for error in errors:
                    print(f"   - {error}")
                all_errors.extend(errors)
            else:
                print(f"✓ {name}: OK")
        except FileNotFoundError as e:
            print(f"⚠ {name}: File not found - {e}")
            all_errors.append(f"{name}: File not found")
        except Exception as e:
            print(f"❌ {name}: Exception - {e}")
            all_errors.append(f"{name}: {e}")

    print()
    if all_errors:
        print(f"Validation complete with {len(all_errors)} error(s)")
        return 1
    else:
        print("Validation complete - all checks passed!")
        return 0


if __name__ == "__main__":
    exit(main())
