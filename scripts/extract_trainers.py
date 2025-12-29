#!/usr/bin/env python3
"""Extract trainer party data from pokered ASM files."""

import json
import re
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
POKERED_PATH = PROJECT_ROOT / "external" / "pokered"
OUTPUT_PATH = PROJECT_ROOT / "data" / "trainers.json"

# Source file
PARTIES_FILE = POKERED_PATH / "data" / "trainers" / "parties.asm"

# Boss trainers
GYM_LEADERS = {"BROCK", "MISTY", "LTSURGE", "ERIKA", "KOGA", "SABRINA", "BLAINE", "GIOVANNI"}
ELITE_FOUR = {"LORELEI", "BRUNO", "AGATHA", "LANCE"}
RIVALS = {"RIVAL1", "RIVAL2", "RIVAL3"}

# Badge rewards
BADGE_REWARDS = {
    "BROCK": "BOULDER",
    "MISTY": "CASCADE",
    "LTSURGE": "THUNDER",
    "ERIKA": "RAINBOW",
    "KOGA": "SOUL",
    "SABRINA": "MARSH",
    "BLAINE": "VOLCANO",
    "GIOVANNI": "EARTH",
}


def parse_trainer_class(class_name: str, data_lines: list[str]) -> list[dict]:
    """Parse all teams for a trainer class."""
    teams = []
    team_index = 1

    for line in data_lines:
        line = line.strip()
        if not line or line.startswith(";"):
            continue

        # Parse team data
        match = re.match(r"db\s+(.+?)\s*,\s*0$", line)
        if not match:
            continue

        parts_str = match.group(1)
        parts = [p.strip() for p in parts_str.split(",")]

        if not parts:
            continue

        team = []
        if parts[0] == "$FF":
            # Variable level format: $FF, level1, species1, level2, species2, ...
            for i in range(1, len(parts) - 1, 2):
                if i + 1 < len(parts):
                    level = int(parts[i])
                    species = parts[i + 1]
                    team.append({"species": species, "level": level})
        else:
            # Fixed level format: level, species1, species2, ...
            level = int(parts[0])
            for species in parts[1:]:
                if species:
                    team.append({"species": species, "level": level})

        if team:
            trainer_id = f"{class_name}_{team_index}"
            teams.append({
                "trainer_id": trainer_id,
                "class": class_name,
                "team_index": team_index,
                "team": team,
            })
            team_index += 1

    return teams


def parse_parties(file_path: Path) -> dict:
    """Parse all trainer parties."""
    content = file_path.read_text()
    trainers = {}

    # Find all trainer class data sections
    pattern = re.compile(r"(\w+)Data:\s*\n(.*?)(?=\n\w+Data:|\Z)", re.DOTALL)

    for match in pattern.finditer(content):
        class_name = match.group(1).upper()
        data_section = match.group(2)

        # Split into lines
        lines = data_section.split("\n")

        # Parse teams
        teams = parse_trainer_class(class_name, lines)

        for team_data in teams:
            trainer_id = team_data["trainer_id"]

            # Check if boss trainer
            is_gym_leader = class_name in GYM_LEADERS
            is_elite_four = class_name in ELITE_FOUR
            is_rival = class_name in RIVALS
            is_boss = is_gym_leader or is_elite_four or is_rival

            trainer_data = {
                "trainer_id": trainer_id,
                "class": class_name,
                "team_index": team_data["team_index"],
                "team": team_data["team"],
                "is_boss": is_boss,
            }

            if is_gym_leader:
                trainer_data["boss_type"] = "GYM_LEADER"
                if class_name in BADGE_REWARDS:
                    trainer_data["badge_reward"] = BADGE_REWARDS[class_name]
            elif is_elite_four:
                trainer_data["boss_type"] = "ELITE_FOUR"
            elif is_rival:
                trainer_data["boss_type"] = "RIVAL"

            trainers[trainer_id] = trainer_data

    return trainers


def main():
    """Extract trainers and save to JSON."""
    print(f"Reading trainer data from {PARTIES_FILE}...")

    trainers = parse_parties(PARTIES_FILE)
    print(f"Extracted {len(trainers)} trainer teams")

    # Count boss trainers
    bosses = [t for t in trainers.values() if t.get("is_boss")]
    print(f"Found {len(bosses)} boss trainer teams")

    # Save to JSON
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(trainers, f, indent=2, sort_keys=True)

    print(f"Saved to {OUTPUT_PATH}")

    # Print examples
    print("\nExamples:")
    for trainer_id in ["BROCK_1", "MISTY_1", "BUGCATCHER_1", "RIVAL1_1"]:
        if trainer_id in trainers:
            t = trainers[trainer_id]
            team_str = ", ".join([f"Lv{p['level']} {p['species']}" for p in t["team"]])
            print(f"  {trainer_id}: [{team_str}]")

    return 0


if __name__ == "__main__":
    exit(main())
