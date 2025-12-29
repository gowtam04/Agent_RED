#!/usr/bin/env python3
"""Extract shop inventory data from pokered ASM files."""

import json
import re
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
POKERED_PATH = PROJECT_ROOT / "external" / "pokered"
OUTPUT_PATH = PROJECT_ROOT / "data" / "shops.json"

# Source file
MARTS_FILE = POKERED_PATH / "data" / "items" / "marts.asm"


def parse_marts(file_path: Path) -> dict:
    """Parse mart inventories from marts.asm."""
    shops = {}
    content = file_path.read_text()

    # Pattern: LabelText:: script_mart ITEM1, ITEM2, ...
    # Match any label ending in ClerkText or Clerk1Text/Clerk2Text with script_mart
    pattern = re.compile(
        r"(\w+)(?:Clerk\d*)?Text::\s*\n\s*script_mart\s+(.+?)(?=\n\n|\n\w|\Z)",
        re.DOTALL
    )

    for match in pattern.finditer(content):
        location = match.group(1)
        items_str = match.group(2)

        # Parse items (comma-separated)
        items = []
        for item in re.findall(r"\b([A-Z][A-Z0-9_]+)\b", items_str):
            if item != "script_mart":
                items.append(item)

        if items:
            shops[location] = {
                "location": location,
                "inventory": items,
            }

    return shops


def load_item_prices() -> dict[str, int]:
    """Load item prices from items.json if it exists."""
    items_path = PROJECT_ROOT / "data" / "items.json"
    if not items_path.exists():
        return {}

    with open(items_path) as f:
        data = json.load(f)

    return {name: item.get("buy_price", 0) for name, item in data.items()}


def main():
    """Extract shop inventories and save to JSON."""
    print(f"Reading shop data from {MARTS_FILE}...")

    # Parse marts
    shops = parse_marts(MARTS_FILE)
    print(f"Found {len(shops)} shops")

    # Load item prices
    prices = load_item_prices()

    # Add prices to inventory
    for shop_name, shop in shops.items():
        shop["inventory_with_prices"] = []
        for item in shop["inventory"]:
            price = prices.get(item, 0)
            shop["inventory_with_prices"].append({
                "item": item,
                "price": price,
            })

    # Save to JSON
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(shops, f, indent=2, sort_keys=True)

    print(f"Saved to {OUTPUT_PATH}")

    # Print examples
    print("\nExamples:")
    for shop_name in ["Viridian", "Pewter", "CeladonMart2FClerk1"]:
        if shop_name in shops:
            shop = shops[shop_name]
            print(f"  {shop_name}: {shop['inventory'][:5]}")

    return 0


if __name__ == "__main__":
    exit(main())
