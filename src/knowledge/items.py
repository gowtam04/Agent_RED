"""Item data accessor."""

from pathlib import Path

from .base import KnowledgeBase


# Default path to items data
DEFAULT_ITEMS_PATH = Path(__file__).parent.parent.parent / "data" / "items.json"


class ItemData(KnowledgeBase):
    """Accessor for Pokemon item data.

    Provides access to all Gen 1 items including:
    - Poke Balls
    - Healing items
    - Evolution stones
    - Key items
    - Battle items
    """

    def __init__(self, data_path: Path = DEFAULT_ITEMS_PATH):
        """Initialize the items accessor.

        Args:
            data_path: Path to items.json file.
        """
        super().__init__(data_path)

    def get(self, item_name: str) -> dict | None:
        """Get item data by name.

        Args:
            item_name: The item name (e.g., "POKE_BALL").

        Returns:
            Item data dictionary or None if not found.
        """
        return self.data.get(item_name.upper())

    def get_by_id(self, item_id: int) -> dict | None:
        """Get item data by ID.

        Args:
            item_id: The item ID.

        Returns:
            Item data dictionary or None if not found.
        """
        for item in self.data.values():
            if item.get("id") == item_id:
                return item
        return None

    def get_items_by_category(self, category: str) -> list[dict]:
        """Get all items of a specific category.

        Args:
            category: The category (e.g., "BALL", "HEALING", "KEY").

        Returns:
            List of item data dictionaries.
        """
        cat_upper = category.upper()
        return [i for i in self.data.values() if i.get("category") == cat_upper]

    def get_poke_balls(self) -> list[dict]:
        """Get all Poke Ball items.

        Returns:
            List of Poke Ball item dictionaries.
        """
        return self.get_items_by_category("BALL")

    def get_healing_items(self) -> list[dict]:
        """Get all healing items.

        Returns:
            List of healing item dictionaries.
        """
        return self.get_items_by_category("HEALING")

    def get_key_items(self) -> list[dict]:
        """Get all key items.

        Returns:
            List of key item dictionaries.
        """
        return [i for i in self.data.values() if i.get("is_key_item")]

    def get_buyable_items(self) -> list[dict]:
        """Get all items that can be bought.

        Returns:
            List of items with buy_price > 0.
        """
        return [i for i in self.data.values() if i.get("buy_price", 0) > 0]

    def get_evolution_stones(self) -> list[dict]:
        """Get all evolution stone items.

        Returns:
            List of evolution stone dictionaries.
        """
        return self.get_items_by_category("EVOLUTION")

    def is_key_item(self, item_name: str) -> bool:
        """Check if an item is a key item.

        Args:
            item_name: The item name.

        Returns:
            True if the item is a key item.
        """
        item = self.get(item_name)
        return item.get("is_key_item", False) if item else False

    def get_buy_price(self, item_name: str) -> int:
        """Get the buy price for an item.

        Args:
            item_name: The item name.

        Returns:
            Buy price or 0 if not buyable.
        """
        item = self.get(item_name)
        return item.get("buy_price", 0) if item else 0

    def get_sell_price(self, item_name: str) -> int:
        """Get the sell price for an item.

        Args:
            item_name: The item name.

        Returns:
            Sell price (half of buy price, or 0).
        """
        item = self.get(item_name)
        return item.get("sell_price", 0) if item else 0
