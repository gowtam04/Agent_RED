# Menu Agent

## Model Configuration

| Setting | Value |
|---------|-------|
| **Model** | `claude-haiku-4-5-20251001` |
| **Reasoning** | Low complexity, procedural operations |
| **Call Frequency** | ~200/hour (healing, shopping, party management) |
| **Latency Tolerance** | Medium (menus aren't time-sensitive) |

**Why Haiku:** Menu operations are almost entirely procedural—navigate to position, select item, confirm. The "decisions" (what to buy, who to heal) are simple threshold checks. Haiku handles this easily at lower cost.

**Optimization Note:** Many menu operations could be hardcoded sequences. Haiku is primarily useful for handling unexpected dialogue or menu states gracefully.

---

## Overview

The Menu Agent handles all non-combat interactions in Pokemon Red, including inventory management, party management, shopping, healing at Pokemon Centers, PC storage, and dialogue with NPCs. It operates whenever the game is in a menu state or dialogue state.

## Responsibilities

1. **Healing** - Use Pokemon Centers and healing items
2. **Shopping** - Buy and sell items at Poke Marts
3. **Inventory Management** - Organize and use items
4. **Party Management** - Reorder party, manage PC storage
5. **Move Management** - Teach TMs/HMs, forget moves
6. **Dialogue Handling** - Parse NPC dialogue and make choices
7. **PC Operations** - Deposit/withdraw Pokemon and items

---

## Menu State Schema

```python
@dataclass 
class MenuState:
    # Menu Location
    menu_type: MenuType     # START_MENU, BAG, PARTY, PC, SHOP, DIALOGUE
    submenu: Optional[str]  # Current submenu if any
    cursor_position: int    # Current selection
    
    # Inventory
    inventory: dict         # {item_name: quantity}
    bag_pocket: str         # ITEMS, KEY_ITEMS, BALLS (Gen 1 has one bag)
    
    # Party Info
    party: list[Pokemon]
    
    # Shop Info (when in shop)
    shop_inventory: Optional[list]
    player_money: int
    
    # Dialogue Info (when in dialogue)
    dialogue_text: str
    dialogue_choices: Optional[list[str]]


class MenuType(Enum):
    START_MENU = "start_menu"
    BAG = "bag"
    PARTY = "party"
    POKEMON_SUMMARY = "pokemon_summary"
    PC = "pc"
    PC_POKEMON = "pc_pokemon"
    PC_ITEMS = "pc_items"
    SHOP = "shop"
    DIALOGUE = "dialogue"
    YES_NO = "yes_no"
    MOVE_LEARN = "move_learn"
    NICKNAME = "nickname"
```

---

## Tools

### 1. `navigate_menu`

Navigates through menu options.

**Input:**
```python
{
    "direction": "DOWN",  # UP, DOWN, LEFT, RIGHT
    "count": 1,           # Number of times to press
}
# OR
{
    "select": True        # Press A to select
}
# OR
{
    "cancel": True        # Press B to go back
}
```

**Output:**
```python
{
    "new_cursor_position": 2,
    "current_selection": "POKéMON",
    "menu_changed": False
}
```

---

### 2. `open_start_menu`

Opens the start menu from overworld.

**Input:** None

**Output:**
```python
{
    "menu_opened": True,
    "options": ["POKéDEX", "POKéMON", "ITEM", "TRAINER", "SAVE", "OPTION"]
}
```

---

### 3. `get_inventory`

Returns current inventory state.

**Input:** None

**Output:**
```python
{
    "items": {
        "POTION": 5,
        "SUPER_POTION": 2,
        "ANTIDOTE": 3,
        "POKE_BALL": 10,
        "GREAT_BALL": 5,
        "ESCAPE_ROPE": 1,
        "REPEL": 3
    },
    "key_items": [
        "BICYCLE",
        "TOWN_MAP",
        "SS_TICKET"
    ],
    "hms_tms": {
        "HM01": "CUT",
        "TM28": "DIG"
    },
    "total_slots_used": 15,
    "max_slots": 20
}
```

---

### 4. `use_item`

Uses an item from inventory.

**Input:**
```python
{
    "item": "SUPER_POTION",
    "target": "PIKACHU"  # Pokemon name or party index
}
# OR for field items
{
    "item": "ESCAPE_ROPE",
    "target": None
}
# OR for HMs
{
    "item": "HM01",      # CUT
    "target": "field"   # Use in overworld on tree
}
```

**Output:**
```python
{
    "success": True,
    "effect": "PIKACHU HP restored by 50",
    "remaining": 1  # Items left
}
```

---

### 5. `heal_at_pokemon_center`

Executes the full Pokemon Center healing sequence.

**Input:** None (assumes player is in Pokemon Center)

**Output:**
```python
{
    "success": True,
    "party_healed": True,
    "pokemon_restored": [
        {"name": "PIKACHU", "hp_before": 23, "hp_after": 55},
        {"name": "CHARIZARD", "hp_before": 89, "hp_after": 150}
    ],
    "pp_restored": True,
    "status_cured": ["PIKACHU"]  # Was poisoned
}
```

---

### 6. `shop_buy`

Purchases items from a Poke Mart.

**Input:**
```python
{
    "items": [
        {"item": "SUPER_POTION", "quantity": 5},
        {"item": "GREAT_BALL", "quantity": 10}
    ]
}
```

**Output:**
```python
{
    "success": True,
    "items_bought": [
        {"item": "SUPER_POTION", "quantity": 5, "cost": 3500},
        {"item": "GREAT_BALL", "quantity": 10, "cost": 6000}
    ],
    "total_cost": 9500,
    "money_remaining": 15230
}
```

---

### 7. `shop_sell`

Sells items to a Poke Mart.

**Input:**
```python
{
    "items": [
        {"item": "NUGGET", "quantity": 1},
        {"item": "ANTIDOTE", "quantity": 5}
    ]
}
```

**Output:**
```python
{
    "success": True,
    "items_sold": [
        {"item": "NUGGET", "quantity": 1, "value": 5000},
        {"item": "ANTIDOTE", "quantity": 5, "value": 500}
    ],
    "total_earned": 5500,
    "money_now": 20730
}
```

---

### 8. `get_shop_inventory`

Returns what's available at the current shop.

**Input:** None (reads from current shop)

**Output:**
```python
{
    "shop_location": "CERULEAN_CITY",
    "items_available": [
        {"item": "POKE_BALL", "price": 200},
        {"item": "SUPER_POTION", "price": 700},
        {"item": "ANTIDOTE", "price": 100},
        {"item": "PARLYZ_HEAL", "price": 200},
        {"item": "AWAKENING", "price": 250},
        {"item": "REPEL", "price": 350}
    ],
    "player_money": 24730
}
```

---

### 9. `manage_party`

Reorders or views party Pokemon.

**Input:**
```python
{
    "action": "SWAP",
    "position_1": 0,  # Lead Pokemon
    "position_2": 3   # 4th Pokemon
}
# OR
{
    "action": "VIEW_SUMMARY",
    "position": 2
}
```

**Output:**
```python
{
    "success": True,
    "new_party_order": ["CHARIZARD", "PIKACHU", "ALAKAZAM", "BLASTOISE", "SNORLAX", "LAPRAS"]
}
```

---

### 10. `teach_move`

Teaches a TM or HM to a Pokemon.

**Input:**
```python
{
    "move_item": "HM01",  # CUT
    "target_pokemon": "BULBASAUR",
    "replace_move": "TACKLE"  # Optional, if all 4 slots full
}
```

**Output:**
```python
{
    "success": True,
    "pokemon": "BULBASAUR",
    "learned": "CUT",
    "forgot": "TACKLE",
    "tm_consumed": False  # HMs aren't consumed
}
```

---

### 11. `pc_deposit_pokemon`

Deposits a Pokemon into the PC.

**Input:**
```python
{
    "pokemon": "RATTATA",  # Name or party index
    "box": 1               # Box number (1-12)
}
```

**Output:**
```python
{
    "success": True,
    "pokemon_deposited": "RATTATA",
    "box": 1,
    "box_space_remaining": 19
}
```

---

### 12. `pc_withdraw_pokemon`

Withdraws a Pokemon from the PC.

**Input:**
```python
{
    "pokemon": "GYARADOS",
    "box": 3
}
```

**Output:**
```python
{
    "success": True,
    "pokemon_withdrawn": "GYARADOS",
    "party_size": 5
}
```

---

### 13. `handle_dialogue`

Processes dialogue and makes choices when needed.

**Input:**
```python
{
    "action": "ADVANCE"  # Press A to continue
}
# OR
{
    "action": "CHOOSE",
    "choice": "YES"  # or "NO", or choice index
}
```

**Output:**
```python
{
    "dialogue_complete": False,
    "current_text": "Would you like to trade your ABRA for my MR. MIME?",
    "choices": ["YES", "NO"],
    "awaiting_choice": True
}
```

---

## Item Knowledge Base

```python
HEALING_ITEMS = {
    "POTION": {"hp_restore": 20, "price": 300, "sell": 150},
    "SUPER_POTION": {"hp_restore": 50, "price": 700, "sell": 350},
    "HYPER_POTION": {"hp_restore": 200, "price": 1200, "sell": 600},
    "MAX_POTION": {"hp_restore": "full", "price": 2500, "sell": 1250},
    "FULL_RESTORE": {"hp_restore": "full", "status_cure": "all", "price": 3000, "sell": 1500}
}

STATUS_ITEMS = {
    "ANTIDOTE": {"cures": "POISON", "price": 100},
    "BURN_HEAL": {"cures": "BURN", "price": 250},
    "ICE_HEAL": {"cures": "FREEZE", "price": 250},
    "AWAKENING": {"cures": "SLEEP", "price": 250},
    "PARLYZ_HEAL": {"cures": "PARALYSIS", "price": 200},
    "FULL_HEAL": {"cures": "all", "price": 600}
}

POKEBALLS = {
    "POKE_BALL": {"catch_rate_mod": 1.0, "price": 200},
    "GREAT_BALL": {"catch_rate_mod": 1.5, "price": 600},
    "ULTRA_BALL": {"catch_rate_mod": 2.0, "price": 1200},
    "MASTER_BALL": {"catch_rate_mod": 255, "price": None}  # Can't buy
}

VALUABLE_ITEMS = {
    "NUGGET": {"sell": 5000},
    "STAR_PIECE": {"sell": 4900},
    "RARE_CANDY": {"sell": 2400, "note": "Don't sell, use for leveling"}
}

REPELS = {
    "REPEL": {"steps": 100, "price": 350},
    "SUPER_REPEL": {"steps": 200, "price": 500},
    "MAX_REPEL": {"steps": 250, "price": 700}
}
```

---

## Shop Data by Location

```python
SHOP_INVENTORY = {
    "VIRIDIAN_CITY": {
        "before_badge": ["POKE_BALL", "ANTIDOTE", "PARLYZ_HEAL", "POTION"],
        "after_badge": ["POKE_BALL", "GREAT_BALL", "SUPER_POTION", "ANTIDOTE", "PARLYZ_HEAL", "BURN_HEAL", "ESCAPE_ROPE", "REPEL"]
    },
    "PEWTER_CITY": ["POKE_BALL", "POTION", "ANTIDOTE", "BURN_HEAL", "AWAKENING", "PARLYZ_HEAL"],
    "CERULEAN_CITY": ["POKE_BALL", "SUPER_POTION", "ANTIDOTE", "BURN_HEAL", "AWAKENING", "PARLYZ_HEAL", "REPEL"],
    "VERMILION_CITY": ["POKE_BALL", "SUPER_POTION", "ANTIDOTE", "BURN_HEAL", "AWAKENING", "PARLYZ_HEAL", "REPEL"],
    # ... all cities
    "INDIGO_PLATEAU": ["ULTRA_BALL", "GREAT_BALL", "FULL_RESTORE", "MAX_POTION", "FULL_HEAL", "REVIVE", "MAX_REPEL"]
}
```

---

## Decision Logic

### Healing Decision

```python
def should_heal(game_state: GameState) -> bool:
    """Determine if we should visit Pokemon Center or use items."""
    party = game_state.party
    
    # Calculate party health
    total_hp_percent = sum(p.current_hp / p.max_hp for p in party if p.current_hp > 0) / len(party)
    
    # Count fainted Pokemon
    fainted = sum(1 for p in party if p.current_hp == 0)
    
    # Check for status conditions
    status_count = sum(1 for p in party if p.status is not None)
    
    # Check PP levels
    low_pp = any(
        all(m.pp_current < 3 for m in p.moves)
        for p in party if p.current_hp > 0
    )
    
    # Decision
    if fainted >= 2:
        return True  # Too many fainted
    if total_hp_percent < 0.4:
        return True  # Party too weak
    if fainted >= 1 and status_count >= 2:
        return True  # Bad shape overall
    if low_pp:
        return True  # Running out of moves
    
    return False


def heal_method(game_state: GameState) -> str:
    """Decide HOW to heal: Pokemon Center or items."""
    
    # How far is the nearest Pokemon Center?
    pc_distance = distance_to_nearest_pokemon_center(game_state.location)
    
    # Can we heal with items?
    can_heal_with_items = (
        count_item("POTION") + count_item("SUPER_POTION") >= 3
    )
    
    # If Pokemon Center is close, always use it (free!)
    if pc_distance < 20:
        return "POKEMON_CENTER"
    
    # If we're deep in a dungeon, use items
    if in_dungeon(game_state.location) and can_heal_with_items:
        return "ITEMS"
    
    # If we have plenty of items and PC is far, use items
    if pc_distance > 100 and can_heal_with_items:
        return "ITEMS"
    
    # Default to Pokemon Center
    return "POKEMON_CENTER"
```

### Shopping Decision

```python
def decide_shopping_list(game_state: GameState) -> list:
    """Determine what to buy at a shop."""
    inventory = game_state.inventory
    money = game_state.money
    shopping_list = []
    
    # Priority 1: Pokeballs (if we need to catch things)
    if inventory.get("POKE_BALL", 0) < 5:
        shopping_list.append({"item": "POKE_BALL", "quantity": 10})
    
    # Priority 2: Healing items
    potions = inventory.get("POTION", 0) + inventory.get("SUPER_POTION", 0)
    if potions < 5:
        if "SUPER_POTION" in current_shop_items():
            shopping_list.append({"item": "SUPER_POTION", "quantity": 5})
        else:
            shopping_list.append({"item": "POTION", "quantity": 10})
    
    # Priority 3: Status heals
    if inventory.get("ANTIDOTE", 0) < 3:
        shopping_list.append({"item": "ANTIDOTE", "quantity": 5})
    
    # Priority 4: Repels (for late game)
    if game_state.badges >= 4 and inventory.get("REPEL", 0) < 3:
        if "SUPER_REPEL" in current_shop_items():
            shopping_list.append({"item": "SUPER_REPEL", "quantity": 5})
    
    # Trim list to what we can afford
    return trim_to_budget(shopping_list, money)


def should_sell_items(inventory: dict) -> list:
    """Determine what items to sell."""
    to_sell = []
    
    # Always sell valuables
    for item in ["NUGGET", "STAR_PIECE"]:
        if item in inventory:
            to_sell.append({"item": item, "quantity": inventory[item]})
    
    # Sell excess basic items
    if inventory.get("POTION", 0) > 10:
        to_sell.append({"item": "POTION", "quantity": inventory["POTION"] - 5})
    
    if inventory.get("ANTIDOTE", 0) > 10:
        to_sell.append({"item": "ANTIDOTE", "quantity": inventory["ANTIDOTE"] - 5})
    
    return to_sell
```

### HM Teaching Decision

```python
def choose_hm_pokemon(hm: str, party: list[Pokemon]) -> Optional[Pokemon]:
    """Choose which Pokemon should learn an HM."""
    
    hm_move = HM_MOVES[hm]  # e.g., "CUT", "SURF", etc.
    
    compatible = [p for p in party if can_learn_move(p.species, hm_move)]
    
    if not compatible:
        return None  # Need to catch something
    
    # Prefer Pokemon that are already "HM slaves"
    hm_slaves = [p for p in compatible if is_hm_slave(p)]
    if hm_slaves:
        return hm_slaves[0]
    
    # Prefer weaker Pokemon (don't waste move slots on your best)
    compatible.sort(key=lambda p: calculate_combat_value(p))
    
    # For SURF specifically, prefer Water types (STAB)
    if hm_move == "SURF":
        water_types = [p for p in compatible if "WATER" in p.types]
        if water_types:
            return water_types[0]
    
    return compatible[0]  # Weakest compatible Pokemon


def is_hm_slave(pokemon: Pokemon) -> bool:
    """Check if Pokemon is primarily used for HMs."""
    hm_moves = ["CUT", "FLY", "SURF", "STRENGTH", "FLASH"]
    known_hm_moves = sum(1 for m in pokemon.moves if m.name in hm_moves)
    return known_hm_moves >= 2
```

---

## Menu Flow Control

```python
def menu_agent_loop(task: MenuTask):
    """Main loop when Menu Agent has control."""
    
    if task.type == "HEAL_POKEMON_CENTER":
        # Navigate to nurse
        navigate_to_nurse()
        # Interact
        handle_dialogue({"action": "ADVANCE"})  # "Welcome..."
        handle_dialogue({"action": "CHOOSE", "choice": "YES"})  # "Heal Pokemon?"
        # Wait for healing jingle
        wait_for_healing_complete()
        handle_dialogue({"action": "ADVANCE"})  # "Your Pokemon are healed!"
        return {"status": "COMPLETE"}
    
    elif task.type == "BUY_ITEMS":
        # Navigate to clerk
        navigate_to_clerk()
        handle_dialogue({"action": "ADVANCE"})  # "Welcome..."
        handle_dialogue({"action": "CHOOSE", "choice": "BUY"})
        
        # Buy each item
        for item in task.items:
            select_item_in_shop(item["item"])
            select_quantity(item["quantity"])
            confirm_purchase()
        
        # Exit shop
        handle_dialogue({"action": "CHOOSE", "choice": "QUIT"})
        return {"status": "COMPLETE", "items_bought": task.items}
    
    elif task.type == "TEACH_HM":
        open_start_menu()
        navigate_to("ITEM")
        select_item(task.hm)
        select_party_member(task.target_pokemon)
        
        if task.replace_move:
            confirm_replace(task.replace_move)
        
        return {"status": "COMPLETE", "move_learned": task.hm}
    
    elif task.type == "MANAGE_PARTY":
        open_start_menu()
        navigate_to("POKéMON")
        perform_party_action(task.action)
        close_menu()
        return {"status": "COMPLETE"}
    
    # ... other task types
```

---

## Dialogue Handling

### Key NPC Dialogues

```python
NPC_DIALOGUES = {
    "POKEMON_CENTER_NURSE": {
        "prompt": "Your POKéMON are tired",
        "choice_expected": True,
        "correct_choice": "YES"
    },
    "POKEMART_CLERK": {
        "prompt": "How may I help you?",
        "choices": ["BUY", "SELL", "QUIT"],
        "context_dependent": True  # Choice depends on what we need
    },
    "BILL_AFTER_RESCUE": {
        "prompt": "Thanks for saving me!",
        "gives_item": "SS_TICKET",
        "choice_expected": False
    }
}

def handle_story_dialogue(npc_id: str, dialogue_state):
    """Handle known story-important dialogues."""
    npc_data = NPC_DIALOGUES.get(npc_id)
    
    if npc_data and npc_data.get("choice_expected"):
        if dialogue_state.awaiting_choice:
            return {"action": "CHOOSE", "choice": npc_data["correct_choice"]}
    
    # Default: just advance
    return {"action": "ADVANCE"}
```

---

## Integration Points

### ← Orchestrator Provides
- Task type (heal, shop, teach, etc.)
- Specific parameters (what to buy, what to teach)

### → Returns to Orchestrator
- Task completion status
- Resources changed (money spent, items gained/used)
- State changes (party order, moves learned)

### ← Navigation Agent May Request
- "Use HM Cut" - Menu Agent uses the HM in the field
- "Use item" - Menu Agent uses field items like Escape Rope

### ← Battle Agent May Request
- Mid-battle item use (handled by Battle Agent directly)
- Post-battle party reorder

---

## Error Handling

```python
def handle_menu_error(error_type: str, context: dict):
    """Handle menu navigation errors."""
    
    if error_type == "ITEM_NOT_FOUND":
        return {"status": "FAILED", "reason": f"Item {context['item']} not in inventory"}
    
    if error_type == "NOT_ENOUGH_MONEY":
        return {"status": "FAILED", "reason": "Insufficient funds", "need": context["cost"]}
    
    if error_type == "PARTY_FULL":
        return {"status": "FAILED", "reason": "Cannot withdraw, party is full"}
    
    if error_type == "CANNOT_LEARN_MOVE":
        return {"status": "FAILED", "reason": f"{context['pokemon']} cannot learn {context['move']}"}
    
    if error_type == "MENU_STUCK":
        # Try to back out
        for _ in range(5):
            navigate_menu({"cancel": True})
        return {"status": "RECOVERED"}
```
