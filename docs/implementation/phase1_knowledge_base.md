# Phase 1: Knowledge Base Foundation

## Objective
Extract game data from the pret/pokered disassembly repository and generate structured JSON files for use by the AI agents.

## Prerequisites
- Python 3.11+
- Poetry installed
- Git

## Setup

### 1. Clone the pokered repository
```bash
mkdir -p external
git clone https://github.com/pret/pokered.git external/pokered
```

### 2. Create the data directory
```bash
mkdir -p data/maps
```

### 3. Create the extraction scripts directory
```bash
mkdir -p scripts
```

---

## Deliverables

### 1. Type Chart (`data/type_chart.json`)

**Source File:** `external/pokered/data/types/type_matchups.asm`

**ASM Format:**
```asm
db ATTACKING_TYPE, DEFENDING_TYPE, EFFECTIVENESS
; where SUPER_EFFECTIVE = 20 (2.0x), NOT_VERY_EFFECTIVE = 05 (0.5x), NO_EFFECT = 00 (0.0x)
```

**Output Schema:**
```json
{
  "NORMAL": {
    "ROCK": 0.5,
    "GHOST": 0.0
  },
  "FIRE": {
    "FIRE": 0.5,
    "WATER": 0.5,
    "GRASS": 2.0,
    "ICE": 2.0,
    "BUG": 2.0,
    "ROCK": 0.5,
    "DRAGON": 0.5
  }
}
```

**CRITICAL:** Preserve the Gen 1 Ghost→Psychic bug: Ghost does 0.0x damage to Psychic (not 2.0x as intended).

**Types (15):** NORMAL, FIRE, WATER, ELECTRIC, GRASS, ICE, FIGHTING, POISON, GROUND, FLYING, PSYCHIC, BUG, ROCK, GHOST, DRAGON

**Script:** `scripts/extract_types.py`

---

### 2. Move Data (`data/moves.json`)

**Source Files:**
- `external/pokered/data/moves/moves.asm`
- `external/pokered/constants/move_constants.asm`

**ASM Format:**
```asm
move NAME, TYPE, POWER, ACCURACY, PP, EFFECT
```

**Output Schema:**
```json
{
  "THUNDERBOLT": {
    "id": 85,
    "name": "THUNDERBOLT",
    "type": "ELECTRIC",
    "category": "SPECIAL",
    "power": 95,
    "accuracy": 100,
    "pp": 15,
    "effect": "PARALYZE_SIDE_EFFECT1",
    "effect_chance": 10,
    "high_crit": false,
    "is_tm": "TM24",
    "is_hm": null
  }
}
```

**Category Rules (Gen 1):**
- PHYSICAL: NORMAL, FIGHTING, FLYING, GROUND, ROCK, BUG, GHOST, POISON
- SPECIAL: FIRE, WATER, ELECTRIC, GRASS, ICE, PSYCHIC, DRAGON
- STATUS: Power = 0

**Include TM/HM Mapping:**
```json
{
  "tm_mapping": {
    "TM01": "MEGA_PUNCH",
    "TM24": "THUNDERBOLT",
    "HM01": "CUT",
    "HM02": "FLY",
    "HM03": "SURF",
    "HM04": "STRENGTH",
    "HM05": "FLASH"
  }
}
```

**Script:** `scripts/extract_moves.py`

---

### 3. Pokemon Data (`data/pokemon.json`)

**Source Files:**
- `external/pokered/data/pokemon/base_stats/*.asm` (one file per species)
- `external/pokered/data/pokemon/evolutions.asm`
- `external/pokered/data/pokemon/learnsets.asm`
- `external/pokered/constants/pokemon_constants.asm`

**Base Stats ASM Format:**
```asm
db DEX_PIKACHU ; pokedex id
db  35,  55,  30,  90,  50
;    hp  atk  def  spd  spc
db ELECTRIC, ELECTRIC ; type (repeated = mono-type)
db 190 ; catch rate
db 82 ; base exp
```

