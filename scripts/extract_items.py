#!/usr/bin/env python3
"""Extract item data from pokered ASM files."""

import json
import re
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
POKERED_PATH = PROJECT_ROOT / "external" / "pokered"
OUTPUT_PATH = PROJECT_ROOT / "data" / "items.json"

# Source files
ITEM_CONSTANTS_FILE = POKERED_PATH / "constants" / "item_constants.asm"
PRICES_FILE = POKERED_PATH / "data" / "items" / "prices.asm"
KEY_ITEMS_FILE = POKERED_PATH / "data" / "items" / "key_items.asm"

# Item categories and effects (manually defined based on game knowledge)
ITEM_CATEGORIES = {
    # Poke Balls
    "MASTER_BALL": ("BALL", {"catch_modifier": 255}),
    "ULTRA_BALL": ("BALL", {"catch_modifier": 2.0}),
    "GREAT_BALL": ("BALL", {"catch_modifier": 1.5}),
    "POKE_BALL": ("BALL", {"catch_modifier": 1.0}),
    "SAFARI_BALL": ("BALL", {"catch_modifier": 1.5}),

    # Healing items
    "POTION": ("HEALING", {"heal_hp": 20}),
    "SUPER_POTION": ("HEALING", {"heal_hp": 50}),
    "HYPER_POTION": ("HEALING", {"heal_hp": 200}),
    "MAX_POTION": ("HEALING", {"heal_hp": 999}),
    "FULL_RESTORE": ("HEALING", {"heal_hp": 999, "heal_status": True}),
    "REVIVE": ("HEALING", {"revive": True, "heal_hp_percent": 50}),
    "MAX_REVIVE": ("HEALING", {"revive": True, "heal_hp_percent": 100}),
    "FRESH_WATER": ("HEALING", {"heal_hp": 50}),
    "SODA_POP": ("HEALING", {"heal_hp": 60}),
    "LEMONADE": ("HEALING", {"heal_hp": 80}),

    # Status healing
    "ANTIDOTE": ("STATUS_HEAL", {"cure": "POISON"}),
    "BURN_HEAL": ("STATUS_HEAL", {"cure": "BURN"}),
    "ICE_HEAL": ("STATUS_HEAL", {"cure": "FREEZE"}),
    "AWAKENING": ("STATUS_HEAL", {"cure": "SLEEP"}),
    "PARLYZ_HEAL": ("STATUS_HEAL", {"cure": "PARALYSIS"}),
    "FULL_HEAL": ("STATUS_HEAL", {"cure": "ALL"}),

    # PP restoration
    "ETHER": ("PP_RESTORE", {"restore_pp": 10, "moves": 1}),
    "MAX_ETHER": ("PP_RESTORE", {"restore_pp": 999, "moves": 1}),
    "ELIXER": ("PP_RESTORE", {"restore_pp": 10, "moves": "ALL"}),
    "MAX_ELIXER": ("PP_RESTORE", {"restore_pp": 999, "moves": "ALL"}),

    # Evolution stones
    "FIRE_STONE": ("EVOLUTION", {"evolves": ["VULPIX", "GROWLITHE", "EEVEE"]}),
    "WATER_STONE": ("EVOLUTION", {"evolves": ["POLIWHIRL", "SHELLDER", "STARYU", "EEVEE"]}),
    "THUNDER_STONE": ("EVOLUTION", {"evolves": ["PIKACHU", "EEVEE"]}),
    "LEAF_STONE": ("EVOLUTION", {"evolves": ["GLOOM", "WEEPINBELL", "EXEGGCUTE"]}),
    "MOON_STONE": ("EVOLUTION", {"evolves": ["NIDORINA", "NIDORINO", "CLEFAIRY", "JIGGLYPUFF"]}),

    # Vitamins
    "HP_UP": ("VITAMIN", {"boost": "HP"}),
    "PROTEIN": ("VITAMIN", {"boost": "ATTACK"}),
    "IRON": ("VITAMIN", {"boost": "DEFENSE"}),
    "CARBOS": ("VITAMIN", {"boost": "SPEED"}),
    "CALCIUM": ("VITAMIN", {"boost": "SPECIAL"}),
    "RARE_CANDY": ("VITAMIN", {"level_up": True}),
    "PP_UP": ("VITAMIN", {"boost_pp": True}),

    # Repels
    "REPEL": ("REPEL", {"steps": 100}),
    "SUPER_REPEL": ("REPEL", {"steps": 200}),
    "MAX_REPEL": ("REPEL", {"steps": 250}),

    # Battle items
    "X_ATTACK": ("BATTLE", {"boost": "ATTACK", "stages": 1}),
    "X_DEFEND": ("BATTLE", {"boost": "DEFENSE", "stages": 1}),
    "X_SPEED": ("BATTLE", {"boost": "SPEED", "stages": 1}),
    "X_SPECIAL": ("BATTLE", {"boost": "SPECIAL", "stages": 1}),
    "X_ACCURACY": ("BATTLE", {"boost": "ACCURACY", "stages": 1}),
    "DIRE_HIT": ("BATTLE", {"boost": "CRITICAL", "stages": 1}),
    "GUARD_SPEC": ("BATTLE", {"prevent_stat_drop": True}),
    "POKE_DOLL": ("BATTLE", {"escape": True}),

    # Fishing rods
    "OLD_ROD": ("FISHING", {"power": 1}),
    "GOOD_ROD": ("FISHING", {"power": 2}),
    "SUPER_ROD": ("FISHING", {"power": 3}),

    # Key items
    "TOWN_MAP": ("KEY", {}),
    "BICYCLE": ("KEY", {}),
    "POKEDEX": ("KEY", {}),
    "SURFBOARD": ("KEY", {}),
    "COIN_CASE": ("KEY", {}),
    "OAKS_PARCEL": ("KEY", {}),
    "ITEMFINDER": ("KEY", {}),
    "SILPH_SCOPE": ("KEY", {}),
    "POKE_FLUTE": ("KEY", {}),
    "LIFT_KEY": ("KEY", {}),
    "S_S_TICKET": ("KEY", {}),
    "GOLD_TEETH": ("KEY", {}),
    "CARD_KEY": ("KEY", {}),
    "SECRET_KEY": ("KEY", {}),
    "BIKE_VOUCHER": ("KEY", {}),
    "EXP_ALL": ("KEY", {}),

    # Fossils
    "OLD_AMBER": ("FOSSIL", {"revives_to": "AERODACTYL"}),
    "DOME_FOSSIL": ("FOSSIL", {"revives_to": "KABUTO"}),
    "HELIX_FOSSIL": ("FOSSIL", {"revives_to": "OMANYTE"}),

    # Badges (treated as items in Gen 1)
    "BOULDERBADGE": ("BADGE", {"gym": 1}),
    "CASCADEBADGE": ("BADGE", {"gym": 2}),
    "THUNDERBADGE": ("BADGE", {"gym": 3}),
    "RAINBOWBADGE": ("BADGE", {"gym": 4}),
    "SOULBADGE": ("BADGE", {"gym": 5}),
    "MARSHBADGE": ("BADGE", {"gym": 6}),
    "VOLCANOBADGE": ("BADGE", {"gym": 7}),
    "EARTHBADGE": ("BADGE", {"gym": 8}),

    # Misc
    "ESCAPE_ROPE": ("ESCAPE", {}),
    "NUGGET": ("SELLABLE", {}),
    "COIN": ("CURRENCY", {}),
}


