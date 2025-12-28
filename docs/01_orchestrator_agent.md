# Orchestrator Agent

## Model Configuration

| Setting | Value |
|---------|-------|
| **Model** | `claude-sonnet-4-5-20250929` |
| **Reasoning** | Moderate complexity strategic decisions |
| **Call Frequency** | ~1,000/hour (after each agent action) |
| **Latency Tolerance** | Medium (not blocking gameplay) |

**Why Sonnet:** The Orchestrator needs reliable strategic reasoning for failure recovery and dynamic sub-objective creation, but is called frequently enough that Opus latency would slow the system. Sonnet provides the right balance.

---

## Overview

The Orchestrator Agent is the central coordinator of the Pokemon Red AI system. It maintains high-level game objectives, detects the current game mode, and routes control to the appropriate specialist agent. Think of it as the "executive function" that decides what to do next at a strategic level.

## Responsibilities

1. **Game Mode Detection** - Continuously monitor and classify the current game state
2. **Objective Management** - Track progress through the game and determine next goals
3. **Agent Routing** - Hand off control to the appropriate specialist agent
4. **Progress Tracking** - Maintain awareness of badges, story flags, and overall progress

---

## Game State Schema

The Orchestrator owns and maintains the shared GameState object that all agents read from:

```python
@dataclass
class GameState:
    # Mode Detection
    current_mode: GameMode  # OVERWORLD | BATTLE | MENU | DIALOGUE
    
    # Location
    current_map: str        # e.g., "Viridian Forest", "Pewter City"
    player_position: tuple  # (x, y) coordinates on current map
    
    # Party State
    party: list[Pokemon]    # Current party (max 6)
    
    # Inventory
    inventory: dict         # {item_name: quantity}
    money: int
    
    # Progress
    badges: list[str]       # ["Boulder", "Cascade", ...]
    story_flags: set[str]   # Completed story events
    hms_obtained: set[str]  # HMs in possession
    hms_usable: set[str]    # HMs that can be used (have badge + taught)
    
    # Current Objective
    current_objective: Objective
    objective_stack: list[Objective]  # Sub-objectives pushed on top
    
    # Battle State (populated when in battle)
    battle_state: Optional[BattleState]


class GameMode(Enum):
    OVERWORLD = "overworld"
    BATTLE = "battle"
    MENU = "menu"
    DIALOGUE = "dialogue"


@dataclass
class Objective:
    type: str           # "navigate", "defeat_gym", "get_item", "catch_pokemon", etc.
    target: str         # Specific target (location, trainer, pokemon, item)
    priority: int       # For ordering when multiple objectives exist
    requirements: list  # Prerequisites (HMs, items, badges needed)
    completed: bool
```

---

## Tools

### 1. `detect_game_mode`

Analyzes the current screen/game state to determine which mode we're in.

**Input:** Current screen state (pixels, memory, or abstracted state)

**Output:**
```python
{
    "mode": "BATTLE",
    "submode": "WILD",  # or "TRAINER", "GYM_LEADER"
    "confidence": 0.98
}
```

**Detection Signals:**
- OVERWORLD: Player sprite visible, can move
- BATTLE: Battle UI visible, HP bars, move menu
- MENU: Start menu or submenu open
- DIALOGUE: Text box on screen, awaiting input

---

### 2. `get_current_objective`

Returns the current high-level objective based on game progress.

**Input:** Current GameState (badges, story_flags, location)

**Output:**
```python
{
    "objective": "defeat_gym",
    "target": "Brock",
    "location": "Pewter City Gym",
    "prerequisites": [],
    "recommended_level": 12,
    "type_advantage": ["Water", "Grass", "Fighting"]
}
```

---

### 3. `get_next_milestone`

Determines what the next major story milestone is.

**Input:** Current progress (badges, story_flags)

**Output:**
```python
{
    "milestone": "Defeat Misty",
    "steps": [
        {"type": "navigate", "target": "Cerulean City"},
        {"type": "optional", "target": "Catch Water/Grass type"},
        {"type": "navigate", "target": "Cerulean Gym"},
        {"type": "defeat_trainer", "target": "Misty"}
    ]
}
```

---

### 4. `check_requirements`

Checks if prerequisites are met for a given objective.

**Input:** Objective, current GameState

**Output:**
```python
{
    "can_proceed": False,
    "missing": [
        {"type": "hm", "name": "CUT", "status": "have_item_not_taught"},
        {"type": "pokemon", "name": "Grass-type", "status": "missing"}
    ],
    "sub_objectives": [
        {"type": "teach_hm", "move": "CUT", "priority": 1},
        {"type": "catch_pokemon", "filter": "type:Grass", "priority": 2}
    ]
}
```

---

### 5. `route_to_agent`

Determines which specialist agent should take control.

**Input:** GameMode, current objective, GameState

