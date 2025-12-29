"""Knowledge base accessors for Pokemon Red game data."""

from .base import KnowledgeBase
from .type_chart import TypeChart
from .moves import MoveData
from .pokemon import PokemonData
from .items import ItemData
from .wild_encounters import WildEncounters
from .shops import ShopData
from .trainers import TrainerData
from .maps import MapData
from .hm_requirements import HMRequirements
from .story_progression import StoryProgression

__all__ = [
    "KnowledgeBase",
    "TypeChart",
    "MoveData",
    "PokemonData",
    "ItemData",
    "WildEncounters",
    "ShopData",
    "TrainerData",
    "MapData",
    "HMRequirements",
    "StoryProgression",
]