**Output Schema:**
```json
{
  "PIKACHU": {
    "dex_number": 25,
    "name": "PIKACHU",
    "types": ["ELECTRIC"],
    "base_stats": {
      "hp": 35,
      "attack": 55,
      "defense": 30,
      "speed": 90,
      "special": 50
    },
    "catch_rate": 190,
    "base_exp_yield": 82,
    "evolution": {
      "to": "RAICHU",
      "method": "ITEM",
      "item": "THUNDER_STONE"
    },
    "learnset": [
      {"level": 1, "move": "THUNDERSHOCK"},
      {"level": 1, "move": "GROWL"},
      {"level": 9, "move": "THUNDER_WAVE"}
    ],
    "tm_compatibility": ["TM01", "TM05", "TM24", "TM25"],
    "hm_compatibility": ["HM05"]
  }
}
```

**Notes:**
- If both types are the same in ASM, output single type in array
- Evolution methods: LEVEL, ITEM, TRADE
- Handle Eevee's multiple evolutions as array

**Script:** `scripts/extract_pokemon.py`

---

### 4. Item Data (`data/items.json`)

**Source Files:**
- `external/pokered/constants/item_constants.asm`
- `external/pokered/data/items/` (various)

**Output Schema:**
```json
{
  "SUPER_POTION": {
    "id": 25,
    "name": "SUPER_POTION",
    "category": "HEALING",
    "buy_price": 700,
    "sell_price": 350,
    "effect": {
      "type": "HEAL_HP",
      "amount": 50
    },
    "usable_in_battle": true,
    "usable_in_field": true,
    "is_key_item": false
  },
  "POKE_BALL": {
    "id": 4,
    "name": "POKE_BALL",
    "category": "BALL",
    "buy_price": 200,
    "sell_price": 100,
    "catch_modifier": 1.0
  },
  "GREAT_BALL": {
    "catch_modifier": 1.5
  },
  "ULTRA_BALL": {
    "catch_modifier": 2.0
  },
  "MASTER_BALL": {
    "catch_modifier": 255
  }
}
```

**Script:** `scripts/extract_items.py`

---

### 5. Trainer Data (`data/trainers.json`)

**Source Files:**
- `external/pokered/data/trainers/parties.asm`
- `external/pokered/maps/*/objects.asm`
- `external/pokered/constants/trainer_constants.asm`

**Output Schema:**
```json
{
  "BROCK": {
    "trainer_id": "BROCK",
    "class": "GYM_LEADER",
    "name": "BROCK",
    "map": "PEWTER_GYM",
    "position": {"x": 4, "y": 2},
    "facing": "DOWN",
    "vision_range": 1,
    "team": [
      {"species": "GEODUDE", "level": 12, "moves": ["TACKLE", "DEFENSE_CURL"]},
      {"species": "ONIX", "level": 14, "moves": ["TACKLE", "SCREECH", "BIDE", "BIND"]}
    ],
    "prize_money": 1386,
    "is_boss": true,
    "boss_type": "GYM_LEADER",
    "badge_reward": "BOULDER"
  }
}
```

**Boss Trainers to Flag:**
- Gym Leaders: BROCK, MISTY, LT_SURGE, ERIKA, KOGA, SABRINA, BLAINE, GIOVANNI
- Elite Four: LORELEI, BRUNO, AGATHA, LANCE
- Champion: RIVAL (final)
- All RIVAL encounters throughout game

**Script:** `scripts/extract_trainers.py`

---

### 6. Shop Inventory (`data/shops.json`)

**Source File:** `external/pokered/data/marts/marts.asm`

**Output Schema:**
```json
{
  "VIRIDIAN_CITY": {
    "location": "VIRIDIAN_CITY",
    "base_inventory": [
      {"item": "POKE_BALL", "price": 200},
      {"item": "ANTIDOTE", "price": 100},
      {"item": "POTION", "price": 300}
    ],
    "unlocked_inventory": [
      {
        "requires": "BADGE_BOULDER",
        "items": [
          {"item": "GREAT_BALL", "price": 600}
        ]
      }
    ]
  }
}
```

**Script:** `scripts/extract_shops.py`

---

### 7. Wild Encounters (`data/wild_encounters.json`)

**Source Files:**
- `external/pokered/data/wild/grass.asm`
- `external/pokered/data/wild/water.asm`
- `external/pokered/data/wild/fish.asm`

**Slot Probabilities:**
| Slot | Probability |
|------|-------------|
| 1 | 20% |
| 2 | 20% |
| 3 | 15% |
| 4 | 10% |
| 5 | 10% |
| 6 | 10% |
| 7 | 5% |
| 8 | 5% |
| 9 | 4% |
| 10 | 1% |

