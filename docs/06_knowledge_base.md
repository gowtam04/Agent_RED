# Pokemon Red AI Agent - Knowledge Base Documentation

This document specifies the data sources, extraction methods, and output schemas for all knowledge bases required by the Pokemon Red AI Agent system.

---

## Table of Contents

1. [Overview](#overview)
2. [Data Source](#data-source)
3. [Pokemon Data](#1-pokemon-data)
4. [Move Data](#2-move-data)
5. [Type Chart](#3-type-chart)
6. [Map Data](#4-map-data)
7. [Trainer Data](#5-trainer-data)
8. [Item Data](#6-item-data)
9. [Shop Inventory](#7-shop-inventory)
10. [Wild Encounters](#8-wild-encounters)
11. [HM Requirements](#9-hm-requirements)
12. [Story Progression](#10-story-progression)
13. [Output Format](#output-format)
14. [Validation](#validation)

---

## Overview

The Pokemon Red AI Agent requires several static knowledge bases to make informed decisions. All data should be extracted from the authoritative source: the disassembled Pokemon Red game code.

### Knowledge Base Summary

| Knowledge Base | Entries (approx) | Primary Consumer |
|---------------|------------------|------------------|
| Pokemon Data | 151 | Battle Agent |
| Move Data | 165 | Battle Agent |
| Type Chart | 15×15 matrix | Battle Agent |
| Map Data | 150 | Navigation Agent |
| Trainer Data | 391 | Navigation, Battle Agents |
| Item Data | 97 | Menu Agent |
| Shop Inventory | 18 | Menu Agent |
| Wild Encounters | ~50 areas | Navigation Agent |
| HM Requirements | ~25 | Orchestrator |
| Story Progression | ~25 | Orchestrator |

---

## Data Source

### Primary Repository

**Repository:** pret/pokered  
**URL:** https://github.com/pret/pokered  
**Branch:** master  
**Description:** Complete disassembly of Pokemon Red (US) in assembly language

This repository contains the entire game's source code, reverse-engineered into readable assembly. All game data (Pokemon stats, maps, trainers, items) exists as structured assembly data files.

### Repository Structure

Key directories for data extraction:

```
pokered/
├── constants/
│   ├── pokemon_constants.asm      # Pokemon IDs and names
│   ├── move_constants.asm         # Move IDs and names
│   ├── item_constants.asm         # Item IDs and names
│   ├── type_constants.asm         # Type IDs
│   └── trainer_constants.asm      # Trainer class IDs
├── data/
│   ├── pokemon/
│   │   ├── base_stats/            # Individual Pokemon .asm files
│   │   ├── evolutions.asm         # Evolution data
│   │   └── learnsets.asm          # Level-up moves (Generation I)
│   ├── moves/
│   │   └── moves.asm              # All move data
│   ├── types/
│   │   └── type_matchups.asm      # Type effectiveness chart
│   ├── trainers/
│   │   └── parties.asm            # Trainer Pokemon teams
│   ├── items/
│   │   └── item_effects.asm       # Item properties
│   ├── marts/
│   │   └── marts.asm              # Shop inventories
│   └── wild/
│       └── *.asm                  # Wild encounter tables
├── maps/
│   └── [MapName]/
│       ├── [MapName].asm          # Map header and scripts
│       └── objects.asm            # NPCs, trainers, items on map
└── gfx/
    └── tilesets/                  # Map tileset data
```

### Assembly Data Format

Data in pokered is stored in assembly format. Common patterns:

**Pokemon Base Stats Example (data/pokemon/base_stats/pikachu.asm):**
```asm
	db DEX_PIKACHU ; pokedex id
	db  35,  55,  30,  90,  50
	;    hp  atk  def  spd  spc
	db ELECTRIC, ELECTRIC ; type
	db 190 ; catch rate
	db 82 ; base exp
    ; ... more fields
```

**Move Data Example (data/moves/moves.asm):**
```asm
	move POUND,        NORMAL,      40, 100, 35, NO_ADDITIONAL_EFFECT
	move KARATE_CHOP,  FIGHTING,    50, 100, 25, HIGH_CRITICAL_EFFECT
```

**Type Matchup Example (data/types/type_matchups.asm):**
```asm
	db FIRE, GRASS, SUPER_EFFECTIVE
	db WATER, FIRE, SUPER_EFFECTIVE
	db ELECTRIC, GROUND, NO_EFFECT
```

---

## 1. Pokemon Data

### Source Files

| File | Data Provided |
|------|---------------|
| `data/pokemon/base_stats/*.asm` | Base stats, types, catch rate, exp yield |
| `data/pokemon/evolutions.asm` | Evolution chains and methods |
| `data/pokemon/learnsets.asm` | Level-up move learning |
| `constants/pokemon_constants.asm` | Pokemon names and IDs |

### Extraction Details

**From base_stats/*.asm files:**

Each Pokemon has its own file (e.g., `pikachu.asm`). Parse the following fields:
- Pokedex number (first `db` value)
- HP, Attack, Defense, Speed, Special (5 values on second `db` line)
- Type 1, Type 2 (third `db` line - if same, Pokemon is mono-type)
- Catch rate
- Base experience yield
- TM/HM compatibility flags (bit flags indicating learnable TMs/HMs)

**From evolutions.asm:**

Format varies by evolution type:
- Level evolution: `db EV_LEVEL, level, EVOLVED_SPECIES`
- Item evolution: `db EV_ITEM, ITEM_ID, EVOLVED_SPECIES`
- Trade evolution: `db EV_TRADE, EVOLVED_SPECIES`

**From learnsets.asm:**

Level-up moves are stored as pairs: `db level, MOVE_ID`

### Output Schema

```json
{
  "pokemon": {
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
        {"level": 9, "move": "THUNDER_WAVE"},
        {"level": 16, "move": "QUICK_ATTACK"},
        {"level": 26, "move": "SWIFT"},
        {"level": 33, "move": "AGILITY"},
        {"level": 43, "move": "THUNDER"}
      ],
      "tm_compatibility": ["TM01", "TM05", "TM06", "TM08", "TM09", "TM10", "TM16", "TM17", "TM19", "TM20", "TM24", "TM25", "TM31", "TM32", "TM33", "TM34", "TM39", "TM40", "TM44", "TM45", "TM50"],
      "hm_compatibility": ["HM05"]
    }
  }
}
```

### Special Considerations

- Pokemon with one type list it twice in the source data; output should show single type
- TM/HM compatibility is stored as a bit field; must decode which TMs/HMs are learnable
- Some Pokemon have multiple evolution paths (Eevee); handle as array
- Dex number in source may differ from array index; use explicit dex_number field

---

## 2. Move Data

### Source Files

| File | Data Provided |
|------|---------------|
| `data/moves/moves.asm` | All move properties |
| `constants/move_constants.asm` | Move names and IDs |

### Extraction Details

**From moves.asm:**

Each move is defined with a macro:
```
move NAME, TYPE, POWER, ACCURACY, PP, EFFECT
```

Fields to extract:
- Move name (ID constant)
- Type
- Power (0 for status moves)
- Accuracy (percent)
- PP (Power Points)
- Effect (secondary effect constant)

**Effect Constants to Handle:**
- `NO_ADDITIONAL_EFFECT` - No secondary effect
- `HIGH_CRITICAL_EFFECT` - High critical hit ratio
- `POISON_SIDE_EFFECT1` - 20% poison chance
- `POISON_SIDE_EFFECT2` - 40% poison chance  
- `BURN_SIDE_EFFECT1` - 10% burn chance
- `BURN_SIDE_EFFECT2` - 30% burn chance
- `FREEZE_SIDE_EFFECT` - 10% freeze chance
- `PARALYZE_SIDE_EFFECT1` - 10% paralysis chance
- `PARALYZE_SIDE_EFFECT2` - 30% paralysis chance
- `FLINCH_SIDE_EFFECT1` - 10% flinch chance
- `FLINCH_SIDE_EFFECT2` - 30% flinch chance
- `SLEEP_EFFECT` - Puts target to sleep
- `CONFUSION_EFFECT` - Confuses target
- And more...

**Determine Move Category:**
- In Gen 1, category is determined by type:
  - Physical: NORMAL, FIGHTING, FLYING, GROUND, ROCK, BUG, GHOST, POISON
  - Special: FIRE, WATER, ELECTRIC, GRASS, ICE, PSYCHIC, DRAGON

### Output Schema

```json
{
  "moves": {
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
      "priority": 0,
      "high_crit": false,
      "is_tm": "TM24",
      "is_hm": null,
      "description": "10% chance to paralyze"
    }
  }
}
```

### TM/HM Mapping

Create a separate mapping of TM/HM numbers to moves:

| TM/HM | Move |
|-------|------|
| TM01 | MEGA_PUNCH |
| TM02 | RAZOR_WIND |
| ... | ... |
| HM01 | CUT |
| HM02 | FLY |
| HM03 | SURF |
| HM04 | STRENGTH |
| HM05 | FLASH |

Source: `constants/item_constants.asm` and cross-reference with move teaching code

### Special Considerations

- Priority moves (Quick Attack = +1) need manual annotation or extraction from battle code
- High crit moves are identified by `HIGH_CRITICAL_EFFECT`
- Some moves have 0 power (status moves) - still include them
- Move ID 0 is sometimes used as "no move" - handle appropriately

---

## 3. Type Chart

### Source Files

| File | Data Provided |
|------|---------------|
| `data/types/type_matchups.asm` | Type effectiveness relationships |
| `constants/type_constants.asm` | Type IDs |

### Extraction Details

**From type_matchups.asm:**

Effectiveness is stored as triplets:
```asm
db ATTACKING_TYPE, DEFENDING_TYPE, EFFECTIVENESS
```

Where effectiveness is:
- `SUPER_EFFECTIVE` = 20 (represents 2.0x)
- `NOT_VERY_EFFECTIVE` = 05 (represents 0.5x)
- `NO_EFFECT` = 00 (represents 0.0x)

Any type pair NOT listed defaults to 1.0x (normal effectiveness).

### Output Schema

```json
{
  "type_chart": {
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
    },
    "WATER": {
      "FIRE": 2.0,
      "WATER": 0.5,
      "GRASS": 0.5,
      "GROUND": 2.0,
      "ROCK": 2.0,
      "DRAGON": 0.5
    },
    "ELECTRIC": {
      "WATER": 2.0,
      "ELECTRIC": 0.5,
      "GRASS": 0.5,
      "GROUND": 0.0,
      "FLYING": 2.0,
      "DRAGON": 0.5
    },
    "GRASS": {
      "FIRE": 0.5,
      "WATER": 2.0,
      "GRASS": 0.5,
      "POISON": 0.5,
      "GROUND": 2.0,
      "FLYING": 0.5,
      "BUG": 0.5,
      "ROCK": 2.0,
      "DRAGON": 0.5
    },
    "ICE": {
      "FIRE": 0.5,
      "WATER": 0.5,
      "GRASS": 2.0,
      "ICE": 0.5,
      "GROUND": 2.0,
      "FLYING": 2.0,
      "DRAGON": 2.0
    },
    "FIGHTING": {
      "NORMAL": 2.0,
      "ICE": 2.0,
      "POISON": 0.5,
      "FLYING": 0.5,
      "PSYCHIC": 0.5,
      "BUG": 0.5,
      "ROCK": 2.0,
      "GHOST": 0.0
    },
    "POISON": {
      "GRASS": 2.0,
      "POISON": 0.5,
      "GROUND": 0.5,
      "ROCK": 0.5,
      "BUG": 2.0,
      "GHOST": 0.5
    },
    "GROUND": {
      "FIRE": 2.0,
      "ELECTRIC": 2.0,
      "GRASS": 0.5,
      "POISON": 2.0,
      "FLYING": 0.0,
      "BUG": 0.5,
      "ROCK": 2.0
    },
    "FLYING": {
      "ELECTRIC": 0.5,
      "GRASS": 2.0,
      "FIGHTING": 2.0,
      "BUG": 2.0,
      "ROCK": 0.5
    },
    "PSYCHIC": {
      "FIGHTING": 2.0,
      "POISON": 2.0,
      "PSYCHIC": 0.5
    },
    "BUG": {
      "FIRE": 0.5,
      "GRASS": 2.0,
      "FIGHTING": 0.5,
      "FLYING": 0.5,
      "POISON": 2.0,
      "GHOST": 0.5,
      "PSYCHIC": 2.0
    },
    "ROCK": {
      "FIRE": 2.0,
      "ICE": 2.0,
      "FIGHTING": 0.5,
      "GROUND": 0.5,
      "FLYING": 2.0,
      "BUG": 2.0
    },
    "GHOST": {
      "NORMAL": 0.0,
      "GHOST": 2.0,
      "PSYCHIC": 0.0
    },
    "DRAGON": {
      "DRAGON": 2.0
    }
  }
}
```

### Gen 1 Type Chart Quirks

**CRITICAL - Must preserve these bugs:**

1. **Ghost → Psychic = 0.0x (IMMUNE)** - This is a famous bug. Ghost was supposed to be super effective against Psychic, but due to a programming error, Ghost does NO damage to Psychic types.

2. **Ghost → Normal = 0.0x** - Normal is immune to Ghost (this is correct and intentional)

3. **Psychic has no effective counters** - Due to the Ghost bug and weak Bug moves, Psychic types dominate Gen 1

4. **No Steel or Dark types** - These didn't exist in Gen 1

5. **Poison is super effective against Bug** - Changed in later generations

### Special Considerations

- Default effectiveness (not listed) = 1.0x
- When calculating damage against dual-types, multiply both effectiveness values
- The type list is: NORMAL, FIRE, WATER, ELECTRIC, GRASS, ICE, FIGHTING, POISON, GROUND, FLYING, PSYCHIC, BUG, ROCK, GHOST, DRAGON (15 types)

---

## 4. Map Data

### Source Files

| File | Data Provided |
|------|---------------|
| `maps/[MapName]/[MapName].asm` | Map header, dimensions, connections |
| `maps/[MapName]/objects.asm` | NPCs, trainers, warps, signs |
| `data/maps/maps.asm` | Map constants and groupings |
| `data/tilesets/*.asm` | Tile collision data |
| `maps/[MapName].blk` | Map tile layout (binary) |

### Extraction Details

**From map header files ([MapName].asm):**

```asm
	map_header MapName, TILESET_ID, MAP_WIDTH, MAP_HEIGHT, ...
	connection NORTH, ConnectedMap, ...
	connection SOUTH, ConnectedMap, ...
```

Extract:
- Map name/ID
- Tileset ID (for collision data)
- Width and height in blocks
- Connections to adjacent maps (north, south, east, west)

**From objects.asm:**

Contains definitions for:
- Warps (doors, stairs, cave entrances)
- Signs (readable text)
- NPCs (static and walking)
- Items (item balls on ground)
- Trainers (includes position, direction, range)

Warp format:
```asm
warp_event X, Y, DEST_MAP, DEST_WARP_ID
```

Trainer format:
```asm
trainer_event X, Y, FACING, VISION_RANGE, TRAINER_CLASS, TRAINER_ID
```

**From .blk files:**

Binary files containing tile indices. Each byte represents one 2x2 tile block. Combined with tileset collision data to determine walkability.

**Tileset collision:**

Each tileset has collision data marking tiles as:
- Walkable (floor, grass)
- Blocked (walls, water without Surf)
- Special (ledge, water, counter)

### Output Schema

```json
{
  "maps": {
    "VIRIDIAN_FOREST": {
      "map_id": "VIRIDIAN_FOREST",
      "display_name": "Viridian Forest",
      "width": 17,
      "height": 24,
      "tileset": "FOREST",
      "connections": {
        "north": {
          "map": "ROUTE_2_GATE",
          "offset": 0
        },
        "south": {
          "map": "ROUTE_2_GATE_2",
          "offset": 0
        }
      },
      "warps": [
        {
          "x": 1,
          "y": 0,
          "destination_map": "ROUTE_2_GATE",
          "destination_warp_id": 0
        }
      ],
      "signs": [
        {
          "x": 5,
          "y": 10,
          "text_id": "VIRIDIAN_FOREST_SIGN_1"
        }
      ],
      "npcs": [
        {
          "x": 8,
          "y": 6,
          "sprite": "YOUNGSTER",
          "movement": "STANDING",
          "facing": "DOWN"
        }
      ],
      "item_balls": [
        {
          "x": 15,
          "y": 20,
          "item": "POTION",
          "hidden": false
        }
      ],
      "trainers": [
        {
          "x": 8,
          "y": 6,
          "trainer_class": "BUG_CATCHER",
          "trainer_id": 1,
          "facing": "DOWN",
          "vision_range": 4
        }
      ],
      "hidden_items": [
        {
          "x": 3,
          "y": 15,
          "item": "ANTIDOTE"
        }
      ],
      "properties": {
        "is_indoor": false,
        "is_dungeon": true,
        "has_wild_pokemon": true,
        "has_pokemon_center": false,
        "has_pokemart": false,
        "has_gym": false,
        "flyable": false
      }
    }
  }
}
```

### Tile Data Output

For pathfinding, include simplified collision grid:

```json
{
  "map_tiles": {
    "VIRIDIAN_FOREST": {
      "width": 17,
      "height": 24,
      "tiles": [
        [1, 1, 0, 0, 0, 2, 2, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1],
        ...
      ],
      "tile_legend": {
        "0": "WALKABLE",
        "1": "BLOCKED",
        "2": "GRASS",
        "3": "WATER",
        "4": "LEDGE_DOWN",
        "5": "CUT_TREE",
        "6": "STRENGTH_BOULDER",
        "7": "DOOR"
      }
    }
  }
}
```

### Special Considerations

- Map dimensions are in "blocks" (2x2 tiles); multiply by 2 for tile coordinates
- Warp destination IDs reference the index in destination map's warp list
- Indoor/outdoor affects wild encounters and Fly availability
- Some maps have multiple floors (Pokemon Tower, Silph Co) - treat as separate maps
- Cave maps use different coordinate systems; normalize all to consistent format

---

## 5. Trainer Data

### Source Files

| File | Data Provided |
|------|---------------|
| `data/trainers/parties.asm` | Trainer Pokemon teams |
| `maps/[MapName]/objects.asm` | Trainer positions and properties |
| `constants/trainer_constants.asm` | Trainer class IDs and names |
| `data/trainers/special_trainer_flags.asm` | Boss battle identifiers |

### Extraction Details

**From parties.asm:**

Trainer teams are defined by class and ID:
```asm
TrainerClass1Party1:
    db POKEMON1, LEVEL1
    db POKEMON2, LEVEL2
    db 0 ; end marker
```

Some trainers have custom movesets (gym leaders, Elite Four).

**From objects.asm (per map):**

```asm
trainer_event X, Y, FACING_DIR, VISION_RANGE, TRAINER_CLASS, TEAM_ID
```

Fields:
- X, Y: Position on map
- FACING_DIR: Direction trainer faces (determines line of sight)
- VISION_RANGE: How many tiles trainer can see (triggers battle)
- TRAINER_CLASS: Class constant (BUG_CATCHER, LASS, etc.)
- TEAM_ID: Which team variant for this class

**Boss Identification:**

Gym Leaders, Elite Four, Champion, and Rival have special flags. Identify by:
- Trainer class constants for gym leaders (BROCK, MISTY, etc.)
- Elite Four have dedicated class constants
- Rival encounters have multiple team variants based on story progress

### Output Schema

```json
{
  "trainers": {
    "BUG_CATCHER_VIRIDIAN_FOREST_1": {
      "trainer_id": "BUG_CATCHER_VIRIDIAN_FOREST_1",
      "class": "BUG_CATCHER",
      "class_id": 1,
      "name": null,
      "map": "VIRIDIAN_FOREST",
      "position": {
        "x": 8,
        "y": 6
      },
      "facing": "DOWN",
      "vision_range": 4,
      "team": [
        {
          "species": "WEEDLE",
          "level": 9,
          "moves": null
        },
        {
          "species": "CATERPIE", 
          "level": 9,
          "moves": null
        }
      ],
      "prize_money": 90,
      "is_boss": false,
      "boss_type": null,
      "defeat_flag": "TRAINER_BUG_CATCHER_VF_1"
    },
    "BROCK": {
      "trainer_id": "BROCK",
      "class": "GYM_LEADER",
      "class_id": 201,
      "name": "BROCK",
      "map": "PEWTER_GYM",
      "position": {
        "x": 4,
        "y": 2
      },
      "facing": "DOWN",
      "vision_range": 1,
      "team": [
        {
          "species": "GEODUDE",
          "level": 12,
          "moves": ["TACKLE", "DEFENSE_CURL"]
        },
        {
          "species": "ONIX",
          "level": 14,
          "moves": ["TACKLE", "SCREECH", "BIDE", "BIND"]
        }
      ],
      "prize_money": 1386,
      "is_boss": true,
      "boss_type": "GYM_LEADER",
      "badge_reward": "BOULDER",
      "defeat_flag": "BADGE_BOULDER"
    }
  }
}
```

### Boss Trainer List

Document these explicitly for Opus model routing:

**Gym Leaders:**
- BROCK (Pewter City)
- MISTY (Cerulean City)
- LT_SURGE (Vermilion City)
- ERIKA (Celadon City)
- KOGA (Fuchsia City)
- SABRINA (Saffron City)
- BLAINE (Cinnabar Island)
- GIOVANNI (Viridian City)

**Elite Four:**
- LORELEI
- BRUNO
- AGATHA
- LANCE

**Champion:**
- RIVAL (final battle)

**Rival Encounters:**
Track all rival battles throughout the game (approximately 7 encounters)

### Special Considerations

- Prize money is calculated from trainer class base rate × highest Pokemon level
- Some trainers can be skipped; track which are mandatory
- Gym trainers often have the same class as the leader type
- Rival teams change based on starter selection - need all variants
- Elite Four and Champion are sequential with no healing between

---

## 6. Item Data

### Source Files

| File | Data Provided |
|------|---------------|
| `constants/item_constants.asm` | Item IDs and names |
| `data/items/item_effects.asm` | Item properties and effects |
| `engine/items/item_effects.asm` | Item use behaviors |

### Extraction Details

**From item_constants.asm:**

List of all item constants with IDs.

**From item data files:**

Extract properties:
- Price (for buying at marts)
- Sellable flag
- Key item flag
- Effect type and parameters

**Categories to identify:**
- Healing items (Potion, Super Potion, etc.)
- Status cure items (Antidote, Awakening, etc.)
- Battle items (X Attack, X Speed, etc.)
- Poke Balls (Poke Ball, Great Ball, Ultra Ball, Master Ball)
- Key Items (Bicycle, HM items, story items)
- TMs and HMs
- Evolution items (Moon Stone, Thunder Stone, etc.)
- Valuables (Nugget, etc. - sell only)

### Output Schema

```json
{
  "items": {
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
      "is_key_item": false,
      "is_tm": false,
      "is_hm": false,
      "description": "Restores 50 HP to one Pokemon"
    },
    "THUNDER_STONE": {
      "id": 33,
      "name": "THUNDER_STONE",
      "category": "EVOLUTION",
      "buy_price": 2100,
      "sell_price": 1050,
      "effect": {
        "type": "EVOLVE",
        "compatible": ["PIKACHU", "EEVEE"]
      },
      "usable_in_battle": false,
      "usable_in_field": true,
      "is_key_item": false,
      "is_tm": false,
      "is_hm": false,
      "description": "Evolves certain Pokemon"
    },
    "HM01": {
      "id": 196,
      "name": "HM01",
      "category": "HM",
      "buy_price": null,
      "sell_price": null,
      "effect": {
        "type": "TEACH_MOVE",
        "move": "CUT"
      },
      "usable_in_battle": false,
      "usable_in_field": true,
      "is_key_item": true,
      "is_tm": false,
      "is_hm": true,
      "hm_number": 1,
      "move_name": "CUT",
      "badge_required": "CASCADE",
      "description": "Teaches Cut to a compatible Pokemon"
    },
    "BICYCLE": {
      "id": 6,
      "name": "BICYCLE",
      "category": "KEY_ITEM",
      "buy_price": 1000000,
      "sell_price": null,
      "effect": {
        "type": "FIELD_USE",
        "action": "DOUBLE_SPEED"
      },
      "usable_in_battle": false,
      "usable_in_field": true,
      "is_key_item": true,
      "is_tm": false,
      "is_hm": false,
      "description": "Doubles movement speed"
    }
  }
}
```

### Poke Ball Catch Modifiers

| Ball | Catch Rate Modifier |
|------|---------------------|
| POKE_BALL | 1.0 |
| GREAT_BALL | 1.5 |
| ULTRA_BALL | 2.0 |
| MASTER_BALL | 255 (guaranteed) |
| SAFARI_BALL | 1.5 |

### Special Considerations

- Key items cannot be sold or discarded
- TMs are consumed when used; HMs are not
- HMs teach moves that cannot be forgotten via normal means
- Some items have different effects in battle vs field
- Item bag has limited slots (20 in Gen 1)

---

## 7. Shop Inventory

### Source Files

| File | Data Provided |
|------|---------------|
| `data/marts/marts.asm` | Shop inventories by location |

### Extraction Details

**From marts.asm:**

Each shop is defined by location with a list of available items:
```asm
Mart_ViridianCity:
    db 4 ; number of items
    db POKE_BALL
    db ANTIDOTE
    db PARLYZ_HEAL
    db POTION
    db -1 ; end marker
```

Some shops have conditional inventory based on badges or story progress.

### Output Schema

```json
{
  "shops": {
    "VIRIDIAN_CITY": {
      "location": "VIRIDIAN_CITY",
      "map": "VIRIDIAN_CITY",
      "position": {
        "x": 20,
        "y": 15
      },
      "base_inventory": [
        {"item": "POKE_BALL", "price": 200},
        {"item": "ANTIDOTE", "price": 100},
        {"item": "PARLYZ_HEAL", "price": 200},
        {"item": "POTION", "price": 300}
      ],
      "unlocked_inventory": [
        {
          "requires": "BADGE_BOULDER",
          "items": [
            {"item": "GREAT_BALL", "price": 600},
            {"item": "SUPER_POTION", "price": 700}
          ]
        }
      ]
    },
    "INDIGO_PLATEAU": {
      "location": "INDIGO_PLATEAU",
      "map": "INDIGO_PLATEAU_LOBBY",
      "position": {
        "x": 15,
        "y": 10
      },
      "base_inventory": [
        {"item": "ULTRA_BALL", "price": 1200},
        {"item": "GREAT_BALL", "price": 600},
        {"item": "FULL_RESTORE", "price": 3000},
        {"item": "MAX_POTION", "price": 2500},
        {"item": "FULL_HEAL", "price": 600},
        {"item": "REVIVE", "price": 1500},
        {"item": "MAX_REPEL", "price": 700}
      ],
      "unlocked_inventory": []
    }
  }
}
```

### Shop Locations

All Poke Mart locations in the game:
1. Viridian City
2. Pewter City
3. Cerulean City
4. Vermilion City
5. Lavender Town
6. Celadon City (Department Store - multiple floors)
7. Celadon City (roof vending machines)
8. Fuchsia City
9. Saffron City
10. Cinnabar Island
11. Indigo Plateau

### Special Considerations

- Celadon Department Store has multiple floors with different inventories
- Some items only become available after certain badges
- Prices are fixed; no haggling or discounts
- Some special trades exist (Magikarp salesman on Route 4)

---

## 8. Wild Encounters

### Source Files

| File | Data Provided |
|------|---------------|
| `data/wild/grass.asm` | Grass encounter tables |
| `data/wild/water.asm` | Water encounter tables |
| `data/wild/fish.asm` | Fishing encounter tables |

### Extraction Details

**From encounter files:**

Each route/area has encounter tables with slots:
```asm
Route1_GrassEncounters:
    db 25 ; encounter rate
    db 3, RATTATA
    db 3, PIDGEY
    db 4, RATTATA
    db 4, PIDGEY
    db 2, RATTATA
    ; ... 10 slots total
```

Each slot has:
- Level
- Pokemon species
- Implicit encounter probability based on slot position

**Slot Probabilities (Grass/Cave):**

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

### Output Schema

```json
{
  "wild_encounters": {
    "ROUTE_1": {
      "location": "ROUTE_1",
      "grass": {
        "encounter_rate": 25,
        "pokemon": [
          {"slot": 1, "species": "RATTATA", "level": 3, "probability": 20},
          {"slot": 2, "species": "PIDGEY", "level": 3, "probability": 20},
          {"slot": 3, "species": "RATTATA", "level": 4, "probability": 15},
          {"slot": 4, "species": "PIDGEY", "level": 4, "probability": 10},
          {"slot": 5, "species": "RATTATA", "level": 2, "probability": 10},
          {"slot": 6, "species": "PIDGEY", "level": 2, "probability": 10},
          {"slot": 7, "species": "RATTATA", "level": 5, "probability": 5},
          {"slot": 8, "species": "PIDGEY", "level": 5, "probability": 5},
          {"slot": 9, "species": "RATTATA", "level": 3, "probability": 4},
          {"slot": 10, "species": "PIDGEY", "level": 3, "probability": 1}
        ]
      },
      "water": null,
      "fishing": null
    },
    "CERULEAN_CITY": {
      "location": "CERULEAN_CITY",
      "grass": null,
      "water": {
        "encounter_rate": 5,
        "pokemon": [
          {"slot": 1, "species": "TENTACOOL", "level": 5, "probability": 100}
        ]
      },
      "fishing": {
        "old_rod": [
          {"species": "MAGIKARP", "level": 5}
        ],
        "good_rod": [
          {"species": "POLIWAG", "level": 10},
          {"species": "GOLDEEN", "level": 10}
        ],
        "super_rod": [
          {"species": "PSYDUCK", "level": 15},
          {"species": "SLOWPOKE", "level": 15},
          {"species": "KRABBY", "level": 15},
          {"species": "HORSEA", "level": 15}
        ]
      }
    }
  }
}
```

### Special Considerations

- Encounter rate determines how often you get encounters while walking (higher = more frequent)
- Some areas have no wild encounters (towns, most buildings)
- Version differences exist (Red vs Blue) - document both or pick one
- Safari Zone has unique mechanics - include but note the differences
- Time of day doesn't affect encounters in Gen 1

---

## 9. HM Requirements

### Source Files

| File | Data Provided |
|------|---------------|
| Various map scripts | Obstacle locations |
| `engine/overworld/hm_moves.asm` | HM usage code |

### Extraction Details

This data needs to be compiled from multiple sources:
1. Map tile data showing CUT trees, water, boulders
2. Badge requirements for HM usage
3. Story progression gates

### Output Schema

```json
{
  "hm_requirements": {
    "HM01_CUT": {
      "hm": "HM01",
      "move": "CUT",
      "badge_required": "CASCADE",
      "obtained_at": "SS_ANNE_CAPTAIN",
      "obtained_map": "SS_ANNE_CAPTAINS_CABIN",
      "usage_type": "FIELD",
      "obstacles": [
        {
          "map": "ROUTE_9",
          "position": {"x": 5, "y": 12},
          "blocks_access_to": ["ROCK_TUNNEL"]
        },
        {
          "map": "ROUTE_2",
          "position": {"x": 8, "y": 35},
          "blocks_access_to": ["DIGLETTS_CAVE_ENTRANCE"]
        }
      ]
    },
    "HM02_FLY": {
      "hm": "HM02",
      "move": "FLY",
      "badge_required": "THUNDER",
      "obtained_at": "ROUTE_16_HOUSE",
      "obtained_map": "ROUTE_16_HOUSE",
      "usage_type": "TRANSPORT",
      "destinations": [
        "PALLET_TOWN",
        "VIRIDIAN_CITY",
        "PEWTER_CITY",
        "CERULEAN_CITY",
        "VERMILION_CITY",
        "LAVENDER_TOWN",
        "CELADON_CITY",
        "FUCHSIA_CITY",
        "SAFFRON_CITY",
        "CINNABAR_ISLAND",
        "INDIGO_PLATEAU"
      ]
    },
    "HM03_SURF": {
      "hm": "HM03",
      "move": "SURF",
      "badge_required": "SOUL",
      "obtained_at": "SAFARI_ZONE_SECRET_HOUSE",
      "obtained_map": "SAFARI_ZONE_SECRET_HOUSE",
      "usage_type": "FIELD",
      "enables_water_travel": true,
      "required_for": [
        "SEAFOAM_ISLANDS",
        "CINNABAR_ISLAND",
        "POWER_PLANT_ENTRANCE",
        "ROUTE_19",
        "ROUTE_20",
        "ROUTE_21"
      ]
    },
    "HM04_STRENGTH": {
      "hm": "HM04",
      "move": "STRENGTH",
      "badge_required": "RAINBOW",
      "obtained_at": "FUCHSIA_CITY_WARDEN",
      "obtained_map": "FUCHSIA_CITY_WARDEN_HOUSE",
      "usage_type": "FIELD",
      "obstacles": [
        {
          "map": "VICTORY_ROAD_1F",
          "boulders": 4,
          "required": true
        },
        {
          "map": "SEAFOAM_ISLANDS_B1F",
          "boulders": 2,
          "required": true
        }
      ]
    },
    "HM05_FLASH": {
      "hm": "HM05",
      "move": "FLASH",
      "badge_required": "BOULDER",
      "obtained_at": "ROUTE_2_GATE",
      "obtained_map": "ROUTE_2_GATE",
      "usage_type": "UTILITY",
      "lights_up": [
        "ROCK_TUNNEL"
      ],
      "optional": true
    }
  }
}
```

### Route Blocking Summary

Quick reference of what blocks what:

| Route/Location | Blocker | HM Required | Badge Required |
|----------------|---------|-------------|----------------|
| Route 9 → Rock Tunnel | CUT tree | CUT | CASCADE |
| Route 2 → Diglett's Cave | CUT tree | CUT | CASCADE |
| Cerulean → Route 24 | CUT tree (optional) | CUT | CASCADE |
| Route 19-21 (Water routes) | Water | SURF | SOUL |
| Seafoam Islands | Water + Boulders | SURF + STRENGTH | SOUL + RAINBOW |
| Victory Road | Boulders | STRENGTH | RAINBOW |
| Rock Tunnel | Darkness | FLASH | BOULDER |

### Special Considerations

- Flash is technically optional (can navigate Rock Tunnel in the dark)
- Fly destinations unlock as you visit cities
- Some HM obstacles respawn; cut trees return after leaving area
- Strength boulders stay pushed until you leave the map

---

## 10. Story Progression

### Source Files

This data is compiled from game script analysis and manual documentation.

| File | Data Provided |
|------|---------------|
| `scripts/*.asm` | Event triggers and flags |
| `engine/events/*.asm` | Story event handlers |
| `constants/event_constants.asm` | Event flag definitions |

### Extraction Details

Story milestones should be manually compiled based on:
1. Required badges to progress
2. Key item acquisitions
3. NPC events that gate progress
4. Battle requirements

### Output Schema

```json
{
  "story_progression": [
    {
      "order": 1,
      "milestone_id": "GET_STARTER",
      "name": "Get Starter Pokemon",
      "type": "STORY_EVENT",
      "location": "OAKS_LAB",
      "trigger": "Talk to Oak after rival leaves",
      "reward": "Starter Pokemon (Bulbasaur/Charmander/Squirtle)",
      "unlocks": ["ROUTE_1_ACCESS"],
      "prerequisites": [],
      "story_flag": "EVENT_GOT_STARTER"
    },
    {
      "order": 2,
      "milestone_id": "DELIVER_PARCEL",
      "name": "Deliver Oak's Parcel",
      "type": "STORY_EVENT",
      "location": "OAKS_LAB",
      "trigger": "Return to Oak with parcel from Viridian Mart",
      "reward": "Pokedex, 5 Poke Balls",
      "unlocks": ["POKEDEX", "VIRIDIAN_FOREST_ACCESS"],
      "prerequisites": ["GET_STARTER"],
      "story_flag": "EVENT_GOT_POKEDEX"
    },
    {
      "order": 3,
      "milestone_id": "DEFEAT_BROCK",
      "name": "Defeat Brock",
      "type": "GYM_LEADER",
      "location": "PEWTER_GYM",
      "trigger": "Defeat Brock in battle",
      "reward": "Boulder Badge, TM34 (Bide)",
      "unlocks": ["FLASH_USABLE", "ROUTE_3_ACCESS"],
      "prerequisites": ["DELIVER_PARCEL"],
      "story_flag": "EVENT_BEAT_BROCK",
      "badge": "BOULDER",
      "recommended_level": 14,
      "recommended_types": ["WATER", "GRASS", "FIGHTING"]
    },
    {
      "order": 4,
      "milestone_id": "DEFEAT_MISTY",
      "name": "Defeat Misty",
      "type": "GYM_LEADER",
      "location": "CERULEAN_GYM",
      "trigger": "Defeat Misty in battle",
      "reward": "Cascade Badge, TM11 (Bubblebeam)",
      "unlocks": ["CUT_USABLE"],
      "prerequisites": ["DEFEAT_BROCK"],
      "story_flag": "EVENT_BEAT_MISTY",
      "badge": "CASCADE",
      "recommended_level": 21,
      "recommended_types": ["ELECTRIC", "GRASS"]
    },
    {
      "order": 5,
      "milestone_id": "RESCUE_BILL",
      "name": "Rescue Bill",
      "type": "STORY_EVENT",
      "location": "BILLS_HOUSE",
      "trigger": "Help Bill transform back from Pokemon",
      "reward": "SS Ticket",
      "unlocks": ["SS_ANNE_ACCESS"],
      "prerequisites": ["DEFEAT_RIVAL_CERULEAN"],
      "story_flag": "EVENT_MET_BILL"
    },
    {
      "order": 6,
      "milestone_id": "GET_HM01_CUT",
      "name": "Get HM01 Cut",
      "type": "KEY_ITEM",
      "location": "SS_ANNE_CAPTAINS_CABIN",
      "trigger": "Talk to Captain after helping with seasickness",
      "reward": "HM01 (Cut)",
      "unlocks": ["CUT_OBTAINED"],
      "prerequisites": ["RESCUE_BILL"],
      "story_flag": "EVENT_GOT_HM01"
    },
    {
      "order": 7,
      "milestone_id": "DEFEAT_LT_SURGE",
      "name": "Defeat Lt. Surge",
      "type": "GYM_LEADER",
      "location": "VERMILION_GYM",
      "trigger": "Defeat Lt. Surge in battle (after solving trash can puzzle)",
      "reward": "Thunder Badge, TM24 (Thunderbolt)",
      "unlocks": ["FLY_USABLE"],
      "prerequisites": ["GET_HM01_CUT"],
      "story_flag": "EVENT_BEAT_LT_SURGE",
      "badge": "THUNDER",
      "recommended_level": 24,
      "recommended_types": ["GROUND"],
      "notes": "Requires solving electric lock puzzle in gym"
    },
    {
      "order": 8,
      "milestone_id": "GET_SILPH_SCOPE",
      "name": "Get Silph Scope",
      "type": "KEY_ITEM",
      "location": "ROCKET_HIDEOUT",
      "trigger": "Defeat Giovanni in Rocket Hideout",
      "reward": "Silph Scope",
      "unlocks": ["POKEMON_TOWER_TOP_ACCESS"],
      "prerequisites": ["DEFEAT_LT_SURGE"],
      "story_flag": "EVENT_GOT_SILPH_SCOPE"
    },
    {
      "order": 9,
      "milestone_id": "RESCUE_MR_FUJI",
      "name": "Rescue Mr. Fuji",
      "type": "STORY_EVENT",
      "location": "POKEMON_TOWER",
      "trigger": "Defeat Ghost Marowak and Team Rocket",
      "reward": "Poke Flute",
      "unlocks": ["SNORLAX_CLEARABLE"],
      "prerequisites": ["GET_SILPH_SCOPE"],
      "story_flag": "EVENT_RESCUED_MR_FUJI"
    },
    {
      "order": 10,
      "milestone_id": "DEFEAT_ERIKA",
      "name": "Defeat Erika",
      "type": "GYM_LEADER",
      "location": "CELADON_GYM",
      "trigger": "Defeat Erika in battle",
      "reward": "Rainbow Badge, TM21 (Mega Drain)",
      "unlocks": ["STRENGTH_USABLE"],
      "prerequisites": ["GET_SILPH_SCOPE"],
      "story_flag": "EVENT_BEAT_ERIKA",
      "badge": "RAINBOW",
      "recommended_level": 30,
      "recommended_types": ["FIRE", "ICE", "FLYING", "POISON"]
    },
    {
      "order": 11,
      "milestone_id": "DEFEAT_KOGA",
      "name": "Defeat Koga",
      "type": "GYM_LEADER",
      "location": "FUCHSIA_GYM",
      "trigger": "Defeat Koga in battle",
      "reward": "Soul Badge, TM06 (Toxic)",
      "unlocks": ["SURF_USABLE"],
      "prerequisites": ["RESCUE_MR_FUJI"],
      "story_flag": "EVENT_BEAT_KOGA",
      "badge": "SOUL",
      "recommended_level": 43,
      "recommended_types": ["GROUND", "PSYCHIC"]
    },
    {
      "order": 12,
      "milestone_id": "GET_HM03_SURF",
      "name": "Get HM03 Surf",
      "type": "KEY_ITEM",
      "location": "SAFARI_ZONE_SECRET_HOUSE",
      "trigger": "Reach secret house in Safari Zone",
      "reward": "HM03 (Surf)",
      "unlocks": ["SURF_OBTAINED"],
      "prerequisites": [],
      "story_flag": "EVENT_GOT_HM03",
      "notes": "Can be obtained before Koga but requires Safari Zone navigation"
    },
    {
      "order": 13,
      "milestone_id": "LIBERATE_SILPH_CO",
      "name": "Liberate Silph Co.",
      "type": "STORY_EVENT",
      "location": "SILPH_CO",
      "trigger": "Defeat Giovanni at Silph Co.",
      "reward": "Master Ball",
      "unlocks": ["SAFFRON_GYM_ACCESS"],
      "prerequisites": ["DEFEAT_KOGA"],
      "story_flag": "EVENT_BEAT_SILPH_CO_GIOVANNI"
    },
    {
      "order": 14,
      "milestone_id": "DEFEAT_SABRINA",
      "name": "Defeat Sabrina",
      "type": "GYM_LEADER",
      "location": "SAFFRON_GYM",
      "trigger": "Defeat Sabrina in battle",
      "reward": "Marsh Badge, TM46 (Psywave)",
      "unlocks": [],
      "prerequisites": ["LIBERATE_SILPH_CO"],
      "story_flag": "EVENT_BEAT_SABRINA",
      "badge": "MARSH",
      "recommended_level": 43,
      "recommended_types": ["BUG"],
      "notes": "Psychic types are OP in Gen 1; bring high-damage Pokemon"
    },
    {
      "order": 15,
      "milestone_id": "DEFEAT_BLAINE",
      "name": "Defeat Blaine",
      "type": "GYM_LEADER",
      "location": "CINNABAR_GYM",
      "trigger": "Defeat Blaine in battle (after answering quiz)",
      "reward": "Volcano Badge, TM38 (Fire Blast)",
      "unlocks": [],
      "prerequisites": ["GET_SECRET_KEY"],
      "story_flag": "EVENT_BEAT_BLAINE",
      "badge": "VOLCANO",
      "recommended_level": 47,
      "recommended_types": ["WATER", "GROUND", "ROCK"]
    },
    {
      "order": 16,
      "milestone_id": "GET_SECRET_KEY",
      "name": "Get Secret Key",
      "type": "KEY_ITEM",
      "location": "POKEMON_MANSION",
      "trigger": "Find Secret Key in Pokemon Mansion",
      "reward": "Secret Key",
      "unlocks": ["CINNABAR_GYM_ACCESS"],
      "prerequisites": ["SURF_OBTAINED"],
      "story_flag": "EVENT_GOT_SECRET_KEY"
    },
    {
      "order": 17,
      "milestone_id": "DEFEAT_GIOVANNI_GYM",
      "name": "Defeat Giovanni (Gym Leader)",
      "type": "GYM_LEADER",
      "location": "VIRIDIAN_GYM",
      "trigger": "Defeat Giovanni in Viridian Gym",
      "reward": "Earth Badge, TM27 (Fissure)",
      "unlocks": ["VICTORY_ROAD_ACCESS"],
      "prerequisites": ["DEFEAT_BLAINE"],
      "story_flag": "EVENT_BEAT_GIOVANNI_GYM",
      "badge": "EARTH",
      "recommended_level": 50,
      "recommended_types": ["WATER", "GRASS", "ICE"]
    },
    {
      "order": 18,
      "milestone_id": "COMPLETE_VICTORY_ROAD",
      "name": "Complete Victory Road",
      "type": "DUNGEON",
      "location": "VICTORY_ROAD",
      "trigger": "Navigate Victory Road to Indigo Plateau",
      "reward": "Access to Elite Four",
      "unlocks": ["ELITE_FOUR_ACCESS"],
      "prerequisites": ["DEFEAT_GIOVANNI_GYM", "STRENGTH_USABLE", "SURF_USABLE"],
      "story_flag": "EVENT_VICTORY_ROAD_COMPLETE",
      "notes": "Requires Surf and Strength"
    },
    {
      "order": 19,
      "milestone_id": "DEFEAT_LORELEI",
      "name": "Defeat Lorelei",
      "type": "ELITE_FOUR",
      "location": "INDIGO_PLATEAU",
      "trigger": "Defeat Lorelei in battle",
      "reward": "Progress to Bruno",
      "unlocks": ["BRUNO_ACCESS"],
      "prerequisites": ["COMPLETE_VICTORY_ROAD"],
      "story_flag": "EVENT_BEAT_LORELEI",
      "recommended_level": 52,
      "recommended_types": ["ELECTRIC", "FIGHTING", "ROCK"]
    },
    {
      "order": 20,
      "milestone_id": "DEFEAT_BRUNO",
      "name": "Defeat Bruno",
      "type": "ELITE_FOUR",
      "location": "INDIGO_PLATEAU",
      "trigger": "Defeat Bruno in battle",
      "reward": "Progress to Agatha",
      "unlocks": ["AGATHA_ACCESS"],
      "prerequisites": ["DEFEAT_LORELEI"],
      "story_flag": "EVENT_BEAT_BRUNO",
      "recommended_level": 54,
      "recommended_types": ["WATER", "PSYCHIC", "ICE", "FLYING"]
    },
    {
      "order": 21,
      "milestone_id": "DEFEAT_AGATHA",
      "name": "Defeat Agatha",
      "type": "ELITE_FOUR",
      "location": "INDIGO_PLATEAU",
      "trigger": "Defeat Agatha in battle",
      "reward": "Progress to Lance",
      "unlocks": ["LANCE_ACCESS"],
      "prerequisites": ["DEFEAT_BRUNO"],
      "story_flag": "EVENT_BEAT_AGATHA",
      "recommended_level": 56,
      "recommended_types": ["GROUND", "PSYCHIC"],
      "notes": "Ghost types use Poison subtype; Ground is effective"
    },
    {
      "order": 22,
      "milestone_id": "DEFEAT_LANCE",
      "name": "Defeat Lance",
      "type": "ELITE_FOUR",
      "location": "INDIGO_PLATEAU",
      "trigger": "Defeat Lance in battle",
      "reward": "Progress to Champion",
      "unlocks": ["CHAMPION_ACCESS"],
      "prerequisites": ["DEFEAT_AGATHA"],
      "story_flag": "EVENT_BEAT_LANCE",
      "recommended_level": 58,
      "recommended_types": ["ICE", "ROCK", "ELECTRIC"]
    },
    {
      "order": 23,
      "milestone_id": "BECOME_CHAMPION",
      "name": "Become Champion",
      "type": "CHAMPION",
      "location": "INDIGO_PLATEAU",
      "trigger": "Defeat Rival in final battle",
      "reward": "Hall of Fame entry, Game Complete",
      "unlocks": ["GAME_COMPLETE", "CERULEAN_CAVE_ACCESS"],
      "prerequisites": ["DEFEAT_LANCE"],
      "story_flag": "EVENT_BEAT_CHAMPION",
      "recommended_level": 60,
      "recommended_types": "Varies by rival's starter"
    }
  ]
}
```

### Special Considerations

- Some milestones can be done out of order (gyms 4-7 especially)
- Elite Four is sequential with no saving/healing between battles
- Rival battles occur at multiple points; each has different teams
- Post-game content (Cerulean Cave, Mewtwo) exists but isn't required

---

## Output Format

### File Structure

All knowledge base data should be output as JSON files:

```
knowledge_base/
├── pokemon.json          # Pokemon data (151 entries)
├── moves.json            # Move data (165 entries)
├── type_chart.json       # Type effectiveness matrix
├── maps/
│   ├── maps.json         # Map metadata
│   └── tiles/
│       └── [map_id].json # Individual map tile data
├── trainers.json         # Trainer data (391 entries)
├── items.json            # Item data (97 entries)
├── shops.json            # Shop inventories (18 entries)
├── wild_encounters.json  # Wild Pokemon tables
├── hm_requirements.json  # HM obstacles and requirements
└── story_progression.json # Story milestones (25 entries)
```

### JSON Conventions

1. **Keys:** Use SCREAMING_SNAKE_CASE for Pokemon, move, item, map names (matching game constants)
2. **Enums:** Use strings, not integers, for type names, categories, etc.
3. **Null handling:** Use `null` for absent optional fields, not empty strings
4. **Arrays:** Use arrays for ordered lists, objects for lookups by key
5. **Numbers:** Use integers where appropriate (no floating point for stats)

### Indexing

Create index files for quick lookups:

```json
{
  "pokemon_by_type": {
    "ELECTRIC": ["PIKACHU", "RAICHU", "VOLTORB", "ELECTRODE", "ELECTABUZZ", "JOLTEON", "ZAPDOS"],
    "WATER": ["SQUIRTLE", "WARTORTLE", "BLASTOISE", ...]
  },
  "moves_by_type": {
    "ELECTRIC": ["THUNDERSHOCK", "THUNDERBOLT", "THUNDER", "THUNDER_WAVE", ...],
    ...
  },
  "maps_with_pokemon_center": ["VIRIDIAN_CITY", "PEWTER_CITY", ...],
  "trainers_by_map": {
    "VIRIDIAN_FOREST": ["BUG_CATCHER_VF_1", "BUG_CATCHER_VF_2", ...],
    ...
  }
}
```

---

## Validation

### Cross-Reference Checks

After extraction, validate:

1. **Pokemon data:**
   - All 151 Pokemon present (dex 1-151)
   - All referenced moves exist in moves.json
   - All evolutions reference valid Pokemon
   - TM/HM compatibility matches move teachability

2. **Move data:**
   - All 165 moves present
   - All types are valid (15 Gen 1 types)
   - Power/accuracy/PP values are within expected ranges
   - TM/HM numbers map correctly

3. **Type chart:**
   - 15 types present
   - All effectiveness values are 0, 0.5, 1.0, or 2.0
   - Ghost → Psychic = 0.0 (Gen 1 bug preserved)

4. **Maps:**
   - All connections reference valid maps
   - All warps have valid destinations
   - Trainer positions within map bounds

5. **Trainers:**
   - All trainer Pokemon exist in pokemon.json
   - All trainers have valid map assignments
   - Boss trainers properly flagged

6. **Items:**
   - TMs teach moves that exist
   - HMs have correct badge requirements
   - Prices match expected values

7. **Story progression:**
   - Prerequisites form valid DAG (no cycles)
   - All referenced badges/items exist

### External Validation Sources

Cross-reference extracted data against:
- Bulbapedia (bulbapedia.bulbagarden.net)
- PokemonDB (pokemondb.net/pokedex/game/red-blue)
- Serebii (serebii.net/rb/)

---

## Summary

This document provides complete specifications for building the Pokemon Red AI Agent knowledge base by parsing the pret/pokered disassembly. The parser should:

1. Clone the pokered repository
2. Parse each data category from the specified source files
3. Transform assembly data into JSON format matching the schemas above
4. Validate output against cross-reference checks
5. Generate index files for efficient lookups

The resulting knowledge base will provide all static game data needed by the Orchestrator, Navigation, Battle, and Menu agents to play Pokemon Red autonomously.
