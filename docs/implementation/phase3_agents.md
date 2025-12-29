# Phase 3: Agent Implementation

## Objective
Implement the four specialized agents: Orchestrator, Navigation, Battle, and Menu.

## Prerequisites
- Phase 1 complete (knowledge bases in `data/`)
- Phase 2 complete (agent framework in `src/agent/`)

---

## Overview

| Agent | Model | Tools | Primary Role |
|-------|-------|-------|--------------|
| Orchestrator | Sonnet | 7 | Coordination, routing, objective management |
| Navigation | Haiku | 8 | Overworld movement, pathfinding |
| Battle | Sonnet/Opus | 9 | Combat decisions, catching |
| Menu | Haiku | 14 | UI interactions, healing, shopping |

---

## 1. Orchestrator Agent (`src/agent/orchestrator.py`)

### Model: Sonnet
### Role: Central coordinator

The Orchestrator is the entry point for each game loop iteration. It detects the current game mode, manages objectives, and routes to specialist agents.

### System Prompt

```python
ORCHESTRATOR_SYSTEM_PROMPT = """You are the Orchestrator agent for a Pokemon Red AI system.

Your responsibilities:
1. Detect the current game mode (OVERWORLD, BATTLE, MENU, DIALOGUE)
2. Manage the objective stack (current goal, sub-goals, prerequisites)
3. Route to the appropriate specialist agent
4. Monitor party health and trigger healing when needed
5. Handle failure recovery

You have access to the following tools:
- detect_game_mode: Identify current game state
- get_current_objective: Get the top objective
- get_next_milestone: Determine next story milestone
- check_requirements: Verify prerequisites are met
- route_to_agent: Select specialist agent
- update_game_state: Sync shared state
- manage_objective_stack: Push/pop objectives

Decision flow:
1. First, detect the game mode
2. Check if party needs healing (HP < 50% or fainted Pokemon)
3. If healing needed, push heal objective and route to appropriate agent
4. Otherwise, get current objective and route based on mode

Always think step by step about what the player should do next to progress.
"""
```

### Tools to Implement

```python
class OrchestratorAgent(BaseAgent):
    AGENT_TYPE = "ORCHESTRATOR"
    DEFAULT_MODEL = "sonnet"
    SYSTEM_PROMPT = ORCHESTRATOR_SYSTEM_PROMPT

    def _register_tools(self) -> list[dict]:
        from src.tools import ORCHESTRATOR_TOOLS
        return ORCHESTRATOR_TOOLS

    def _execute_tool(self, tool_name: str, tool_input: dict, state: GameState) -> AgentResult:
        tool_handlers = {
            "detect_game_mode": self._detect_game_mode,
            "get_current_objective": self._get_current_objective,
            "get_next_milestone": self._get_next_milestone,
            "check_requirements": self._check_requirements,
            "route_to_agent": self._route_to_agent,
            "update_game_state": self._update_game_state,
            "manage_objective_stack": self._manage_objective_stack,
        }
        handler = tool_handlers.get(tool_name)
        if handler:
            return handler(tool_input, state)
        return AgentResult(success=False, action_taken=tool_name, error=f"Unknown tool: {tool_name}")
```

### Tool Implementations

#### detect_game_mode
```python
def _detect_game_mode(self, input: dict, state: GameState) -> AgentResult:
    """Detect current game mode from memory."""
    from src.emulator.state_reader import StateReader

    # Read memory to determine mode
    # Battle type address: 0xD057 (0=none, 1=wild, 2=trainer)
    # Menu detection via screen state

    mode = "OVERWORLD"  # Default

    # Check battle
    battle_type = self._read_memory(0xD057)
    if battle_type > 0:
        mode = "BATTLE"
        submode = "WILD" if battle_type == 1 else "TRAINER"
    # Check menu (screen-based detection)
    elif self._is_menu_open():
        mode = "MENU"
    elif self._is_dialogue_active():
        mode = "DIALOGUE"

    return AgentResult(
        success=True,
        action_taken="detect_game_mode",
        result_data={
            "mode": mode,
            "submode": submode if mode == "BATTLE" else None,
        }
    )
```

