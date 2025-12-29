"""Enhanced game state with objective management."""

from dataclasses import dataclass, field

from .types import BattleState, GameMode, Objective, Pokemon, Position


@dataclass
class GameState:
    """Complete game state shared across all agents."""

    # Current mode
    mode: GameMode = "OVERWORLD"

    # Player position
    position: Position = field(default_factory=lambda: Position("PALLET_TOWN", 0, 0))

    # Party Pokemon (up to 6)
    party: list[Pokemon] = field(default_factory=list)

    # Battle state (None if not in battle)
    battle: BattleState | None = None

    # Progression
    badges: list[str] = field(default_factory=list)
    story_flags: list[str] = field(default_factory=list)
    hms_obtained: list[str] = field(default_factory=list)
    hms_usable: list[str] = field(default_factory=list)  # Have badge + taught

    # Inventory
    money: int = 0
    items: dict[str, int] = field(default_factory=dict)
    key_items: list[str] = field(default_factory=list)

    # Objective stack
    objective_stack: list[Objective] = field(default_factory=list)

    # Session tracking
    last_pokemon_center: str | None = None
    defeated_trainers: set[str] = field(default_factory=set)

    @property
    def current_objective(self) -> Objective | None:
        """Return the top objective on the stack."""
        return self.objective_stack[-1] if self.objective_stack else None

    @property
    def party_hp_percent(self) -> float:
        """Average HP percentage of party."""
        if not self.party:
            return 0.0
        return sum(p.current_hp / p.max_hp for p in self.party) / len(self.party) * 100

    @property
    def fainted_count(self) -> int:
        """Number of fainted Pokemon."""
        return sum(1 for p in self.party if p.current_hp == 0)

    @property
    def needs_healing(self) -> bool:
        """Check if party needs healing."""
        return self.party_hp_percent < 50 or self.fainted_count > 0

    def push_objective(self, objective: Objective) -> None:
        """Push a new objective onto the stack."""
        self.objective_stack.append(objective)

    def pop_objective(self) -> Objective | None:
        """Pop and return the top objective."""
        return self.objective_stack.pop() if self.objective_stack else None

    def has_badge(self, badge: str) -> bool:
        """Check if player has a specific badge."""
        return badge in self.badges

    def can_use_hm(self, hm: str) -> bool:
        """Check if player can use a specific HM in the field."""
        return hm in self.hms_usable
