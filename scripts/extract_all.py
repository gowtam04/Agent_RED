#!/usr/bin/env python3
"""Master script to run all data extractors."""

import subprocess
import sys
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# Extractors in order of dependencies
EXTRACTORS = [
    "extract_types.py",
    "extract_moves.py",
    "extract_pokemon.py",
    "extract_items.py",
    "extract_wild.py",
    "extract_shops.py",
    "extract_trainers.py",
    "extract_maps.py",
]


def run_extractor(script_name: str) -> bool:
    """Run a single extractor script.

    Args:
        script_name: Name of the script file.

    Returns:
        True if successful, False otherwise.
    """
    script_path = SCRIPTS_DIR / script_name
    print(f"\n{'='*60}")
    print(f"Running {script_name}...")
    print("=" * 60)

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=PROJECT_ROOT,
        capture_output=False,
    )

    return result.returncode == 0


def main():
    """Run all extractors and validation."""
    print("=" * 60)
    print("Project RED - Data Extraction Pipeline")
    print("=" * 60)

    # Check pokered exists
    pokered_path = PROJECT_ROOT / "external" / "pokered"
    if not pokered_path.exists():
        print(f"ERROR: pokered repository not found at {pokered_path}")
        print("Please clone it first:")
        print("  git clone https://github.com/pret/pokered.git external/pokered")
        return 1

    # Run all extractors
    failed = []
    for script in EXTRACTORS:
        if not run_extractor(script):
            failed.append(script)
            print(f"WARNING: {script} failed!")

    # Run validation
    print(f"\n{'='*60}")
    print("Running validation...")
    print("=" * 60)

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "validate_data.py")],
        cwd=PROJECT_ROOT,
    )

    if result.returncode != 0:
        failed.append("validate_data.py")

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print("=" * 60)

    if failed:
        print(f"Failed scripts: {', '.join(failed)}")
        return 1
    else:
        print("All extractors and validation completed successfully!")
        return 0


if __name__ == "__main__":
    exit(main())