#### route_to_agent
```python
def _route_to_agent(self, input: dict, state: GameState) -> AgentResult:
    """Route to appropriate specialist agent."""
    mode = input.get("game_mode", state.mode)

    # Check for healing priority
    if state.needs_healing and mode != "BATTLE":
        return AgentResult(
            success=True,
            action_taken="route_to_agent",
            result_data={"agent": "MENU", "reason": "party_needs_healing"},
            new_objectives=[create_heal_objective()],
        )

    # Standard routing
    routing = {
        "OVERWORLD": "NAVIGATION",
        "BATTLE": "BATTLE",
        "MENU": "MENU",
        "DIALOGUE": "MENU",
    }

    agent = routing.get(mode, "NAVIGATION")

    # Check for boss battle escalation
    if mode == "BATTLE" and state.battle:
        if state.battle.battle_type in {"GYM_LEADER", "ELITE_FOUR", "CHAMPION"}:
            return AgentResult(
                success=True,
                action_taken="route_to_agent",
                result_data={
                    "agent": "BATTLE",
                    "escalate_to_opus": True,
                    "reason": "boss_battle",
                }
            )

    return AgentResult(
        success=True,
        action_taken="route_to_agent",
        result_data={"agent": agent}
    )
```

---

## 2. Navigation Agent (`src/agent/navigation.py`)

### Model: Haiku
### Role: Overworld movement and pathfinding

### System Prompt

```python
NAVIGATION_SYSTEM_PROMPT = """You are the Navigation agent for a Pokemon Red AI system.

Your responsibilities:
1. Move the player through the overworld
2. Find optimal paths using A* pathfinding
3. Avoid unwanted trainer battles when possible
4. Use HM moves to clear obstacles (Cut, Surf, Strength)
5. Handle wild encounters (flee or fight based on objective)

You have access to these tools:
- get_current_position: Get player location
- get_map_data: Get map layout and objects
- find_path: Calculate path to destination
- get_interactables: Find nearby objects/NPCs
- execute_movement: Send movement inputs
- check_route_accessibility: Check HM requirements
- get_hidden_items: Find hidden items on map
- use_hm_in_field: Use Cut/Surf/Strength/Flash

Movement principles:
1. Minimize grass tiles to reduce encounters
2. Avoid trainer line-of-sight when not grinding
3. Pick up visible items when convenient
4. Use warps and connections efficiently

If movement is interrupted by a wild encounter, report back and let Battle agent handle it.
"""
```

### Tool Implementations

#### find_path
```python
def _find_path(self, input: dict, state: GameState) -> AgentResult:
    """Calculate path using A* algorithm."""
    from src.pathfinding import find_path
    from src.knowledge import Maps

    destination = input["destination"]
    from_pos = input.get("from") or {
        "map": state.position.map_id,
        "x": state.position.x,
        "y": state.position.y,
    }
    preferences = input.get("preferences", {
        "avoid_grass": True,
        "avoid_trainers": True,
        "allowed_hms": state.hms_usable,
    })

    # Get map data
    maps = Maps()

    # Run pathfinding
    path = find_path(
        from_map=from_pos["map"],
        from_x=from_pos["x"],
        from_y=from_pos["y"],
        to_map=destination["map"],
        to_x=destination.get("x"),
        to_y=destination.get("y"),
        preferences=preferences,
        maps=maps,
    )

    if path is None:
        return AgentResult(
            success=False,
            action_taken="find_path",
            error="No path found",
            result_data={"blocked_by": "unknown"}
        )

    return AgentResult(
        success=True,
        action_taken="find_path",
        result_data={
            "path_found": True,
            "total_steps": len(path.moves),
            "segments": path.segments,
            "trainers_in_path": path.trainers,
            "estimated_encounters": path.encounter_estimate,
        }
    )
```

