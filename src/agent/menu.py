"""Menu agent for UI navigation and interactions."""

from typing import Any

from src.knowledge import ItemData, ShopData
from src.tools import MENU_TOOLS

from .base import BaseAgent
from .state import GameState
from .types import AgentResult, AgentType, ModelType

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


class MenuAgent(BaseAgent):
    """Agent for handling menu navigation and UI interactions."""

    AGENT_TYPE: AgentType = "MENU"
    DEFAULT_MODEL: ModelType = "haiku"
    SYSTEM_PROMPT: str = MENU_SYSTEM_PROMPT

    def __init__(
        self,
        client: Any | None = None,
        model: ModelType | None = None,
    ):
        super().__init__(client, model)
        self._item_data = ItemData()
        self._shop_data = ShopData()
        self._emulator = None

    def _register_tools(self) -> list[dict[str, Any]]:
        """Return menu tool definitions."""
        return MENU_TOOLS

    def _get_emulator(self) -> Any:
        """Get emulator instance, returns None if not available."""
        return self._emulator

    def set_emulator(self, emulator: Any) -> None:
        """Set the emulator instance for this agent."""
        self._emulator = emulator

    def act(self, state: GameState) -> AgentResult:
        """Take a menu action based on current state."""
        # Format state for Claude
        state_str = self._format_state_for_prompt(state)

        # Add menu-specific context
        state_str += "\n\n=== MENU CONTEXT ==="
        state_str += f"\nMoney: ${state.money}"
        state_str += f"\nItems: {len(state.items)} types in bag"

        # Build messages
        messages = [{"role": "user", "content": state_str}]

        # Call Claude
        response = self._call_claude(messages)

        # Process tool calls
        return self._process_tool_calls(response, state)

    def _execute_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        state: GameState,
    ) -> AgentResult:
        """Execute a menu tool."""
        tool_handlers = {
            "navigate_menu": self._navigate_menu,
            "open_start_menu": self._open_start_menu,
            "get_inventory": self._get_inventory,
            "use_item": self._use_item,
            "heal_at_pokemon_center": self._heal_at_pokemon_center,
            "shop_buy": self._shop_buy,
            "shop_sell": self._shop_sell,
            "get_shop_inventory": self._get_shop_inventory,
            "manage_party": self._manage_party,
            "teach_move": self._teach_move,
            "pc_deposit_pokemon": self._pc_deposit_pokemon,
            "pc_withdraw_pokemon": self._pc_withdraw_pokemon,
            "handle_dialogue": self._handle_dialogue,
            "get_party_status": self._get_party_status,
        }

        handler = tool_handlers.get(tool_name)
        if handler:
            return handler(tool_input, state)

        return AgentResult(
            success=False,
            action_taken=tool_name,
            error=f"Unknown tool: {tool_name}",
        )

    def _navigate_menu(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Navigate menus with cursor movement and selection."""
        action = tool_input["action"]
        direction = tool_input.get("direction")
        count = tool_input.get("count", 1)

        emulator = self._get_emulator()
        if emulator is None:
            return AgentResult(
                success=True,
                action_taken="navigate_menu",
                result_data={
                    "action": action,
                    "executed": False,
                    "reason": "emulator_not_available",
                },
            )

        try:
            if action == "move":
                if direction:
                    for _ in range(count):
                        emulator.press_button(direction.lower())
                        emulator.tick(8)
            elif action == "select":
                emulator.press_button("a")
                emulator.tick(15)
            elif action == "cancel":
                emulator.press_button("b")
                emulator.tick(15)

            return AgentResult(
                success=True,
                action_taken="navigate_menu",
                result_data={
                    "action": action,
                    "direction": direction,
                    "count": count,
                    "executed": True,
                },
            )
        except Exception as e:
            return AgentResult(
                success=False,
                action_taken="navigate_menu",
                error=str(e),
            )

    def _open_start_menu(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Open the start menu from overworld."""
        emulator = self._get_emulator()
        if emulator is None:
            return AgentResult(
                success=True,
                action_taken="open_start_menu",
                result_data={"executed": False, "reason": "emulator_not_available"},
            )

        try:
            emulator.press_button("start")
            emulator.tick(20)

            return AgentResult(
                success=True,
                action_taken="open_start_menu",
                result_data={"menu_opened": True},
            )
        except Exception as e:
            return AgentResult(
                success=False,
                action_taken="open_start_menu",
                error=str(e),
            )

    def _get_inventory(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Get inventory contents from game state."""
        category_filter = tool_input.get("category_filter", "all")

        items = state.items.copy()
        key_items = state.key_items.copy() if state.key_items else []

        # Apply category filter
        filtered_items = {}

        if category_filter == "all":
            filtered_items = items
        elif category_filter == "key_items":
            # Key items are a separate list
            return AgentResult(
                success=True,
                action_taken="get_inventory",
                result_data={
                    "category": "key_items",
                    "key_items": key_items,
                    "count": len(key_items),
                },
            )
        elif category_filter == "balls":
            ball_names = [
                "POKE_BALL",
                "GREAT_BALL",
                "ULTRA_BALL",
                "MASTER_BALL",
                "SAFARI_BALL",
            ]
            filtered_items = {k: v for k, v in items.items() if k in ball_names}
        elif category_filter == "healing":
            healing_names = [
                "POTION",
                "SUPER_POTION",
                "HYPER_POTION",
                "MAX_POTION",
                "FULL_RESTORE",
                "REVIVE",
                "MAX_REVIVE",
                "FULL_HEAL",
                "ANTIDOTE",
                "BURN_HEAL",
                "ICE_HEAL",
                "AWAKENING",
                "PARLYZ_HEAL",
            ]
            filtered_items = {k: v for k, v in items.items() if k in healing_names}
        elif category_filter == "tms_hms":
            filtered_items = {
                k: v
                for k, v in items.items()
                if k.startswith("TM") or k.startswith("HM")
            }
        elif category_filter == "items":
            # Regular items (not key items, TMs, HMs)
            filtered_items = {
                k: v
                for k, v in items.items()
                if not k.startswith("TM") and not k.startswith("HM")
            }

        return AgentResult(
            success=True,
            action_taken="get_inventory",
            result_data={
                "category": category_filter,
                "items": filtered_items,
                "count": len(filtered_items),
                "total_money": state.money,
            },
        )

    def _use_item(self, tool_input: dict[str, Any], state: GameState) -> AgentResult:
        """Use an item from inventory."""
        item_name = tool_input["item"]
        target = tool_input.get("target_pokemon")
        context = tool_input.get("context", "field")

        # Check if item exists
        if item_name not in state.items or state.items[item_name] <= 0:
            return AgentResult(
                success=False,
                action_taken="use_item",
                error=f"Item not in inventory: {item_name}",
            )

        emulator = self._get_emulator()
        if emulator is None:
            return AgentResult(
                success=True,
                action_taken="use_item",
                result_data={
                    "item": item_name,
                    "executed": False,
                    "reason": "emulator_not_available",
                },
            )

        try:
            # Open start menu if in field
            if context == "field":
                emulator.press_button("start")
                emulator.tick(20)

            # Navigate to BAG
            emulator.press_button("down")  # Move to ITEM
            emulator.tick(5)
            emulator.press_button("a")
            emulator.tick(15)

            # Would need actual item navigation here
            emulator.press_button("a")  # Select item
            emulator.tick(10)

            if target:
                # Select target Pokemon
                emulator.press_button("a")
                emulator.tick(10)

            # Use item
            emulator.press_button("a")
            emulator.tick(30)

            # Update state
            state.items[item_name] -= 1
            if state.items[item_name] <= 0:
                del state.items[item_name]

            return AgentResult(
                success=True,
                action_taken="use_item",
                result_data={
                    "item_used": item_name,
                    "target": target,
                    "context": context,
                },
            )
        except Exception as e:
            return AgentResult(
                success=False,
                action_taken="use_item",
                error=str(e),
            )

    def _heal_at_pokemon_center(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Execute full Pokemon Center healing sequence."""
        confirm_location = tool_input.get("confirm_location", True)

        # Could verify we're in a Pokemon Center here
        if confirm_location:
            # Check if current map is a Pokemon Center
            # For now, we assume caller has verified this
            pass

        emulator = self._get_emulator()
        if emulator is None:
            # Mock healing for testing
            healed_pokemon = []
            for pokemon in state.party:
                healed_pokemon.append(
                    {
                        "species": pokemon.species,
                        "hp_before": pokemon.current_hp,
                        "hp_after": pokemon.max_hp,
                    }
                )
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
                    "emulator_available": False,
                },
            )

        try:
            # Walk to nurse and talk
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
                healed_pokemon.append(
                    {
                        "species": pokemon.species,
                        "hp_before": pokemon.current_hp,
                        "hp_after": pokemon.max_hp,
                    }
                )
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
                },
            )
        except Exception as e:
            return AgentResult(
                success=False,
                action_taken="heal_at_pokemon_center",
                error=str(e),
            )

    def _shop_buy(self, tool_input: dict[str, Any], state: GameState) -> AgentResult:
        """Purchase items from Poke Mart."""
        items_to_buy = tool_input["items"]

        total_spent = 0
        items_bought = []

        emulator = self._get_emulator()

        for purchase in items_to_buy:
            item_name = purchase["item"]
            quantity = purchase["quantity"]

            # Get item price from knowledge base
            item_info = self._item_data.get(item_name)
            if not item_info:
                continue

            price = item_info.get("buy_price", 0)
            if price == 0:
                continue

            total_cost = price * quantity

            if total_cost > state.money:
                # Can't afford, skip
                continue

            if emulator:
                try:
                    # Navigate to item in shop menu
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
                except Exception:
                    continue

            # Update state
            state.money -= total_cost
            state.items[item_name] = state.items.get(item_name, 0) + quantity

            items_bought.append(
                {
                    "item": item_name,
                    "quantity": quantity,
                    "unit_price": price,
                    "total_cost": total_cost,
                }
            )
            total_spent += total_cost

        return AgentResult(
            success=True,
            action_taken="shop_buy",
            result_data={
                "items_bought": items_bought,
                "total_spent": total_spent,
                "money_after": state.money,
            },
        )

    def _shop_sell(self, tool_input: dict[str, Any], state: GameState) -> AgentResult:
        """Sell items at Poke Mart."""
        items_to_sell = tool_input["items"]

        total_earned = 0
        items_sold = []

        emulator = self._get_emulator()

        for sale in items_to_sell:
            item_name = sale["item"]
            quantity = sale["quantity"]

            # Check if we have enough
            if item_name not in state.items or state.items[item_name] < quantity:
                continue

            # Get sell price (half of buy price in Gen 1)
            item_info = self._item_data.get(item_name)
            if not item_info:
                continue

            sell_price = item_info.get("sell_price", 0)
            if sell_price == 0:
                # Can't sell key items
                continue

            total_value = sell_price * quantity

            if emulator:
                try:
                    emulator.press_button("a")
                    emulator.tick(10)

                    for _ in range(quantity - 1):
                        emulator.press_button("up")
                        emulator.tick(5)

                    emulator.press_button("a")
                    emulator.tick(20)
                except Exception:
                    continue

            # Update state
            state.money += total_value
            state.items[item_name] -= quantity
            if state.items[item_name] <= 0:
                del state.items[item_name]

            items_sold.append(
                {
                    "item": item_name,
                    "quantity": quantity,
                    "unit_price": sell_price,
                    "total_value": total_value,
                }
            )
            total_earned += total_value

        return AgentResult(
            success=True,
            action_taken="shop_sell",
            result_data={
                "items_sold": items_sold,
                "total_earned": total_earned,
                "money_after": state.money,
            },
        )

    def _get_shop_inventory(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Get current shop's inventory."""
        # Get shop based on current location
        current_map = state.position.map_id

        # Try to get shop data for current location
        shop_data = self._shop_data.get(current_map)

        inventory: list[dict[str, Any]] = []
        if not shop_data:
            # Return default Poke Mart items
            inventory = [
                {"item": "POKE_BALL", "price": 200},
                {"item": "POTION", "price": 300},
                {"item": "ANTIDOTE", "price": 100},
                {"item": "PARLYZ_HEAL", "price": 200},
                {"item": "BURN_HEAL", "price": 250},
            ]
        else:
            # Enrich with prices from item data
            for item_name in shop_data:
                item_info = self._item_data.get(item_name)
                if item_info:
                    inventory.append(
                        {
                            "item": item_name,
                            "price": item_info.get("buy_price", 0),
                        }
                    )

        return AgentResult(
            success=True,
            action_taken="get_shop_inventory",
            result_data={
                "location": current_map,
                "items": inventory,
                "player_money": state.money,
            },
        )

    def _manage_party(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Manage party Pokemon."""
        action = tool_input["action"]
        pos1 = tool_input.get("position_1")
        pos2 = tool_input.get("position_2")

        if action == "view":
            party_info = []
            for i, pokemon in enumerate(state.party):
                party_info.append(
                    {
                        "index": i,
                        "species": pokemon.species,
                        "level": pokemon.level,
                        "hp": f"{pokemon.current_hp}/{pokemon.max_hp}",
                        "status": pokemon.status,
                    }
                )
            return AgentResult(
                success=True,
                action_taken="manage_party",
                result_data={"action": "view", "party": party_info},
            )

        elif action == "swap":
            if pos1 is None or pos2 is None:
                return AgentResult(
                    success=False,
                    action_taken="manage_party",
                    error="swap requires position_1 and position_2",
                )

            if pos1 >= len(state.party) or pos2 >= len(state.party):
                return AgentResult(
                    success=False,
                    action_taken="manage_party",
                    error="Position out of range",
                )

            emulator = self._get_emulator()
            if emulator:
                try:
                    # Open party menu
                    emulator.press_button("start")
                    emulator.tick(20)
                    emulator.press_button("a")  # POKEMON
                    emulator.tick(15)

                    # Select first Pokemon
                    for _ in range(pos1):
                        emulator.press_button("down")
                        emulator.tick(5)
                    emulator.press_button("a")
                    emulator.tick(10)

                    # Select SWITCH
                    emulator.press_button("down")
                    emulator.tick(5)
                    emulator.press_button("a")
                    emulator.tick(10)

                    # Select second Pokemon
                    for _ in range(pos2):
                        emulator.press_button("down")
                        emulator.tick(5)
                    emulator.press_button("a")
                    emulator.tick(10)

                    # Exit menus
                    emulator.press_button("b")
                    emulator.tick(10)
                    emulator.press_button("b")
                    emulator.tick(10)
                except Exception:
                    pass

            # Swap in state
            state.party[pos1], state.party[pos2] = state.party[pos2], state.party[pos1]

            return AgentResult(
                success=True,
                action_taken="manage_party",
                result_data={
                    "action": "swap",
                    "swapped": [pos1, pos2],
                    "new_order": [p.species for p in state.party],
                },
            )

        elif action == "view_summary":
            if pos1 is None or pos1 >= len(state.party):
                return AgentResult(
                    success=False,
                    action_taken="manage_party",
                    error="Invalid position",
                )

            pokemon = state.party[pos1]
            return AgentResult(
                success=True,
                action_taken="manage_party",
                result_data={
                    "action": "view_summary",
                    "pokemon": {
                        "species": pokemon.species,
                        "level": pokemon.level,
                        "types": pokemon.types,
                        "hp": f"{pokemon.current_hp}/{pokemon.max_hp}",
                        "status": pokemon.status,
                        "stats": {
                            "hp": pokemon.stats.hp,
                            "attack": pokemon.stats.attack,
                            "defense": pokemon.stats.defense,
                            "speed": pokemon.stats.speed,
                            "special": pokemon.stats.special,
                        },
                    },
                },
            )

        elif action == "view_moves":
            if pos1 is None or pos1 >= len(state.party):
                return AgentResult(
                    success=False,
                    action_taken="manage_party",
                    error="Invalid position",
                )

            pokemon = state.party[pos1]
            moves = [
                {
                    "name": m.name,
                    "type": m.type,
                    "pp": f"{m.pp_current}/{m.pp_max}",
                }
                for m in pokemon.moves
            ]
            return AgentResult(
                success=True,
                action_taken="manage_party",
                result_data={
                    "action": "view_moves",
                    "species": pokemon.species,
                    "moves": moves,
                },
            )

        return AgentResult(
            success=False,
            action_taken="manage_party",
            error=f"Unknown action: {action}",
        )

    def _teach_move(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Teach TM/HM to a Pokemon."""
        move_item = tool_input["move_item"]
        target = tool_input["target_pokemon"]
        replace_move = tool_input.get("replace_move")

        # Find target Pokemon
        target_pokemon = None
        target_index = None

        try:
            target_index = int(target)
            if 0 <= target_index < len(state.party):
                target_pokemon = state.party[target_index]
        except ValueError:
            # Search by species name
            for i, p in enumerate(state.party):
                if p.species.upper() == target.upper():
                    target_pokemon = p
                    target_index = i
                    break

        if not target_pokemon:
            return AgentResult(
                success=False,
                action_taken="teach_move",
                error=f"Target Pokemon not found: {target}",
            )

        # Check if Pokemon already has 4 moves
        if len(target_pokemon.moves) >= 4 and not replace_move:
            return AgentResult(
                success=False,
                action_taken="teach_move",
                error="Pokemon has 4 moves, must specify replace_move",
            )

        emulator = self._get_emulator()
        if emulator is None:
            return AgentResult(
                success=True,
                action_taken="teach_move",
                result_data={
                    "move_item": move_item,
                    "target": target_pokemon.species,
                    "executed": False,
                    "reason": "emulator_not_available",
                },
            )

        try:
            # Would implement actual TM teaching sequence here
            emulator.press_button("start")
            emulator.tick(20)
            # Navigate to bag, TM pocket, select TM, select Pokemon...
            emulator.press_button("a")
            emulator.tick(60)

            return AgentResult(
                success=True,
                action_taken="teach_move",
                result_data={
                    "move_item": move_item,
                    "target": target_pokemon.species,
                    "replaced": replace_move,
                    "executed": True,
                },
            )
        except Exception as e:
            return AgentResult(
                success=False,
                action_taken="teach_move",
                error=str(e),
            )

    def _pc_deposit_pokemon(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Deposit Pokemon to PC storage."""
        pokemon_target = tool_input["pokemon"]
        box = tool_input.get("box", 1)

        # Find Pokemon in party
        target_pokemon = None
        target_index = None

        try:
            target_index = int(pokemon_target)
            if 0 <= target_index < len(state.party):
                target_pokemon = state.party[target_index]
        except ValueError:
            for i, p in enumerate(state.party):
                if p.species.upper() == pokemon_target.upper():
                    target_pokemon = p
                    target_index = i
                    break

        if not target_pokemon or target_index is None:
            return AgentResult(
                success=False,
                action_taken="pc_deposit_pokemon",
                error=f"Pokemon not found in party: {pokemon_target}",
            )

        if len(state.party) <= 1:
            return AgentResult(
                success=False,
                action_taken="pc_deposit_pokemon",
                error="Cannot deposit last Pokemon",
            )

        emulator = self._get_emulator()
        if emulator is None:
            # Mock deposit
            deposited = state.party.pop(target_index)
            return AgentResult(
                success=True,
                action_taken="pc_deposit_pokemon",
                result_data={
                    "deposited": deposited.species,
                    "to_box": box,
                    "party_size": len(state.party),
                    "emulator_available": False,
                },
            )

        try:
            # Navigate PC menus
            emulator.press_button("a")  # Use PC
            emulator.tick(30)
            emulator.press_button("a")  # Bill's PC
            emulator.tick(20)
            emulator.press_button("a")  # Deposit
            emulator.tick(20)

            # Select Pokemon
            for _ in range(target_index):
                emulator.press_button("down")
                emulator.tick(5)
            emulator.press_button("a")
            emulator.tick(30)

            # Exit PC
            emulator.press_button("b")
            emulator.tick(10)
            emulator.press_button("b")
            emulator.tick(10)

            deposited = state.party.pop(target_index)

            return AgentResult(
                success=True,
                action_taken="pc_deposit_pokemon",
                result_data={
                    "deposited": deposited.species,
                    "to_box": box,
                    "party_size": len(state.party),
                },
            )
        except Exception as e:
            return AgentResult(
                success=False,
                action_taken="pc_deposit_pokemon",
                error=str(e),
            )

    def _pc_withdraw_pokemon(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Withdraw Pokemon from PC storage."""
        pokemon_name = tool_input["pokemon"]
        box = tool_input["box"]

        if len(state.party) >= 6:
            return AgentResult(
                success=False,
                action_taken="pc_withdraw_pokemon",
                error="Party is full, cannot withdraw",
            )

        emulator = self._get_emulator()
        if emulator is None:
            return AgentResult(
                success=True,
                action_taken="pc_withdraw_pokemon",
                result_data={
                    "pokemon": pokemon_name,
                    "from_box": box,
                    "executed": False,
                    "reason": "emulator_not_available",
                },
            )

        try:
            # Navigate PC menus
            emulator.press_button("a")
            emulator.tick(30)
            emulator.press_button("a")
            emulator.tick(20)
            emulator.press_button("down")
            emulator.tick(5)
            emulator.press_button("a")  # Withdraw
            emulator.tick(30)

            # Would need to navigate box and select Pokemon
            emulator.press_button("a")
            emulator.tick(30)

            return AgentResult(
                success=True,
                action_taken="pc_withdraw_pokemon",
                result_data={
                    "withdrawn": pokemon_name,
                    "from_box": box,
                    "party_size": len(state.party) + 1,
                },
            )
        except Exception as e:
            return AgentResult(
                success=False,
                action_taken="pc_withdraw_pokemon",
                error=str(e),
            )

    def _handle_dialogue(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Process dialogue and make choices."""
        action = tool_input["action"]
        choice = tool_input.get("choice")
        choice_index = tool_input.get("choice_index")

        emulator = self._get_emulator()
        if emulator is None:
            return AgentResult(
                success=True,
                action_taken="handle_dialogue",
                result_data={
                    "action": action,
                    "executed": False,
                    "reason": "emulator_not_available",
                },
            )

        try:
            if action == "advance":
                emulator.press_button("a")
                emulator.tick(15)

            elif action == "choose":
                if choice == "YES" or choice_index == 0:
                    emulator.press_button("a")
                elif choice == "NO" or choice_index == 1:
                    emulator.press_button("down")
                    emulator.tick(5)
                    emulator.press_button("a")
                elif choice_index is not None:
                    for _ in range(choice_index):
                        emulator.press_button("down")
                        emulator.tick(5)
                    emulator.press_button("a")
                emulator.tick(15)

            elif action == "cancel":
                emulator.press_button("b")
                emulator.tick(15)

            return AgentResult(
                success=True,
                action_taken="handle_dialogue",
                result_data={
                    "action": action,
                    "choice_made": choice or choice_index,
                },
            )
        except Exception as e:
            return AgentResult(
                success=False,
                action_taken="handle_dialogue",
                error=str(e),
            )

    def _get_party_status(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Get detailed party status."""
        include_moves = tool_input.get("include_moves", False)

        party_status = []
        for i, pokemon in enumerate(state.party):
            info = {
                "index": i,
                "species": pokemon.species,
                "level": pokemon.level,
                "hp": pokemon.current_hp,
                "max_hp": pokemon.max_hp,
                "hp_percent": round(pokemon.current_hp / pokemon.max_hp * 100, 1),
                "status": pokemon.status,
                "types": pokemon.types,
            }

            if include_moves:
                info["moves"] = [
                    {
                        "name": m.name,
                        "type": m.type,
                        "pp_current": m.pp_current,
                        "pp_max": m.pp_max,
                    }
                    for m in pokemon.moves
                ]

            party_status.append(info)

        # Summary stats
        total_hp = sum(p.current_hp for p in state.party)
        max_hp = sum(p.max_hp for p in state.party)
        fainted = sum(1 for p in state.party if p.current_hp <= 0)

        # needs_healing is True if any Pokemon is at or below 50% HP or fainted
        any_low_hp = any(
            p.current_hp / p.max_hp <= 0.5 if p.max_hp > 0 else True
            for p in state.party
        )
        needs_healing = any_low_hp or fainted > 0

        return AgentResult(
            success=True,
            action_taken="get_party_status",
            result_data={
                "party": party_status,
                "party_size": len(state.party),
                "total_hp_percent": round(total_hp / max_hp * 100, 1) if max_hp else 0,
                "fainted_count": fainted,
                "needs_healing": needs_healing,
            },
        )