**Output:**
```python
{
    "agent": "BATTLE",
    "context": {
        "battle_type": "TRAINER",
        "can_flee": False,
        "objective": "win"
    }
}
```

---

## Game Progression Knowledge Base

The Orchestrator needs a static knowledge base of game progression:

```python
GAME_PROGRESSION = [
    {
        "milestone": "Defeat Brock",
        "location": "Pewter City Gym",
        "badge": "Boulder",
        "unlocks": ["HM_FLASH_USABLE"],
        "requirements": []
    },
    {
        "milestone": "Get HM01 Cut",
        "location": "SS Anne",
        "requirements": ["SS_TICKET"]
    },
    {
        "milestone": "Defeat Misty",
        "location": "Cerulean City Gym", 
        "badge": "Cascade",
        "unlocks": ["HM_CUT_USABLE"],
        "requirements": []
    },
    # ... etc for all 8 gyms + Elite Four
]

HM_REQUIREMENTS = {
    "CUT": {"badge": "Cascade", "location": "SS Anne Captain"},
    "FLY": {"badge": "Thunder", "location": "Route 16"},
    "SURF": {"badge": "Soul", "location": "Safari Zone"},
    "STRENGTH": {"badge": "Rainbow", "location": "Fuchsia Warden"},
    "FLASH": {"badge": "Boulder", "location": "Route 2 Gate"}
}

ROUTE_REQUIREMENTS = {
    ("Cerulean City", "Route 9"): ["CUT"],
    ("Lavender Town", "Fuchsia City"): ["SURF"],  # via water route
    ("Victory Road", "Indigo Plateau"): ["SURF", "STRENGTH"]
}
```

---

## Control Flow Logic

```python
def orchestrator_loop():
    while not game_complete():
        # 1. Detect current mode
        mode = detect_game_mode()
        update_game_state(mode=mode)
        
        # 2. Route to appropriate agent
        if mode == GameMode.BATTLE:
            battle_agent.take_control(game_state)
        
        elif mode == GameMode.MENU:
            menu_agent.take_control(game_state)
        
        elif mode == GameMode.DIALOGUE:
            menu_agent.handle_dialogue(game_state)
        
        elif mode == GameMode.OVERWORLD:
            # Check if we need to update objectives
            if objective_complete(game_state.current_objective):
                new_objective = get_next_milestone()
                push_objective(new_objective)
            
            # Check prerequisites
            reqs = check_requirements(game_state.current_objective)
            if not reqs["can_proceed"]:
                for sub_obj in reqs["sub_objectives"]:
                    push_objective(sub_obj)
            
            # Let navigation agent handle movement
            navigation_agent.take_control(game_state)
        
        # 3. Update shared state
        sync_game_state()
```

---

## Objective Stack Example

The Orchestrator uses a stack to handle sub-objectives:

```
Initial State:
  Stack: [Defeat Elite Four]

After planning:
  Stack: [Defeat Elite Four, Defeat Giovanni, Get 8 Badges, Defeat Brock]

After detecting we need a Grass type for Brock:
  Stack: [Defeat Elite Four, ..., Defeat Brock, Catch Bulbasaur/Oddish]

After catching:
  Stack: [Defeat Elite Four, ..., Defeat Brock]  # Catch objective popped
```

---

## Failure Handling

When a specialist agent fails (e.g., loses a battle):

```python
def handle_agent_failure(agent: str, failure_type: str, context: dict):
    if failure_type == "BATTLE_LOST":
        # We respawn at last Pokemon Center
        # Update location, restore party HP (game does this)
        game_state.location = game_state.last_pokemon_center
        
        # Analyze why we lost
        if context["cause"] == "UNDERLEVELED":
            push_objective(Objective("grind", target_level=context["recommended"]))
        elif context["cause"] == "BAD_MATCHUP":
            push_objective(Objective("catch_pokemon", type=context["needed_type"]))
    
    elif failure_type == "STUCK":
        # Navigation agent can't find path
        # Check if we're missing an HM
        missing_hm = check_route_requirements(game_state.location, game_state.target)
        if missing_hm:
            push_objective(Objective("get_hm", hm=missing_hm))
```

---

## Integration Points

| Agent | Orchestrator Provides | Agent Returns |
|-------|----------------------|---------------|
| Navigation | Target location, allowed actions | Movement complete, encountered trainer/pokemon |
| Battle | Battle context, strategic priority | Win/loss, resources used, pokemon caught |
| Menu | Action to perform (heal, buy, teach) | Action complete, state changes |

---

## Success Criteria

The Orchestrator considers the game complete when:

```python
def game_complete():
    return "CHAMPION" in game_state.story_flags
```

Intermediate success milestones:
- Each badge obtained
- Each HM obtained and usable
- Key items obtained (Silph Scope, Poke Flute, etc.)
- Elite Four members defeated