#### execute_movement
```python
def _execute_movement(self, input: dict, state: GameState) -> AgentResult:
    """Execute movement sequence."""
    from src.emulator import EmulatorInterface

    moves = input["moves"]
    stop_conditions = input.get("stop_conditions", ["BATTLE_START", "DIALOGUE_START", "WARP"])
    frame_delay = input.get("frame_delay", 4)

    emulator = EmulatorInterface.get_instance()

    moves_completed = 0
    stopped_reason = None

    for move in moves:
        # Execute the move
        if move in ["UP", "DOWN", "LEFT", "RIGHT"]:
            emulator.move(move.lower(), 1)
        else:
            emulator.press_button(move.lower())

        # Wait frames
        emulator.tick(frame_delay)

        # Check stop conditions
        if "BATTLE_START" in stop_conditions and self._check_battle_started():
            stopped_reason = "BATTLE_START"
            break
        if "DIALOGUE_START" in stop_conditions and self._check_dialogue_active():
            stopped_reason = "DIALOGUE_START"
            break
        if "WARP" in stop_conditions and self._check_map_changed(state):
            stopped_reason = "WARP"
            break

        moves_completed += 1

    # Get new position
    new_position = self._read_position()

    return AgentResult(
        success=True,
        action_taken="execute_movement",
        result_data={
            "moves_completed": moves_completed,
            "moves_total": len(moves),
            "stopped_reason": stopped_reason,
            "new_position": new_position,
        },
        handoff_to="BATTLE" if stopped_reason == "BATTLE_START" else None,
    )
```

---

## 3. Battle Agent (`src/agent/battle.py`)

### Model: Sonnet (Opus for bosses)
### Role: Combat decision-making

### System Prompt

```python
BATTLE_SYSTEM_PROMPT = """You are the Battle agent for a Pokemon Red AI system.

Your responsibilities:
1. Select optimal moves based on type effectiveness
2. Decide when to switch Pokemon
3. Determine whether to catch wild Pokemon
4. Manage items in battle
5. Know when to flee from wild battles

You have access to these tools:
- get_pokemon_data: Look up species data
- calculate_type_effectiveness: Check type matchups
- estimate_damage: Calculate expected damage
- calculate_catch_rate: Estimate catch probability
- evaluate_switch_options: Score party matchups
- get_best_move: Rank available moves
- should_catch_pokemon: Evaluate catch priority
- battle_execute_action: Execute move/switch/item/catch/run
- get_battle_state: Read current battle state

Battle strategy:
1. Always consider type effectiveness first
2. Use STAB (Same Type Attack Bonus) moves when effective
3. Switch if current Pokemon has bad matchup AND healthy alternative exists
4. In trainer battles, preserve team for upcoming fights
5. Catch Pokemon that fill team gaps or counter upcoming gyms

Gen 1 quirks to remember:
- Ghost is bugged: does 0x damage to Psychic (not super effective!)
- Special stat is both Special Attack and Special Defense
- High crit moves (Slash, Razor Leaf) have ~25% crit rate
- Focus Energy is bugged and REDUCES crit rate
"""
```

### Boss Battle Prompt (Opus)

```python
BOSS_BATTLE_SYSTEM_PROMPT = """You are the Battle agent in a BOSS BATTLE against a Gym Leader, Elite Four, or Champion.

This is a critical battle. Think carefully and strategically.

{base_prompt}

Additional boss battle considerations:
1. This trainer has high-level Pokemon with good movesets
2. They may switch tactically - anticipate this
3. Preserve healthy Pokemon for later in the battle
4. Use items strategically (Full Restore before key Pokemon)
5. Consider stat-boosting moves if you have type advantage
6. The trainer cannot be fled from

Think through each decision carefully. What are the opponent's likely moves?
What's the safest path to victory?
"""
```

### Tool Implementations