**Output Schema:**
```json
{
  "ROUTE_1": {
    "grass": {
      "encounter_rate": 25,
      "pokemon": [
        {"slot": 1, "species": "RATTATA", "level": 3, "probability": 20},
        {"slot": 2, "species": "PIDGEY", "level": 3, "probability": 20}
      ]
    },
    "water": null,
    "fishing": null
  }
}
```

**Script:** `scripts/extract_wild.py`

---

### 8. Map Data (`data/maps/`)

**Source Files:**
- `external/pokered/maps/[MapName]/[MapName].asm`
- `external/pokered/maps/[MapName]/objects.asm`
- `external/pokered/data/maps/maps.asm`

**Output:** One JSON file per map + index file

**Index Schema (`data/maps/index.json`):**
```json
{
  "maps": ["PALLET_TOWN", "VIRIDIAN_CITY", "ROUTE_1", ...],
  "map_count": 150
}
```

**Per-Map Schema (`data/maps/VIRIDIAN_FOREST.json`):**
```json
{
  "map_id": "VIRIDIAN_FOREST",
  "display_name": "Viridian Forest",
  "width": 17,
  "height": 24,
  "tileset": "FOREST",
  "connections": {
    "north": {"map": "ROUTE_2_GATE", "offset": 0},
    "south": {"map": "ROUTE_2_GATE_2", "offset": 0}
  },
  "warps": [
    {"x": 1, "y": 0, "destination_map": "ROUTE_2_GATE", "destination_warp_id": 0}
  ],
  "trainers": [
    {"x": 8, "y": 6, "trainer_id": "BUG_CATCHER_1", "facing": "DOWN", "vision_range": 4}
  ],
  "item_balls": [
    {"x": 15, "y": 20, "item": "POTION"}
  ],
  "hidden_items": [
    {"x": 3, "y": 15, "item": "ANTIDOTE"}
  ],
  "properties": {
    "is_indoor": false,
    "has_wild_pokemon": true,
    "has_pokemon_center": false
  }
}
```

**Tile Data (optional, for pathfinding):**
```json
{
  "tiles": [
    [1, 1, 0, 0, 0, 2, 2, 0, 0, 1],
    ...
  ],
  "tile_legend": {
    "0": "WALKABLE",
    "1": "BLOCKED",
    "2": "GRASS",
    "3": "WATER",
    "4": "LEDGE_DOWN",
    "5": "CUT_TREE"
  }
}
```

**Script:** `scripts/extract_maps.py`

---

### 9. HM Requirements (`data/hm_requirements.json`)

**Manually compiled from game knowledge:**

```json
{
  "HM01_CUT": {
    "hm": "HM01",
    "move": "CUT",
    "badge_required": "CASCADE",
    "obtained_at": "SS_ANNE_CAPTAINS_CABIN",
    "obstacles": [
      {"map": "ROUTE_9", "blocks_access_to": ["ROCK_TUNNEL"]}
    ]
  },
  "HM02_FLY": {
    "hm": "HM02",
    "move": "FLY",
    "badge_required": "THUNDER",
    "obtained_at": "ROUTE_16_HOUSE"
  },
  "HM03_SURF": {
    "hm": "HM03",
    "move": "SURF",
    "badge_required": "SOUL",
    "obtained_at": "SAFARI_ZONE_SECRET_HOUSE",
    "enables_water_travel": true
  },
  "HM04_STRENGTH": {
    "hm": "HM04",
    "move": "STRENGTH",
    "badge_required": "RAINBOW",
    "obtained_at": "FUCHSIA_CITY_WARDEN_HOUSE"
  },
  "HM05_FLASH": {
    "hm": "HM05",
    "move": "FLASH",
    "badge_required": "BOULDER",
    "obtained_at": "ROUTE_2_GATE",
    "optional": true
  }
}
```

**Script:** `scripts/extract_hm.py` (or manual JSON file)

---

### 10. Story Progression (`data/story_progression.json`)

**Manually compiled:**