def parse_item_constants(file_path: Path) -> dict[str, int]:
    """Parse item constants to get item IDs."""
    item_ids = {}
    content = file_path.read_text()

    # Pattern: const ITEM_NAME ; $XX
    pattern = re.compile(r"const\s+(\w+)\s*;\s*\$([0-9a-fA-F]+)")

    for match in pattern.finditer(content):
        name = match.group(1)
        hex_id = match.group(2)
        if name not in ("NO_ITEM", "const_def"):
            item_ids[name] = int(hex_id, 16)

    return item_ids


def parse_prices(file_path: Path) -> dict[str, int]:
    """Parse item prices."""
    prices = {}
    content = file_path.read_text()

    # Pattern: bcd3 PRICE ; ITEM_NAME
    pattern = re.compile(r"bcd3\s+(\d+)\s*;\s*(\w+)")

    for match in pattern.finditer(content):
        price = int(match.group(1))
        name = match.group(2)
        prices[name] = price

    return prices


def parse_key_items(file_path: Path) -> set[str]:
    """Parse key item flags."""
    key_items = set()
    content = file_path.read_text()

    # Pattern: dbit TRUE ; ITEM_NAME
    pattern = re.compile(r"dbit\s+TRUE\s*;\s*(\w+)")

    for match in pattern.finditer(content):
        name = match.group(1)
        key_items.add(name)

    return key_items


def main():
    """Extract items and save to JSON."""
    print(f"Reading item data from {POKERED_PATH}...")

    # Parse item IDs
    item_ids = parse_item_constants(ITEM_CONSTANTS_FILE)
    print(f"Found {len(item_ids)} item constants")

    # Parse prices
    prices = parse_prices(PRICES_FILE)
    print(f"Found {len(prices)} item prices")

    # Parse key items
    key_items = parse_key_items(KEY_ITEMS_FILE)
    print(f"Found {len(key_items)} key items")

    # Build item data
    items = {}
    for name, item_id in item_ids.items():
        # Skip floors and other non-items
        if name.startswith("FLOOR_") or name.startswith("ITEM_"):
            continue

        buy_price = prices.get(name, 0)
        is_key = name in key_items

        # Get category and effect from our mapping
        category, effect = ITEM_CATEGORIES.get(name, ("MISC", {}))

        item_data = {
            "id": item_id,
            "name": name,
            "category": category,
            "buy_price": buy_price,
            "sell_price": buy_price // 2 if buy_price > 0 else 0,
            "is_key_item": is_key,
        }

        if effect:
            item_data["effect"] = effect

        items[name] = item_data

    print(f"Built {len(items)} items")

    # Save to JSON
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(items, f, indent=2, sort_keys=True)

    print(f"Saved to {OUTPUT_PATH}")

    # Print examples
    print("\nExamples:")
    for name in ["POKE_BALL", "SUPER_POTION", "THUNDER_STONE", "BICYCLE", "MASTER_BALL"]:
        if name in items:
            item = items[name]
            print(f"  {name}: {item['category']} "
                  f"Buy:{item['buy_price']} Key:{item['is_key_item']}")

    return 0


if __name__ == "__main__":
    exit(main())