#### calculate_type_effectiveness
```python
def _calculate_type_effectiveness(self, input: dict, state: GameState) -> AgentResult:
    """Calculate type matchup multiplier."""
    from src.knowledge import TypeChart

    attack_type = input["attack_type"]
    defender_types = input["defender_types"]

    chart = TypeChart()
    multiplier = chart.get_effectiveness(attack_type, defender_types)

    # Describe effectiveness
    if multiplier == 0:
        effectiveness = "immune"
    elif multiplier < 1:
        effectiveness = "not_very_effective"
    elif multiplier > 1:
        effectiveness = "super_effective"
    else:
        effectiveness = "normal"

    return AgentResult(
        success=True,
        action_taken="calculate_type_effectiveness",
        result_data={
            "attack_type": attack_type,
            "defender_types": defender_types,
            "multiplier": multiplier,
            "effectiveness": effectiveness,
        }
    )
```

#### estimate_damage
```python
def _estimate_damage(self, input: dict, state: GameState) -> AgentResult:
    """Estimate damage using Gen 1 formula."""
    attacker = input["attacker"]
    defender = input["defender"]
    move = input["move"]

    # Gen 1 damage formula
    # Damage = ((2 * Level / 5 + 2) * Power * A/D) / 50 + 2) * Modifiers

    level = attacker["level"]
    power = move["power"]

    # Determine stat to use (Physical vs Special)
    if move["category"] == "PHYSICAL":
        atk = attacker["attack"]
        dfn = defender["defense"]
    else:
        atk = attacker["special"]
        dfn = defender["special"]

    # Base damage
    base = ((2 * level / 5 + 2) * power * atk / dfn) / 50 + 2

    # Type effectiveness
    from src.knowledge import TypeChart
    chart = TypeChart()
    type_mult = chart.get_effectiveness(move["type"], defender["types"])

    # STAB
    stab = 1.5 if move["type"] in attacker["types"] else 1.0

    # Random modifier (0.85 to 1.0)
    min_damage = int(base * type_mult * stab * 0.85)
    max_damage = int(base * type_mult * stab * 1.0)

    # Critical hit damage (2x in Gen 1)
    crit_min = min_damage * 2
    crit_max = max_damage * 2

    defender_hp = defender["current_hp"]
    can_ko = max_damage >= defender_hp
    guaranteed_ko = min_damage >= defender_hp

    return AgentResult(
        success=True,
        action_taken="estimate_damage",
        result_data={
            "min_damage": min_damage,
            "max_damage": max_damage,
            "average_damage": (min_damage + max_damage) // 2,
            "can_ko": can_ko,
            "guaranteed_ko": guaranteed_ko,
            "crit_damage": {"min": crit_min, "max": crit_max},
            "modifiers_applied": {
                "type_effectiveness": type_mult,
                "stab": stab,
            }
        }
    )
```

#### get_best_move
```python
def _get_best_move(self, input: dict, state: GameState) -> AgentResult:
    """Score and rank available moves."""
    active = input["active_pokemon"]
    enemy = input["enemy_pokemon"]

    move_scores = []

    for i, move in enumerate(active["moves"]):
        if move["pp_current"] == 0:
            move_scores.append({"index": i, "name": move["name"], "score": -1, "reason": "no_pp"})
            continue

        if move["power"] == 0:
            # Status move - lower priority
            score = 20
            move_scores.append({"index": i, "name": move["name"], "score": score, "reason": "status_move"})
            continue

        # Calculate expected damage
        damage_result = self._estimate_damage({
            "attacker": active,
            "defender": enemy,
            "move": move,
        }, state)

        avg_damage = damage_result.result_data["average_damage"]
        type_mult = damage_result.result_data["modifiers_applied"]["type_effectiveness"]

        # Score based on damage and accuracy
        accuracy = move.get("accuracy", 100) / 100
        score = avg_damage * accuracy

        # Bonus for super effective
        if type_mult > 1:
            score *= 1.2

        # Penalty for low accuracy
        if accuracy < 0.8:
            score *= 0.8

        move_scores.append({
            "index": i,
            "name": move["name"],
            "score": int(score),
            "avg_damage": avg_damage,
            "type_mult": type_mult,
            "accuracy": move.get("accuracy", 100),
        })

    # Sort by score
    move_scores.sort(key=lambda x: x["score"], reverse=True)

    return AgentResult(
        success=True,
        action_taken="get_best_move",
        result_data={
            "recommended_move": move_scores[0] if move_scores else None,
            "all_moves": move_scores,
            "ko_analysis": {
                "can_ko_this_turn": damage_result.result_data.get("can_ko", False),
            }
        }
    )
```