```json
{
  "milestones": [
    {
      "order": 1,
      "id": "GET_STARTER",
      "name": "Get Starter Pokemon",
      "type": "STORY_EVENT",
      "location": "OAKS_LAB",
      "prerequisites": [],
      "unlocks": ["ROUTE_1_ACCESS"]
    },
    {
      "order": 3,
      "id": "DEFEAT_BROCK",
      "name": "Defeat Brock",
      "type": "GYM_LEADER",
      "location": "PEWTER_GYM",
      "prerequisites": ["DELIVER_PARCEL"],
      "badge": "BOULDER",
      "recommended_level": 14,
      "recommended_types": ["WATER", "GRASS", "FIGHTING"]
    }
  ]
}
```

See `docs/06_knowledge_base.md` for full 23-milestone progression.

**Script:** `scripts/extract_story.py` (or manual JSON file)

---

## Accessor Classes

Create Python classes to load and query the JSON data:

### `src/knowledge/base.py`
```python
from abc import ABC, abstractmethod
from pathlib import Path
import json

class KnowledgeBase(ABC):
    def __init__(self, data_path: Path):
        self.data_path = data_path
        self._data = None

    def load(self) -> None:
        with open(self.data_path) as f:
            self._data = json.load(f)

    @property
    def data(self) -> dict:
        if self._data is None:
            self.load()
        return self._data

    @abstractmethod
    def get(self, key: str) -> dict | None:
        pass
```

### `src/knowledge/type_chart.py`
```python
class TypeChart(KnowledgeBase):
    def get_effectiveness(self, attack_type: str, defend_types: list[str]) -> float:
        """Calculate total effectiveness multiplier."""
        multiplier = 1.0
        for defend_type in defend_types:
            if defend_type in self.data.get(attack_type, {}):
                multiplier *= self.data[attack_type][defend_type]
        return multiplier
```

### Similar accessors for:
- `src/knowledge/pokemon.py`
- `src/knowledge/moves.py`
- `src/knowledge/items.py`
- `src/knowledge/trainers.py`
- `src/knowledge/shops.py`
- `src/knowledge/wild_encounters.py`
- `src/knowledge/maps.py`
- `src/knowledge/hm_requirements.py`
- `src/knowledge/story_progression.py`

---

## Master Extraction Script

### `scripts/extract_all.py`
```python
#!/usr/bin/env python3
"""Run all data extractors."""

import subprocess
import sys

SCRIPTS = [
    "scripts/extract_types.py",
    "scripts/extract_moves.py",
    "scripts/extract_pokemon.py",
    "scripts/extract_items.py",
    "scripts/extract_trainers.py",
    "scripts/extract_shops.py",
    "scripts/extract_wild.py",
    "scripts/extract_maps.py",
]

def main():
    for script in SCRIPTS:
        print(f"Running {script}...")
        result = subprocess.run([sys.executable, script])
        if result.returncode != 0:
            print(f"FAILED: {script}")
            return 1
    print("All extractions complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

---

## Validation

After extraction, validate:

1. **Pokemon:** All 151 species present (dex 1-151)
2. **Moves:** All referenced moves exist
3. **Types:** 15 types present, Ghost→Psychic = 0.0
4. **Cross-references:** Evolution species exist, learnset moves exist

### `scripts/validate_data.py`
```python
def validate():
    # Load all data
    # Check cross-references
    # Report errors
    pass
```

---

## Success Criteria

- [ ] `external/pokered/` repo cloned successfully
- [ ] All 10 JSON files generated in `data/`
- [ ] Type chart has 15 types with correct Gen 1 quirks
- [ ] All 151 Pokemon extracted with stats and learnsets
- [ ] All 165 moves extracted with properties
- [ ] Accessor classes load and query data correctly
- [ ] Validation script passes with no errors
- [ ] Unit tests in `tests/test_knowledge/` pass

---

## Estimated Complexity

| Component | Difficulty | Notes |
|-----------|------------|-------|
| Type chart | Easy | Simple triplet parsing |
| Moves | Medium | Need TM/HM mapping |
| Pokemon | Hard | Multiple ASM files, TM compatibility bits |
| Items | Medium | Scattered across files |
| Trainers | Hard | Cross-reference maps and parties |
| Maps | Very Hard | Complex ASM parsing, tile data |
| Shops | Easy | Single file parsing |
| Wild encounters | Medium | Multiple files |
| HM requirements | Easy | Manual compilation |
| Story progression | Easy | Manual compilation |
