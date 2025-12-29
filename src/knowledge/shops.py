"""Shop inventory data accessor."""

from pathlib import Path

from .base import KnowledgeBase


# Default path to shops data
DEFAULT_SHOPS_PATH = Path(__file__).parent.parent.parent / "data" / "shops.json"


class ShopData(KnowledgeBase):
    """Accessor for Pokemon mart inventory data."""

    def __init__(self, data_path: Path = DEFAULT_SHOPS_PATH):
        """Initialize the shops accessor.

        Args:
            data_path: Path to shops.json file.
        """
        super().__init__(data_path)

    def get(self, shop_id: str) -> dict | None:
        """Get shop data by ID.

        Args:
            shop_id: The shop ID (e.g., "ViridianMart").

        Returns:
            Shop data dictionary or None if not found.
        """
        return self.data.get(shop_id)

    def get_inventory(self, shop_id: str) -> list[str]:
        """Get the inventory for a shop.

        Args:
            shop_id: The shop ID.

        Returns:
            List of item names available at the shop.
        """
        shop = self.get(shop_id)
        return shop.get("inventory", []) if shop else []

    def get_inventory_with_prices(self, shop_id: str) -> list[dict]:
        """Get inventory with prices for a shop.

        Args:
            shop_id: The shop ID.

        Returns:
            List of dicts with 'item' and 'price' keys.
        """
        shop = self.get(shop_id)
        return shop.get("inventory_with_prices", []) if shop else []

    def find_shops_selling(self, item_name: str) -> list[str]:
        """Find all shops that sell a specific item.

        Args:
            item_name: The item name to search for.

        Returns:
            List of shop IDs that sell the item.
        """
        item_upper = item_name.upper()
        return [
            shop_id for shop_id, shop in self.data.items()
            if item_upper in shop.get("inventory", [])
        ]

    def get_all_shops(self) -> list[str]:
        """Get all shop IDs.

        Returns:
            List of shop IDs.
        """
        return list(self.data.keys())