---

## 4. Menu Agent (`src/agent/menu.py`)

### Model: Haiku
### Role: UI navigation and interactions

### System Prompt

```python
MENU_SYSTEM_PROMPT = """You are the Menu agent for a Pokemon Red AI system.

Your responsibilities:
1. Navigate menus efficiently
2. Heal at Pokemon Centers
3. Buy/sell at Poke Marts
4. Use items on Pokemon
5. Teach TMs and HMs
6. Manage party order
7. Handle dialogue choices

You have access to these tools:
- navigate_menu: Move cursor, select, cancel
- open_start_menu: Open the pause menu
- get_inventory: Check bag contents
- use_item: Use an item
- heal_at_pokemon_center: Full healing sequence
- shop_buy / shop_sell: Purchase/sell items
- get_shop_inventory: Check shop stock
- manage_party: View/swap party
- teach_move: Teach TM/HM
- pc_deposit_pokemon / pc_withdraw_pokemon: PC operations
- handle_dialogue: Advance/choose in dialogues
- get_party_status: Check party HP/status

Menu navigation tips:
- A button selects, B button cancels/backs out
- D-pad moves cursor
- Start opens main menu from overworld
- Menus have different cursor positions to track
"""
```

### Tool Implementations

#### heal_at_pokemon_center
```python
def _heal_at_pokemon_center(self, input: dict, state: GameState) -> AgentResult:
    """Execute full Pokemon Center healing sequence."""
    from src.emulator import EmulatorInterface

    emulator = EmulatorInterface.get_instance()

    # Walk to nurse (assuming we're in PC)
    # Nurse is typically at top center of Pokemon Centers

    # Face nurse and talk
    emulator.press_button("up")
    emulator.tick(10)
    emulator.press_button("a")
    emulator.tick(30)

    # Dialogue: "Welcome to our Pokemon Center..."
    emulator.press_button("a")
    emulator.tick(20)

    # Dialogue: "Shall we heal your Pokemon?"
    emulator.press_button("a")  # Select YES
    emulator.tick(10)

    # Wait for healing jingle (~3 seconds)
    emulator.tick(180)

    # Dialogue: "Your Pokemon are fighting fit!"
    emulator.press_button("a")
    emulator.tick(20)

    # Dialogue: "We hope to see you again!"
    emulator.press_button("a")
    emulator.tick(20)

    # Update state
    healed_pokemon = []
    for pokemon in state.party:
        healed_pokemon.append({
            "species": pokemon.species,
            "hp_before": pokemon.current_hp,
            "hp_after": pokemon.max_hp,
        })
        pokemon.current_hp = pokemon.max_hp
        pokemon.status = None
        for move in pokemon.moves:
            move.pp_current = move.pp_max

    return AgentResult(
        success=True,
        action_taken="heal_at_pokemon_center",
        result_data={
            "party_healed": True,
            "pokemon_restored": healed_pokemon,
            "pp_fully_restored": True,
        }
    )
```

