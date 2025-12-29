"""Base class for knowledge base accessors."""

from abc import ABC, abstractmethod
from pathlib import Path
import json


class KnowledgeBase(ABC):
    """Abstract base class for loading and querying JSON game data."""

    def __init__(self, data_path: Path):
        """Initialize with path to JSON data file.

        Args:
            data_path: Path to the JSON file containing the data.
        """
        self.data_path = data_path
        self._data: dict | None = None

    def load(self) -> None:
        """Load data from JSON file."""
        with open(self.data_path) as f:
            self._data = json.load(f)

    @property
    def data(self) -> dict:
        """Get the loaded data, loading if necessary."""
        if self._data is None:
            self.load()
        return self._data  # type: ignore

    @abstractmethod
    def get(self, key: str) -> dict | None:
        """Get an item by key.

        Args:
            key: The key to look up.

        Returns:
            The item data or None if not found.
        """
        pass

    def __contains__(self, key: str) -> bool:
        """Check if a key exists in the data."""
        return key in self.data

    def __len__(self) -> int:
        """Return the number of items in the data."""
        return len(self.data)

    def keys(self) -> list[str]:
        """Return all keys in the data."""
        return list(self.data.keys())