#### shop_buy
```python
def _shop_buy(self, input: dict, state: GameState) -> AgentResult:
    """Purchase items from Poke Mart."""
    from src.emulator import EmulatorInterface

    items_to_buy = input["items"]
    emulator = EmulatorInterface.get_instance()

    total_spent = 0
    items_bought = []

    for purchase in items_to_buy:
        item_name = purchase["item"]
        quantity = purchase["quantity"]

        # Get item price
        from src.knowledge import Items
        items_kb = Items()
        item_data = items_kb.get(item_name)

        if not item_data:
            continue

        price = item_data["buy_price"]
        total_cost = price * quantity

        if total_cost > state.money:
            # Can't afford, skip
            continue

        # Navigate to item in shop menu
        # (simplified - would need actual menu navigation)

        # Select item
        emulator.press_button("a")
        emulator.tick(10)

        # Set quantity
        for _ in range(quantity - 1):
            emulator.press_button("up")
            emulator.tick(5)

        # Confirm
        emulator.press_button("a")
        emulator.tick(10)

        # Yes to purchase
        emulator.press_button("a")
        emulator.tick(20)

        state.money -= total_cost
        state.items[item_name] = state.items.get(item_name, 0) + quantity

        items_bought.append({
            "item": item_name,
            "quantity": quantity,
            "unit_price": price,
            "total_cost": total_cost,
        })
        total_spent += total_cost

    return AgentResult(
        success=True,
        action_taken="shop_buy",
        result_data={
            "items_bought": items_bought,
            "total_spent": total_spent,
            "money_after": state.money,
        }
    )
```

---

## Model Selection Logic

Implement dynamic model selection in the Battle agent:

```python
class BattleAgent(BaseAgent):
    AGENT_TYPE = "BATTLE"
    DEFAULT_MODEL = "sonnet"

    def act(self, state: GameState) -> AgentResult:
        # Check if we should escalate to Opus
        if state.battle and state.battle.battle_type in {"GYM_LEADER", "ELITE_FOUR", "CHAMPION"}:
            self.model = "opus"
            self.SYSTEM_PROMPT = BOSS_BATTLE_SYSTEM_PROMPT.format(base_prompt=BATTLE_SYSTEM_PROMPT)
        else:
            self.model = "sonnet"
            self.SYSTEM_PROMPT = BATTLE_SYSTEM_PROMPT

        # Continue with normal act() flow
        ...
```

---

## Testing

**`tests/test_agent/test_orchestrator.py`:**
```python
def test_route_to_battle_agent():
    from src.agent import OrchestratorAgent, GameState, BattleState

    state = GameState()
    state.mode = "BATTLE"
    state.battle = BattleState(battle_type="WILD", ...)

    agent = OrchestratorAgent()
    result = agent._route_to_agent({"game_mode": "BATTLE"}, state)

    assert result.result_data["agent"] == "BATTLE"
```

**`tests/test_agent/test_battle.py`:**
```python
def test_type_effectiveness():
    from src.agent import BattleAgent

    agent = BattleAgent()
    result = agent._calculate_type_effectiveness({
        "attack_type": "WATER",
        "defender_types": ["FIRE", "ROCK"],
    }, None)

    assert result.result_data["multiplier"] == 4.0
    assert result.result_data["effectiveness"] == "super_effective"
```

---

## Success Criteria

- [ ] OrchestratorAgent implements all 7 tools
- [ ] NavigationAgent implements all 8 tools
- [ ] BattleAgent implements all 9 tools with Opus escalation
- [ ] MenuAgent implements all 14 tools
- [ ] Each agent has proper system prompts
- [ ] Model selection works correctly (Haiku/Sonnet/Opus)
- [ ] Tool handlers return proper AgentResult objects
- [ ] Agents can hand off to each other via handoff_to field
- [ ] All unit tests pass
- [ ] Integration test: Orchestrator routes correctly based on game mode

---

## Notes

- Full tool schemas are in `docs/05_tool_schemas.md`
- System prompts are in `docs/pokemon_red_agent_prompts.md`
- Some tools require emulator access; mock for unit tests
- The Navigation agent needs Phase 4 (pathfinding) for full functionality
